"""Two-phase close: reserve work atomically, execute outside locks, revalidate and commit.

The test checkpoint passes through the same close: it is implement's review gate over the
authored tests, and it locks them on pass instead of closing a phase."""

import functools
import hashlib
import uuid
from pathlib import Path

from . import artifact_hygiene, engine, evidence, review, review_plan, traceability
from .store import (
    BASELINE_FOLDER,
    OUTPUT_FOLDER,
    RECORD_FOLDERS,
    WorkflowError,
    digest,
    event,
    load,
    now,
    record_folder,
    save,
    transaction,
    unit_dir,
)


def _ready(root, record, phase, session):
    engine.ownership(record, session)
    opened = evidence.ordered(phase)
    if record.get("pending_repair"):
        raise WorkflowError("A repair is pending; run recover-repair before closing.")
    engine.check_parent(root, record)
    if any(record["workers"].values()):
        raise WorkflowError(
            "Workers are still active; finish their work before closing the phase."
        )
    current, state, reason = engine.phase_state(root, record)
    if current != opened or state != "open" or record["owner"] != session:
        if phase == evidence.CHECKPOINT:
            raise WorkflowError(
                f"Unit {record['unit']}: the test checkpoint runs inside implement; enter implement first. "
                f"Current {current} is {state}. {reason}"
            )
        raise WorkflowError(
            f"Unit {record['unit']}: enter {phase} before close; current {current} is {state}. {reason}"
        )
    from .retrospective import require_phase_observations

    require_phase_observations(record)
    evidence.structural(root, record, phase)
    review_plan.require(record, phase)
    from .handoff import disposition_blockers, undispositioned

    # This phase's own review suggestions are dispositioned at the next phase's entry.
    blocked = disposition_blockers(
        record, record["unit"], undispositioned(record, before=opened),
        "Accepted suggestions from earlier phases have no recorded disposition",
    )
    if blocked:
        raise WorkflowError(blocked)
    if phase in {"design", "spec"}:
        # Links and coverage are re-checked at every close, so a renamed upstream heading
        # is caught at the next downstream close.
        traceability.check(root, record, phase)
    if phase == "spec":
        evidence.check_creates(root, record)
    if phase == "breakdown":
        from . import test_preparation

        # Breakdown accepts a plan: its tasks are validated here and run in implement.
        test_preparation.plan(root, record)
    if phase == "implement" and engine.test_outcome(root, record) == "no-tests":
        # No tests and no test tasks: no checkpoint and no lock, and no scoped test may appear.
        from .test_preparation import check_empty_inventory

        check_empty_inventory(root, record, "Implementation close is refused")
        from .handoff import verify_task_runs

        verify_task_runs(root, record)
    elif phase == "implement":
        if not engine.checkpoint_locked(root, record):
            raise WorkflowError(
                f"Unit {record['unit']}: implementation closes only on tests the test checkpoint reviewed "
                "and locked, with that acceptance still current. Finish every test task with a completed, "
                f"current run, then run test-checkpoint {record['unit']} and let it pass before closing implement."
            )
        engine.verify_locks(root, record)
        from .handoff import verify_task_runs

        verify_task_runs(root, record)
    if phase == evidence.CHECKPOINT:
        if engine.test_outcome(root, record) == "no-tests":
            raise WorkflowError(
                f"Unit {record['unit']} has no scoped tests and no test tasks, so no test checkpoint applies; "
                "it is writing code. Run the implementation tasks, then close implement."
            )
        if engine.checkpoint_current(root, record):
            raise WorkflowError(
                f"Unit {record['unit']}: the test checkpoint has already accepted the current tests. "
                "It runs again only after an unlock, a reopen, or a governing change makes that acceptance not current."
            )
        try:
            return _checkpoint_ready(root, record)
        except (OSError, UnicodeError) as exc:
            where = getattr(exc, "filename", None) or "a file the checkpoint reads"
            raise WorkflowError(
                f"The test checkpoint cannot read or write {where} ({getattr(exc, 'strerror', None) or exc}); "
                "fix that file, then run test-checkpoint again."
            ) from exc
    return evidence.revision(root, record, phase)


def _checkpoint_ready(root, record):
    """The checkpoint's readiness once its acceptance is known not to be current: no task
    running, the unit ready, its output folder free, and the tree consistent with the
    writing-tests baseline. Returns the checkpoint revision."""
    running = sorted(task for task, run in record.get("task_runs", {}).items() if run["status"] == "running")
    if running:
        raise WorkflowError(
            f"Unit {record['unit']}: tasks are still running ({', '.join(running)}), and the checkpoint "
            "must compare a tree no task is changing. Finish or cancel them, then run test-checkpoint again."
        )
    if record["locks"] and record.get("lock_origin") != evidence.CHECKPOINT:
        raise WorkflowError(
            f"Unit {record['unit']}: its tests carry locks the test checkpoint did not make, and the "
            "checkpoint is the only way to lock tests. Move the unit under .fbk/archive/ and redo it as a new unit."
        )
    if engine.implement_stage(root, record) != "ready-for-checkpoint":
        raise WorkflowError(
            f"Unit {record['unit']} is still writing tests; finish every test task with a completed, "
            "current run, and settle any unlock, before running test-checkpoint."
        )
    from .test_preparation import baseline_comparison

    # The output folder is replaced whole, so a unit living there is refused first. An
    # undeclared production change, or a baseline the comparison cannot rely on, is
    # refused before any check or reviewer runs.
    record_folder(root, record["unit"], OUTPUT_FOLDER)
    comparison = baseline_comparison(root, record, diffs=True)
    from .test_preparation import held_in_baseline, scoped_tests

    # A region-bearing file whose region was and is empty holds no test; its change or
    # removal is a production change, which the comparison already judged.
    held = held_in_baseline(root, record) | set(scoped_tests(root, record))
    differ = [path for path in comparison["changed_by_test_tasks"] + comparison["removed_by_test_tasks"]
              if path in held]
    if differ and engine.test_outcome(root, record) == "preservation":
        # No test task exists to change a scoped test, so the tests locked are the ones
        # that existed when implement was entered.
        raise WorkflowError(
            f"Unit {record['unit']}: a preservation checkpoint locks the scoped tests as they were when "
            f"implement was entered, since no test task could change them, but these differ from the "
            f"writing-tests baseline: {', '.join(sorted(differ))}. Restore them to their saved copies in "
            f".fbk/{record['unit']}/{BASELINE_FOLDER}/ (remove tests that are new), or reopen breakdown to "
            "plan a test task that writes them, then run test-checkpoint again."
        )
    return evidence.revision(root, record, evidence.CHECKPOINT)


def close_checkpoint(root, unit, session, *, reviewer=None, verifier=None):
    """Run the test checkpoint: review the authored tests and lock them on pass."""
    return close_phase(root, unit, evidence.CHECKPOINT, session, reviewer=reviewer, verifier=verifier)


def close_phase(root, unit, phase, session, *, reviewer=None, verifier=None):
    operation = str(uuid.uuid4())
    try:
        trimmed = None
        if phase == "spec":
            from . import spec_trim

            # A fresh session trims the draft before its review, once per draft.
            trimmed = spec_trim.run(root, unit, session, _ready)
        try:
            result = _close_phase(
                root, unit, phase, session, operation, reviewer=reviewer, verifier=verifier
            )
        except WorkflowError as exc:
            # The trim's line follows the close's own problem, when the trim changed something.
            if trimmed and trimmed["outcome"] != "unchanged":
                raise WorkflowError(f"{exc}\n{spec_trim.summary(trimmed)}", code=exc.code) from exc
            raise
        return {**result, "spec_trim": spec_trim.summary(trimmed)} if trimmed else result
    except Exception as exc:
        # Preflight and lost reservations also have a final attempt outcome.
        # If state storage itself failed, preserve the original policy exception.
        escalation = None
        try:
            with transaction(root, timeout=30):
                record = load(root, unit)
                if not any(
                    e.get("event") == "close-attempt"
                    and e.get("operation") == operation
                    for e in record["events"]
                ):
                    event(
                        record,
                        "close-attempt",
                        session,
                        phase=phase,
                        operation=operation,
                        outcome="failed",
                        reason=str(exc),
                        error=str(exc),
                    )
                work = record["phases"].get(phase, {})
                # A checkpoint attempt that fails for any reason withdraws an acceptance that
                # is no longer current, so restoring the earlier inputs cannot revive it; only
                # the refusal to rerun a current acceptance leaves it standing.
                if phase == evidence.CHECKPOINT and work.get("evidence") and not engine.checkpoint_current(root, record):
                    event(record, "test-checkpoint-withdrawn", session, phase=phase,
                          evidence=work["evidence"], operation=operation)
                    work["evidence"] = None
                if engine.review_budget_exhausted(
                    work, engine.review_accepted(root, record, phase) if work else None
                ):
                    escalation = engine.review_escalation(unit, phase, record)
                    if not any(e.get("event") == "human-review-required"
                               and e.get("phase") == phase
                               and e.get("generation") == work["generation"]
                               and e.get("round_limit") == work["round_limit"]
                               for e in record["events"]):
                        event(record, "human-review-required", session, phase=phase,
                              generation=work["generation"], round_limit=work["round_limit"],
                              rounds_used=engine.spent_rounds(work), reason=str(exc))
                save(root, record)
        except Exception:  # noqa: BLE001 - recording the escalation is best effort; the refusal below is raised either way
            pass
        if escalation:
            raise WorkflowError(f"{exc}\n{escalation}", code=getattr(exc, "code", 2)) from exc
        raise


def _close_phase(
    root, unit, phase, session, operation, *, reviewer=None, verifier=None
):
    checkpoint = phase == evidence.CHECKPOINT
    reviewer = reviewer or review.review
    # The checkpoint expects red, so every declared check runs to completion, and its
    # reviewer reads each check's complete output, saved inside the unit's folder.
    if checkpoint and verifier is None:
        output = unit_dir(root, unit).relative_to(root).as_posix() + "/" + OUTPUT_FOLDER
        verifier = functools.partial(review.verify, keep_going=True, save_output=output)
    verifier = verifier or review.verify
    from . import review_baseline
    with transaction(root):
        record = load(root, unit)
        revision = _ready(root, record, phase, session)
        work = record["phases"][phase]
        if work.get("budget_exhausted"):
            raise WorkflowError(engine.review_escalation(unit, phase, record))
        selection = review_plan.require(record, phase)
        # One review at a time: implement's close and its test checkpoint never overlap.
        if any(other.get("pending") for other in record["phases"].values()):
            raise WorkflowError(
                "A close is already running; wait, or stop it and use recover-close with a reason."
            )
        previous = work["rounds"][-1] if work["rounds"] else None
        reuse = (
            previous
            and previous["revision"] == revision
            and previous.get("result")
            and not previous.get("error")
            and previous["generation"] == work["generation"]
            and previous.get("binding") == engine.review_binding(record, phase)
            and _snapshot_current(root, previous["result"])
            and (
                reviewer is not review.review
                or (previous["result"].get("source_policy") == "original-snapshot-v1"
                    and review_baseline.reusable(root, record, phase, previous["result"]))
            )
        )
        # A pass with suggestions is held for the author's sort; the next close accepts the
        # sorted revision on that review, unless the phase was reopened, its review plan
        # changed, or a decision governing it was recorded after the review.
        sorted_pass = bool(
            not checkpoint
            and previous
            and previous.get("held_for_author")
            and previous.get("result")
            and not previous.get("error")
            and previous["generation"] == work["generation"]
            and previous.get("binding") == engine.review_binding(record, phase)
            and previous.get("selection") == selection
            and not _governing_after(record, phase, previous["at"])
        )
        reuse = reuse or sorted_pass
        if not reuse and engine.spent_rounds(work) >= work["round_limit"]:
            raise WorkflowError(
                engine.review_escalation(unit, phase, record)
            )
        work["pending"] = {
            "id": operation,
            "revision": revision,
            "at": now(),
            "session": session,
        }
        files = evidence.subject(root, record, phase)
        commands = evidence.scope(root, unit)["checks"] if phase == "implement" else []
        if checkpoint:
            from .test_preparation import checkpoint_commands

            commands, expected, demand_red = checkpoint_commands(root, record)
            preservation = engine.test_outcome(root, record) == "preservation"
            # The lock binds exactly the tests this checkpoint checked and reviewed.
            reviewed_tests = evidence.test_fingerprints(root, evidence.scope(root, unit))
            # A fingerprint reads through a link, so each test's link target is kept beside
            # it for the later checkpoint's carried-forward judgement; the lock ignores it.
            reviewed_links = evidence.symlink_targets(root, reviewed_tests)
            # This run replaces the saved output, so the previous acceptance's output, which
            # carries red forward for tests unchanged since, is kept aside first.
            from .test_preparation import accepted_output_paths, keep_accepted_output

            keep_accepted_output(root, record)
            # The reviewer will need that output; without it the run is refused before any check.
            accepted_output_paths(root, record)
        save(root, record)
    result, checks, failure, red = None, [], None, None
    failure_diagnostics = None
    hygiene = None
    try:
        # Invisible characters in the unit's own artifacts fail here, before any
        # round is appended or reviewer launched, so a hit spends no review budget.
        hygiene = artifact_hygiene.scan_files(root, _unit_artifacts(root, unit, files))
        if hygiene["findings"]:
            raise WorkflowError(artifact_hygiene.failure_message(hygiene))
        checks = verifier(root, commands) if commands else []
        if checkpoint:
            from .test_preparation import red_evidence

            # Each check's output must still be what was saved: a later check may have
            # rewritten it, and the reviewer must read the fingerprinted bytes.
            review.saved_output_intact(root, checks)
            red = red_evidence(checks, expected, evidence.scope(root, unit)["checks"], demand_red, preservation)
            # A round covers only the check results and output its reviewer assessed.
            if reuse and previous.get("checks_digest") != checks_digest(checks):
                reuse = False
                if engine.spent_rounds(work) >= work["round_limit"]:
                    raise WorkflowError(engine.review_escalation(unit, phase, record))
        elif commands and (
            len(checks) != len(commands) or any(c["exit_code"] for c in checks)
        ):
            raise WorkflowError(
                "Verification failed; fix the reported behavior before closing."
            )
        if reuse:
            result = previous["result"]
        else:
            with transaction(root):
                record = load(root, unit)
                _reservation(record, phase, operation)
                if _ready(root, record, phase, session) != revision:
                    raise WorkflowError(
                        "Inputs changed during verification; retry close on the current revision."
                    )
                record["phases"][phase]["rounds"].append(
                    {
                        "revision": revision,
                        "at": now(),
                        "operation": operation,
                        "result": None,
                        "generation": record["phases"][phase]["generation"],
                        "files": files,
                        "selection": selection,
                        **({"checks_digest": checks_digest(checks)} if checkpoint else {}),
                        **({"binding": binding} if (binding := engine.review_binding(record, phase)) else {}),
                    }
                )
                save(root, record)
            result = reviewer(root, unit, phase, files, checks)
        if result.get("error"):
            raise WorkflowError(result["error"])
        review.validate_review(review.reader_review(result))
        if selection and result["shape"] != selection["mode"]:
            raise WorkflowError(
                "Review result does not match the selected review mode; close refused."
            )
    except Exception as exc:  # noqa: BLE001 — preserve the reservation outcome for any reviewer failure
        failure = str(exc)
        failure_diagnostics = getattr(exc, "diagnostics", None)
    with transaction(root, timeout=30):
        record = load(root, unit)
        _reservation(record, phase, operation)
        work = record["phases"][phase]
        work["pending"] = None
        stages = review_stages(result)
        if (
            not reuse
            and work["rounds"]
            and work["rounds"][-1].get("operation") == operation
        ):
            work["rounds"][-1].update({"result": result, "error": failure})
            if failure_diagnostics:
                work["rounds"][-1]["failure_diagnostics"] = failure_diagnostics
            # Required council sessions report failures in their retained stage records;
            # a single reader instead raises its diagnostic directly.
            diagnostics = [failure_diagnostics]
            if result:
                diagnostics.append((result.get("failure") or {}).get("diagnostics"))
                diagnostics.extend(item.get("diagnostics") for item in result.get("failures", []))
            exhausted = next((item for item in diagnostics
                              if item and item.get("budget_exhausted")), None)
            if failure and exhausted:
                work["budget_exhausted"] = exhausted
            if failure and any(item and item.get("round_unspent") for item in diagnostics):
                work["rounds"][-1]["unspent"] = True
        try:
            if failure:
                raise WorkflowError(failure)
            if _ready(root, record, phase, session) != revision:
                raise WorkflowError(
                    "Inputs changed during review; this result is stale. Re-run close."
                )
            if not (
                _supporting_current(root, result, set(files) | set(previous.get("files", {})))
                if sorted_pass else _snapshot_current(root, result)
            ):
                raise WorkflowError(
                    "Review sources changed during review; re-run close against current original sources."
                )
            blockers = [
                f for f in result["review"]["findings"] if f["severity"] == "blocker"
            ]
            suggestions = [
                f for f in result["review"]["findings"] if f["severity"] == "suggestion"
            ]
            if not blockers and suggestions and not checkpoint and not reuse:
                work["rounds"][-1]["held_for_author"] = True
                raise WorkflowError(
                    f"Review passed with {len(suggestions)} suggestion(s); the phase is not accepted yet. "
                    "Sort each one as fix, escalate or refute, apply your fixes and the operator's answers, "
                    f"then run phase-close {phase} {unit} again: it accepts on that review without another round. "
                    "A decision governing this phase recorded after the review needs a fresh review instead. "
                    f"Read them with current-findings {unit} --phase {phase}."
                )
            grant = None
            if blockers:
                try:
                    grant = engine.consume(root, record, "close-over-findings", phase)
                except WorkflowError as exc:
                    entries = []
                    for number, finding in enumerate(result["review"]["findings"], 1):
                        if finding["severity"] != "blocker":
                            continue
                        entry = f"- {finding['title']} ({finding['location']}): {finding['evidence']}\n  Remedy: {finding['remedy']}"
                        if entries and sum(map(len, entries)) + len(entry) > 8000:
                            entries.append(
                                f"Additional blockers are recorded; read current-findings {unit} --phase {phase} --index {number} and subsequent findings."
                            )
                            break
                        entries.append(entry)
                    details = "\n".join(entries)
                    raise WorkflowError(
                        "Review found blocking defects:\n"
                        + details
                        + f"\nFix demonstrated defects within scope and retry close. Use current-findings {unit} --phase {phase} for this attempt's evidence; workflow-report --history expands the audit. "
                        + str(exc),
                        code=exc.code,
                    ) from exc
            accepted = {
                "revision": revision,
                "files": files,
                "at": now(),
                "opened_at": record["opened_at"],
                "verification": checks,
                "review": result,
                "review_plan": selection,
                "grant_id": grant,
                "outcome": "approved-over-findings" if blockers else "pass",
            }
            if previous and reuse and previous.get("held_for_author"):
                # Suggestions were sorted by the author before this acceptance; files changed
                # since the review were accepted without a reviewer reading them.
                accepted["author_sorted"] = True
                accepted["unreviewed_changes"] = sorted(
                    path for path in set(files) | set(previous.get("files", {}))
                    if files.get(path) != previous.get("files", {}).get(path)
                )
            if phase == "implement":
                from .acceptance_drift import baseline

                accepted["drift_baseline"] = baseline(root, record)
            if checkpoint:
                from .handoff import disposition_blockers, undispositioned_in

                # The checkpoint read the tests and the suite locks now, so a test remedy it
                # raised is dispositioned first; the round keeps the review for the retry.
                undecided = disposition_blockers(
                    record, unit,
                    undispositioned_in(record, phase, result["review"]["findings"], remedy_kind="test"),
                    "Suggestions from the test checkpoint review whose remedy is a test have no recorded disposition",
                )
                if undecided:
                    raise WorkflowError(undecided)
                # Locks, acceptance, and the pass event are saved together below.
                engine.lock_tests(root, record, session, red["red_check"], red["preservation_reason"],
                                  reviewed_tests, persist=False)
                accepted["red_evidence"] = red
                # A later checkpoint carries this one's red forward for tests unchanged since.
                accepted["tests"] = reviewed_tests
                accepted["test_links"] = reviewed_links
            if phase == "implement":
                # The saved copies of locked tests serve implementation only. They are deleted
                # after every refusal point, and a failed deletion refuses the close, so it
                # can be retried; a unit living in that folder is refused, never deleted. A
                # copy set aside until the close is saved lets recover-close put them back.
                from .test_preparation import discard_locked_copies

                discard_locked_copies(root, record)
            work["evidence"] = accepted
            event(
                record,
                "close-attempt",
                session,
                phase=phase,
                operation=operation,
                revision=revision,
                verification=checks,
                artifact_hygiene=hygiene,
                error=None,
                reason=None,
                outcome=accepted["outcome"],
                reused=bool(reuse),
                round_operation=previous.get("operation") if reuse else operation,
                review_stages=stages,
            )
            if checkpoint:
                # Its own pass event, not a phase close: implement stays open and no
                # phase observation is owed.
                event(record, "test-checkpoint-passed", session, phase=phase, evidence=accepted)
            else:
                # A later spec close accepts a declared path this unit has since created.
                declared = {"creates": evidence.scope(root, unit).get("creates", [])} if phase == "spec" else {}
                event(record, "closed", session, phase=phase, evidence=accepted, **declared)
                record["open_phase"], record["owner"], record["opened_at"] = (
                    None,
                    None,
                    None,
                )
        except Exception as exc:
            if checkpoint and work["evidence"]:
                # The checkpoint runs only once its acceptance is no longer current, so a
                # failed attempt withdraws that acceptance, whatever the failure: restoring
                # the earlier inputs cannot revive it. The event keeps it for history, and
                # the locks, their origin, and the budget stay.
                event(record, "test-checkpoint-withdrawn", session, phase=phase,
                      evidence=work["evidence"], operation=operation)
                work["evidence"] = None
            event(
                record,
                "close-attempt",
                session,
                phase=phase,
                operation=operation,
                revision=revision,
                verification=checks,
                artifact_hygiene=hygiene,
                error=str(exc),
                reason=str(exc),
                outcome="failed",
                reused=bool(reuse),
                round_operation=previous.get("operation") if reuse else operation,
                review_stages=stages,
            )
            save(root, record)
            raise
        save(root, record)
        cleanup = {}
        if phase == "implement":
            from .test_preparation import drop_discarded_copies

            cleanup = drop_discarded_copies(root, record)
        return {
            **engine.status_report(root, record),
            **cleanup,
            "accepted_phase": phase,
            "review_shape": result["shape"],
            "findings": result["review"]["findings"],
            **(
                {"second_reader_failure": result["second_reader_failure"]}
                if result.get("second_reader_failure")
                else {}
            ),
        }


def checks_digest(checks):
    """What a checkpoint round's reviewer saw of its checks: commands, exit codes and
    output, without timing."""
    return digest([{k: v for k, v in check.items() if k != "seconds"} for check in checks])


def _unit_artifacts(root, unit, files):
    """The phase's own work products: subject files under the unit directory, never code,
    tests, or context, and never Firebreak's own records, such as captured check output,
    whose terminal color codes are not authored text."""
    base = unit_dir(root, unit).relative_to(root).as_posix() + "/"
    return [path for path in files
            if path.startswith(base) and path[len(base):].split("/")[0] not in RECORD_FOLDERS]


COUNCIL_STEPS = ("opening", "turn", "stance", "second-round", "final")


def review_stages(result):
    """What each council step, or the external second reader's assessor, did in a round.

    A council step is "ran", "skipped" (nothing to do: no proposals, no tied blocker, nothing
    standing), "failed" or "incomplete" where the round stopped, and "not-reached" after it.
    None when the round has neither a council nor an assessor."""
    if not isinstance(result, dict):
        return None
    if result.get("shape") == "council":
        ran = {r.get("stage") for r in result.get("readers", [])}
        stopped = None
        if result.get("failures"):
            stopped = ("opening", "failed")
        elif result.get("failure"):
            stopped = (result["failure"]["stage"], "failed")
        elif result.get("incomplete_context"):
            stopped = (result["incomplete_context"][0]["stage"], "incomplete")
        stages, reached = {}, True
        for step in COUNCIL_STEPS:
            if not reached:
                stages[step] = "not-reached"
            elif stopped and step == stopped[0]:
                stages[step], reached = stopped[1], False
            else:
                stages[step] = "ran" if step in ran else "skipped"
        return stages
    if "adjudication" not in result:
        return None
    return {"adjudication": result["adjudication"]}


def _snapshot_current(root, result):
    if "snapshot_files" not in result:
        return True
    from .review_context import snapshot_fresh

    return snapshot_fresh(root, result)


def _governing_after(record, phase, at):
    """A decision governing this phase, or amending it, recorded after its review, even if
    since superseded; the document must be reviewed for stating it. A decision recorded
    before kinds existed counts as governing."""
    return any((row["phase"] == phase or row.get("amends") == phase)
               and row.get("kind", "governs") == "governs" and row["at"] > at
               for row in record.get("decisions", []))


def _supporting_current(root, result, subject):
    """A sorted pass may change its subject files; every other source the review read must
    still be what it read."""
    snapshot = result.get("snapshot_files")
    if snapshot is None:
        return True
    from .review_context import source_paths

    try:
        current = {
            p: hashlib.sha256((Path(root) / p).read_bytes()).hexdigest()
            for p in source_paths(root, result["required_files"]) if p not in subject
        }
    except (KeyError, OSError, WorkflowError):
        return False
    return {p: h for p, h in snapshot.items() if p not in subject} == current


def _reservation(record, phase, operation):
    pending = record["phases"][phase]["pending"]
    if not pending or pending["id"] != operation:
        raise WorkflowError(
            "Close reservation was recovered or replaced; this old process cannot commit."
        )


def recover(root, record, phase, session, reason):
    engine.ownership(record, session)
    if not reason.strip():
        raise WorkflowError(
            "Recovery needs a reason; first stop the old close process."
        )
    pending = record["phases"][phase]["pending"]
    rounds = record["phases"][phase]["rounds"]
    if pending and rounds and rounds[-1].get("operation") == pending["id"]:
        rounds[-1]["error"] = "Interrupted review recovered: " + reason
        if rounds[-1].get("result") is not None:
            rounds[-1]["result"]["error"] = rounds[-1]["error"]
    if pending and rounds:
        round_id = (rounds[-1].get("result") or {}).get("investigation_round")
        if round_id:
            from .review_execution import recover_execution
            recover_execution(root, round_id, reason, locked=True)
            record["phases"][phase]["budget_exhausted"] = {"budget_exhausted": "interrupted-review", "investigation_round": round_id}
    record["phases"][phase]["pending"] = None
    # A killed checkpoint may have replaced the copies of locked tests without saving its locks.
    from .test_preparation import reconcile_locked_copies

    reconcile_locked_copies(root, record)
    event(
        record, "close-recovered", session, phase=phase, pending=pending, reason=reason
    )
    save(root, record)


def extend_review(root, record, phase, session, reason, rounds=1):
    engine.ownership(record, session)
    if not reason.strip() or isinstance(rounds, bool) or not 1 <= rounds <= 10:
        raise WorkflowError("Extend review by 1–10 rounds with the operator's reason.")
    exhausted = record["phases"][phase].get("budget_exhausted") or {}
    if exhausted.get("investigation_round"):
        from .review_execution import extend_round
        extend_round(root, exhausted["investigation_round"], rounds, reason, locked=True)
    record["phases"][phase]["round_limit"] += rounds
    record["phases"][phase].pop("budget_exhausted", None)
    event(record, "review-extended", session, phase=phase, rounds=rounds, reason=reason)
    save(root, record)
