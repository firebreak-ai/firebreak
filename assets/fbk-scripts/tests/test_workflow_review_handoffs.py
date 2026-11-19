"""Behavioral regressions for context isolation and lossless finding adjudication."""

import json
from pathlib import Path

import pytest

from fbk.workflow import council, review, review_context, store
from tests.test_workflow_review import assessor, finding, native


def decision(finding_id, operative, disposition="supported"):
    return {
        "finding_id": finding_id,
        "disposition": disposition,
        "evidence": "tests/test_jobs.py:32 refutes the bare-return scenario.",
        "finding": operative,
    }


def test_live_council_contradiction_becomes_corrected_operative_finding(tmp_path):
    fixture = (
        Path(__file__).resolve().parents[3] / "docs/0.6.0/evidence/live-council.json"
    )
    recorded = json.loads(fixture.read_text())["round"]["result"]
    old = next(c["finding"] for c in recorded["candidates"] if c["id"] == "guardian:1")
    assessment = next(
        a
        for a in recorded["readers"][-1]["review"]["assessments"]
        if a["finding_id"] == "guardian:1"
    )
    assert "bare" in assessment["evidence"] or "return" in assessment["evidence"]
    corrected = {
        **old,
        "title": "Truthy nonboolean success results pass",
        "evidence": "tests/test_jobs.py:32 rejects bare return; assertTrue accepts a truthy nonboolean success result.",
        "remedy": "Assert success return is True.",
    }
    result = council.adjudicate(
        tmp_path,
        "Review",
        {},
        [{**native([old]), "member": "guardian"}],
        lambda *a, **k: {
            "review": {
                "summary": "Narrowed against original tests.",
                "assessments": [decision("guardian:1", corrected)],
            }
        },
        shape="dual",
    )
    assert result["review"]["findings"] == [corrected]
    assert result["candidates"][0]["finding"] == old
    assert result["readers"][-1]["review"]["assessments"][0]["evidence"]


def test_dual_cannot_drop_minority_candidate(tmp_path):
    result = council.adjudicate(
        tmp_path,
        "Review",
        {},
        [
            {**native([finding()]), "member": "native"},
            {**native([finding()]), "member": "external"},
        ],
        lambda *a, **k: {
            "review": {
                "summary": "Done",
                "assessments": [decision("native:1", finding())],
            }
        },
        shape="dual",
    )
    assert result["review"] is None
    assert "every candidate exactly once" in result["error"]


def test_refuted_candidate_cannot_retain_an_operative_claim():
    _, validate = council.assessment_contract(["guardian:1"], canonical=True)
    with pytest.raises(store.WorkflowError, match="null operative"):
        validate(
            {
                "summary": "Done",
                "assessments": [decision("guardian:1", finding(), "refuted")],
            }
        )


def test_unresolved_blocker_cannot_be_demoted(tmp_path):
    suggestion = {**finding(), "severity": "suggestion"}
    result = council.adjudicate(
        tmp_path,
        "Review",
        {},
        [{**native([finding()]), "member": "guardian"}],
        lambda *a, **k: {
            "review": {
                "summary": "Unknown",
                "assessments": [decision("guardian:1", suggestion, "unresolved")],
            }
        },
        shape="dual",
    )
    assert result["review"] is None and "cannot be downgraded" in result["error"]


def test_snapshot_excludes_history_and_keeps_original_conventions(tmp_path):
    for path, content in {
        ".fbk/unit/prd.md": "Release exactly once",
        ".fbk/unit/state.json": "Wrong past verdict",
        ".fbk/unit/reviews/old.md": "Misleading prior review",
        ".claude/settings.json": "{}",
        ".claude/rules/testing.md": "Check observable behavior",
        "CLAUDE.md": "Read rules",
        "src/app.py": "def release(): pass",
    }.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    with review_context.snapshot(tmp_path, [".fbk/unit/prd.md"]) as (root, manifest):
        assert (root / ".fbk/unit/prd.md").read_text() == "Release exactly once"
        assert (root / "CLAUDE.md").read_text() == "Read rules"
        assert not (root / ".fbk/unit/state.json").exists()
        assert not (root / ".fbk/unit/reviews").exists()
        assert ".claude/settings.json" not in manifest
        saved = {
            "snapshot_files": manifest,
            "required_files": [".fbk/unit/prd.md"],
            "supporting_files": review_context.supporting_manifest(tmp_path),
            "source_policy": "original-snapshot-v1",
        }
    assert review_context.snapshot_fresh(tmp_path, saved)
    (tmp_path / "src/app.py").write_text("changed implementation")
    assert not review_context.snapshot_fresh(tmp_path, saved)
    assert review_context.supporting_fresh(tmp_path, saved)
    (tmp_path / "AGENTS.md").write_text("New authoritative convention")
    assert not review_context.supporting_fresh(tmp_path, saved)


def test_missing_required_context_is_not_silently_omitted(tmp_path):
    with pytest.raises(store.WorkflowError, match="Missing or unreadable"):
        with review_context.snapshot(tmp_path, ["missing.md"]):
            pytest.fail("Missing source entered review")


def context(**overrides):
    return {
        "status": "complete",
        "inspected_files": ["spec.md"],
        "supporting_files": [],
        "missing_context": [],
        **overrides,
    }


@pytest.mark.parametrize(
    "reported",
    [
        context(status="complete", missing_context=["Human decision unavailable"]),
        context(status="incomplete", missing_context=[]),
        context(inspected_files=[]),
        context(inspected_files=["spec.md", "../state.json"]),
    ],
)
def test_reported_context_must_be_well_formed_and_confined(reported):
    with pytest.raises(store.WorkflowError):
        review_context.validate_context(reported, ["spec.md"], ["spec.md"])


def test_native_auth_preserved_and_auto_instruction_loading_disabled(
    tmp_path, monkeypatch
):
    calls = []

    def run(argv, root, timeout, prompt):
        calls.append(argv)
        return {
            "exit_code": 0,
            "stdout": json.dumps(
                {"structured_output": {**native()["review"], "context": context()}}
            ),
            "stderr": "",
            "seconds": 0,
        }

    monkeypatch.setattr(review, "run_command", run)
    result = review.claude_review(
        tmp_path,
        "Read spec.md",
        {"_review_required_files": ["spec.md"], "_review_available_files": ["spec.md"]},
    )
    assert result["context"]["inspected_files"] == ["spec.md"]
    assert "--safe-mode" in calls[0] and "--restricted" in calls[0]
    assert "--bare" not in calls[0]
    assert calls[0][calls[0].index("--setting-sources") + 1] == ""


def test_single_reader_and_diagnostic_output_are_bounded():
    with pytest.raises(store.WorkflowError, match="bounded finding"):
        review.validate_single(native([finding()] * 9)["review"])
    # validate_review is the merged-review validator: a council can return every proposal
    # that stands, so it admits the council's limit and rejects one more.
    limit = council.COUNCIL_FINDING_LIMIT
    assert review.validate_review(native([finding()] * limit)["review"])
    with pytest.raises(store.WorkflowError, match="bounded finding"):
        review.validate_review(native([finding()] * (limit + 1))["review"])
    data = review.bounded_checks(
        [{"argv": ["pytest"], "exit_code": 1, "stdout": "x" * 9000}]
    )[0]
    assert len(data["stdout"]) == 2000 and data["stdout_omitted_chars"] == 7000
    assert data["exit_code"] == 1


def test_process_capture_bounds_memory_and_discloses_omission(tmp_path):
    import sys

    data = review.run_command(
        [sys.executable, "-c", 'print("x" * 1100000)'], tmp_path, 10
    )
    assert len(data["stdout"]) <= 1024 * 1024
    assert data["stdout_omitted_bytes"] > 0


def test_merged_review_retains_more_than_one_readers_quota(tmp_path):
    readers = [
        {**native([finding()] * count), "member": member}
        for member, count in [("native", 5), ("external", 4)]
    ]
    assessments = [
        decision(f"{member}:{i}", finding())
        for member, count in [("native", 5), ("external", 4)]
        for i in range(1, count + 1)
    ]
    result = council.adjudicate(
        tmp_path,
        "Review",
        {},
        readers,
        lambda *a, **k: {
            "review": {
                "summary": "Every candidate assessed.",
                "assessments": assessments,
            }
        },
        shape="dual",
    )
    review.validate_review(result["review"])
    assert len(result["review"]["findings"]) == 9


def test_many_verbose_checks_keep_exact_outcomes_retrievable(tmp_path):
    checks = [
        {"argv": ["pytest", f"test_{i}.py"], "exit_code": 0, "stdout": "x" * 12000}
        for i in range(50)
    ]
    available = {}
    brief = review.bounded_checks(checks, tmp_path, available)
    assert len(json.dumps(brief)) < 32000
    assert json.loads((tmp_path / brief["evidence_file"]).read_text()) == checks
    assert brief["evidence_file"] in available


def test_review_focus_distinguishes_work_from_authority():
    brief = review.focus_brief(
        "unit",
        "spec",
        [".fbk/unit/prd.md", ".fbk/unit/spec.md", ".fbk/unit/scope.json"],
    )
    assert brief["phase_targets"] == [".fbk/unit/scope.json", ".fbk/unit/spec.md"]
    assert "authoritative_context" not in brief
    assert "both its phase_targets and its authoritative_context" in brief["coverage"]


@pytest.mark.parametrize("change", ["edit", "remove"])
def test_reported_external_authority_is_freshness_dependency(tmp_path, change):
    contract = tmp_path / "contracts/cancellation.md"
    contract.parent.mkdir()
    contract.write_text("Release once.")
    with review_context.snapshot(tmp_path, []) as (_, manifest):
        result = {
            "source_policy": "original-snapshot-v1",
            "supporting_files": {},
            "readers": [
                {"context": {"supporting_files": ["contracts/cancellation.md"]}}
            ],
        }
        result["additional_supporting_files"] = review_context.additional_supporting(
            tmp_path, "unit", "intent", [], result, manifest
        )
    assert review_context.supporting_fresh(tmp_path, result)
    if change == "edit":
        contract.write_text("Release twice.")
    else:
        contract.unlink()
    assert not review_context.supporting_fresh(tmp_path, result)


def test_unfinished_deliverables_are_not_durable_authority(tmp_path):
    paths = {
        ".fbk/unit/prd.md": "Release once.",
        "src/app.py": "pending implementation",
        "tests/test_app.py": "pending tests",
        "docs/app.md": "pending documentation",
        "contracts/cancellation.md": "Shared release contract",
    }
    for relative, content in paths.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    store.atomic_json(
        tmp_path / ".fbk/unit/scope.json",
        {"sources": ["src"], "tests": ["tests"], "docs": ["docs"], "checks": []},
    )
    required = [".fbk/unit/prd.md"]
    with review_context.snapshot(tmp_path, required) as (_, manifest):
        result = {
            "source_policy": "original-snapshot-v1",
            "supporting_files": {},
            "readers": [{"context": {"supporting_files": list(paths)}}],
        }
        result["additional_supporting_files"] = review_context.additional_supporting(
            tmp_path, "unit", "intent", required, result, manifest
        )
    assert list(result["additional_supporting_files"]) == ["contracts/cancellation.md"]
    for relative in ["src/app.py", "tests/test_app.py", "docs/app.md"]:
        (tmp_path / relative).write_text("Now implemented.")
    assert review_context.supporting_fresh(tmp_path, result)


def test_convention_freshness_ignores_unrelated_symlink_directory(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("Repository rules.")
    saved = review_context.supporting_manifest(tmp_path)
    (tmp_path / "external-build").symlink_to("/tmp", target_is_directory=True)
    assert review_context.supporting_manifest(tmp_path) == saved


def test_new_repository_intent_review_receives_only_current_decision_inputs(
    tmp_path, monkeypatch
):
    """Reproduce the live failure's empty repo, inspecting the actual native wire packet."""
    from fbk.workflow import engine, evidence

    store.atomic_json(tmp_path / ".fbk/config.json", {"schema_version": 1})
    with store.transaction(tmp_path):
        engine.initialize(tmp_path, "unit", design=False)
    (tmp_path / ".fbk/unit/prd.md").write_text(
        "A cancellation releases a resource exactly once."
    )
    record = store.load(tmp_path, "unit")
    seen = []

    def native_host(argv, source_root, timeout, prompt):
        packet = json.loads(
            next(line for line in prompt.splitlines() if line.startswith("{"))
        )
        seen.append(packet)
        priority = packet["reading_priority"]
        assert "files" not in packet and "phase_targets" not in priority
        assert packet["required_files"] == {"phase_targets": [".fbk/unit/prd.md"], "authoritative_context": []}
        assert priority["later_deliverables"] == [
            "design",
            "specification",
            "task breakdown",
            "implementation",
            "executable tests",
            "delivery documentation",
        ]
        assert packet["available_conventions"] == []
        assert "verification" not in packet and "test_discipline" not in packet
        assert not (source_root / "README.md").exists()
        for relative in packet["required_files"]["phase_targets"]:
            (source_root / relative).read_text()
        return {
            "exit_code": 0,
            "stderr": "",
            "seconds": 0,
            "stdout": json.dumps(
                {
                    "structured_output": {
                        "summary": "Intent is coherent and feasible.",
                        "findings": [],
                        "context": context(inspected_files=packet["required_files"]["phase_targets"]),
                    }
                }
            ),
        }

    monkeypatch.setattr(review, "run_command", native_host)
    result = review.review(
        tmp_path, "unit", "intent", evidence.subject(tmp_path, record, "intent"), []
    )
    assert result["review"]["findings"] == []
    assert len(seen) == 1


@pytest.mark.parametrize(
    "phase,targets,future",
    [
        (
            "design",
            [".fbk/unit/design/architecture.md"],
            [
                "specification",
                "task breakdown",
                "implementation",
                "executable tests",
                "delivery documentation",
            ],
        ),
        (
            "spec",
            [".fbk/unit/scope.json", ".fbk/unit/spec.md"],
            [
                "task breakdown",
                "implementation",
                "executable tests",
                "delivery documentation",
            ],
        ),
        (
            "breakdown",
            [".fbk/unit/tasks.json"],
            ["implementation", "delivery documentation"],
        ),
        ("implement", ["README.md", "src/app.py", "tests/test_app.py"], []),
    ],
)
def test_review_decision_contract_advances_without_demands_for_future_work(
    phase, targets, future, tmp_path, monkeypatch
):
    files = [".fbk/unit/prd.md", *targets]
    calls = []

    def reader(root, prompt, config):
        packet = json.loads(
            next(line for line in prompt.splitlines() if line.startswith("{"))
        )
        calls.append(packet)
        return native()

    monkeypatch.setattr(review, "claude_review", reader)
    record = {"events": [], "parent": None, "review_plans": {phase: {"mode": "single"}}}
    review._review_sources(tmp_path, "unit", phase, files, [], {}, record)
    packet = calls[0]
    assert packet["required_files"] == {"phase_targets": targets, "authoritative_context": [".fbk/unit/prd.md"]}
    assert packet["reading_priority"]["later_deliverables"] == future
    assert ("verification" in packet) == (phase in {"breakdown", "implement"})
    # Implement keeps its test discipline slot; a plan-only breakdown has none to give.
    if phase == "breakdown":
        assert not packet.get("test_discipline"), packet.get("test_discipline")
    else:
        assert ("test_discipline" in packet) == (phase == "implement")
    assert (
        packet["reading_priority"]["acceptance_obligations"]
        != review.focus_brief("unit", "intent", files)["acceptance_obligations"]
    )


RULE_SENTENCE = (
    "Every path in required_files, in both its phase_targets and authoritative_context "
    "lists, must appear in the declaration, in inspected_files or in supporting_files; "
    "supporting_files is the subset relied on as governing authority."
)
STAGE_CLAUSE = "The context declaration applies to this pass exactly as to an independent reader."


def test_packet_names_the_enforced_required_files(tmp_path, monkeypatch):
    """The reviewer sees the exact list validate_context enforces, not only the phase files."""
    files = [".fbk/unit/prd.md", ".fbk/unit/spec.md"]
    decisions = [
        {
            "id": f"D-{i}",
            "text": "Cancellation releases the resource once.",
            "phase": "intent",
            "source": {"path": path, "hash": "0" * 64},
            "supersedes": None,
        }
        for i, path in enumerate(["contracts/cancellation.md", "docs/decisions-log.md"], 1)
    ]
    required = sorted({*files, *(d["source"]["path"] for d in decisions), ".fbk/parent/spec.md"})
    config = {"_review_required_files": required, "_review_decisions": decisions}
    calls = []

    def reader(root, prompt, config):
        calls.append(json.loads(next(line for line in prompt.splitlines() if line.startswith("{"))))
        return native()

    monkeypatch.setattr(review, "claude_review", reader)
    record = {"events": [], "parent": "parent", "review_plans": {"spec": {"mode": "single"}}}
    review._review_sources(tmp_path, "unit", "spec", files, [], config, record)
    packet = calls[0]
    listed = packet["required_files"]["phase_targets"] + packet["required_files"]["authoritative_context"]
    # Each enforced path appears exactly once, under its role.
    assert sorted(listed) == config["_review_required_files"] and len(set(listed)) == len(listed)
    assert packet["required_files"]["phase_targets"] == [".fbk/unit/spec.md"]
    assert {d["source"]["path"] for d in decisions} <= set(packet["required_files"]["authoritative_context"])
    keys = list(packet)
    assert keys.index("required_files") == keys.index("reading_priority") + 1
    assert "required_files" in packet["reading_priority"]["coverage"]


def test_session_prompt_states_the_declaration_rule_next_to_the_list(tmp_path, monkeypatch):
    """The rule is rendered by the constraint registry into the packet's rules block,
    which sits directly after required_files."""
    prompts = []

    def run(argv, root, timeout, prompt):
        prompts.append(prompt)
        return {
            "exit_code": 0,
            "stdout": json.dumps(
                {"structured_output": {**native()["review"], "context": context()}}
            ),
            "stderr": "",
            "seconds": 0,
        }

    monkeypatch.setattr(review, "run_command", run)
    record = {"events": [], "parent": None, "review_plans": {"spec": {"mode": "single"}}}
    review._review_sources(
        tmp_path, "unit", "spec", ["spec.md"], [], {"_review_required_files": ["spec.md"]}, record
    )
    [prompt] = prompts
    packet = json.loads(next(line for line in prompt.splitlines() if line.startswith("{")))
    keys = list(packet)
    assert keys.index("rules") == keys.index("required_files") + 1
    [rule] = [r for r in packet["rules"]["context-declaration"] if r["id"] == "required-files-declared"]
    assert rule["rule"] == RULE_SENTENCE
    assert "inspected_files" in prompt and "supporting_files" in prompt
    assert "governing authority documents" in prompt


def test_the_assessor_carries_the_declaration_obligation(tmp_path):
    prompts = []

    def reader(root, prompt, config, **kwargs):
        prompts.append(prompt)
        return assessor(["guardian:1"], canonical=True)

    result = council.adjudicate(
        tmp_path,
        "Review",
        {},
        [{**native([finding()]), "member": "guardian"}],
        reader,
        shape="dual",
    )
    assert result["review"]["findings"]
    [prompt] = prompts
    assert STAGE_CLAUSE in prompt
    # The assessor carries its own registry block, which restates the required_files rule.
    assert '"id": "required-files-declared"' in prompt
    assert RULE_SENTENCE in prompt


@pytest.mark.parametrize(
    "envelope,expected",
    [
        (
            {
                "subtype": "error_max_turns",
                "result": "Reached the review turn limit while reading the shared contract.",
            },
            "Reached the review turn limit while reading the shared contract.",
        ),
        (
            {"error": "Authentication session expired."},
            "Authentication session expired.",
        ),
        ({"subtype": "error_max_turns"}, "error_max_turns"),
    ],
)
def test_stdout_only_native_failure_preserves_actionable_diagnostic(
    tmp_path, monkeypatch, envelope, expected
):
    monkeypatch.setattr(
        review,
        "run_command",
        lambda *a: {
            "exit_code": 1,
            "stderr": "",
            "stdout": json.dumps(envelope),
            "seconds": 0,
        },
    )
    with pytest.raises(store.WorkflowError) as failure:
        review.claude_review(tmp_path, "Inspect the current phase.", {})
    message = str(failure.value)
    assert expected in message and "exit 1" in message
    assert "Use a host supporting" not in message


@pytest.mark.parametrize(
    "diagnostic",
    ["error: unknown option '--safe-mode'", "unrecognized option '--restricted'"],
)
def test_unsupported_host_explains_required_isolation_without_requiring_api_auth(
    tmp_path, monkeypatch, diagnostic
):
    monkeypatch.setattr(
        review,
        "run_command",
        lambda *a: {"exit_code": 2, "stderr": diagnostic, "stdout": "", "seconds": 0},
    )
    with pytest.raises(store.WorkflowError) as failure:
        review.claude_review(tmp_path, "Inspect the current phase.", {})
    message = str(failure.value)
    assert diagnostic in message
    assert (
        "Use a host supporting --safe-mode and --restricted with normal Claude authentication."
        in message
    )


def test_native_error_diagnostic_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(
        review,
        "run_command",
        lambda *a: {
            "exit_code": 1,
            "stderr": "",
            "stdout": json.dumps({"error": "x" * 10000 + "Final actionable cause."}),
            "seconds": 0,
        },
    )
    with pytest.raises(store.WorkflowError) as failure:
        review.claude_review(tmp_path, "Inspect.", {})
    assert str(failure.value).endswith("Final actionable cause.")
    assert len(str(failure.value)) < 2100


EVERY_BLOCKER_SENTENCE = (
    "Report every blocker you can demonstrate in this pass, across the whole artifact and not only "
    "the recently changed region, because each round is budgeted and a blocker left for the next "
    "round costs a round."
)


def test_base_review_prompt_asks_for_every_extant_blocker_in_one_pass(tmp_path, monkeypatch):
    prompts = []

    def reader(root, prompt, config):
        prompts.append(prompt)
        return native()

    monkeypatch.setattr(review, "claude_review", reader)
    record = {"events": [], "parent": None, "review_plans": {"spec": {"mode": "single"}}}
    review._review_sources(tmp_path, "unit", "spec", [".fbk/unit/prd.md", ".fbk/unit/spec.md"], [], {}, record)
    assert EVERY_BLOCKER_SENTENCE in prompts[0]
    assert prompts[0].index("as blockers when the violation is material") < prompts[0].index(EVERY_BLOCKER_SENTENCE)


@pytest.mark.parametrize("kind", ["artifact", "test", "code", "documentation"])
def test_finding_validates_with_each_remedy_kind(kind):
    tagged = {**finding(), "remedy_kind": kind}
    single = review.validate_single(native([tagged])["review"])
    merged = review.validate_review(native([tagged] * 9)["review"])
    assert single["findings"][0]["remedy_kind"] == kind
    assert all(f["remedy_kind"] == kind for f in merged["findings"])
    assert kind in review.SCHEMA["properties"]["findings"]["items"]["properties"]["remedy_kind"]["enum"]


def test_finding_without_remedy_kind_still_validates_and_is_not_required():
    untagged = finding()
    assert "remedy_kind" not in untagged
    assert review.validate_single(native([untagged])["review"])
    item = review.SCHEMA["properties"]["findings"]["items"]
    assert "remedy_kind" not in item["required"]
    assert item["properties"]["remedy_kind"]["enum"] == ["artifact", "test", "code", "documentation"]


@pytest.mark.parametrize("value", ["prose", "", "Test", 3, None, ["test"]])
def test_unknown_remedy_kind_is_rejected_with_the_registered_message(value):
    tagged = {**finding(), "remedy_kind": value}
    with pytest.raises(
        store.WorkflowError,
        match="remedy_kind must be one of artifact, test, code, or documentation",
    ):
        review.validate_review(native([tagged])["review"])
    with pytest.raises(store.WorkflowError, match="remedy_kind must be one of"):
        review.validate_single(native([tagged])["review"])


def test_breakdown_brief_obliges_a_documented_command_check():
    brief = review.focus_brief("unit", "breakdown", [".fbk/unit/tasks.json", ".fbk/unit/spec.md"])
    obligation = [
        o for o in brief["acceptance_obligations"]
        if "documented usage" in o and "check_expectations" in o
    ]
    assert len(obligation) == 1
    assert "finished program" in obligation[0]
    assert "grep" in obligation[0]
    assert not any("documented usage" in o for o in review.focus_brief("unit", "spec", [".fbk/unit/spec.md"])["acceptance_obligations"])


def _decision(i, text="Cancellation releases the resource once."):
    return {"id": f"D-{i}", "text": text, "phase": "intent",
            "source": {"path": "decisions.md", "quote": f"quote {i}", "hash": "0" * 64},
            "supersedes": f"D-old-{i}"}


def _packet(tmp_path, monkeypatch, phase, config):
    calls = []

    def reader(root, prompt, config):
        calls.append((json.loads(next(line for line in prompt.splitlines() if line.startswith("{"))), config))
        return native()

    monkeypatch.setattr(review, "claude_review", reader)
    record = {"events": [], "parent": None, "review_plans": {phase: {"mode": "single"}}}
    review._review_sources(tmp_path, "unit", phase, [".fbk/unit/spec.md", "decisions.md"], [], config, record)
    return calls[0]


def test_reviewer_sees_only_the_current_decision_not_its_bookkeeping(tmp_path, monkeypatch):
    packet, _ = _packet(tmp_path, monkeypatch, "spec", {"_review_decisions": [_decision(1)]})
    assert packet["current_decisions"] == [{"id": "D-1", "text": "Cancellation releases the resource once.",
                                            "phase": "intent", "path": "decisions.md", "quote": "quote 1"}]


def test_large_decision_set_moves_to_a_required_snapshot_file(tmp_path, monkeypatch):
    rows = [_decision(i, "x" * 900) for i in range(120)]
    available = {".fbk/unit/spec.md": "a", "decisions.md": "b"}
    packet, config = _packet(tmp_path, monkeypatch, "spec",
                             {"_review_decisions": rows, "_review_available_files": available,
                              "_review_required_files": [".fbk/unit/spec.md", "decisions.md"]})
    brief = packet["current_decisions"]
    assert brief["count"] == 120 and len(json.dumps(packet)) < 40000
    stored = json.loads((tmp_path / brief["decisions_file"]).read_text())
    assert len(stored) == 120 and stored[0] == {"id": "D-0", "text": "x" * 900, "phase": "intent",
                                                "path": "decisions.md", "quote": "quote 0"}
    # The reviewer must declare reading it, and may name it without leaving the snapshot.
    assert brief["decisions_file"] in packet["required_files"]["authoritative_context"]
    assert brief["decisions_file"] in config["_review_required_files"]
    assert brief["decisions_file"] in available


def test_breakdown_packet_carries_no_test_discipline(tmp_path, monkeypatch):
    # A plan-only breakdown has no red output, baseline execution, or lineage to judge.
    packet, _ = _packet(tmp_path, monkeypatch, "breakdown", {})
    assert not packet.get("test_discipline"), packet.get("test_discipline")
    text = json.dumps(packet)
    assert "lineage_review" not in text and "baseline_execution" not in text
    assert "Baseline execution records" not in text and "preservation evidence" not in text
