"""Confined paths and atomic, serialized workflow transactions.

The project lock protects cross-unit prerequisites as well as a single record.
No model calls or verification commands execute while it is held.
"""

import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


# Version 2 adds the test checkpoint's review record; older records are refused, not migrated.
SCHEMA_VERSION = 2

# Folders Firebreak writes directly inside a unit's folder: the saved copies of the
# writing-tests baseline, the test checkpoint's complete check output, the output of
# the latest accepted checkpoint, kept so a later checkpoint can carry its red forward,
# and the saved copies of the locked tests, kept so a changed locked test can be shown
# and restored. Like state.json, they are Firebreak's own records: git-ignored and
# refused to the write hook.
BASELINE_FOLDER = "writing-tests-baseline"
OUTPUT_FOLDER = "check-output"
ACCEPTED_OUTPUT_FOLDER = "accepted-check-output"
LOCKED_FOLDER = "locked-tests"
RECORD_FOLDERS = (BASELINE_FOLDER, OUTPUT_FOLDER, ACCEPTED_OUTPUT_FOLDER, LOCKED_FOLDER)
IGNORED = ("runtime/", *(f"**/{folder}/" for folder in RECORD_FOLDERS))


class WorkflowError(Exception):
    """An actionable refusal, suitable for both CLI and hook adapters."""

    def __init__(self, message, code=2):
        super().__init__(message)
        self.code = code


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


# A review round's id is also its runtime folder name: an optional readable label (its
# unit and phase, or "review" and its start time) before 32 hex digest characters. A bare
# digest is the older form, still read.
ROUND_ID = re.compile(r"(?:[A-Za-z0-9](?:[A-Za-z0-9._-]{0,62}[A-Za-z0-9])?-)?[a-f0-9]{32}")


def readable(text):
    """Text as a readable runtime folder name prefix: characters other than letters,
    digits, ".", "_" and "-" as hyphens, cut to 48."""
    return re.sub(r"[^A-Za-z0-9._-]", "-", text)[:48]


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()


def confined(root, relative):
    root = Path(root).resolve()
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise WorkflowError(f"Use a repository-relative path: {relative!r}")
    target = root / path
    if not target.resolve().is_relative_to(root):
        raise WorkflowError(f"Path escapes the repository: {relative}")
    return target


def unit_dir(root, unit):
    if (
        not isinstance(unit, str)
        or not unit
        or any(
            part.startswith(".") or part in {"runtime", "archive", *RECORD_FOLDERS}
            for part in Path(unit).parts
        )
    ):
        raise WorkflowError(f"Invalid unit name: {unit!r}")
    return confined(confined(root, ".fbk"), unit)


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise WorkflowError(
            f"Cannot read {path}; restore a valid JSON file: {exc}"
        ) from exc


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".fbk-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        parent = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@contextmanager
def transaction(root, timeout=2.0):
    path = confined(root, ".fbk/runtime/project.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise WorkflowError(
                        "Another Firebreak operation is committing; retry this command."
                    ) from None
                time.sleep(0.01)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def load(root, unit):
    path = unit_dir(root, unit) / "state.json"
    confined(root, path.relative_to(root))
    record = read_json(path)
    if isinstance(record, dict) and record.get("schema_version") == 1:
        raise WorkflowError(
            f"Unit {unit}: its state record predates the test-checkpoint amendment, and this "
            f"Firebreak does not migrate it. Move .fbk/{unit}/ under .fbk/archive/, which "
            "Firebreak skips, and finish that unit with the Firebreak version that started it."
        )
    if not isinstance(record, dict) or record.get("schema_version") != SCHEMA_VERSION:
        raise WorkflowError(
            f"Unit {unit}: unsupported state schema; restore the unit from git."
        )
    actual = digest({k: v for k, v in record.items() if k != "content_hash"})
    if record.get("content_hash") != actual or record.get("unit") != unit:
        raise WorkflowError(
            f"Unit {unit}: damaged state record; restore state.json from git."
        )
    if not isinstance(record.get("phases"), dict) or not isinstance(
        record.get("events"), list
    ):
        raise WorkflowError(
            f"Unit {unit}: invalid state structure; restore state.json from git."
        )
    return record


def save(root, record):
    confined(root, (unit_dir(root, record["unit"]) / "state.json").relative_to(root))
    record["content_hash"] = digest(
        {k: v for k, v in record.items() if k != "content_hash"}
    )
    atomic_json(unit_dir(root, record["unit"]) / "state.json", record)


def event(record, kind, session, **fields):
    record["events"].append(
        json.loads(
            json.dumps({"event": kind, "at": now(), "session": session, **fields})
        )
    )


def discover(root):
    base = confined(root, ".fbk")
    units, clashing = [], []
    for p in base.rglob("state.json"):
        parts = p.relative_to(base).parts
        if "runtime" in parts or "archive" in parts or any(part.startswith(".") for part in parts):
            continue
        if set(RECORD_FOLDERS) & set(parts):
            # A saved copy of a scoped file is skipped; a unit record here is a collision.
            clashing.extend(_unit_records(base, [p]))
            continue
        units.append(str(p.parent.relative_to(base)))
    if clashing:
        raise _reserved(clashing)
    return sorted(units)


def _unit_records(base, paths):
    """The units whose own records these state.json files are: each names its folder."""
    names = []
    for path in paths:
        name = path.parent.relative_to(base).as_posix()
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get("unit") == name:
            names.append(name)
    return names


def _reserved(units):
    return WorkflowError(
        f"Unit {', '.join(sorted(units))} uses a name Firebreak reserves for its own record folders "
        f"({', '.join(RECORD_FOLDERS)}); move it under .fbk/archive/ and recreate it under another name."
    )


def unclaimed_record_folder(root, unit, folder):
    """One of the unit's record folders, once no unit is found living there: Firebreak
    moves, replaces, and deletes these folders whole, so a colliding unit is refused, never
    moved or removed. Every move or delete of a record folder goes through this check."""
    path = unit_dir(root, unit) / folder
    if path.is_dir():
        clashing = _unit_records(confined(root, ".fbk"), path.rglob("state.json"))
        if clashing:
            raise _reserved(clashing)
    return path


def record_folder(root, unit, folder):
    """One of the unit's record folders, unclaimed by any unit and git-ignored."""
    path = unclaimed_record_folder(root, unit, folder)
    ensure_ignored(root, unit)
    return path


def remove_record_folder(root, unit, folder):
    """Delete one of the unit's record folders, refusing a unit found living there. Only
    an absent folder is ignored; a failed deletion is refused."""
    remove_folder(root, unclaimed_record_folder(root, unit, folder))


def remove_folder(root, path):
    """Delete one of Firebreak's own folders. Only an absent folder is ignored; a failed
    deletion is refused, so the caller can retry."""
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise WorkflowError(
            f"Firebreak could not delete {path.relative_to(Path(root).resolve()).as_posix()} "
            f"({getattr(exc, 'filename', None) or path}: {exc.strerror or exc}); make it deletable, then retry."
        ) from exc


def ensure_ignored(root, unit=None):
    """Keep Firebreak's own folders out of Git. .fbk/.gitignore gains any missing entry,
    keeping the project's own lines, and the runtime folder and every unit's record folders
    carry their own ignore-everything file, which no rule in .fbk/.gitignore can override.
    What those files still cannot hide, such as a copied ignore file re-including a path
    inside the baseline, is refused, naming the rule."""
    path = confined(root, ".fbk/.gitignore")
    try:
        text = path.read_text() if path.exists() else ""
        missing = [entry for entry in IGNORED if entry not in text.splitlines()]
        if missing:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text + ("\n" if text and not text.endswith("\n") else "")
                            + "".join(f"{entry}\n" for entry in missing))
        runtime = confined(root, ".fbk/runtime")
        runtime.mkdir(parents=True, exist_ok=True)
        folders = [runtime] + [
            unit_dir(root, name) / folder
            for name in sorted({*discover(root), *([unit] if unit else [])})
            for folder in RECORD_FOLDERS
            if (unit_dir(root, name) / folder).is_dir()
        ]
        for folder in folders:
            ignore_everything(folder)
        exposed = _exposed(root, _ignore_probes(root, folders))
        if exposed:
            rules = _including_rules(root, exposed)
            raise WorkflowError(
                f"Git does not ignore {', '.join(exposed[:5])}{' and more' if len(exposed) > 5 else ''}, "
                "which Firebreak keeps out of the repository. Remove the rule that re-includes them ("
                + ("; ".join(rules) if rules else "it may be in another ignore file")
                + "), then retry."
            )
    except (OSError, UnicodeError) as exc:
        raise WorkflowError(
            f"Firebreak cannot update its ignore files ({getattr(exc, 'filename', None) or '.fbk/.gitignore'}: "
            f"{getattr(exc, 'strerror', None) or exc}); make them readable, writable text files, then retry."
        ) from exc


def ignore_everything(folder):
    """Give one of Firebreak's own folders an ignore file matching everything in it."""
    marker = Path(folder) / ".gitignore"
    if not marker.is_file() or marker.read_text() != "*\n":
        marker.write_text("*\n")


def _git(root, *arguments, stdin=None):
    try:
        return subprocess.run(["git", "-C", str(root), *arguments], input=stdin,
                              capture_output=True, text=True, check=False)
    except OSError:
        return None  # Without Git there is nothing to keep these folders out of.


def _ignore_probes(root, folders):
    """Paths Git must ignore: a sample and every actual file in each of these folders."""
    base = Path(root).resolve()
    probes = []
    for folder in folders:
        probes.append(Path(folder).relative_to(base).as_posix() + "/saved.txt")
        probes.extend(p.relative_to(base).as_posix() for p in Path(folder).rglob("*") if p.is_file())
    return probes


def _exposed(root, paths):
    """The paths Git would not ignore; empty when Git cannot say, as outside a repository
    or without Git."""
    probe = _git(root, "check-ignore", "--no-index", "--stdin", "-z", stdin="\0".join(paths) + "\0")
    if probe is None or probe.returncode not in (0, 1):
        return []
    ignored = set(filter(None, probe.stdout.split("\0")))
    return [path for path in paths if path not in ignored]


def _including_rules(root, paths):
    """The ignore rules, with file and line, that re-include these paths or their folders."""
    candidates = set(paths)
    for path in paths:
        parent = Path(path).parent
        while parent.parts and parent != Path(".fbk"):
            if confined(root, parent.as_posix()).is_dir():
                candidates.add(parent.as_posix())
            parent = parent.parent
    probe = _git(root, "check-ignore", "-v", "-n", "--no-index", "--stdin", stdin="\n".join(sorted(candidates)) + "\n")
    rules = {line.partition("\t")[0] for line in (probe.stdout if probe else "").splitlines()}
    return sorted(rule for rule in rules if ":!" in rule)  # source:line:!pattern


def project_root(start):
    start = Path(start).resolve()
    for path in (start, *start.parents):
        if (path / ".fbk/config.json").is_file() or (path / ".git").exists():
            return path
    return start


def enabled(root):
    return confined(root, ".fbk/config.json").is_file()


def project_config(root):
    config = read_json(confined(root, ".fbk/config.json"))
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise WorkflowError(
            "Invalid .fbk/config.json; restore schema_version 1 configuration."
        )
    return config
