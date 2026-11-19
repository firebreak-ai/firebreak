"""Original-source snapshots and explicit, bounded review context contracts."""

import hashlib
import json
import os
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .store import ACCEPTED_OUTPUT_FOLDER, OUTPUT_FOLDER, WorkflowError, confined

EXCLUDED = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".fbk-capture",
    "test-results",
}
CONTEXT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "status": {"enum": ["complete", "incomplete"]},
        "inspected_files": {
            "type": "array",
            "maxItems": 500,
            "items": {"type": "string", "minLength": 1, "maxLength": 500},
        },
        "supporting_files": {
            "type": "array",
            "maxItems": 500,
            "items": {"type": "string", "minLength": 1, "maxLength": 500},
        },
        "missing_context": {
            "type": "array",
            "maxItems": 20,
            "items": {"type": "string", "minLength": 1, "maxLength": 500},
        },
    },
    "required": ["status", "inspected_files", "supporting_files", "missing_context"],
}


def validate_context(data, available=None, required=()):
    if not isinstance(data, dict) or set(data) != set(CONTEXT_SCHEMA["required"]):
        # constraint: context-record
        raise WorkflowError(
            "Review needs an explicit context completeness and source inspection record."
        )
    if data["status"] not in ("complete", "incomplete"):
        # constraint: context-record
        raise WorkflowError("Invalid review context status.")
    for key, limit in [
        ("inspected_files", 500),
        ("supporting_files", 500),
        ("missing_context", 20),
    ]:
        values = data[key]
        if (
            not isinstance(values, list)
            or len(values) > limit
            or any(
                not isinstance(v, str) or not 1 <= len(v.strip()) <= 500 for v in values
            )
        ):
            # constraint: length-budgets
            raise WorkflowError("Review context record exceeded its bounded format.")
    # Both statuses are honest verdicts. Only a contradictory declaration is malformed:
    # complete with named gaps, or incomplete that names nothing.
    if data["status"] == "complete" and data["missing_context"]:
        # constraint: context-status-shape
        raise WorkflowError(
            "Review context declaration is malformed: status complete requires an empty "
            "missing_context. Report status incomplete to name unavailable evidence, or "
            "clear missing_context when nothing needed for this decision is missing."
        )
    if data["status"] == "incomplete" and not data["missing_context"]:
        # constraint: context-status-shape
        raise WorkflowError(
            "Review context declaration is malformed: status incomplete requires "
            "missing_context to name each unavailable item needed for this decision. "
            "Report status complete when nothing is missing."
        )
    # A supporting source the reviewer relied on is a source it read, so the
    # inspection declaration is the union of both lists.
    inspected = set(data["inspected_files"]) | set(data["supporting_files"])
    missing = sorted(set(required) - inspected)
    if missing:
        error = WorkflowError(
            "Review inspection declaration is missing required paths: "
            + ", ".join(missing)
            + ". A required path counts as declared when it appears in either "
            "context.inspected_files or context.supporting_files. Read any of these sources "
            "not yet inspected, then include every actually read required path in one of those "
            "two lists and resubmit the complete structured response. If a source cannot be "
            "inspected, report context.status=incomplete and name it in missing_context. "
            "This validates the declaration, not proof that reading occurred."
        )
        error.inspection_missing_paths = missing
        # constraint: required-files-declared
        raise error
    if available is not None and not inspected <= set(available):
        unknown = sorted(inspected - set(available))
        shown = unknown[:25]
        listed = ", ".join(shown)
        if len(unknown) > len(shown):
            listed += f" (and {len(unknown) - len(shown)} more)"
        error = WorkflowError(
            "Review inspection declaration names paths outside the controlled snapshot: "
            + listed
            + ". Each declared entry must be a file path spelled exactly as it appears in "
            "required_files or the snapshot listing: no directories, wildcards, ./ prefixes, "
            "or absolute paths. Correct the declaration and resubmit the complete structured "
            "response."
        )
        error.inspection_unknown_paths = unknown
        # constraint: declared-paths-in-snapshot
        raise error
    # These checks establish a well-formed claim, not evidence of actual inspection.
    return data


def incomplete_context(readers):
    """Readers that truthfully reported missing evidence: a verdict, not a harness failure."""
    # constraint: incomplete-context-is-a-verdict
    # constraint: stance-incomplete-context
    return [
        {
            "member": reader.get("member"),
            "stage": reader.get("stage") or "independent",
            "missing_context": list(reader["context"]["missing_context"]),
        }
        for reader in readers
        if (reader.get("context") or {}).get("status") == "incomplete"
    ]


def incomplete_message(items):
    """The round's plain outcome sentence, naming every missing item the readers reported."""
    entries = []
    for item in items:
        for missing in item["missing_context"]:
            entries.append(f"{item['member']}: {missing}" if item["member"] else missing)
    return "Review incomplete; missing context: " + "; ".join(entries)


def _ignored_sources(root):
    """Let Git interpret ignore rules, retaining tracked files even when ignored."""
    environment = {**os.environ, "LC_ALL": "C"}
    try:
        root_ignored = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "-q", "--", "."],
            capture_output=True,
            check=False,
            env=environment,
        )
        if root_ignored.returncode == 0:
            tracked = subprocess.run(
                ["git", "-C", str(root), "ls-files", "--cached", "-z", "--", "."],
                capture_output=True,
                check=False,
                env=environment,
            )
            if tracked.returncode:
                raise WorkflowError(
                    "Cannot discover tracked review sources: "
                    + os.fsdecode(tracked.stderr).strip()
                )
            if not tracked.stdout:
                # A standalone project inside an ignored workspace directory is
                # not part of the containing repository's source tree.
                return set()
        result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "--others",
                "--ignored",
                "--exclude-standard",
                # Git cannot collapse directories when its prefix is ignored.
                *([] if root_ignored.returncode == 0 else ["--directory"]),
                "-z",
                "--",
                ".",
            ],
            capture_output=True,
            check=False,
            env=environment,
        )
    except FileNotFoundError:
        if any((parent / ".git").exists() for parent in (root, *root.parents)):
            raise WorkflowError(
                "Git is required to discover this repository's review sources."
            ) from None
        return set()  # Git is optional for projects outside version control.
    if result.returncode:
        probe = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            check=False,
            env=environment,
        )
        if (probe.returncode and b"not a git repository" in probe.stderr) or (
            not probe.returncode and probe.stdout.strip() == b"false"
        ):
            return set()
        raise WorkflowError(
            "Cannot discover Git-ignored review sources: "
            + os.fsdecode(result.stderr).strip()
        )
    return {os.fsdecode(path).rstrip("/") for path in result.stdout.split(b"\0") if path}


def _source_walk(root):
    ignored = _ignored_sources(root)
    for directory, dirs, names in os.walk(root, followlinks=False):
        rel = Path(directory).relative_to(root)
        dirs[:] = sorted(
            d
            for d in dirs
            if d not in EXCLUDED
            and (rel / d).as_posix() not in ignored
            and not (rel == Path(".") and d == ".fbk")
            and not (rel == Path(".claude") and d in {"projects", "sessions", "memory"})
        )
        yield Path(directory), rel, dirs, [
            name
            for name in names
            if (rel / name).as_posix() not in ignored and not host_history(rel / name)
        ]


def source_paths(root, required):
    """Discover sources; workflow runtime and host session history are never sources."""
    root = Path(root).resolve()
    paths = set()
    for directory, rel, dirs, names in _source_walk(root):
        for name in dirs:
            if (directory / name).is_symlink():
                raise WorkflowError(
                    f"Review source directory is a symlink; declare concrete source files: {rel / name}"
                )
        for name in names:
            path = rel / name
            paths.add(path.as_posix())
    for relative in required:
        path = Path(relative)
        if (
            path.is_absolute()
            or ".." in path.parts
            or any(p in EXCLUDED for p in path.parts)
            or host_history(path)
        ):
            raise WorkflowError(f"Invalid required review source: {relative}")
        if path.parts and path.parts[0] == ".fbk" and not _unit_source(root, path):
            raise WorkflowError(
                f"Workflow history cannot be a review source: {relative}"
            )
        paths.add(relative)
    return sorted(paths)


def host_history(path):
    path = Path(path)
    return bool(
        path.parts
        and path.parts[0] == ".claude"
        and (
            len(path.parts) > 1
            and path.parts[1] in {"projects", "sessions", "memory"}
            or path.name in {"settings.json", "settings.local.json"}
            or path.name.startswith(".credentials")
        )
    )


# Unit folders whose files a reviewer may read: design documents, decision sources, and
# the test checkpoint's saved check output, current and accepted.
_UNIT_SOURCE_FOLDERS = {"design", "decisions", OUTPUT_FOLDER, ACCEPTED_OUTPUT_FOLDER}


def _unit_source(root, path):
    """Resolve the deepest owning unit, including nested project/feature names."""
    target = Path(root) / path
    for directory in target.parents:
        if directory == Path(root) / ".fbk" or directory == Path(root):
            break
        if (directory / "state.json").is_file():
            relative = target.relative_to(directory)
            return relative.as_posix() in {
                "prd.md",
                "spec.md",
                "scope.json",
                "tasks.json",
            } or (
                len(relative.parts) > 1 and relative.parts[0] in _UNIT_SOURCE_FOLDERS
            )
    # Snapshot helpers can also inspect standalone original artifacts without state,
    # including a stored snapshot's saved check output.
    return (
        len(path.parts) >= 3
        and (
            path.name in {"prd.md", "spec.md", "scope.json", "tasks.json"}
            or (any(p in _UNIT_SOURCE_FOLDERS for p in path.parts[2:-1]))
        )
        and "runtime" not in path.parts
    )


@contextmanager
def snapshot(root, required):
    """Fail explicitly on unavailable sources; no truncation or silent size omission."""
    root = Path(root).resolve()
    manifest, links = {}, {}
    with tempfile.TemporaryDirectory(prefix="fbk-review-") as directory:
        target = Path(directory)
        total = 0
        for relative in source_paths(root, required):
            source = root / relative
            if not source.resolve().is_relative_to(root):
                raise WorkflowError(f"Review source escapes repository: {relative}")
            try:
                # A link's target is captured with the bytes read through it.
                if source.is_symlink():
                    links[relative] = os.readlink(source)
                data = source.read_bytes()
            except OSError as exc:
                raise WorkflowError(
                    f"Missing or unreadable review source {relative}: {exc}"
                ) from exc
            total += len(data)
            if total > 256 * 1024 * 1024:
                raise WorkflowError(
                    "Review snapshot exceeds 256 MiB; remove generated material from the repository or use a focused checkout."
                )
            dest = target / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            # The reviewer sees each file's executable bit as it is in the tree.
            dest.chmod(0o755 if source.stat().st_mode & 0o111 else 0o644)
            manifest[relative] = hashlib.sha256(data).hexdigest()
        # Each file is copied as the content it reads as; a symbolic link's target is
        # listed apart, so the reviewer sees what each link points at. The listing sits in
        # Firebreak's runtime folder, which is never a review source, so it cannot replace
        # a project file and the manifest, which never walks it, stays the sources alone.
        if links:
            listing = target / SYMLINKS_FILE
            listing.parent.mkdir(parents=True, exist_ok=True)
            listing.write_text(json.dumps({
                "note": "These review sources are symbolic links in the project; each is copied here as "
                        "the content it points at, and this file names the target each link points to.",
                "links": links}, ensure_ascii=False, indent=2))
        yield target, manifest


SYMLINKS_FILE = ".fbk/runtime/review-symlinks.json"


def captured_symlinks(snapshot_root):
    """The link targets a snapshot captured with its files, from its listing; the one map
    every later use of the snapshot reads."""
    listing = Path(snapshot_root) / SYMLINKS_FILE
    return json.loads(listing.read_text())["links"] if listing.is_file() else {}


def listing_inputs(snapshot_root):
    """The snapshot's link listing as a reader input, path to fingerprint, when it has one;
    every snapshot consumer adds it to the files a reader may read and must read."""
    listing = Path(snapshot_root) / SYMLINKS_FILE
    return {SYMLINKS_FILE: hashlib.sha256(listing.read_bytes()).hexdigest()} if listing.is_file() else {}


def symlink_paths(root, paths):
    """Each path that is a symbolic link in the live tree, with its target."""
    from .evidence import symlink_targets

    return symlink_targets(root, paths)


def convention_paths(paths):
    return sorted(
        p
        for p in paths
        if Path(p).name in {"CLAUDE.md", "AGENTS.md"}
        or p.startswith((".claude/docs/", ".claude/rules/", ".claude/fbk-docs/"))
    )


def supporting_manifest(root):
    """Find convention files without opening or validating unrelated source material."""
    root = Path(root).resolve()
    paths = []
    for _, relative, _, names in _source_walk(root):
        for name in names:
            path = (relative / name).as_posix()
            if convention_paths([path]):
                paths.append(path)
    return {
        p: hashlib.sha256(confined(root, p).read_bytes()).hexdigest()
        for p in sorted(paths)
    }


def additional_supporting(root, unit, phase, files, result, manifest):
    """Bind reported governing authorities without freezing unfinished deliverables."""
    from . import evidence

    excluded = set(files) | set(convention_paths(manifest))
    if phase != "implement" and (Path(root) / ".fbk" / unit / "scope.json").exists():
        declared = evidence.scope(root, unit)
        excluded.update(
            evidence.expand(
                root, declared["sources"] + declared["tests"] + declared["docs"]
            )
        )
    reported = {
        path
        for reader in result.get("readers", [])
        for path in reader.get("context", {}).get("supporting_files", [])
    }
    return {
        path: manifest[path] for path in sorted(reported - excluded) if path in manifest
    }


def supporting_fresh(root, result):
    """Conservative authority freshness, including new or removed conventions."""
    try:
        if result.get("source_policy") != "original-snapshot-v1" or result.get(
            "supporting_files"
        ) != supporting_manifest(root):
            return False
        return all(
            hashlib.sha256(confined(root, path).read_bytes()).hexdigest() == expected
            for path, expected in result.get("additional_supporting_files", {}).items()
        )
    except (OSError, WorkflowError):
        return False


def snapshot_fresh(root, result):
    """Check the entire in-flight/reusable read surface, including additions."""
    if result.get("source_policy") != "original-snapshot-v1":
        return False
    try:
        paths = source_paths(root, result["required_files"])
        return result["snapshot_files"] == {
            p: hashlib.sha256((Path(root) / p).read_bytes()).hexdigest() for p in paths
        } and result.get("snapshot_executables", executable_paths(root, paths)) == executable_paths(root, paths) \
            and result.get("snapshot_symlinks", {}) == symlink_paths(root, paths)  # none recorded: fresh only without links
    except (KeyError, OSError, WorkflowError):
        return False


def executable_paths(root, paths):
    """The paths whose executable bit is set, which a snapshot's identity includes."""
    return sorted(p for p in paths if (Path(root) / p).stat().st_mode & 0o111)
