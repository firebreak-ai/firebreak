"""Review-only requirements and the implementation review's per-requirement assessment
(build step 9a, plan decision 9, first three bullets).

A requirement is behavioral by default. A requirement whose own text, after its heading,
starts with the line ``Checked by review: <reason>`` is review-only: breakdown needs an
implementation task for it but no test task, the spec review is told about each marker and
judges it, and the implementation review must return a verdict on each such requirement.

Lead rulings these tests rely on (step 9a brief):

1. **Marker form.** The first non-blank line of the item's own text after its heading, exactly
   ``Checked by review: `` and a non-empty reason, read by step 7's parser (so a fence, a quote
   or inline code does not count). A ``Checked by review:`` line anywhere else in a requirement
   item, or one with an empty reason, is refused at spec close naming the file, line and item.
   Outside the Requirements section such lines are left alone.
2. **Spec close** runs the marker checks with the traceability checks, before any review
   round, naming every problem at once. A review-only requirement still needs its upstream link.
3. **Spec review** is told which requirements are review-only, with each reason.
4. **Breakdown coverage**: a review-only requirement is exempt from the test-task half only;
   a test task may still link it. The refusal keeps saying which half is missing.
5. **Assessment shape**, implement phase only and only when the unit has review-only
   requirements: the review object gains a required ``requirement_assessments`` array, one
   entry per review-only requirement of the unit's own spec.md, each
   ``{"requirement": "<spec path>#<anchor>", "verdict": "met" | "not met", "evidence": ...}``
   plus a non-empty ``remedy`` when not met. Missing, duplicated, unknown or malformed entries
   are refused naming the problem. Without review-only requirements the schema is unchanged.
   The prompt lists each review-only requirement (reference, name, reason).
6. **Not met is a blocker**: one blocker per operative "not met", titled with the requirement,
   located at its reference, with the assessment's evidence and remedy. The operative
   assessments are stored with the round's result.
7. **Routes**: the single reader's assessments are operative. With the configured second
   reader, both readers must return assessments; when they agree on every verdict and there
   are no finding candidates the agreed verdicts are operative (evidence and remedy from the
   native reader); otherwise adjudication runs, sees each reader's assessments, and must return
   assessments itself, which are operative. One blocker per operative "not met", never one per
   reader. A council cannot review implement, so the council route is not tested (lead's
   correction to ruling 7).
8. **Registry**: new constraint entries render only for implement with review-only
   requirements, for the review and adjudication kinds; the second reader gets the same prompt.

Shapes the tests assume, leaving names to the implementer: the real review path
(``review.review``) runs with ``review.run_command`` stubbed for the Claude host and the
second reader (other commands, such as the unit's checks, run for real). Refusals are
``WorkflowError``; reason words are matched loosely. Operative assessments are looked for at
the round result's top level or in its operative review object.

Red or guard: each test's docstring says which. **Red** tests fail today on an assertion about
missing behavior; **guard** tests (marked ``# Guard:``) pass today and pin behavior a plausible
wrong implementation would break.
"""

import json
import re
import sys

import pytest

from fbk.workflow import close, engine, review, store
from tests import test_workflow_lifecycle as scenarios
from tests.test_workflow_constraints import complete_context, packet_of, stage_of
from tests.test_workflow_managed_investigations import host
from tests.test_workflow_review import finding
from tests.test_workflow_task_traceability import (
    breakdown_refusal,
    lines_naming,
    refs,
    task,
    through_spec,
    write_tasks,
)
from tests.test_workflow_traceability import (
    SPEC,
    UNIT,
    accept,
    accepted_through_design,
    enter,
    names_all,
    refused,
)

SPEC_PATH = f".fbk/{UNIT}/spec.md"
LISTING_REASON = "the listing's wording is judged by a reader, not a program."
MARKED_SPEC = SPEC.replace(
    "### History listing\n\n",
    f"### History listing\n\nChecked by review: {LISTING_REASON}\n\n",
)


def closes(root, phase, unit=UNIT):
    """Enter and close ``phase`` with a clean review; a refusal fails the test with its message."""
    enter(root, phase, unit)
    try:
        close.close_phase(root, unit, phase, "s", reviewer=scenarios.clean_review)
    except store.WorkflowError as exc:
        pytest.fail(f"{phase} close refused: {exc}")
    scenarios.observe_phase(root, phase, unit=unit)


def line_number(text, needle, occurrence=1):
    """The 1-based line of the ``occurrence``-th line containing ``needle``."""
    found = [n for n, line in enumerate(text.splitlines(), 1) if needle in line]
    return found[occurrence - 1]


def names_line(message, path, number, item):
    """Some line of the refusal names the file, the line number and the item."""
    for line in message.splitlines():
        if path in line and re.search(rf"\b{number}\b", line) and item in line:
            return
    pytest.fail(f"No refusal line names {path}, line {number} and {item!r}: {message}")


# --- spec close: the marker's form ----------------------------------------------------------


def test_marker_as_first_non_blank_line_is_accepted_at_spec_close(tmp_path):
    # Guard: passes today; protects behavior that must not regress.
    """Guard: the marker as the first non-blank line under a requirement's heading closes spec.
    Catches: refusing every marker line, or refusing the marker line as text outside the
    Markdown subset."""
    accepted_through_design(tmp_path, spec=MARKED_SPEC)
    closes(tmp_path, "spec")


MISPLACED = {
    "after-text": SPEC.replace(
        "from [Retention log](design/storage.md#retention-log).\n",
        "from [Retention log](design/storage.md#retention-log).\n"
        "Checked by review: the wording is judged by a reader.\n",
    ),
    "later-paragraph": SPEC.replace(
        "from [Retention log](design/storage.md#retention-log).\n",
        "from [Retention log](design/storage.md#retention-log).\n\n"
        "Checked by review: the wording is judged by a reader.\n",
    ),
    "under-a-deeper-heading": SPEC.replace(
        "#### Listing format\n\n",
        "#### Listing format\n\nChecked by review: the wording is judged by a reader.\n\n",
    ),
    "second-marker": MARKED_SPEC.replace(
        "One date per line.\n",
        "One date per line.\n\nChecked by review: the wording is judged by a reader.\n",
    ),
    "empty-reason": SPEC.replace("### History listing\n\n", "### History listing\n\nChecked by review:\n\n"),
    "blank-reason": SPEC.replace("### History listing\n\n", "### History listing\n\nChecked by review:    \n\n"),
}


@pytest.mark.parametrize("variant", sorted(MISPLACED))
def test_misplaced_or_empty_marker_is_refused_naming_file_line_and_item(tmp_path, variant):
    """Red. A ``Checked by review:`` line that is not the item's first non-blank line, or has
    an empty reason, is refused at spec close before any review round, naming the spec file,
    the line and the requirement. Today spec close accepts it as ordinary text. Catches: counting
    a marker anywhere in the item; accepting an empty reason; checking only the first marker."""
    spec = MISPLACED[variant]
    accepted_through_design(tmp_path, spec=spec)
    message = refused(tmp_path, "spec")
    occurrence = 2 if variant == "second-marker" else 1
    names_line(message, SPEC_PATH, line_number(spec, "Checked by review:", occurrence), "History listing")


def test_spec_close_names_every_marker_problem_with_the_traceability_problems(tmp_path):
    """Red. Two misplaced markers in two requirements and an unlinked requirement are all named
    in one refusal. Catches: stopping at the first marker problem, or running the marker check
    after (and only when) the link checks pass."""
    spec = SPEC.replace(
        "from [Snapshot store](design/storage.md#snapshot-store).\n",
        "from [Snapshot store](design/storage.md#snapshot-store).\n\nChecked by review: late marker one.\n",
    ).replace(
        "### History listing\n\n",
        "### History listing\n\nChecked by review:\n\n",
    ).replace(
        "## Checks",
        "### Audit report\n\nA monthly report; no link.\n\n## Checks",
    )
    accepted_through_design(tmp_path, spec=spec)
    message = refused(tmp_path, "spec")
    names_line(message, SPEC_PATH, line_number(spec, "Checked by review: late"), "Restore command")
    names_line(message, SPEC_PATH, line_number(spec, "Checked by review:", 2), "History listing")
    names_all(message, "Audit report")


NOT_MARKERS = {
    "fenced-first": SPEC.replace(
        "### History listing\n\n",
        "### History listing\n\n```\nChecked by review: an example inside a fence.\n```\n\n",
    ),
    "fenced-later": SPEC.replace(
        "One date per line.\n",
        "One date per line.\n\n```\nChecked by review: an example inside a fence.\n```\n",
    ),
    "quoted": SPEC.replace(
        "### History listing\n\n",
        "### History listing\n\n> Checked by review: a quoted example.\n\n",
    ),
    "inline-code": SPEC.replace(
        "### History listing\n\n",
        "### History listing\n\n`Checked by review: an inline example.`\n\n",
    ),
}


@pytest.mark.parametrize("variant", sorted(NOT_MARKERS))
def test_marker_text_inside_a_fence_quote_or_inline_code_is_not_refused(tmp_path, variant):
    # Guard: passes today; protects behavior that must not regress.
    """Guard: marker text inside a fenced block, a blockquote or inline code is not a marker,
    so it is not refused as misplaced. Catches: scanning the raw item text for the marker."""
    accepted_through_design(tmp_path, spec=NOT_MARKERS[variant])
    closes(tmp_path, "spec")


def test_marker_lines_outside_the_requirements_section_are_left_alone(tmp_path):
    # Guard: passes today; protects behavior that must not regress.
    """Guard: a ``Checked by review:`` line in spec.md outside Requirements, and one in a design
    choice, close design and spec. Catches: applying the marker rule to every section or
    document."""
    from tests.test_workflow_traceability import DESIGN

    spec = SPEC.replace("Run the unit tests.", "Run the unit tests.\nChecked by review:")
    design = DESIGN.replace(
        "One folder per day, named by date.",
        "One folder per day, named by date.\nChecked by review: misplaced in a design choice.",
    )
    accepted_through_design(tmp_path, spec=spec, designs={"storage.md": design})
    closes(tmp_path, "spec")


def test_review_only_requirement_still_needs_its_upstream_link(tmp_path):
    # Guard: passes today; protects behavior that must not regress.
    """Guard: a review-only requirement with no design-choice link is refused by name at spec
    close. Catches: exempting review-only requirements from step 7's link rule."""
    spec = MARKED_SPEC.replace(
        "## Checks",
        "### Audit wording\n\nChecked by review: wording is judged by a reader.\n\nNo link.\n\n## Checks",
    )
    accepted_through_design(tmp_path, spec=spec)
    names_all(refused(tmp_path, "spec"), "Audit wording")


# --- breakdown close: coverage --------------------------------------------------------------


def marked_tasks(test_links=("restore-command",), code_links=("restore-command", "history-listing")):
    return [task("restore-tests", "tests", ["tests/test_restore.py"], refs(*test_links)),
            task("restore-code", "implementation", ["src/backup.py"], refs(*code_links))]


def test_review_only_requirement_needs_no_test_task(tmp_path):
    """Red. A review-only requirement linked by an implementation task and no test task closes
    breakdown. Today breakdown refuses it for want of a test task."""
    through_spec(tmp_path, spec=MARKED_SPEC)
    write_tasks(tmp_path, marked_tasks())
    closes(tmp_path, "breakdown")


def test_review_only_requirement_may_also_be_linked_by_a_test_task(tmp_path):
    # Guard: passes today; protects behavior that must not regress.
    """Guard: a test task may still link a review-only requirement. Catches: refusing a test
    link to a review-only requirement."""
    through_spec(tmp_path, spec=MARKED_SPEC)
    write_tasks(tmp_path, marked_tasks(test_links=("restore-command", "history-listing")))
    closes(tmp_path, "breakdown")


def test_review_only_requirement_without_an_implementation_task_is_refused_for_that_half_only(tmp_path):
    """Red. A review-only requirement with neither task is refused for want of an
    implementation task only; the refusal does not ask for a test task. Today the line asks for
    both. Catches: exempting review-only requirements from the implementation half too (which
    would not refuse at all)."""
    through_spec(tmp_path, spec=MARKED_SPEC)
    message = breakdown_refusal(tmp_path, marked_tasks(code_links=("restore-command",)))
    line = lines_naming(message, "History listing")
    assert line and re.search(r"implementation", line, re.I), (
        f"History listing should be refused for want of an implementation task: {message}")
    assert not re.search(r"test task", line, re.I), (
        f"A review-only requirement is refused for want of a test task: {line}")


def test_behavioral_requirement_beside_a_review_only_one_still_needs_a_test_task(tmp_path):
    # Guard: passes today; protects behavior that must not regress.
    """Guard: in a spec with a review-only requirement, a behavioral requirement linked only by
    an implementation task is still refused for want of a test task, and the review-only one is
    not. Catches: exempting every requirement once one carries a marker."""
    through_spec(tmp_path, spec=MARKED_SPEC)
    tasks = marked_tasks(test_links=("history-listing",))
    message = breakdown_refusal(tmp_path, tasks)
    line = lines_naming(message, "Restore command")
    assert line and re.search(r"test", line, re.I), message


@pytest.mark.parametrize("variant", sorted(NOT_MARKERS))
def test_marker_text_inside_a_fence_quote_or_inline_code_leaves_the_requirement_behavioral(tmp_path, variant):
    # Guard: passes today; protects behavior that must not regress.
    """Guard: marker text inside a fence, a quote or inline code does not make a requirement
    review-only, so breakdown still refuses it without a test task. Catches: reading the raw
    first line, or any line of the item, instead of the parser's text lines."""
    through_spec(tmp_path, spec=NOT_MARKERS[variant])
    message = breakdown_refusal(tmp_path, marked_tasks())
    line = lines_naming(message, "History listing")
    assert line and re.search(r"test", line, re.I), message


# --- the implementation review --------------------------------------------------------------

NAMING_REASON = "naming is a convention no executable check can meaningfully verify."
CHANGELOG_REASON = "a documentation obligation read by people, not a program."
IMPLEMENT_SPEC = f"""\
# Cancellation contract

## Requirements

### Cancel once

Cancel returns true once, false when already canceled. Release exactly once. Serves [Release on cancel](prd.md#release-on-cancel).

### Cancel naming

Checked by review: {NAMING_REASON}

Public cancellation functions start with cancel_. Serves [Release on cancel](prd.md#release-on-cancel).

### Changelog entry

Checked by review: {CHANGELOG_REASON}

The changelog records the cancellation change. Serves [Release on cancel](prd.md#release-on-cancel).
"""
NAMING = f"{SPEC_PATH}#cancel-naming"
CHANGELOG = f"{SPEC_PATH}#changelog-entry"
SECOND = "fake-second-reader"


def assess(ref, verdict="met", evidence=None, remedy=None):
    item = {"requirement": ref, "verdict": verdict,
            "evidence": evidence or f"src/app.py shows {ref.rsplit('#', 1)[1]} {verdict}."}
    if verdict == "not met":
        item["remedy"] = remedy or f"Bring {ref.rsplit('#', 1)[1]} in line with its requirement."
    return item


def all_met(tag="native"):
    return [assess(NAMING, evidence=f"{tag}: names follow the convention."),
            assess(CHANGELOG, evidence=f"{tag}: the changelog records it.")]


def marked_project(root, *, spec=IMPLEMENT_SPEC, review_refs=(NAMING, CHANGELOG)):
    """The lifecycle fixture with ``spec`` written and both tasks also linking ``review_refs``,
    so breakdown closes before and after this step."""
    root.mkdir(parents=True, exist_ok=True)
    scenarios.project.__wrapped__(root)
    unit = root / f".fbk/{UNIT}"
    (unit / "spec.md").write_text(spec)
    tasks = store.read_json(unit / "tasks.json")
    for each in tasks:
        each["acceptance_refs"] += list(review_refs)
    store.atomic_json(unit / "tasks.json", tasks)
    return root


def implement_unit(root, *, marked=True, spec=IMPLEMENT_SPEC, review_refs=(NAMING, CHANGELOG)):
    """The lifecycle fixture in writing code, with the implementation task complete and the
    whole-unit check passing; its spec has review-only requirements when ``marked``."""
    if marked:
        marked_project(root, spec=spec, review_refs=review_refs)
    else:
        root.mkdir(parents=True, exist_ok=True)
        scenarios.project.__wrapped__(root)
    scenarios.prepare_implementation(root)
    (root / "src/app.py").write_text("release()")
    scenarios.complete_declared_implementation_task(root)
    return root


def second_reader(root):
    config = store.project_config(root)
    store.atomic_json(root / ".fbk/config.json", {**config, "second_reader": [SECOND]})


class Readers:
    """Stands in for the Claude host and the second reader. ``plan`` gives each role's
    findings and requirement assessments (None leaves the property out); prompts and schemas
    are recorded by role."""

    def __init__(self, monkeypatch, **plan):
        self.plan = plan
        self.prompts = {}
        self.schemas = {}
        self.real = review.run_command
        monkeypatch.setattr(review, "run_command", self)

    def body(self, role, cwd):
        part = self.plan.get(role, {})
        data = {"summary": f"The {role} reader inspected the delivered code.",
                "findings": list(part.get("findings", []))}
        if part.get("assessments") is not None:
            data["requirement_assessments"] = part["assessments"]
        data.update(part.get("extra", {}))
        data["context"] = complete_context(cwd)
        return data

    def __call__(self, argv, cwd, timeout, prompt=None, **kwargs):
        if argv == [SECOND]:
            self.prompts.setdefault("external", []).append(prompt)
            return {"exit_code": 0, "seconds": 1, "stdout": json.dumps(self.body("external", cwd)), "stderr": ""}
        if argv[:1] != ["claude"]:
            return self.real(argv, cwd, timeout, prompt, **kwargs)
        stage, schema = stage_of(argv)
        role = "native" if stage == "member" else stage
        self.prompts.setdefault(role, []).append(prompt)
        self.schemas.setdefault(role, []).append(schema)
        if role == "native":
            return host(self.body("native", cwd))
        ids = schema["properties"]["assessments"]["items"]["properties"]["finding_id"].get("enum", [])
        part = self.plan.get(role, {})
        data = {"summary": "Verified each candidate against the sources.", "assessments": [
            {"finding_id": i, "disposition": "supported", "evidence": "src/app.py:1 confirms it.",
             **({"finding": finding()} if role == "adjudication" else {})} for i in ids]}
        if role == "adjudication" and part.get("assessments") is not None:
            data["requirement_assessments"] = part["assessments"]
        data["context"] = complete_context(cwd)
        return host(data)


def close_implement(root):
    """Close implement through the real review path; returns None on acceptance or the
    refusal message."""
    try:
        close.close_phase(root, UNIT, "implement", "s")
    except store.WorkflowError as exc:
        return str(exc)
    return None


def latest_result(root):
    return store.load(root, UNIT)["phases"]["implement"]["rounds"][-1]["result"] or {}


def operative_assessments(result):
    for holder in (result, result.get("review") or {}):
        if isinstance(holder.get("requirement_assessments"), list):
            return holder["requirement_assessments"]
    pytest.fail(f"The round's result stores no operative requirement assessments: {sorted(result)}")


def verdicts(assessments):
    return {a["requirement"]: a["verdict"] for a in assessments}


def requirement_blockers(result, ref):
    return [f for f in (result.get("review") or {}).get("findings", []) if f.get("location") == ref]


def assert_accepted(root, outcome):
    assert outcome is None, f"Implement close refused: {outcome}"
    assert store.load(root, UNIT)["phases"]["implement"]["evidence"], "Implement was not accepted."


def assert_refused_naming(outcome, *needles):
    assert outcome is not None, "Implement close accepted the review."
    missing = [n for n in needles if n not in outcome]
    assert not missing, f"The refusal does not name {missing}: {outcome}"


# Single reader.


def test_single_reader_met_verdicts_are_accepted_and_stored_with_the_round(tmp_path, monkeypatch):
    """Red. The single reader returns a "met" verdict for each review-only requirement;
    implement closes and the round's result stores the operative assessments. Today the extra
    property is refused as a malformed review."""
    root = implement_unit(tmp_path / "p")
    Readers(monkeypatch, native={"assessments": all_met()})
    assert_accepted(root, close_implement(root))
    assert verdicts(operative_assessments(latest_result(root))) == {NAMING: "met", CHANGELOG: "met"}


def test_single_reader_prompt_lists_each_review_only_requirement_and_its_reason(tmp_path, monkeypatch):
    """Red. The implement review prompt names each review-only requirement by reference and
    name, with its reason, and asks for requirement_assessments. Today it carries none."""
    root = implement_unit(tmp_path / "p")
    readers = Readers(monkeypatch, native={"assessments": all_met()})
    close_implement(root)
    prompt = readers.prompts["native"][0]
    for needle in (NAMING, "Cancel naming", NAMING_REASON, CHANGELOG, "Changelog entry", CHANGELOG_REASON,
                   "requirement_assessments"):
        assert needle in prompt, f"The implement review prompt does not carry {needle!r}."
    assert f"{SPEC_PATH}#cancel-once" not in prompt, "A behavioral requirement is listed for assessment."


def test_single_reader_omitting_an_assessment_is_refused(tmp_path, monkeypatch):
    """Red. A single-reader result with no assessment for one review-only requirement is
    refused through the validator, naming the requirement, and implement is not accepted.
    Today the review is accepted. Catches: requiring the property but not every entry."""
    root = implement_unit(tmp_path / "p")
    Readers(monkeypatch, native={"assessments": all_met()[:1]})
    outcome = close_implement(root)
    assert_refused_naming(outcome, CHANGELOG)
    assert not store.load(root, UNIT)["phases"]["implement"]["evidence"]


def test_single_reader_omitting_the_property_is_refused(tmp_path, monkeypatch):
    """Red. A single-reader result without requirement_assessments is refused when the unit
    has review-only requirements. Today it is accepted."""
    root = implement_unit(tmp_path / "p")
    Readers(monkeypatch, native={})
    outcome = close_implement(root)
    assert outcome is not None and "requirement_assessments" in outcome, outcome
    assert not store.load(root, UNIT)["phases"]["implement"]["evidence"]


MALFORMED = {
    "duplicated": ([*all_met(), assess(NAMING)], NAMING),
    "unknown": ([*all_met(), assess(f"{SPEC_PATH}#cancel-once")], f"{SPEC_PATH}#cancel-once"),
    "bad-verdict": ([{**all_met()[0], "verdict": "partly met"}, all_met()[1]], "verdict"),
    "empty-evidence": ([{**all_met()[0], "evidence": "  "}, all_met()[1]], "evidence"),
    "not-met-without-remedy": ([{k: v for k, v in assess(NAMING, "not met").items() if k != "remedy"},
                                all_met()[1]], "remedy"),
    "missing-requirement-field": ([{k: v for k, v in all_met()[0].items() if k != "requirement"},
                                   all_met()[1]], "requirement"),
}


@pytest.mark.parametrize("variant", sorted(MALFORMED))
def test_single_reader_malformed_assessments_are_refused_naming_the_problem(tmp_path, monkeypatch, variant):
    """Red. A duplicated, unknown (a behavioral requirement) or malformed assessment refuses the
    result, naming the problem (the reference, or the bad field). Today the extra property is
    refused generically without naming it. Catches: checking only that each listed requirement
    appears, letting an extra or doubled entry through."""
    root = implement_unit(tmp_path / "p")
    assessments, needle = MALFORMED[variant]
    Readers(monkeypatch, native={"assessments": assessments})
    outcome = close_implement(root)
    assert_refused_naming(outcome, needle)
    assert not store.load(root, UNIT)["phases"]["implement"]["evidence"]


def test_single_reader_not_met_yields_one_blocker_at_the_requirement(tmp_path, monkeypatch):
    """Red. A "not met" verdict adds exactly one blocker to the operative findings: titled with
    the requirement's name, located at its reference, carrying the assessment's evidence and
    remedy; close is refused as over blocking defects. Today the property is refused as
    malformed, with no blocker."""
    root = implement_unit(tmp_path / "p")
    missed = assess(NAMING, "not met", "src/app.py:1 defines release, not cancel_release.",
                    "Rename the public function to cancel_release.")
    Readers(monkeypatch, native={"assessments": [missed, all_met()[1]]})
    outcome = close_implement(root)
    assert outcome is not None and "Review found blocking defects" in outcome, outcome
    [blocker] = requirement_blockers(latest_result(root), NAMING)
    assert blocker["severity"] == "blocker"
    assert "Cancel naming" in blocker["title"]
    assert blocker["evidence"] == missed["evidence"] and blocker["remedy"] == missed["remedy"]
    assert not requirement_blockers(latest_result(root), CHANGELOG)


# Unit without review-only requirements.


def test_without_review_only_requirements_the_review_schema_is_unchanged(tmp_path, monkeypatch):
    # Guard: no review-only requirements, no new property.
    """Guard: a unit with no review-only requirement gets today's review schema and a prompt
    with no requirement_assessments, and a review without the property is accepted. Catches:
    adding the property (or its rules) to every implement review."""
    root = implement_unit(tmp_path / "p", marked=False)
    readers = Readers(monkeypatch, native={})
    assert_accepted(root, close_implement(root))
    assert readers.schemas["native"][0] == review.wire_contract(review.SCHEMA, managed=True)
    assert "requirement_assessments" not in readers.prompts["native"][0]


# Native reader plus the configured second reader.


def test_dual_readers_agreeing_met_without_candidates_need_no_adjudication(tmp_path, monkeypatch):
    """Red. Both readers say "met" for every requirement and report no findings: no
    adjudication runs, implement closes, and the stored assessments carry the native reader's
    evidence. Today both results are refused as malformed (the native) or ignored."""
    root = implement_unit(tmp_path / "p")
    second_reader(root)
    readers = Readers(monkeypatch, native={"assessments": all_met("native")},
                      external={"assessments": all_met("external")})
    assert_accepted(root, close_implement(root))
    assert "adjudication" not in readers.prompts, "Adjudication ran although the readers agreed."
    stored = operative_assessments(latest_result(root))
    assert verdicts(stored) == {NAMING: "met", CHANGELOG: "met"}
    assert all(a["evidence"].startswith("native:") for a in stored), stored


def test_dual_readers_disagreeing_without_candidates_run_adjudication_whose_verdict_is_operative(tmp_path, monkeypatch):
    """Red. The native reader says "met", the second reader "not met", with no findings: the
    disagreement alone makes adjudication run; adjudication sees each reader's assessments and
    its "met" verdicts are operative, so implement closes. Catches: skipping adjudication when
    there are no candidates; blocking on any reader's "not met"; checking only the first
    reader."""
    root = implement_unit(tmp_path / "p")
    second_reader(root)
    dissent = assess(NAMING, "not met", "external: release is not prefixed with cancel_.", "external remedy.")
    readers = Readers(
        monkeypatch,
        native={"assessments": all_met("native")},
        external={"assessments": [dissent, all_met("external")[1]]},
        adjudication={"assessments": all_met("adjudicated")},
    )
    assert_accepted(root, close_implement(root))
    assert len(readers.prompts.get("adjudication", [])) == 1, "Adjudication did not run once."
    prompt = readers.prompts["adjudication"][0]
    assert dissent["evidence"] in prompt and "native: names follow the convention." in prompt, (
        "Adjudication does not see each reader's assessments.")
    stored = operative_assessments(latest_result(root))
    assert verdicts(stored) == {NAMING: "met", CHANGELOG: "met"}
    assert all(a["evidence"].startswith("adjudicated:") for a in stored), stored


def test_dual_adjudication_not_met_is_one_blocker(tmp_path, monkeypatch):
    """Red. When adjudication rules "not met" after a disagreement, its verdict is operative:
    exactly one blocker at the requirement, with adjudication's evidence and remedy. Today
    adjudication never runs without candidates and the review is accepted."""
    root = implement_unit(tmp_path / "p")
    second_reader(root)
    final = assess(NAMING, "not met", "adjudicated: release lacks the cancel_ prefix.", "adjudicated remedy.")
    Readers(
        monkeypatch,
        native={"assessments": all_met("native")},
        external={"assessments": [assess(NAMING, "not met"), all_met("external")[1]]},
        adjudication={"assessments": [final, all_met("adjudicated")[1]]},
    )
    outcome = close_implement(root)
    assert outcome is not None and "Review found blocking defects" in outcome, outcome
    [blocker] = requirement_blockers(latest_result(root), NAMING)
    assert blocker["severity"] == "blocker"
    assert blocker["evidence"] == final["evidence"] and blocker["remedy"] == final["remedy"]


def test_dual_adjudication_omitting_an_assessment_is_refused(tmp_path, monkeypatch):
    """Red. After a disagreement, an adjudication result missing one review-only requirement's
    assessment is refused like any malformed adjudication, naming the requirement, and
    implement is not accepted. Today the review is accepted."""
    root = implement_unit(tmp_path / "p")
    second_reader(root)
    readers = Readers(
        monkeypatch,
        native={"assessments": all_met("native")},
        external={"assessments": [assess(NAMING, "not met"), all_met("external")[1]]},
        adjudication={"assessments": all_met("adjudicated")[:1]},
    )
    outcome = close_implement(root)
    assert "adjudication" in readers.prompts, "Adjudication did not run after the disagreement."
    assert_refused_naming(outcome, CHANGELOG)
    assert not store.load(root, UNIT)["phases"]["implement"]["evidence"]


@pytest.mark.parametrize("silent", ["native", "external"])
def test_dual_reader_omitting_assessments_is_refused(tmp_path, monkeypatch, silent):
    """Red. Each independent reader must return assessments: a native or second reader that
    leaves requirement_assessments out is refused and implement is not accepted. Catches:
    validating only the native reader's result. Today both clean reviews are accepted."""
    root = implement_unit(tmp_path / "p")
    second_reader(root)
    plan = {"native": {"assessments": all_met("native")}, "external": {"assessments": all_met("external")},
            "adjudication": {"assessments": all_met("adjudicated")}}
    plan[silent] = {}
    Readers(monkeypatch, **plan)
    outcome = close_implement(root)
    assert outcome is not None, "A reader without requirement assessments was accepted."
    assert not store.load(root, UNIT)["phases"]["implement"]["evidence"]
    failure = latest_result(root).get("second_reader_failure")
    if silent == "native":
        assert not failure, f"The second reader's complete assessments were refused: {failure}"
        assert "requirement_assessments" in outcome, outcome
    else:
        assert "requirement_assessments" in f"{outcome} {failure or ''}", (outcome, failure)


def test_dual_readers_both_not_met_yield_one_blocker_from_the_native_reader(tmp_path, monkeypatch):
    """Red. Both readers say "not met" for one requirement with no findings: the agreed verdict
    is operative without adjudication and yields exactly one blocker carrying the native
    reader's evidence and remedy. Catches: one blocker per reader; taking the second reader's
    text. Today the review is accepted."""
    root = implement_unit(tmp_path / "p")
    second_reader(root)
    mine = assess(NAMING, "not met", "native: release lacks the prefix.", "native: rename it.")
    theirs = assess(NAMING, "not met", "external: no cancel_ prefix.", "external: rename.")
    readers = Readers(monkeypatch, native={"assessments": [mine, all_met("native")[1]]},
                      external={"assessments": [theirs, all_met("external")[1]]})
    outcome = close_implement(root)
    assert outcome is not None and "Review found blocking defects" in outcome, outcome
    assert "adjudication" not in readers.prompts
    [blocker] = requirement_blockers(latest_result(root), NAMING)
    assert blocker["evidence"] == mine["evidence"] and blocker["remedy"] == mine["remedy"]


def test_dual_readers_with_candidates_both_not_met_yield_one_blocker_through_adjudication(tmp_path, monkeypatch):
    """Red. Both readers say "not met" and each reports a finding, so adjudication runs; its
    "not met" yields exactly one requirement blocker beside the adjudicated finding. Catches:
    adding a blocker for each reader's verdict as well as adjudication's."""
    root = implement_unit(tmp_path / "p")
    second_reader(root)
    candidate = {**finding(), "severity": "suggestion"}
    readers = Readers(
        monkeypatch,
        native={"findings": [candidate], "assessments": [assess(NAMING, "not met"), all_met()[1]]},
        external={"findings": [candidate], "assessments": [assess(NAMING, "not met"), all_met()[1]]},
        adjudication={"assessments": [assess(NAMING, "not met", "adjudicated: no prefix.", "adjudicated: rename."),
                                      all_met("adjudicated")[1]]},
    )
    outcome = close_implement(root)
    assert "adjudication" in readers.prompts
    assert outcome is not None and "Review found blocking defects" in outcome, outcome
    [blocker] = requirement_blockers(latest_result(root), NAMING)
    assert blocker["evidence"] == "adjudicated: no prefix."


# --- prompts and the constraint registry ----------------------------------------------------


def rule_ids(prompt):
    return {item["id"] for group, items in packet_of(prompt)["rules"].items() if group != "preamble"
            for item in items}


def rules_text(prompt):
    return json.dumps(packet_of(prompt)["rules"])


def test_registry_renders_assessment_rules_only_for_implement_with_review_only_requirements(tmp_path, monkeypatch):
    """Red. The implement review of a unit with review-only requirements carries registry
    entries that a unit without them does not; those entries are registered for the review and
    adjudication kinds (not the challenge), and together state the property, the entry fields
    and verdicts, and that "not met" is a blocker. Today no such entry exists."""
    from fbk.workflow import constraints

    marked = implement_unit(tmp_path / "marked")
    readers = Readers(monkeypatch, native={"assessments": all_met()})
    close_implement(marked)
    with_rules = readers.prompts["native"][0]
    plain = implement_unit(tmp_path / "plain", marked=False)
    readers = Readers(monkeypatch, native={})
    close_implement(plain)
    without = readers.prompts["native"][0]
    new = rule_ids(with_rules) - rule_ids(without)
    assert new, "The implement prompt states no extra rule for review-only requirements."
    assert "requirement_assessments" not in rules_text(without)
    sentences = []
    for entry_id in new:
        entry = constraints.BY_ID[entry_id]
        assert {"review", "adjudication"} <= entry.applies_to, entry_id
        assert "challenge" not in entry.applies_to, entry_id
        sentences += [r["rule"] for r in constraints.rules(packet_of(with_rules)["rules"]) if r["id"] == entry_id]
    text = " ".join(sentences)
    for needle in ("requirement_assessments", "verdict", "not met", "evidence", "remedy", "blocker"):
        assert needle in text, f"The new rules do not state {needle!r}: {text}"


def test_second_reader_gets_the_same_rules_and_adjudication_states_them(tmp_path, monkeypatch):
    """Red. The second reader's prompt carries the same rules block as the native reader's,
    including the assessment rules, and the adjudication pass states requirement_assessments in
    its own rules. Today neither mentions it."""
    root = implement_unit(tmp_path / "p")
    second_reader(root)
    readers = Readers(
        monkeypatch,
        native={"assessments": all_met("native")},
        external={"assessments": [assess(NAMING, "not met"), all_met("external")[1]]},
        adjudication={"assessments": all_met("adjudicated")},
    )
    close_implement(root)
    native, external = readers.prompts["native"][0], readers.prompts["external"][0]
    assert packet_of(external)["rules"] == packet_of(native)["rules"]
    assert "requirement_assessments" in rules_text(native)
    assert "adjudication" in readers.prompts, "Adjudication did not run after the disagreement."
    adjudication = readers.prompts["adjudication"][0]
    assert "requirement_assessments" in adjudication[adjudication.index("fresh final assessor"):], (
        "The adjudication pass is not told to return requirement_assessments.")


def spec_review_prompt(root, monkeypatch, spec):
    """Close spec through the real review path and return the reader's prompt and schema."""
    accepted_through_design(root, spec=spec)
    enter(root, "spec")
    readers = Readers(monkeypatch, native={})
    try:
        close.close_phase(root, UNIT, "spec", "s")
    except store.WorkflowError as exc:
        pytest.fail(f"spec close refused: {exc}")
    return readers.prompts["native"][0], readers.schemas["native"][0]


SPEC_TWO_MARKERS = MARKED_SPEC.replace(
    "### Restore command\n\n",
    "### Restore command\n\nChecked by review: the restore wording is judged by a reader.\n\n",
)


def test_spec_review_is_told_each_review_only_requirement_and_its_reason(tmp_path, monkeypatch):
    """Red. The spec review prompt names each review-only requirement with its reason and asks
    the reader to judge each marker against observable behavior. Today it carries neither."""
    prompt, _ = spec_review_prompt(tmp_path, monkeypatch, SPEC_TWO_MARKERS)
    for needle in ("History listing", LISTING_REASON, "Restore command",
                   "the restore wording is judged by a reader."):
        assert needle in prompt, f"The spec review prompt does not carry {needle!r}."
    assert re.search(r"review-only|Checked by review", prompt, re.I), (
        "The spec review is not asked to judge the review-only markers.")
    assert_marker_judgment(prompt)


def sentences(text):
    return re.split(r"(?<=[.;:])\s+|\\n|\n", text)


def assert_marker_judgment(prompt):
    """The prompt tells the reader to judge each marker, and that a marker on a requirement
    naming observable behavior an executable check could verify is a blocker."""
    assert re.search(r"\b(judge|assess|check)\b[^.]*\beach marker", prompt, re.I), (
        "The spec review prompt does not ask the reader to judge each marker.")
    blocking = [s for s in sentences(prompt)
                if all(re.search(w, s, re.I) for w in (r"marker", r"observable", r"executable", r"blocker"))]
    assert blocking, ("The spec review prompt does not say that a marker on a requirement naming observable "
                      "behavior an executable check could verify is a blocker.")


def test_spec_council_members_are_each_told_to_judge_the_markers(tmp_path, monkeypatch):
    # Guard: passes since the step 9a build; pins the marker judgment on the spec council route.
    """Guard: with a spec council, every member's prompt lists the review-only requirements and
    carries the marker judgment instruction. Catches: adding the instruction only on the single
    reader's route."""
    from tests.test_workflow_review import choose

    accepted_through_design(tmp_path, spec=SPEC_TWO_MARKERS)
    choose(tmp_path, "council", members=["builder", "guardian"])
    enter(tmp_path, "spec")
    readers = Readers(monkeypatch, native={})
    try:
        close.close_phase(tmp_path, UNIT, "spec", "s")
    except store.WorkflowError as exc:
        pytest.fail(f"spec close refused: {exc}")
    prompts = readers.prompts["native"]
    assert len(prompts) == 2, "Each council member should be asked once."
    for prompt in prompts:
        for needle in ("History listing", LISTING_REASON, "Restore command"):
            assert needle in prompt, f"A council member's prompt does not carry {needle!r}."
        assert_marker_judgment(prompt)


def test_spec_review_carries_no_assessment_property_or_rules(tmp_path, monkeypatch):
    # Guard: the assessment belongs to the implement review only.
    """Guard: the spec review of a unit with review-only requirements keeps today's schema and
    rules. Catches: rendering the assessment rules or schema in every phase."""
    prompt, schema = spec_review_prompt(tmp_path, monkeypatch, MARKED_SPEC)
    assert "requirement_assessments" not in json.dumps(schema)
    assert "requirement_assessments" not in rules_text(prompt)


def test_test_checkpoint_review_does_not_assess_review_only_requirements(tmp_path, monkeypatch):
    # Guard: the checkpoint's review is out of scope for assessments.
    """Guard: the test checkpoint of a unit with review-only requirements runs its review
    without requirement_assessments and passes. Catches: requiring assessments from every
    review held inside the implement phase."""
    root = tmp_path / "p"
    root.mkdir()
    scenarios.project.__wrapped__(root)
    unit = root / f".fbk/{UNIT}"
    (unit / "spec.md").write_text(IMPLEMENT_SPEC)
    tasks = store.read_json(unit / "tasks.json")
    for each in tasks:
        each["acceptance_refs"] += [NAMING, CHANGELOG]
    store.atomic_json(unit / "tasks.json", tasks)
    scenarios.enter_implementation(root)
    scenarios.run_test_tasks(root)
    readers = Readers(monkeypatch, native={})
    close.close_checkpoint(root, UNIT, "s")
    assert engine.implement_stage(root, store.load(root, UNIT)) == "writing-code"
    assert "requirement_assessments" not in json.dumps(readers.schemas["native"][0])


# --- review round 1 -------------------------------------------------------------------------
# Lead's rulings on the round-1 cross-model review findings (2026-10-23):
# 1. The marker starts at the beginning of its line: any leading spaces or tab make it a
#    misplaced marker, refused at spec close, and it exempts nothing at breakdown.
# 2. Blockers synthesized from "not met" verdicts are not held to the reader's output limits
#    (24 findings, a 300-character location); the reader's own limits stay enforced.
# 3. The breakdown and test checkpoint prompts list the review-only requirements, say they need
#    no test, and limit the per-requirement test obligation to behavioral requirements.
# 4. The spec review prompt instructs judging each marker (asserted above).
# 5. A child's implement review assesses exactly the child's own review-only requirements.

INDENTS = {"1-space": " ", "2-spaces": "  ", "3-spaces": "   ", "4-spaces": "    ", "tab": "\t"}


def indented_spec(indent):
    return SPEC.replace(
        "### History listing\n\n",
        f"### History listing\n\n{indent}Checked by review: {LISTING_REASON}\n\n",
    )


@pytest.mark.parametrize("indent", sorted(INDENTS))
def test_indented_marker_is_refused_at_spec_close(tmp_path, indent):
    """Red. A marker line with any leading spaces or a tab, even as the item's first non-blank
    line, is refused at spec close naming the file, line and requirement. Today the line is
    stripped before it is recognized, so it is accepted as a marker."""
    spec = indented_spec(INDENTS[indent])
    accepted_through_design(tmp_path, spec=spec)
    message = refused(tmp_path, "spec")
    names_line(message, SPEC_PATH, line_number(spec, "Checked by review:"), "History listing")


@pytest.mark.parametrize("indent", sorted(INDENTS))
def test_indented_marker_does_not_exempt_the_requirement_at_breakdown(tmp_path, indent):
    """Red. An indented marker does not make the requirement review-only: breakdown's coverage
    check still demands a test task for it. Spec close refuses such a spec, so this drives the
    coverage check (``traceability.task_coverage``) directly on the unit's written documents,
    the lowest real level. Today the indented line exempts the requirement."""
    from fbk.workflow import traceability
    from tests.test_workflow_task_traceability import project_files
    from tests.test_workflow_traceability import feature

    feature(tmp_path, spec=indented_spec(INDENTS[indent]))
    project_files(tmp_path)
    with pytest.raises(store.WorkflowError) as failure:
        traceability.task_coverage(tmp_path, store.load(tmp_path, UNIT), marked_tasks())
    line = lines_naming(str(failure.value), "History listing")
    assert line and re.search(r"test task", line, re.I), str(failure.value)


MANY = [f"{SPEC_PATH}#rule-{i:02d}" for i in range(1, 26)]
MANY_SPEC = IMPLEMENT_SPEC.split("### Cancel naming")[0] + "".join(
    f"### Rule {i:02d}\n\nChecked by review: rule {i:02d} is a convention people read.\n\n"
    "Serves [Release on cancel](prd.md#release-on-cancel).\n\n"
    for i in range(1, 26)
)


def test_twenty_five_not_met_verdicts_yield_twenty_five_blockers(tmp_path, monkeypatch):
    """Red. Twenty-five "not met" verdicts and no reader findings yield a round whose operative
    findings hold one blocker at each requirement, and close stops over blocking defects; an
    approval over findings then closes implement on that round. Today the synthesized blockers
    exceed the reader's 24-finding limit and close refuses the review as malformed."""
    root = implement_unit(tmp_path / "p", spec=MANY_SPEC, review_refs=MANY)
    Readers(monkeypatch, native={"assessments": [assess(ref, "not met") for ref in MANY]})
    outcome = close_implement(root)
    assert outcome is not None and "Review found blocking defects" in outcome, outcome
    result = latest_result(root)
    for ref in MANY:
        assert len(requirement_blockers(result, ref)) == 1, f"{ref} does not have exactly one blocker."
    scenarios.mutate(root, engine.approve, "s", "close-over-findings", "implement",
                     "The operator accepts the open conventions.")
    assert_accepted(root, close_implement(root))


LONG_NAME = "Naming " + " ".join(["convention"] * 30)
LONG_REF = f"{SPEC_PATH}#{LONG_NAME.lower().replace(' ', '-')}"
LONG_SPEC = IMPLEMENT_SPEC.replace("### Cancel naming", f"### {LONG_NAME}")


def test_a_requirement_reference_over_300_characters_keeps_its_blocker_and_exact_location(tmp_path, monkeypatch):
    """Red. A valid review-only requirement whose reference is longer than 300 characters still
    yields its blocker, located at the exact reference. Today the synthesized finding breaks the
    reader's 300-character location limit and close refuses the review as malformed."""
    assert len(LONG_REF) > 300
    root = implement_unit(tmp_path / "p", spec=LONG_SPEC, review_refs=(LONG_REF, CHANGELOG))
    Readers(monkeypatch, native={"assessments": [assess(LONG_REF, "not met"), all_met()[1]]})
    outcome = close_implement(root)
    assert outcome is not None and "Review found blocking defects" in outcome, outcome
    [blocker] = requirement_blockers(latest_result(root), LONG_REF)
    assert blocker["location"] == LONG_REF and blocker["severity"] == "blocker"


def test_single_reader_returning_nine_findings_is_still_refused(tmp_path, monkeypatch):
    # Guard: passes today; the reader's own output limits must stay enforced.
    """Guard: a single reader returning nine findings (over its eight) is refused even when the
    unit has review-only requirements. Catches: lifting the reader's limits to make room for the
    synthesized blockers."""
    root = implement_unit(tmp_path / "p")
    nine = [{**finding(), "severity": "suggestion", "title": f"Suggestion {i}"} for i in range(9)]
    Readers(monkeypatch, native={"findings": nine, "assessments": all_met()})
    outcome = close_implement(root)
    assert outcome is not None and re.search(r"bounded", outcome, re.I), outcome
    assert not store.load(root, UNIT)["phases"]["implement"]["evidence"]


NO_TEST = re.compile(
    r"(review-only|Checked by review)[^.]*\b(no|without( a)?|not need( a)?)\s+tests?\b"
    r"|\b(no|without( a)?)\s+tests?\b[^.]*(review-only|Checked by review)",
    re.I,
)


def breakdown_prompt(root, monkeypatch):
    scenarios.accept(root, "intent")
    scenarios.accept(root, "spec")
    scenarios.enter(root, "breakdown")
    readers = Readers(monkeypatch, native={})
    try:
        close.close_phase(root, UNIT, "breakdown", "s")
    except store.WorkflowError as exc:
        pytest.fail(f"breakdown close refused: {exc}")
    return readers.prompts["native"][0]


def checkpoint_prompt(root, monkeypatch):
    scenarios.enter_implementation(root)
    scenarios.run_test_tasks(root)
    readers = Readers(monkeypatch, native={})
    try:
        close.close_checkpoint(root, UNIT, "s")
    except store.WorkflowError as exc:
        pytest.fail(f"test checkpoint refused: {exc}")
    return readers.prompts["native"][0]


def obligations(prompt):
    return packet_of(prompt)["reading_priority"]["acceptance_obligations"]


def assert_tests_scoped_to_behavioral(prompt):
    per_requirement = [o for o in obligations(prompt) if re.search(r"material requirement", o, re.I)]
    unscoped = [o for o in per_requirement if not re.search(r"behavioral", o, re.I)]
    assert not unscoped, f"A per-requirement test obligation is not limited to behavioral requirements: {unscoped}"
    assert any(re.search(r"behavioral", o, re.I) for o in obligations(prompt)), (
        "No obligation limits the test demand to behavioral requirements.")


@pytest.mark.parametrize("prompt_of", [breakdown_prompt, checkpoint_prompt], ids=["breakdown", "checkpoint"])
def test_test_reviews_list_review_only_requirements_and_need_no_test_for_them(tmp_path, monkeypatch, prompt_of):
    """Red. The breakdown and test checkpoint review prompts list the unit's review-only
    requirements, say they need no test, and limit the "each material requirement" test
    obligation to behavioral requirements. Today neither prompt mentions them, so a reviewer
    following its instructions could block the deliberately absent test."""
    prompt = prompt_of(marked_project(tmp_path / "p"), monkeypatch)
    for needle in (NAMING, "Cancel naming", CHANGELOG, "Changelog entry"):
        assert needle in prompt, f"The prompt does not list {needle!r}."
    assert NO_TEST.search(prompt), "The prompt does not say review-only requirements need no test."
    assert_tests_scoped_to_behavioral(prompt)


@pytest.mark.parametrize("prompt_of", [breakdown_prompt, checkpoint_prompt], ids=["breakdown", "checkpoint"])
def test_test_reviews_without_review_only_requirements_stay_as_today(tmp_path, monkeypatch, prompt_of):
    # Guard: passes today; prompts of units without review-only requirements are unchanged.
    """Guard: without review-only requirements, the breakdown and checkpoint prompts carry no
    review-only text and keep the "each material requirement" obligation. Catches: adding the
    review-only block or wording to every unit's prompts."""
    root = tmp_path / "p"
    root.mkdir()
    scenarios.project.__wrapped__(root)
    prompt = prompt_of(root, monkeypatch)
    assert not re.search(r"review-only|review_only|Checked by review", prompt, re.I)
    assert any(re.search(r"each material requirement", o, re.I) for o in obligations(prompt))


CHILD_REVIEW_SPEC = """\
# Console contract

## Requirements

### Button cancels

From [Console button](design/console.md#console-button) and the parent's
[Job state machine](../platform/design/overview.md#job-state-machine).

### Scheduler reuse

Checked by review: reuse is a structural choice read in the code.

From [Reuse scheduler](design/console.md#reuse-scheduler).
"""
PARENT_REVIEW_SPEC = """\
# Platform contract

## Requirements

### Scheduler API

Checked by review: the API's naming is a convention.

From [One scheduler](design/overview.md#one-scheduler).

### Cancel API

From [Job state machine](design/overview.md#job-state-machine).
"""
CHILD_REF = ".fbk/child/spec.md#scheduler-reuse"
PARENT_REF = ".fbk/platform/spec.md#scheduler-api"


def child_in_implement(root):
    """A project unit and a child feature unit, both with a review-only requirement in their
    own spec, the child in implement."""
    from tests import test_workflow_traceability as docs
    from tests.test_workflow_task_traceability import into_implement, project_files

    base = docs.make_unit(root, "platform", kind="project")
    docs.write(base, "prd.md", docs.PARENT_PRD)
    docs.write(base, "design/overview.md", docs.PARENT_DESIGN)
    docs.write(base, "spec.md", PARENT_REVIEW_SPEC)
    for phase in ("intent", "design", "spec"):
        accept(root, phase, unit="platform")
    child = docs.make_unit(root, "child", parent="platform")
    docs.write(child, "prd.md", docs.CHILD_PRD)
    docs.write(child, "design/console.md", docs.CHILD_DESIGN)
    docs.write(child, "spec.md", CHILD_REVIEW_SPEC)
    project_files(root)
    for phase in ("intent", "design", "spec"):
        accept(root, phase, unit="child")
    linked = refs("button-cancels", "scheduler-reuse", base=".fbk/child")
    into_implement(root, [task("child-tests", "tests", ["tests/test_restore.py"], linked),
                          task("child-code", "implementation", ["src/backup.py"], linked)], unit="child")
    return root


def child_review(root):
    """The child's implementation review through ``review.review``, the lowest real level that
    builds the prompt, schema and validator for a child record; driving the child through its
    test checkpoint and implementation tasks to implement close adds nothing to what is tested."""
    from fbk.workflow import evidence

    record = store.load(root, "child")
    return review.review(root, "child", "implement", evidence.subject(root, record, "implement"), [])


def child_assessment(ref, verdict="met"):
    return assess(ref, verdict, evidence=f"src/backup.py shows {ref.rsplit('#', 1)[1]} {verdict}.")


def test_child_review_assesses_exactly_the_childs_own_review_only_requirements(tmp_path, monkeypatch):
    # Guard: passes since the step 9a build; pins ruling 5's own-unit scope for a child.
    """Guard: a child whose own spec and whose parent's spec both have a review-only requirement
    is asked to assess only its own: the prompt lists the child's, not the parent's, the
    schema's requirement enum is exactly the child's reference, and an assessment of the child's
    requirement alone is accepted and stored. Catches: gathering review-only requirements
    through the lineage, or skipping assessments for child units."""
    child_in_implement(tmp_path)
    readers = Readers(monkeypatch, native={"assessments": [child_assessment(CHILD_REF)]})
    result = child_review(tmp_path)
    assert not result.get("error"), result.get("error")
    prompt, schema = readers.prompts["native"][0], readers.schemas["native"][0]
    assert CHILD_REF in prompt and "reuse is a structural choice read in the code." in prompt
    assert PARENT_REF not in prompt and "the API's naming is a convention." not in prompt
    enum = schema["properties"]["requirement_assessments"]["items"]["properties"]["requirement"]["enum"]
    assert enum == [CHILD_REF]
    assert verdicts(operative_assessments(result)) == {CHILD_REF: "met"}


@pytest.mark.parametrize("returned", ["omitted", "parent-instead"])
def test_child_review_omitting_its_own_assessment_is_refused(tmp_path, monkeypatch, returned):
    # Guard: passes since the step 9a build; pins the refusal for a child's omitted assessment.
    """Guard: a child review that omits its own review-only requirement, or assesses the
    parent's in its place, is refused naming the child's requirement. Catches: accepting the
    parent's requirement as the child's, or not validating child reviews."""
    child_in_implement(tmp_path)
    given = [] if returned == "omitted" else [child_assessment(PARENT_REF)]
    Readers(monkeypatch, native={"assessments": given})
    with pytest.raises(store.WorkflowError) as failure:
        child_review(tmp_path)
    assert CHILD_REF in str(failure.value), str(failure.value)


# --- review round 2 -------------------------------------------------------------------------


def test_single_reader_duplicate_replacing_another_entry_is_refused(tmp_path, monkeypatch):
    # Guard: passes against the step 9a build; pins a round-2 coverage gap.
    """A duplicate that keeps the array length: the second entry repeats the first requirement
    in place of the other one. Refused, naming the duplicate or the requirement left unassessed.
    Catches: a validator checking only the entry count and that each reference is allowed."""
    root = implement_unit(tmp_path / "p")
    Readers(monkeypatch, native={"assessments": [assess(NAMING), assess(NAMING, evidence="Again.")]})
    outcome = close_implement(root)
    assert outcome is not None, "Two assessments of one requirement were accepted."
    assert NAMING in outcome or CHANGELOG in outcome, outcome
    assert not store.load(root, UNIT)["phases"]["implement"]["evidence"]


def test_dual_readers_disagreeing_only_on_a_later_requirement_run_adjudication(tmp_path, monkeypatch):
    # Guard: passes against the step 9a build; pins a round-2 coverage gap.
    """The readers agree on the first requirement and disagree only on the second, with no
    finding candidates: adjudication runs, and its "not met" for the second is operative and
    yields one blocker there. Catches: comparing only the first verdict."""
    root = implement_unit(tmp_path / "p")
    second_reader(root)
    final = assess(CHANGELOG, "not met", "adjudicated: the changelog omits it.", "adjudicated: add the entry.")
    readers = Readers(
        monkeypatch,
        native={"assessments": all_met("native")},
        external={"assessments": [all_met("external")[0], assess(CHANGELOG, "not met")]},
        adjudication={"assessments": [all_met("adjudicated")[0], final]},
    )
    outcome = close_implement(root)
    assert len(readers.prompts.get("adjudication", [])) == 1, "Adjudication did not run once."
    assert outcome is not None and "Review found blocking defects" in outcome, outcome
    result = latest_result(root)
    assert verdicts(operative_assessments(result)) == {NAMING: "met", CHANGELOG: "not met"}
    [blocker] = requirement_blockers(result, CHANGELOG)
    assert blocker["evidence"] == final["evidence"] and blocker["remedy"] == final["remedy"]
    assert not requirement_blockers(result, NAMING)


@pytest.mark.parametrize("agreed,ruled", [("met", "not met"), ("not met", "met")])
def test_adjudication_overrules_agreeing_readers_when_a_candidate_makes_it_run(tmp_path, monkeypatch, agreed, ruled):
    # Guard: passes against the step 9a build; pins a round-2 coverage gap.
    """Both readers give the same verdict on a requirement and each reports a finding, so
    adjudication runs; when it reverses that verdict, the stored assessment and the
    requirement's blocker (or its absence) follow adjudication. Catches: keeping the readers'
    agreed verdicts while adjudicating only the findings."""
    root = implement_unit(tmp_path / "p")
    second_reader(root)
    candidate = {**finding(), "severity": "suggestion"}
    readers = Readers(
        monkeypatch,
        native={"findings": [candidate], "assessments": [assess(NAMING, agreed), all_met("native")[1]]},
        external={"findings": [candidate], "assessments": [assess(NAMING, agreed), all_met("external")[1]]},
        adjudication={"assessments": [assess(NAMING, ruled, "adjudicated: verdict reversed."),
                                      all_met("adjudicated")[1]]},
    )
    close_implement(root)
    assert "adjudication" in readers.prompts, "Adjudication did not run with finding candidates."
    result = latest_result(root)
    stored = operative_assessments(result)
    assert verdicts(stored)[NAMING] == ruled
    assert next(a for a in stored if a["requirement"] == NAMING)["evidence"] == "adjudicated: verdict reversed."
    blockers = requirement_blockers(result, NAMING)
    if ruled == "not met":
        assert len(blockers) == 1 and blockers[0]["evidence"] == "adjudicated: verdict reversed."
    else:
        assert not blockers, f"A blocker survives adjudication's met verdict: {blockers}"
