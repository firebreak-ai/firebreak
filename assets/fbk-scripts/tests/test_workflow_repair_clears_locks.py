"""A contradiction repair that invalidates breakdown clears the test locks, as a breakdown reopen
does (operator, 2026-10-23; plan decision 11).

When such a repair invalidates breakdown, and with it the test checkpoint, it clears the locks,
the outstanding unlocks and the lock origin, and discards the saved copies of locked tests, in
the same durable save that invalidates acceptance, so a repair that fails or is recovered after
that save leaves them cleared. The repair's event records the cleared values the way a
``reopened`` event records ``cleared_locks``, ``cleared_unlocks`` and ``cleared_lock_origin``. A
reference repair, and a contradiction repair that does not invalidate breakdown, keep the locks.

Shapes the tests assume: the cleared values appear under those three keys on some repair event
(``repair-prepared``, ``repair-completed`` or another ``repair-*`` event) recorded by the repair.

Red or guard: **red** tests fail today on an assertion about missing behavior; **guard** tests
(marked ``# Guard:``) pass today and pin behavior that must not regress.
"""

import sys

import pytest

from fbk.workflow import engine, repair, store
from tests import test_workflow_lifecycle as scenarios
from tests.test_workflow_commands import call
from tests.test_workflow_implement_stages import CHECK, stage, start
from tests.test_workflow_lock_enforcement import RELEASE, copy_of
from tests.test_workflow_repairs import authorize
from tests.test_workflow_test_checkpoint import CK, scoped_test_hashes
from tests.test_workflow_unlock_rework_reopen import finish

project = scenarios.project

UNIT = "feature"
EQUIVALENT = {"status": "equivalent", "evidence": "The quoted source settles it."}
SPEC_REPAIR = {
    "kind": "contradiction", "path": f".fbk/{UNIT}/spec.md",
    "before": "Release exactly once.", "after": "Release exactly once. Cancel returns true once.",
    "decision_id": "cancel-return",
}


def record(root):
    return store.load(root, UNIT)


def locked(root, built=False):
    """Authorize repairs, then pass the checkpoint so the tests are locked; with ``built`` the
    implementation task also completes its release."""
    authorize(root)
    scenarios.prepare_implementation(root)
    state = record(root)
    assert state["locks"] and state.get("lock_origin") == CK and copy_of(root, RELEASE)
    if built:
        assert start(root, "cancel", "implementer") is None
        (root / "src/app.py").write_text("release()")
        finish(root, "cancel", ["src/app.py"], CHECK)
    return state


def repair_spec(root):
    return repair.apply(root, UNIT, "s", dict(SPEC_REPAIR), verifier=lambda *a: dict(EQUIVALENT))


def with_unlock(root):
    scenarios.approve_unlock(root, {RELEASE: "fail"}, [{"argv": CHECK, "tests": [RELEASE]}],
                             reason="The cancellation test asserts the wrong call.")
    assert record(root)["unlocks"] == [RELEASE]


def repair_events(root, since):
    return [e for e in record(root)["events"][since:] if e["event"].startswith("repair")]


def assert_cleared(root):
    state = record(root)
    assert state["locks"] == {}, f"The repair kept the locks: {state['locks']}"
    assert state["unlocks"] == [], f"The repair kept the unlocks: {state['unlocks']}"
    assert not state.get("lock_origin"), "The repair kept the lock origin."
    assert copy_of(root, RELEASE) is None, "The repair kept the saved copy of the locked test."


# Contradiction repair invalidating breakdown


@pytest.mark.parametrize("built", [False, True], ids=["before-code", "after-code"])
def test_a_spec_contradiction_repair_clears_locks_origin_and_copies(project, built):
    """Red. A contradiction repair of spec after the checkpoint locked the tests clears the locks,
    the lock origin and the saved copies, with or without code built."""
    locked(project, built)
    repair_spec(project)
    assert not record(project)["phases"][CK]["evidence"]
    assert_cleared(project)


def test_a_spec_contradiction_repair_clears_an_outstanding_unlock(project):
    """Red. With an unlock outstanding, the repair clears it along with the locks."""
    locked(project, built=True)
    with_unlock(project)
    repair_spec(project)
    assert_cleared(project)


def test_the_repair_event_records_the_cleared_values(project):
    """Red. Some repair event records the cleared locks, unlocks and lock origin under the keys a
    reopen uses."""
    locked(project, built=True)
    with_unlock(project)
    before = record(project)
    since = len(before["events"])
    repair_spec(project)
    events = repair_events(project, since)
    holder = next((e for e in events if "cleared_locks" in e), None)
    assert holder is not None, f"No repair event records the cleared locks: {[e['event'] for e in events]}"
    assert holder["cleared_locks"] == before["locks"]
    assert holder.get("cleared_unlocks") == before["unlocks"]
    assert holder.get("cleared_lock_origin") == CK


def test_after_the_repair_the_unit_writes_tests_again_and_the_checkpoint_relocks(project):
    """Red. After the repair, spec and breakdown are accepted again and implement re-entered: the
    unit is writing tests with no locks, an implementation task waits, and once the test task
    reruns the checkpoint locks the tests again and saves their copies."""
    locked(project, built=True)
    repair_spec(project)
    for phase in ("spec", "breakdown"):
        scenarios.accept(project, phase)
    scenarios.mutate(project, engine.approve, "s", "start-implementation", "implement", "Proceed with the repaired plan.")
    scenarios.enter(project, "implement")
    assert record(project)["locks"] == {}, "Re-entering implement after the repair still holds the old locks."
    assert stage(project) == "writing-tests"
    assert start(project, "cancel", "implementer") is not None
    scenarios.run_test_tasks(project)
    assert stage(project) == "ready-for-checkpoint"
    scenarios.pass_checkpoint(project)
    state = record(project)
    assert state["locks"] == scoped_test_hashes(project) and state.get("lock_origin") == CK
    assert copy_of(project, RELEASE) is not None
    assert stage(project) == "writing-code"


# Repairs that keep the locks


def test_a_reference_repair_keeps_the_locks(project):
    # Guard: passes today; a reference repair rebinds acceptance and never touches locks.
    """Guard. A reference repair of the PRD after the checkpoint, with an unlock outstanding,
    keeps the locks, the unlock, the lock origin and the saved copies."""
    path = project / f".fbk/{UNIT}/prd.md"
    path.write_text(path.read_text().replace(
        "# Cancellation\n\n", "# Cancellation\n\nBackground: [Cancellation](#old).\n\n", 1))
    locked(project, built=True)
    with_unlock(project)
    before = record(project)
    repair.apply(project, UNIT, "s", {
        "kind": "reference", "path": f".fbk/{UNIT}/prd.md",
        "before": "[Cancellation](#old)", "after": "[Cancellation](#cancellation)",
    })
    state = record(project)
    assert not state.get("pending_repair")
    assert state["locks"] == before["locks"] and state.get("lock_origin") == CK
    assert state["unlocks"] == [RELEASE], "The reference repair revoked the outstanding unlock."
    assert copy_of(project, RELEASE) is not None


def documented(root, decision_phase):
    """The lifecycle unit with declared documentation docs/cancel.md, repair authority, and a
    decision governing ``decision_phase`` sourced from docs-decision.md, through to a passed
    checkpoint, built code and an outstanding unlock."""
    path = root / f".fbk/{UNIT}/scope.json"
    store.atomic_json(path, {**store.read_json(path), "docs": ["docs"]})
    (root / "docs").mkdir()
    (root / "docs/cancel.md").write_text("# Cancel\n\nCancel releases the resource.\n")
    (root / "docs-decision.md").write_text("Cancel releases the resource exactly once.\n")
    quote = "Cancel releases the resource exactly once."
    store.atomic_json(root / ".fbk/docs-once.json", {
        "id": "docs-once", "text": quote, "phase": decision_phase, "kind": "governs",
        "source": {"path": "docs-decision.md", "quote": quote}})
    call(root, "decision-record", UNIT, "--request", ".fbk/docs-once.json")
    locked(root, built=True)
    with_unlock(root)
    return record(root)


def repair_docs(root):
    since = len(record(root)["events"])
    repair.apply(root, UNIT, "s", {
        "kind": "contradiction", "path": "docs/cancel.md",
        "before": "Cancel releases the resource.", "after": "Cancel releases the resource exactly once.",
        "decision_id": "docs-once",
    }, verifier=lambda *a: dict(EQUIVALENT))
    assert "exactly once" in (root / "docs/cancel.md").read_text(), "The documentation repair was not applied."
    prepared = [e for e in record(root)["events"][since:] if e["event"] == "repair-prepared"]
    assert prepared, "No repair-prepared event was recorded."
    return prepared[-1]


def test_a_contradiction_repair_of_documentation_invalidates_only_implement_and_keeps_the_locks(project):
    # Guard: passes today; a repair that leaves breakdown accepted keeps the locks.
    """Guard. A contradiction repair of declared documentation, against a decision governing
    implement, invalidates implement only; breakdown stays accepted, and the locks, the
    outstanding unlock, the lock origin and the saved copies stay."""
    before = documented(project, "implement")
    prepared = repair_docs(project)
    state = record(project)
    assert not state.get("pending_repair")
    assert "breakdown" not in prepared.get("invalidated", []), prepared.get("invalidated")
    assert state["phases"]["breakdown"]["evidence"], "The documentation repair invalidated breakdown."
    assert state["phases"][CK]["evidence"] == before["phases"][CK]["evidence"]
    assert state["locks"] == before["locks"] and state.get("lock_origin") == CK
    assert state["unlocks"] == [RELEASE], "The implement-only repair revoked the outstanding unlock."
    assert copy_of(project, RELEASE) is not None


def test_a_contradiction_repair_of_documentation_governed_by_breakdown_clears_the_locks(project):
    # Guard: passes with the built change; pins clearing beyond spec repairs.
    """Guard. A contradiction repair of declared documentation against a decision governing breakdown
    invalidates breakdown, so it clears the locks, the unlock, the lock origin and the saved
    copies, recording the cleared values. Catches: clearing only for spec repairs."""
    before = documented(project, "breakdown")
    prepared = repair_docs(project)
    assert "breakdown" in prepared.get("invalidated", []), prepared.get("invalidated")
    assert not record(project)["phases"]["breakdown"]["evidence"]
    assert_cleared(project)
    assert prepared.get("cleared_locks") == before["locks"]
    assert prepared.get("cleared_unlocks") == before["unlocks"]
    assert prepared.get("cleared_lock_origin") == CK


# A repair that fails after it invalidated acceptance


def assert_cleared_values_recorded(root, since, before):
    """A saved repair event since ``since`` records the cleared locks, unlocks and origin."""
    holder = next((e for e in repair_events(root, since) if "cleared_locks" in e), None)
    assert holder is not None, "No saved repair event records the cleared locks."
    assert holder["cleared_locks"] == before["locks"]
    assert holder.get("cleared_unlocks") == before["unlocks"] and before["unlocks"]
    assert holder.get("cleared_lock_origin") == CK


def crash(*args):
    raise OSError("simulated interruption")


@pytest.mark.parametrize("step", ["_write", "_finish"])
def test_a_repair_interrupted_after_preparation_leaves_the_locks_cleared(project, monkeypatch, step):
    """Red. A contradiction repair interrupted after its durable invalidation (in the artifact
    write, or after it) leaves the locks, unlocks, lock origin and copies cleared with the
    acceptance; recovering the repair keeps them cleared."""
    locked(project, built=True)
    with_unlock(project)
    before = record(project)
    since = len(before["events"])
    original = getattr(repair, step)
    monkeypatch.setattr(repair, step, crash)
    with pytest.raises(OSError):
        repair_spec(project)
    state = record(project)
    assert state["pending_repair"] and not state["phases"][CK]["evidence"]
    assert_cleared(project)
    assert_cleared_values_recorded(project, since, before)
    monkeypatch.setattr(repair, step, original)
    repair.recover(project, UNIT, "s", "Resume the interrupted repair.")
    assert not record(project)["pending_repair"]
    assert_cleared(project)


def test_an_abandoned_repair_leaves_the_locks_cleared(project, monkeypatch):
    """Red. A contradiction repair interrupted in its write and then abandoned at recovery
    (its authority changed) leaves the locks cleared with the acceptance it invalidated."""
    locked(project, built=True)
    with_unlock(project)
    before = record(project)
    since = len(before["events"])
    monkeypatch.setattr(repair, "_write", crash)
    with pytest.raises(OSError):
        repair_spec(project)
    (project / "authority.md").write_text("Authorization revoked.")
    result = repair.recover(project, UNIT, "s", "Recover after the authority changed.")
    assert result["status"] == "abandoned"
    assert_cleared(project)
    assert_cleared_values_recorded(project, since, before)
