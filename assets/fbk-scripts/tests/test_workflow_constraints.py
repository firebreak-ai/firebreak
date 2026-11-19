"""Every rule the runtime enforces on a reviewer's response is registered once, stated in
the prompt the real assembler builds, and named at the site that rejects it."""

import ast
import importlib
import inspect
import json
import re
from pathlib import Path

import pytest
from fbk.workflow import (
    constraints,
    council,
    investigations,
    remediation_verification as remediation,
    repair,
    review,
    review_contributors as contributors,
    review_rounds as rounds,
    store,
)
from tests.test_workflow_commands import call
from tests.test_workflow_managed_investigations import host
from tests.test_workflow_remediation_verification import (  # noqa: F401 — fixture reuse
    declaration,
    followup,
    setup,
    worker,
)
from tests.test_workflow_review import assessor, at_spec, choose, finding, project  # noqa: F401


def complete_context(cwd):
    return {
        "status": "complete",
        "inspected_files": sorted(p.relative_to(cwd).as_posix() for p in cwd.rglob("*") if p.is_file()),
        "supporting_files": [],
        "missing_context": [],
    }


def stage_of(argv):
    schema = json.loads(argv[argv.index("--json-schema") + 1])
    props = schema["properties"]
    for key, stage in (("assessments", "adjudication"), ("comment", "turn"),
                       ("stances", "stance"), ("consensus", "final")):
        if key in props:
            return stage, schema
    return "member", schema


def enum_of(node):
    return node.get("enum", [])


def packet_of(prompt):
    return json.loads(next(line for line in prompt.splitlines() if line.startswith("{")))


def assert_stated(prompt, block):
    """Every rendered sentence of the block appears in the prompt, and the block is
    present as one JSON structure rather than scattered sentences."""
    for item in constraints.rules(block):
        assert item["rule"] in prompt, item["id"]
    assert block["preamble"] in prompt


def reviewer_stub(prompts):
    def command(argv, cwd, timeout, prompt):
        stage, schema = stage_of(argv)
        prompts.setdefault(stage, []).append((prompt, schema, timeout))
        context = complete_context(cwd)
        if stage == "member":
            return host({"summary": "Inspected the sources.", "findings": [{**finding(), "severity": "suggestion"}],
                         "context": context})
        if stage == "turn":
            return host({"comment": "Nothing to add.", "responses": [], "proposals": [], "context": context})
        if stage == "stance":
            ids = enum_of(schema["properties"]["stances"]["items"]["properties"]["proposal"])
            return host({"stances": [{"proposal": i, "stance": "support", "reason": ""} for i in ids],
                         "context": context})
        if stage == "final":
            ids = enum_of(schema["properties"]["findings"]["items"]["properties"]["proposal"])
            return host({"summary": "The corrections stand.", "consensus": [], "dropped": [],
                         "findings": [{"proposal": i, "finding": {**finding(), "severity": "suggestion"},
                                       "dissent": ""} for i in ids], "context": context})
        ids = schema["properties"]["assessments"]["items"]["properties"]["finding_id"]["enum"]
        assessment = assessor(ids, canonical=stage == "adjudication")["review"]
        for item in assessment["assessments"]:
            if item.get("finding"):
                item["finding"]["severity"] = "suggestion"
        return host({**assessment, "context": context})
    return command


def review_held(root):
    """Run the spec review; its suggestion holds the phase for the author's sort."""
    with pytest.raises(store.WorkflowError, match="Review passed with"):
        call(root, "phase-close", "spec", "feature")


def managed_config(root, **overrides):
    return {**store.project_config(root), **overrides, "_managed_project_root": str(root)}


# ---------------------------------------------------------------------------
# Test one: every applicable entry is stated in the prompt the real assembler builds.


def test_single_review_packet_carries_the_registry_block(project, monkeypatch):
    at_spec(project)
    choose(project, "single")
    prompts = {}
    monkeypatch.setattr(review, "run_command", reviewer_stub(prompts))
    review_held(project)
    [(prompt, schema, _)] = prompts["member"]
    packet = packet_of(prompt)
    expected = constraints.render("review", managed_config(project), review.SCHEMA)
    assert packet["rules"] == expected
    keys = list(packet)
    assert keys.index("rules") == keys.index("required_files") + 1
    assert_stated(prompt, expected)
    # The reader is managed, so the investigation and authorization groups are present.
    assert {"investigation-request", "authorization", "budgets"} <= set(expected)


def test_every_council_session_states_its_own_block(project, monkeypatch):
    at_spec(project)
    choose(project, "council", members=["architect", "builder"])
    prompts = {}
    monkeypatch.setattr(review, "run_command", reviewer_stub(prompts))
    review_held(project)
    config = managed_config(project)
    ids = ["architect:1", "builder:1"]
    expected = {
        "member": constraints.render("council-member", config, council.CANDIDATE_SCHEMA),
        "turn": constraints.render("council-turn", config, council.turn_contract(ids, [])[0]),
        "stance": constraints.render("council-stance", config, council.stance_contract(ids)[0]),
        "final": constraints.render("council-final", config,
                                    council.final_contract(dict.fromkeys(ids, "suggestion"), [])[0]),
    }
    assert {stage: len(found) for stage, found in prompts.items()} == {
        "member": 2, "turn": 2, "stance": 2, "final": 1}
    for stage, block in expected.items():
        for prompt, _, _ in prompts[stage]:
            assert packet_of(prompt)["rules"] == block, stage
            assert_stated(prompt, block)
    turn_rules = {r["id"] for r in constraints.rules(expected["turn"])}
    assert {"turn-responses", "turn-replacements", "finding-fields"} <= turn_rules
    stance_rules = {r["id"] for r in constraints.rules(expected["stance"])}
    assert {"stance-every-proposal", "count-rule", "stance-incomplete-context"} <= stance_rules
    assert "incomplete-context-is-a-verdict" not in stance_rules
    assert "finding-fields" not in stance_rules
    final_rules = {r["id"] for r in constraints.rules(expected["final"])}
    assert {"final-findings-match", "final-dropped-match"} <= final_rules


@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {"review_timeout": 777, "reviewer_max_turns": 42, "investigation_max_attempts": 5,
         "investigation_timeout": 90},
    ],
)
def test_rendered_numbers_track_configuration(project, monkeypatch, overrides):
    config_path = project / ".fbk/config.json"
    store.atomic_json(config_path, {**json.loads(config_path.read_text()), **overrides})
    at_spec(project)
    choose(project, "single")
    prompts = {}
    monkeypatch.setattr(review, "run_command", reviewer_stub(prompts))
    review_held(project)
    [(prompt, _, timeout)] = prompts["member"]
    rules = {r["id"]: r["rule"] for r in constraints.rules(packet_of(prompt)["rules"])}
    seconds = overrides.get("review_timeout", 1200)
    turns = overrides.get("reviewer_max_turns", 100)
    attempts = overrides.get("investigation_max_attempts", 3)
    per_question = overrides.get("investigation_timeout", 600)
    assert f"stopped after {seconds} seconds (the configured review_timeout)" in rules["session-time-limit"]
    assert timeout == seconds
    assert f"at most {turns} turns (the configured reviewer_max_turns)" in rules["turn-ceiling"]
    assert f"at most {attempts} attempts and {per_question} seconds" in rules["investigation-budgets"]
    # The numbers come from the same readings the validators use.
    assert investigations._positive(overrides, "investigation_max_attempts", 3) == attempts
    assert review.bounded_number(overrides, "review_timeout", 1200, 86400) == seconds
    assert investigations._positive(overrides, "reviewer_max_turns", 100) == turns


def test_contributor_prompt_carries_the_registry_block(tmp_path, monkeypatch):
    (tmp_path / "app.py").write_text("answer=42\n")
    record = rounds.begin(tmp_path, ["reader"], "Check answer=42", {})
    captured = {}

    def session(root, prompt, config, **kwargs):
        captured["prompt"], captured["config"] = prompt, config
        return {"review": {"result": []}, "seconds": 1}

    monkeypatch.setattr(review, "_claude_session", session)
    contributors.run(tmp_path, record["id"], ["reader"])
    expected = constraints.render("contributor", captured["config"], contributors.SCHEMA)
    assert_stated(captured["prompt"], expected)
    ids = {r["id"] for r in constraints.rules(expected)}
    assert {"contributor-result", "contributor-incomplete-context", "managed-response-shape"} <= ids
    assert "result, context" in next(r["rule"] for r in constraints.rules(expected) if r["id"] == "response-properties")
    assert captured["prompt"].index("required_files:") < captured["prompt"].index("rules:")


def test_repair_verifier_prompt_carries_the_registry_block(project, monkeypatch):
    (project / "notes.md").write_text("Cancel returns false once.\n")
    (project / "decisions.md").write_text("Cancel returns true once.\n")
    captured = {}

    def session(root, prompt, config, *, schema, validator):
        captured.update(prompt=prompt, config=config, schema=schema)
        return {"review": {"status": "equivalent", "evidence": "Restates the decision."},
                "context": complete_context(root), "seconds": 1}

    monkeypatch.setattr(review, "claude_review", session)
    packet = {"kind": "contradiction", "path": "notes.md", "before": "false", "after": "true",
              "decision_id": "cancel", "original_hash": "0" * 64,
              "decision": {"id": "cancel", "source": {"path": "decisions.md", "hash": "0" * 64}}}
    assert repair._verify(project, packet)["status"] == "equivalent"
    expected = constraints.render("repair-verifier", captured["config"], captured["schema"])
    assert_stated(captured["prompt"], expected)
    ids = {r["id"] for r in constraints.rules(expected)}
    assert {"repair-verdict", "repair-not-applied", "repair-incomplete-context", "required-files-declared"} <= ids
    assert "investigation-request" not in expected  # a standalone session has no investigation protocol
    assert "evidence at most 2000 characters" in next(r["rule"] for r in constraints.rules(expected) if r["id"] == "length-budgets")


def test_remediation_verifier_prompt_carries_the_registry_block(setup, monkeypatch):
    root, first = setup
    declaration(root, first)
    post = followup(root, first)
    captured = {}

    def capturing(argv, cwd, timeout, prompt=None):
        captured["prompt"] = prompt
        return worker(argv, cwd, timeout, prompt)

    monkeypatch.setattr(investigations, "run_command", capturing)
    assert remediation.verify(root, post["id"], "square-fix")["status"] == "verified"
    configuration = rounds.load_round(root, post["id"])["configuration"]
    expected = constraints.render("remediation-verifier", configuration)
    assert_stated(captured["prompt"], expected)
    ids = {r["id"] for r in constraints.rules(expected)}
    assert ids == {"worker-limits", "remediation-report-identity", "remediation-report-fields",
                   "remediation-evidence-quote", "remediation-verified-proof",
                   "remediation-rejected-verdict"}


def test_spec_trim_prompt_carries_the_registry_block(project, monkeypatch):
    from fbk.workflow import spec_trim

    monkeypatch.undo()  # the real launch, in place of the suite's session that cuts nothing
    captured = {}

    def host(argv, cwd, timeout, prompt=None):
        captured["prompt"] = prompt
        return {"exit_code": 0, "stderr": "", "stdout": json.dumps({"subtype": "success", "structured_output": {"removed": []}})}

    monkeypatch.setattr(review, "run_command", host)
    assert spec_trim.launch(project, "feature", [], {}) == []
    expected = constraints.render("spec-trim", {}, spec_trim.SCHEMA)
    assert_stated(captured["prompt"], expected)
    assert {r["id"] for r in constraints.rules(expected)} == {
        "trim-edit-scope", "trim-removed-list", "trim-limits", "trim-result-checks"}


def test_standalone_session_states_no_investigation_rules():
    block = constraints.render("review", {}, review.SCHEMA)
    assert "investigation" not in json.dumps(block)
    managed = constraints.render("review", {"_managed_project_root": "/x"}, review.SCHEMA)
    assert {"investigation-request", "authorization", "budgets"} <= set(managed)


def test_registry_entries_are_well_formed():
    ids = [entry.id for entry in constraints.REGISTRY]
    assert len(ids) == len(set(ids))
    for entry in constraints.REGISTRY:
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", entry.id), entry.id
        assert entry.applies_to and entry.applies_to <= set(constraints.KINDS), entry.id
        if entry.enforced_by is None:
            assert entry.note, f"{entry.id} is unenforced and needs a note saying why"
        else:
            for reference in entry.enforced_by:
                module_name, function_name = reference.rsplit(".", 1)
                module = importlib.import_module(f"fbk.workflow.{module_name}")
                assert callable(getattr(module, function_name)), reference
        if entry.managed:
            assert entry.applies_to <= constraints.MANAGED, entry.id
    for kind in constraints.KINDS:
        assert constraints.applicable(kind, {"_managed_project_root": "/x"}), kind


# ---------------------------------------------------------------------------
# Test two: every rejection site inside a validator names a registered rule.

VALIDATORS = {
    "review": ("validate_review", "validate_single", "wire_contract", "length_budgets", "_claude_session"),
    "review_context": ("validate_context", "incomplete_context"),
    "council": ("validate_candidates", "assessment_contract", "adjudicate", "turn_contract",
                "stance_contract", "final_contract", "_finding_ok"),
    "investigations": ("validate_request", "_authorization", "_refuse"),
    "managed_investigations": ("_correction", "run_reader"),
    "repair": ("_verify",),
    "remediation_verification": ("_validate", "_evidence"),
    "review_contributors": ("_validate",),
    "spec_trim": ("_parse", "_check"),
}
# Registry targets that orchestrate a stage: their judgments of model output are marked, but
# their other raises guard state and preconditions, so they are not held to the marker rule.
ORCHESTRATORS = {
    "review": ("run_command",),
    "investigations": ("run",),
    "remediation_verification": ("verify",),
    "repair": ("apply",),
    "review_contributors": ("_worker",),
}
MARKER = re.compile(r"#\s*constraint:\s*(\S+)(?:\s+(.*))?$")


def _module_source(module_name):
    module = importlib.import_module(f"fbk.workflow.{module_name}")
    source = inspect.getsource(module)
    return source.splitlines(), ast.parse(source)


def _function(tree, name):
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)


def _sites(module_name, function_name):
    """Every marker inside the function, and every raise that carries an exception."""
    lines, tree = _module_source(module_name)
    node = _function(tree, function_name)
    markers = {}
    for lineno in range(node.lineno, node.end_lineno + 1):
        match = MARKER.search(lines[lineno - 1])
        if match:
            markers[lineno] = (match.group(1), (match.group(2) or "").strip())
    raises = [sub.lineno for sub in ast.walk(node) if isinstance(sub, ast.Raise) and sub.exc is not None]
    return markers, raises


def test_every_marker_in_the_package_names_a_registered_rule():
    package = Path(constraints.__file__).parent
    seen = 0
    for path in sorted(package.glob("*.py")):
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            match = MARKER.search(line)
            if not match:
                continue
            seen += 1
            marker, reason = match.group(1), (match.group(2) or "").strip()
            if marker == "n/a":
                assert reason, f"{path.name}:{lineno} n/a marker needs a reason"
            else:
                assert marker in constraints.BY_ID, f"{path.name}:{lineno} names unknown rule {marker}"
    assert seen > len(constraints.REGISTRY)


def test_every_registry_target_is_a_listed_validator_or_orchestrator():
    """A function the registry names is checked here or deliberately exempted, never unknown."""
    listed = {
        f"{module}.{function}"
        for table in (VALIDATORS, ORCHESTRATORS)
        for module, functions in table.items()
        for function in functions
    }
    for entry in constraints.REGISTRY:
        for reference in entry.enforced_by or ():
            assert reference in listed, (
                f"{entry.id} names {reference}, which is neither a listed validator nor a listed orchestrator"
            )


def test_every_rejection_site_in_a_validator_is_annotated():
    for module_name, functions in VALIDATORS.items():
        for function_name in functions:
            markers, raises = _sites(module_name, function_name)
            for lineno in raises:
                assert lineno in markers or lineno - 1 in markers, (
                    f"{module_name}.{function_name} line {lineno} raises without a # constraint: marker"
                )


def test_every_enforced_entry_is_named_at_a_site_in_its_validator():
    for entry in constraints.REGISTRY:
        for reference in entry.enforced_by or ():
            module_name, function_name = reference.rsplit(".", 1)
            markers, _ = _sites(module_name, function_name)
            assert entry.id in {marker for marker, _ in markers.values()}, (
                f"{entry.id} claims {reference} but no site there names it"
            )


def test_not_applicable_markers_are_only_where_no_model_output_is_judged():
    """The n/a list is deliberate and short; a new one is a review question."""
    expected = {"review._claude_session": 9, "spec_trim._parse": 2}
    for module_name, functions in VALIDATORS.items():
        for function_name in functions:
            markers, _ = _sites(module_name, function_name)
            count = sum(marker == "n/a" for marker, _ in markers.values())
            assert count == expected.get(f"{module_name}.{function_name}", 0), (
                f"{module_name}.{function_name} carries {count} n/a markers"
            )
