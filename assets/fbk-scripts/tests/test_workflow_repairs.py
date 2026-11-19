"""Real file repairs retain settled authority and fail closed across interruptions."""

import pytest

from fbk.workflow import decisions, engine, repair, store
from tests import test_workflow_lifecycle as scenarios

project = scenarios.project

# A spec whose one requirement states the contradicted return; the repair changes its wording.
FALSE_SPEC = (
    "# Cancellation contract\n\n## Requirements\n\n### Cancel once\n\n"
    "Cancel returns false once. Serves [Release on cancel](prd.md#release-on-cancel).\n"
)
TRUE_SPEC = FALSE_SPEC.replace("false", "true")


def authorize(root, classes=("reference", "contradiction")):
    (root / "authority.md").write_text(
        "The operator authorizes routine reference and contradiction repairs.\nCancel returns true once."
    )
    with store.transaction(root):
        record = store.load(root, "feature")
        decisions.policy(
            root,
            record,
            "s",
            {
                "classes": list(classes),
                "source": {
                    "path": "authority.md",
                    "quote": "The operator authorizes routine reference and contradiction repairs.",
                },
            },
        )
        decisions.record(
            root,
            record,
            "s",
            {
                "id": "cancel-return",
                "text": "Cancel returns true once.",
                "phase": "spec", "kind": "governs",
                "source": {
                    "path": "authority.md",
                    "quote": "Cancel returns true once.",
                },
            },
        )
        store.save(root, record)


def reference(root):
    path = root / ".fbk/feature/prd.md"
    path.write_text(
        "# Cancellation\nA canceled task releases its resource. [Cancellation](#old)."
    )
    return {
        "kind": "reference",
        "path": ".fbk/feature/prd.md",
        "before": "[Cancellation](#old)",
        "after": "[Cancellation](#cancellation)",
    }


def test_reference_repair_preserves_current_acceptance_and_audits(project):
    authorize(project)
    request = reference(project)
    scenarios.accept(project, "intent")
    before = store.load(project, "feature")["phases"]["intent"]
    repair.apply(project, "feature", "s", request)
    record = store.load(project, "feature")
    assert "(#cancellation)" in (project / request["path"]).read_text()
    assert engine.phase_state(project, record)[1] == "ready"
    assert record["phases"]["intent"]["evidence"]
    assert record["phases"]["intent"]["rounds"] == before["rounds"]
    audit = record["events"][-1]["repair"]
    assert audit["before_hash"] != audit["after_hash"]
    assert audit["before"] == request["before"]


@pytest.mark.parametrize("change", ["label", "target", "valid", "duplicate"])
def test_reference_proof_rejects_ambiguous_or_behavior_changing_links(project, change):
    authorize(project)
    request = reference(project)
    path = project / request["path"]
    if change == "label":
        request["after"] = "[Other](#cancellation)"
    elif change == "target":
        request["after"] = "[Cancellation](other.md#cancellation)"
    elif change == "valid":
        path.write_text(path.read_text() + "\n# Old\n")
    else:
        path.write_text(path.read_text() + "\n# Cancellation\n")
    content = path.read_text()
    with pytest.raises(store.WorkflowError):
        repair.apply(project, "feature", "s", request)
    assert path.read_text() == content
    assert not store.load(project, "feature").get("pending_repair")


def test_interrupted_write_keeps_acceptance_invalid_until_recovery(
    project, monkeypatch
):
    authorize(project)
    request = reference(project)
    scenarios.accept(project, "intent")
    original_write = repair._write

    def crash(*args):
        raise OSError("simulated disk interruption")

    monkeypatch.setattr(repair, "_write", crash)
    with pytest.raises(OSError):
        repair.apply(project, "feature", "s", request)
    record = store.load(project, "feature")
    assert record["pending_repair"] and not record["phases"]["intent"]["evidence"]
    monkeypatch.setattr(repair, "_write", original_write)
    repair.recover(project, "feature", "s", "Resume interrupted local write.")
    record = store.load(project, "feature")
    assert not record["pending_repair"] and record["phases"]["intent"]["evidence"]


def test_semantic_repair_needs_current_source_and_independent_check(project):
    authorize(project)
    scenarios.accept(project, "intent")
    path = project / ".fbk/feature/spec.md"
    path.write_text(FALSE_SPEC)
    scenarios.accept(project, "spec")
    request = {
        "kind": "contradiction",
        "path": ".fbk/feature/spec.md",
        "before": "false",
        "after": "true",
        "decision_id": "cancel-return",
    }
    # An honest negative is the verifier's verdict: nothing applied, verdict and evidence named.
    for status, evidence in [
        ("rejected", "Needs an unsettled design choice."),
        ("insufficient_context", "The quoted source does not mention cancel."),
    ]:
        with pytest.raises(
            store.WorkflowError,
            match=f"Repair not applied: verifier returned {status}: {evidence}",
        ) as error:
            repair.apply(
                project,
                "feature",
                "s",
                request,
                verifier=lambda *a, status=status, evidence=evidence: {
                    "status": status,
                    "evidence": evidence,
                },
            )
        assert not getattr(error.value, "diagnostics", None)
        assert path.read_text() == FALSE_SPEC
        assert not store.load(project, "feature").get("pending_repair")
    with pytest.raises(store.WorkflowError, match="did not establish fidelity"):
        repair.apply(
            project,
            "feature",
            "s",
            request,
            verifier=lambda *a: {"status": "equivalent", "evidence": " "},
        )
    assert path.read_text() == FALSE_SPEC
    repair.apply(
        project,
        "feature",
        "s",
        request,
        verifier=lambda root, packet: {
            "status": "equivalent",
            "evidence": packet["decision"]["source"]["quote"],
        },
    )
    record = store.load(project, "feature")
    assert path.read_text() == TRUE_SPEC
    assert (
        record["phases"]["intent"]["evidence"]
        and not record["phases"]["spec"]["evidence"]
    )
    assert len(record["phases"]["spec"]["rounds"]) == 1


def test_concurrent_source_edit_cannot_commit_semantic_repair(project):
    authorize(project)
    path = project / ".fbk/feature/spec.md"
    path.write_text("Cancel returns false once.")
    request = {
        "kind": "contradiction",
        "path": ".fbk/feature/spec.md",
        "before": "false",
        "after": "true",
        "decision_id": "cancel-return",
    }

    def mutate(root, packet):
        (root / "authority.md").write_text("Changed intent.")
        return {"status": "equivalent", "evidence": "Prior source agreed."}

    with pytest.raises(store.WorkflowError, match="source|Source"):
        repair.apply(project, "feature", "s", request, verifier=mutate)
    assert path.read_text() == "Cancel returns false once."


def test_superseding_decisions_are_explicit_and_source_changes_are_stale(project):
    authorize(project)
    with store.transaction(project):
        record = store.load(project, "feature")
        decisions.record(
            project,
            record,
            "s",
            {
                "id": "clear-return",
                "text": "Cancel returns true once.",
                "phase": "spec", "kind": "governs",
                "supersedes": "cancel-return",
                "source": {
                    "path": "authority.md",
                    "quote": "Cancel returns true once.",
                },
            },
        )
        store.save(project, record)
    assert [r["id"] for r in decisions.current(project, record)] == ["clear-return"]
    (project / "authority.md").write_text(
        "Cancel returns true once. Changed surrounding authority."
    )
    with pytest.raises(store.WorkflowError, match="changed"):
        decisions.current(project, record)


def test_no_standing_authority_or_code_test_repair_bypass(project):
    request = reference(project)
    with pytest.raises(store.WorkflowError, match="standing"):
        repair.apply(project, "feature", "s", request)
    authorize(project)
    request["path"] = "src/app.py"
    with pytest.raises(store.WorkflowError, match="never code or tests"):
        repair.apply(project, "feature", "s", request)


def test_new_sourced_decision_can_repair_now_stale_accepted_spec(project):
    authorize(project)
    scenarios.accept(project, "intent")
    scenarios.accept(project, "spec")
    (project / "new-source.md").write_text("The return is true once.")
    with store.transaction(project):
        record = store.load(project, "feature")
        decisions.record(
            project,
            record,
            "s",
            {
                "id": "clarified",
                "text": "The return is true once.",
                "phase": "spec", "kind": "governs",
                "supersedes": "cancel-return",
                "source": {
                    "path": "new-source.md",
                    "quote": "The return is true once.",
                },
            },
        )
        store.save(project, record)
    request = {
        "kind": "contradiction",
        "path": ".fbk/feature/spec.md",
        "before": "Cancel returns true once",
        "after": "The return is true once",
        "decision_id": "clarified",
    }
    repair.apply(
        project,
        "feature",
        "s",
        request,
        verifier=lambda *a: {
            "status": "equivalent",
            "evidence": "The original quoted source explicitly settles the same return.",
        },
    )
    record = store.load(project, "feature")
    assert record["phases"]["intent"]["evidence"]
    assert not record["phases"]["spec"]["evidence"]
    assert len(record["phases"]["spec"]["rounds"]) == 1


def test_recovery_abandons_changed_authority_without_overwriting(project, monkeypatch):
    authorize(project)
    request = reference(project)
    scenarios.accept(project, "intent")

    def crash(*args):
        raise OSError("interrupted")

    monkeypatch.setattr(repair, "_write", crash)
    with pytest.raises(OSError):
        repair.apply(project, "feature", "s", request)
    (project / "authority.md").write_text("Authorization revoked.")
    result = repair.recover(
        project, "feature", "s", "Recover interrupted write after changed intent."
    )
    assert result["status"] == "abandoned"
    record = store.load(project, "feature")
    assert not record["pending_repair"] and not record["phases"]["intent"]["evidence"]
    assert "(#old)" in (project / request["path"]).read_text()


def test_stale_supporting_convention_prevents_mechanical_acceptance_rebind(project):
    from fbk.workflow import review_context

    authorize(project)
    request = reference(project)
    (project / "CLAUDE.md").write_text("Current contract.")
    scenarios.accept(project, "intent")
    with store.transaction(project):
        record = store.load(project, "feature")
        accepted = record["phases"]["intent"]["evidence"]
        accepted["review"]["source_policy"] = "original-snapshot-v1"
        accepted["review"]["supporting_files"] = review_context.supporting_manifest(
            project
        )
        store.save(project, record)
    (project / "CLAUDE.md").write_text("Changed contract.")
    with pytest.raises(store.WorkflowError, match="stale"):
        repair.apply(project, "feature", "s", request)
    assert "(#old)" in (project / request["path"]).read_text()


def test_decision_changes_refuse_owned_workers_and_pending_close(project):
    authorize(project)
    with store.transaction(project):
        record = store.load(project, "feature")
        record["workers"] = {"worker": True}
        with pytest.raises(store.WorkflowError, match="workers"):
            decisions.policy(
                project,
                record,
                "s",
                {
                    "classes": [],
                    "source": {
                        "path": "authority.md",
                        "quote": "Cancel returns true once.",
                    },
                },
            )
        record["workers"] = {}
        record["phases"]["intent"]["pending"] = {"id": "pending"}
        with pytest.raises(store.WorkflowError, match="pending"):
            decisions.record(project, record, "s", {})


def test_recovery_after_artifact_write_finishes_without_reapplying_patch(
    project, monkeypatch
):
    authorize(project)
    request = reference(project)
    scenarios.accept(project, "intent")
    original_finish = repair._finish

    def crash(*args):
        raise OSError("crash after artifact replacement")

    monkeypatch.setattr(repair, "_finish", crash)
    with pytest.raises(OSError):
        repair.apply(project, "feature", "s", request)
    assert "(#cancellation)" in (project / request["path"]).read_text()
    assert not store.load(project, "feature")["phases"]["intent"]["evidence"]
    monkeypatch.setattr(repair, "_finish", original_finish)
    repair.recover(project, "feature", "s", "Finalize completed atomic file write.")
    assert store.load(project, "feature")["phases"]["intent"]["evidence"]


@pytest.mark.parametrize("suffix", ["\n# Old!\n", "\nOld\n===\n"])
def test_unsupported_heading_cannot_be_misidentified_as_missing_anchor(project, suffix):
    authorize(project)
    request = reference(project)
    path = project / request["path"]
    path.write_text(path.read_text() + suffix)
    with pytest.raises(store.WorkflowError, match="unsupported heading"):
        repair.apply(project, "feature", "s", request)
    assert "(#old)" in path.read_text()


def test_missing_future_decision_source_does_not_pollute_earlier_phase(project):
    authorize(project)
    record = store.load(project, "feature")
    (project / "authority.md").unlink()
    assert decisions.binding(project, record, "intent") == []
    with pytest.raises(store.WorkflowError, match="Cannot read"):
        decisions.binding(project, record, "spec")


def test_verifier_incomplete_declaration_is_insufficient_context(project, monkeypatch):
    """An honest incomplete declaration can never carry an equivalent verdict into an applied repair."""
    from fbk.workflow import review

    authorize(project)
    scenarios.accept(project, "intent")
    path = project / ".fbk/feature/spec.md"
    path.write_text(FALSE_SPEC)
    scenarios.accept(project, "spec")
    request = {
        "kind": "contradiction",
        "path": ".fbk/feature/spec.md",
        "before": "false",
        "after": "true",
        "decision_id": "cancel-return",
    }

    def session(root, prompt, config, *, schema, validator):
        return {
            "review": {"status": "equivalent", "evidence": "Looks equivalent."},
            "context": {
                "status": "incomplete",
                "inspected_files": list(config["_review_required_files"]),
                "supporting_files": [],
                "missing_context": ["the decision source quotes a different sentence"],
            },
            "seconds": 1,
        }

    monkeypatch.setattr(review, "claude_review", session)
    with pytest.raises(
        store.WorkflowError,
        match="Repair not applied: verifier returned insufficient_context: Verifier reported missing context: the decision source",
    ):
        repair.apply(project, "feature", "s", request)
    assert path.read_text() == FALSE_SPEC
    assert not store.load(project, "feature").get("pending_repair")
