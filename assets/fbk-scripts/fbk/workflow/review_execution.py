"""Shared active-wall execution, cancellation and recovery for all review rounds.

The persisted ``managed_clock`` field retains its existing format; both managed
phase reviews and standalone contributor batches use this execution lifecycle.
"""

import signal
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import investigations
from .store import WorkflowError, now, transaction


def _exhausted(message, round_id):
    error = WorkflowError(message + "; human help is required.")
    error.diagnostics = {
        "budget_exhausted": "review-round-time",
        "investigation_round": round_id,
    }
    return error


def activate_record(root, record):
    """Activate a loaded round while its caller holds the project transaction."""
    round_id = record["id"]
    record.setdefault(
        "managed_clock",
        {
            "worker_seconds": 0,
            "worker_usage": [],
            "created_at": now(),
            "human_wait_seconds": 0,
        },
    )
    clock = record["managed_clock"]
    if clock.get("active") or investigations.needs_human_review(record):
        raise _exhausted("Previous review execution needs reconciliation", round_id)
    if record["budget"]["spent_seconds"] >= record["budget"]["seconds"]:
        raise _exhausted("Shared review budget exhausted", round_id)
    if clock.get("finished_at"):
        clock["human_wait_seconds"] += max(
            0,
            (
                datetime.now(timezone.utc)
                - datetime.fromisoformat(clock["finished_at"])
            ).total_seconds(),
        )
    clock.update(active=True, started_at=now(), execution_id=uuid.uuid4().hex)
    investigations._save(root, record)


def activate_round(root, round_id):
    with transaction(root):
        record = investigations._load(root, round_id)
        if record.get("superseded_by"):
            raise WorkflowError("Round is superseded; activate its successor.")
        activate_record(root, record)
    return RoundExecution(Path(root), record)


def recover_execution(root, round_id, reason, *, locked=False):
    """Caller confirms old processes stopped. Unknown interrupted time stays charged."""
    from contextlib import nullcontext

    if not reason.strip():
        raise WorkflowError(
            "Recovery requires the operator reason and stopped processes."
        )
    with nullcontext() if locked else transaction(root):
        record = investigations._load(root, round_id)
        clock = record.get("managed_clock", {})
        if clock.get("active"):
            from .review import _process_group_running, release_stopped_command_groups

            if any(
                _process_group_running(group)
                for group in clock.get("termination_unconfirmed", [])
            ):
                raise WorkflowError(
                    "Recorded worker process group is still running; stop it before recovery."
                )
            stopped_groups = clock.pop("termination_unconfirmed", [])
            release_stopped_command_groups(stopped_groups)
            record["budget"]["spent_seconds"] = max(
                record["budget"]["spent_seconds"], record["budget"]["seconds"]
            )
            clock.update(active=False, finished_at=now())
            clock.setdefault("recoveries", []).append(
                {
                    "reason": reason,
                    "at": now(),
                    "charge": "interrupted remaining reservation",
                    "stopped_process_groups": stopped_groups,
                }
            )
            investigations._save(root, record)


class RoundExecution:
    def __init__(self, root, record):
        self.root = root
        self.round_id = record["id"]
        self.started = time.monotonic()
        self.spent = record["budget"]["spent_seconds"]
        self.limit = record["budget"]["seconds"]
        self.lock = threading.RLock()
        self.execution_id = record["managed_clock"].get("execution_id")
        self._finished = False
        self._previous_interrupt = None
        self._interrupt_handler = None
        if threading.current_thread() is threading.main_thread():
            self._previous_interrupt = signal.getsignal(signal.SIGINT)
            if self._previous_interrupt != signal.SIG_IGN:

                def interrupt(signum, frame):
                    from .review import cancel_command_groups

                    cancel_command_groups(self.root)
                    if callable(self._previous_interrupt):
                        self._previous_interrupt(signum, frame)
                    else:
                        signal.default_int_handler(signum, frame)

                self._interrupt_handler = interrupt
                interrupt._fbk_execution = self
                signal.signal(signal.SIGINT, interrupt)

    def remaining(self):
        remaining = self.limit - self.spent - (time.monotonic() - self.started)
        if remaining <= 0:
            raise _exhausted("Shared review budget exhausted", self.round_id)
        return remaining

    def record_worker(self, response):
        with transaction(self.root):
            record = investigations._load(self.root, self.round_id)
            clock = record["managed_clock"]
            clock["worker_seconds"] += response.get("seconds", 0)
            cost = response.get("reported_cost_usd")
            if isinstance(cost, (int, float)):
                clock["reported_cost_usd"] = clock.get("reported_cost_usd", 0) + cost
            if response.get("usage") is not None:
                clock["worker_usage"].append(response["usage"])
            investigations._save(self.root, record)

    def finish(self):
        from .review import outstanding_command_groups

        if self._finished:
            return
        self._finished = True
        if (
            self._interrupt_handler is not None
            and threading.current_thread() is threading.main_thread()
            and signal.getsignal(signal.SIGINT) is self._interrupt_handler
        ):
            previous = self._previous_interrupt
            while (
                hasattr(previous, "_fbk_execution")
                and previous._fbk_execution._finished
            ):
                previous = previous._fbk_execution._previous_interrupt
            signal.signal(signal.SIGINT, previous)
        unresolved = outstanding_command_groups(self.root)
        with transaction(self.root):
            record = investigations._load(self.root, self.round_id)
            clock = record["managed_clock"]
            if clock.get("execution_id") != self.execution_id or not clock.get(
                "active"
            ):
                return  # A recovered/replaced controller cannot refund or close its successor.
            elapsed = self.spent + max(0, time.monotonic() - self.started)
            record["budget"]["spent_seconds"] = (
                max(
                    record["budget"]["spent_seconds"],
                    record["budget"]["seconds"],
                    elapsed,
                )
                if unresolved
                else elapsed
            )
            clock.update(
                active=bool(unresolved),
                finished_at=now(),
                active_seconds=record["budget"]["spent_seconds"],
            )
            if unresolved:
                clock["termination_unconfirmed"] = unresolved
                record.setdefault("events", []).append(
                    {
                        "type": "review-execution-interrupted",
                        "at": now(),
                        "process_groups": unresolved,
                        "reason": "Worker termination unconfirmed; retained active state and remaining reservation.",
                    }
                )
            clock["elapsed_seconds"] = (
                datetime.now(timezone.utc) - datetime.fromisoformat(clock["created_at"])
            ).total_seconds()
            investigations._save(self.root, record)

    def investigate(self, request, reader_key):
        investigations.validate_request(request, managed=True)
        # Native sessions remain concurrent; serializing short experiment dispatch
        # prevents conflicting reservations, with waiting charged only as wall time.
        with self.lock:
            self.remaining()
            identifier = reader_key + "-" + str(request.get("id", ""))
            with transaction(self.root):
                record = investigations._load(self.root, self.round_id)
                record["budget"]["spent_seconds"] = self.spent + max(
                    0, time.monotonic() - self.started
                )
                investigations._save(self.root, record)
            entry = record["investigations"].get(identifier)
            if entry is not None and investigations.exhausted_question(entry):
                # Asking again costs nothing: the same unresolved evidence comes back.
                return identifier, entry
            if entry is None:
                investigations.start(
                    self.root, self.round_id, {**request, "id": identifier}
                )
            try:
                entry = investigations.run(
                    self.root, self.round_id, identifier, request
                )
            except investigations.InvestigationRefused as exc:
                # Refusal is evidence, not failure; it still counts as an attempt.
                exc.identifier = identifier
                self._raise_if_exhausted(exc.entry)
                raise
            attempt = entry["attempts"][-1]
            self.record_worker(attempt["result"])
            self._raise_if_exhausted(entry)
            return identifier, entry

    def _raise_if_exhausted(self, entry):
        """Only the round clock ends the reader; a per-question limit is a caveat."""
        if entry.get("human_review") and not investigations.exhausted_question(entry):
            error = _exhausted(
                "Investigation exhausted its "
                + entry["human_review"]["limit"]
                + " budget",
                self.round_id,
            )
            error.diagnostics["budget_exhausted"] = (
                "investigation-" + entry["human_review"]["limit"]
            )
            raise error


def extend_round(root, round_id, rounds, reason, *, locked=False):
    """Existing operator round extension adds time, never erases consumed usage."""
    from contextlib import nullcontext

    if not reason.strip() or type(rounds) is not int or not 1 <= rounds <= 10:
        raise WorkflowError("Extension requires 1–10 rounds and the operator reason.")
    with nullcontext() if locked else transaction(root):
        record = investigations._load(root, round_id)
        clock = record["managed_clock"]
        if clock.get("active"):
            raise WorkflowError(
                "Recover the interrupted review and confirm old processes stopped before extension."
            )
        config = record["configuration"]
        seconds = config.get("review_round_timeout", 9999) * rounds
        record["budget"]["seconds"] += seconds
        clock.setdefault("extensions", []).append(
            {"rounds": rounds, "seconds": seconds, "reason": reason, "at": now()}
        )
        investigations._save(root, record)
