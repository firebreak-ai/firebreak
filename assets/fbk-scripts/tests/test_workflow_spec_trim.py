"""Spec close trims the draft before its review, once per draft, lists the cuts at the end of
the spec, and neither a failed trim nor a trim that breaks a check spends a review round."""

import pytest
from fbk.workflow import close, engine, spec_trim, store

from tests import test_workflow_lifecycle as scenarios

project = scenarios.project
SPEC = ".fbk/feature/spec.md"
EXTRA = "\n### Cancel twice\n\nA second cancel returns false. Serves [Release on cancel](prd.md#release-on-cancel).\n"


def at_spec(root):
    scenarios.accept(root, "intent")
    scenarios.enter(root, "spec")
    with open(root / SPEC, "a") as spec:
        spec.write(EXTRA)


def trimmer(calls, *, edit=lambda text: text.replace(EXTRA, ""), removed=None, failures=0):
    """A trim session that applies an edit to the spec and lists what it removed."""

    def launch(root, unit, rows, config):
        calls.append([row["id"] for row in rows])
        path = root / SPEC
        path.write_text(edit(path.read_text()))
        if len(calls) <= failures:
            # A session can fail partway, after some of its edits.
            raise store.WorkflowError("the session failed (exit 1): overloaded")
        return removed if removed is not None else [{"item": "Cancel twice", "reason": "Cancel once already shows it."}]

    return launch


def reviewing(seen, result=scenarios.clean_review):
    def reviewer(root, *args):
        seen.append((root / SPEC).read_text())
        return result()

    return reviewer


def rounds(root):
    return len(store.load(root, "feature")["phases"]["spec"]["rounds"])


def test_the_review_reads_the_trimmed_spec_ending_with_its_list(project, monkeypatch):
    at_spec(project)
    calls, seen = [], []
    monkeypatch.setattr(spec_trim, "launch", trimmer(calls))
    result = close.close_phase(project, "feature", "spec", "s", reviewer=reviewing(seen))
    assert result["accepted_phase"] == "spec"
    assert "Cancel twice" not in seen[0].split(spec_trim.SECTION)[0]
    assert seen[0].endswith(f"{spec_trim.SECTION}\n\n{spec_trim.OPENING}\n\n"
                            "- Cancel twice: Cancel once already shows it.\n")
    assert "1 item(s)" in result["spec_trim"]


def test_the_trim_sees_every_earlier_phase_decision(project, monkeypatch):
    source = project / ".fbk/feature/decisions/once.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("Release exactly once.")
    with store.transaction(project):
        record = store.load(project, "feature")
        from fbk.workflow import decisions

        decisions.record(project, record, "s", {
            "id": "release-once", "text": "Release exactly once.", "phase": "intent", "kind": "governs",
            "source": {"path": ".fbk/feature/decisions/once.md", "quote": "Release exactly once."}})
        store.save(project, record)
    at_spec(project)
    calls = []
    monkeypatch.setattr(spec_trim, "launch", trimmer(calls))
    close.close_phase(project, "feature", "spec", "s", reviewer=scenarios.clean_review)
    assert calls == [["release-once"]]


def test_the_trim_runs_once_per_draft_and_again_after_a_reopen(project, monkeypatch):
    at_spec(project)
    calls = []
    monkeypatch.setattr(spec_trim, "launch", trimmer(calls))
    with pytest.raises(store.WorkflowError, match="1 item"):
        close.close_phase(project, "feature", "spec", "s", reviewer=scenarios.blocking_review)
    path = project / SPEC
    path.write_text(path.read_text().replace("Release exactly once.", "Release it exactly once."))
    close.close_phase(project, "feature", "spec", "s", reviewer=scenarios.clean_review)
    assert len(calls) == 1
    scenarios.observe_phase(project, "spec")
    scenarios.mutate(project, engine.approve, "s", "reopen", "spec", "Revisit the contract.")
    scenarios.mutate(project, engine.reopen, "spec", "s", "Revisit the contract.")
    scenarios.enter(project, "spec")
    with open(project / SPEC, "a") as spec:
        spec.write("\n### Cancel thrice\n\nA third cancel returns false. Serves [Release on cancel](prd.md#release-on-cancel).\n")
    monkeypatch.setattr(spec_trim, "launch", trimmer(
        calls, edit=lambda text: text.split("\n### Cancel thrice")[0] + "\n",
        removed=[{"item": "Cancel thrice", "reason": "Same as cancel once."}]))
    close.close_phase(project, "feature", "spec", "s", reviewer=scenarios.clean_review)
    assert len(calls) == 2
    text = (project / SPEC).read_text()
    assert text.count(spec_trim.SECTION) == 1
    assert text.endswith("- Cancel twice: Cancel once already shows it.\n- Cancel thrice: Same as cancel once.\n")


def test_a_failed_session_is_retried_once(project, monkeypatch):
    at_spec(project)
    calls, seen = [], []
    monkeypatch.setattr(spec_trim, "launch", trimmer(calls, failures=1))
    result = close.close_phase(project, "feature", "spec", "s", reviewer=reviewing(seen))
    assert len(calls) == 2 and "Cancel twice" not in seen[0].split(spec_trim.SECTION)[0]
    assert "cut the spec" in result["spec_trim"]


def test_two_failed_sessions_leave_the_spec_untrimmed_and_spend_no_round(project, monkeypatch):
    at_spec(project)
    before = (project / SPEC).read_text()
    calls, seen = [], []
    monkeypatch.setattr(spec_trim, "launch", trimmer(calls, failures=2))
    result = close.close_phase(project, "feature", "spec", "s", reviewer=reviewing(seen))
    assert len(calls) == 2 and seen == [before]
    assert result["spec_trim"].startswith("The spec trim did not run (the session failed (exit 1): overloaded)")
    assert rounds(project) == 1


def test_a_trim_that_breaks_a_check_returns_to_the_author_without_a_round(project, monkeypatch):
    at_spec(project)
    calls = []
    raw = trimmer(calls, edit=lambda text: text.replace(EXTRA, "").replace("Release exactly", "Release exactly"))
    monkeypatch.setattr(spec_trim, "launch", raw)
    with pytest.raises(store.WorkflowError, match="U\\+00A0 NO-BREAK SPACE") as refusal:
        close.close_phase(project, "feature", "spec", "s", reviewer=scenarios.clean_review)
    assert "failed a check" in str(refusal.value)
    assert rounds(project) == 0
    status = engine.status_report(project, store.load(project, "feature"))
    assert "failed a check" in status["spec_trim"]
    # The author fixes the spec; the trim does not run again for this draft.
    path = project / SPEC
    path.write_text(path.read_text().replace(" ", " "))
    close.close_phase(project, "feature", "spec", "s", reviewer=scenarios.clean_review)
    assert len(calls) == 1 and rounds(project) == 1


def test_a_spec_with_nothing_to_cut_is_left_as_written(project, monkeypatch):
    at_spec(project)
    before = (project / SPEC).read_text()
    calls = []
    monkeypatch.setattr(spec_trim, "launch", trimmer(calls, edit=lambda text: text, removed=[]))
    result = close.close_phase(project, "feature", "spec", "s", reviewer=scenarios.clean_review)
    assert (project / SPEC).read_text() == before
    assert result["spec_trim"] == "The spec trim found nothing to cut."
