"""Expose one acceptance-bound original source tree to managed readers."""

import hashlib
import re

from .evidence import CHECKPOINT
from .review_context import source_paths
from .store import ROUND_ID, WorkflowError, atomic_json, confined, digest, read_json


PREFIX = ".fbk/runtime/review-baseline/sources"


def select(record, phase):
    """Ratchet to the last same-phase acceptance. Before implement's first acceptance, the
    accepted test checkpoint is its baseline: the reviewed tests and their saved output. A
    unit with no tests and no test tasks uses its writing-tests baseline instead (_comparison)."""
    accepted = record.get("phases", {}).get(phase, {}).get("evidence")
    if not accepted:
        for row in reversed(record.get("events", [])):
            accepted = row.get("superseded_evidence", {}).get(phase)
            if not accepted and row.get("event") == "closed" and row.get("phase") == phase:
                accepted = row.get("evidence")
            if accepted:
                break
    if accepted:
        return accepted, phase, "Most recent accepted revision of this phase."
    if phase == "implement":
        accepted = record.get("phases", {}).get(CHECKPOINT, {}).get("evidence")
        if accepted:
            return accepted, CHECKPOINT, "Accepted test checkpoint: the test contract before first implementation."
    return None, None, "No applicable accepted source baseline exists for this phase."


def retained(accepted):
    """Retain the latest accepted source identity without reviewer narrative."""
    reviewed = accepted.get("review", {})
    return {
        "revision": accepted["revision"],
        "files": accepted.get("files", {}),
        "review": {key: reviewed[key] for key in
                   ("source_policy", "snapshot_files", "snapshot_symlinks", "investigation_round")
                   if key in reviewed},
    }


def _comparison(root, record, phase):
    accepted, baseline_phase, reason = select(record, phase)
    if not accepted and phase == "implement":
        from .engine import test_outcome

        if test_outcome(root, record) == "no-tests":
            return _entry_baseline(root, record, _in_scope(root, record))
    if not accepted:
        return {"status": "unavailable", "reason": reason}, {}
    provenance = {"phase": baseline_phase, "accepted_revision": accepted.get("revision"),
                  "selection": reason}
    try:
        manifest, bodies = _bodies(root, accepted)
        return {**provenance, **_provenance(accepted, baseline_phase, manifest, _in_scope(root, record)),
                "status": "available"}, bodies
    except WorkflowError as exc:
        return {**provenance, "status": "unavailable", "reason": str(exc)}, {}


def _in_scope(root, record):
    """Keep only the links among the unit's declared tests and sources, so the brief stays
    bounded by the unit, not by every link in the project."""
    from . import evidence

    try:
        declared = evidence.scope(root, record["unit"])
    except (WorkflowError, KeyError):
        return lambda links: {}
    return lambda links: {path: target for path, target in (links or {}).items()
                          if evidence.matches(path, declared["tests"] + declared["sources"])}


def _entry_baseline(root, record, scoped=lambda links: links):
    """A unit with no tests and no test tasks has no checkpoint snapshot; before its first
    implement acceptance, the writing-tests baseline recorded when implement was entered is
    the comparison tree."""
    from .test_preparation import _baseline_copy

    baseline = record.get("writing_tests_baseline")
    provenance = {"phase": "writing-tests-baseline", "accepted_revision": None,
                  "selection": "Writing-tests baseline recorded when implement was entered: the unit has "
                               "no tests and no test tasks, so no test checkpoint snapshot exists."}
    if not baseline or not baseline["files"]:
        return {**provenance, "status": "unavailable",
                "reason": "The unit has no tests and no test tasks, and no writing-tests baseline holds files."}, {}
    bodies = {}
    for path in baseline["files"]:
        try:
            bodies[path] = _baseline_copy(root, record, path)
        except WorkflowError:
            return {**provenance, "status": "unavailable", "reason": (
                f"The unit has no scoped tests and no test tasks, so implement compares against the writing-tests "
                f"baseline recorded at entry, but its saved copy of {path} is missing or no longer matches its "
                "recorded fingerprint, so no comparison tree is available.")}, {}
    return {**provenance, "status": "available", "recorded_at": baseline["at"],
            "source_revision": digest(baseline["files"]), "source_root": PREFIX,
            "files": len(baseline["files"]), **_symlinks(scoped(baseline.get("links")))}, bodies


def prepare(root, reader_root, record, phase, available):
    provenance, bodies = _comparison(root, record, phase)
    if provenance["status"] == "available":
        _copy(reader_root, bodies, available)
    return provenance


def remember(root, round_id, provenance):
    """Record what readers received outside their source tree and result schema."""
    atomic_json(confined(root, f".fbk/runtime/review-rounds/{round_id}/baseline.json"), provenance)


def _bodies(root, accepted):
    reviewed = accepted.get("review", {})
    manifest = reviewed.get("snapshot_files")
    round_id = reviewed.get("investigation_round")
    if (
        reviewed.get("source_policy") != "original-snapshot-v1"
        or not isinstance(manifest, dict)
        or not manifest
        or any(not isinstance(p, str) or not isinstance(h, str)
               or not re.fullmatch(r"[a-f0-9]{64}", h) for p, h in manifest.items())
        or not isinstance(round_id, str)
        or not ROUND_ID.fullmatch(round_id)
        or not accepted.get("revision")
    ):
        raise WorkflowError("The selected review baseline lacks a revision-bound captured source tree.")
    if any(manifest.get(path) != expected for path, expected in accepted.get("files", {}).items()):
        raise WorkflowError("The selected review baseline does not match its accepted source files.")
    stored = confined(root, f".fbk/runtime/review-rounds/{round_id}/sources")
    # Reapply the original-source policy even to a malformed retained manifest.
    source_paths(stored, manifest)
    bodies = {}
    total = 0
    for relative, expected in manifest.items():
        try:
            source = confined(stored, relative)
            if source.is_symlink() or any(p.is_symlink() for p in source.parents if p != stored.parent):
                raise WorkflowError(f"Baseline source is a symlink: {relative}")
            data = source.read_bytes()
        except OSError as exc:
            raise WorkflowError(f"Missing or unreadable baseline source {relative}: {exc}") from exc
        if hashlib.sha256(data).hexdigest() != expected:
            raise WorkflowError(f"Baseline source differs from its accepted revision: {relative}")
        total += len(data)
        if total > 256 * 1024 * 1024:
            raise WorkflowError("Review baseline exceeds 256 MiB.")
        bodies[relative] = data
    return manifest, bodies


def reusable(root, record, phase, result):
    """A cached native review must have received this same verified baseline."""
    round_id = result.get("investigation_round")
    if not isinstance(round_id, str) or not ROUND_ID.fullmatch(round_id):
        return False
    try:
        provenance, bodies = _comparison(root, record, phase)
        supplied = read_json(confined(root, f".fbk/runtime/review-rounds/{round_id}/baseline.json"))
        if supplied != provenance:
            return False
        previous = confined(root, f".fbk/runtime/review-rounds/{round_id}/sources/{PREFIX}")
        if provenance["status"] == "unavailable":
            return not previous.exists()
        return all(confined(previous, path).read_bytes() == body for path, body in bodies.items()) and {
            p.relative_to(previous).as_posix() for p in previous.rglob("*") if p.is_file()
        } == set(bodies)
    except (WorkflowError, OSError):
        return False


def expose(root, reader_root, accepted, phase, available):
    """Copy only verified original bodies; retained review outputs stay outside."""
    manifest, bodies = _bodies(root, accepted)
    _copy(reader_root, bodies, available)
    return _provenance(accepted, phase, manifest)


def _copy(reader_root, bodies, available):
    target = confined(reader_root, PREFIX)
    if target.exists():
        raise WorkflowError("The review baseline source location is already occupied.")
    for relative, data in bodies.items():
        destination = confined(target, relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        available[f"{PREFIX}/{relative}"] = hashlib.sha256(data).hexdigest()


def _provenance(accepted, phase, manifest, scoped=lambda links: links):
    return {
        "phase": phase,
        "accepted_revision": accepted["revision"],
        "source_revision": digest(manifest),
        "source_root": PREFIX,
        "files": len(manifest),
        **_symlinks(scoped(accepted.get("review", {}).get("snapshot_symlinks"))),
    }


def _symlinks(links):
    """The baseline's symbolic links and their targets, which its copied bodies flatten."""
    return {"symlinks": {
        "links": links,
        "note": "These baseline sources were symbolic links; each body is the content it pointed at, "
                "and this names the target each link pointed to.",
    }} if links else {}
