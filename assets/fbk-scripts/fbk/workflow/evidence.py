"""Artifact selection and executable acceptance checks, independent of Claude."""

import fnmatch
import hashlib
import re
from pathlib import Path

from .store import WorkflowError, confined, digest, read_json, unit_dir

PHASES = ("intent", "design", "spec", "breakdown", "implement")
# The test checkpoint is implement's review gate over the authored tests. Its review
# record sits beside the phases' in record["phases"], but it is not a phase.
CHECKPOINT = "test-checkpoint"
REVIEWS = (*PHASES, CHECKPOINT)


def ordered(phase):
    """The phase that places a review in phase order: the checkpoint reviews inside implement."""
    return "implement" if phase == CHECKPOINT else phase


def phases(record):
    return [
        p
        for p in PHASES
        if (p != "design" or record["design"])
        and (record["kind"] != "project" or p not in {"breakdown", "implement"})
    ]


def scope(root, unit):
    data = read_json(unit_dir(root, unit) / "scope.json")
    if not isinstance(data, dict) or set(data) - {
        "sources",
        "tests",
        "checks",
        "docs",
        "context",
        "creates",
        "test_regions",
    }:
        raise WorkflowError(
            "scope.json needs sources, tests, checks, and optional docs/context/creates/test_regions; remove unknown fields."
        )
    creates = data.get("creates", [])
    if not isinstance(creates, list) or any(
        not isinstance(p, str) or not p.strip("/") or any(c in p for c in "*?[")
        for p in creates
    ):
        raise WorkflowError(
            "scope.json creates must list exact repository-relative paths the unit creates; end a directory with /."
        )
    for path in creates:
        confined(root, path)
    regions = data.get("test_regions", [])
    if not isinstance(regions, list) or any(
        not isinstance(entry, dict)
        or set(entry) != {"files", "start"}
        or not isinstance(entry["files"], list)
        or not entry["files"]
        or any(not isinstance(p, str) or not p for p in entry["files"])
        or not isinstance(entry["start"], str)
        for entry in regions
    ):
        raise WorkflowError(
            'scope.json test_regions must list objects {"files": [<paths or globs>], "start": "<regular expression>"}, '
            "each naming the files whose tests sit at the end and the line where those tests start."
        )
    for entry in regions:
        try:
            re.compile(entry["start"])
        except re.error as exc:
            raise WorkflowError(
                f"scope.json test_regions start {entry['start']!r} is not a valid regular expression ({exc})."
            ) from exc
    fields = {field: data.get(field, []) for field in ("sources", "tests", "docs", "context")}
    # Region globs follow the confinement and control-record rules of the other fields.
    fields["test_regions"] = [p for entry in regions for p in entry["files"]]
    for field, values in fields.items():
        if not isinstance(values, list) or any(
            not isinstance(p, str) or not p for p in values
        ):
            raise WorkflowError(
                f"scope.json {field} must be a list of repository-relative paths or globs."
            )
        for pattern in values:
            confined(root, pattern)
            if field == "context":
                from .review_context import host_history

                if host_history(pattern) or any(
                    host_history(p) for p in expand(root, [pattern])
                ):
                    raise WorkflowError(
                        "Context must contain original contracts or conventions; host history, settings and credentials are excluded."
                    )
            if field != "context" and (
                Path(pattern).parts[0] in {".fbk", ".git", ".claude"}
                or any(
                    Path(p).parts[0] in {".fbk", ".claude"}
                    for p in expand(root, [pattern])
                )
            ):
                raise WorkflowError(
                    f"Scope cannot include workflow or host control records: {pattern}"
                )
            if field == "context" and (
                Path(pattern).parts[0] in {".fbk", ".git"}
                or any(
                    Path(p).parts[0] in {".fbk", ".git"}
                    for p in expand(root, [pattern])
                )
            ):
                raise WorkflowError(
                    "Context sources must name original repository conventions or contracts, outside workflow history."
                )
    checks = data.get("checks", [])
    if not isinstance(checks, list) or any(
        not isinstance(c, list)
        or not c
        or any(not isinstance(a, str) or not a for a in c)
        for c in checks
    ):
        raise WorkflowError(
            'scope.json checks must be argument arrays, for example [["uv", "run", "pytest"]].'
        )
    result = {
        "sources": data.get("sources", []),
        "tests": data.get("tests", []),
        "docs": data.get("docs", []),
        "checks": checks,
    }
    if "context" in data:
        result["context"] = data["context"]
    if "creates" in data:
        result["creates"] = creates
    if regions:
        result["test_regions"] = regions
        _check_region_files(root, result)
    return result


# Some languages keep unit tests at the end of the source file they test. A test region
# is that end of a file: it starts at the first line its start expression matches and runs
# to the end of the file. The region is a scoped test; the code above it is a production file.


def _check_region_files(root, declared):
    """Each file a region entry matches, existing or declared in creates, is a production
    file, not a whole-file test, and is matched by one entry only."""
    created = [canonical(p) for p in declared.get("creates", []) if not p.endswith("/")]
    seen = {}
    for entry in declared["test_regions"]:
        for path in sorted(set(expand(root, entry["files"])) | {p for p in created if matches(p, entry["files"])}):
            if path in seen:
                raise WorkflowError(
                    f"scope.json test_regions matches {path} in two entries; match each file with one entry."
                )
            seen[path] = entry
            if not matches(path, declared["sources"]):
                raise WorkflowError(
                    f"scope.json test_regions matches {path}, which sources does not cover; a region-bearing "
                    "file is a production file, so add it to sources or correct the region's files."
                )
            if matches(path, declared["tests"]):
                raise WorkflowError(
                    f"scope.json test_regions matches {path}, which tests also matches as a whole test file; "
                    "remove it from tests or from the region's files."
                )


def region_start(declared, path):
    """The start expression of the test region a file carries, or None when it carries none."""
    return next((entry["start"] for entry in declared.get("test_regions", [])
                 if matches(path, entry["files"])), None)


def split_region(data, start):
    """A region-bearing file's bytes as the code above its region and the region. Text
    matching only: the region starts at the first line the expression finds on the line
    without its line ending, and is empty when no line matches."""
    offset = 0
    for line in data.splitlines(keepends=True):
        text = line.decode("utf-8", errors="surrogateescape").rstrip("\r\n")
        if re.search(start, text):
            return data[:offset], data[offset:]
        offset += len(line)
    return data, b""


def test_files(root, declared):
    """Every scoped test location: whole test files and region-bearing files."""
    regions = [p for entry in declared.get("test_regions", []) for p in entry["files"]]
    return sorted(set(expand(root, declared["tests"])) | set(expand(root, regions)))


def test_fingerprint(declared, path, data):
    """A scoped test's fingerprint: a whole test file's, or a region's alone, so writing
    the code above a region never changes it."""
    start = region_start(declared, path)
    return hashlib.sha256(data if start is None else split_region(data, start)[1]).hexdigest()


EMPTY_REGION = hashlib.sha256(b"").hexdigest()


def held_tests(declared, fingerprints):
    """Fingerprints without empty regions: a region-bearing file with no start line holds
    no test, so it compares as a file that does not exist, and a new one changes nothing."""
    return {path: value for path, value in fingerprints.items()
            if value != EMPTY_REGION or region_start(declared, path) is None}


def test_fingerprints(root, declared, paths=None):
    """The fingerprint of each scoped test, or of each named one. A named region-bearing
    file that does not exist has an empty region."""
    result = {}
    for relative in sorted(set(test_files(root, declared) if paths is None else paths)):
        target = confined(root, relative)
        if region_start(declared, relative) is not None and not target.exists() and not target.is_symlink():
            result[relative] = EMPTY_REGION
            continue
        try:
            data = target.read_bytes()
        except OSError as exc:
            raise WorkflowError(f"Missing or unreadable evidence {relative}: {exc}") from exc
        result[relative] = test_fingerprint(declared, relative, data)
    return result


def canonical(path):
    """One spelling per repository path: ./pkg/, pkg/ and pkg name the same path."""
    return Path(path).as_posix()


def _declaration(entry):
    """A creates entry as (canonical path, kind); a trailing / declares a directory."""
    return canonical(entry), "directory" if entry.endswith("/") else "file"


def declared_kinds(declared):
    """The kind of each path the spec declares it creates, keyed by canonical path."""
    kinds = {}
    for entry in declared.get("creates", []):
        path, kind = _declaration(entry)
        if kinds.setdefault(path, kind) != kind:
            raise WorkflowError(
                f"scope.json creates {path} as both a file and a directory; keep one entry, "
                "ending in / only when it is a directory."
            )
    return kinds


def check_creates(root, record):
    """Spec close: every declared new path is new, in scope (sources, tests, or docs, since
    tasks own all three), and under a real or declared directory. A path an earlier
    accepted spec of this unit declared with the same kind may exist by now."""
    declared = scope(root, record["unit"])
    kinds = declared_kinds(declared)
    accepted = {
        _declaration(entry)
        for row in record["events"]
        if row["event"] == "closed" and row.get("phase") == "spec"
        for entry in row.get("creates", [])
    }
    scoped = declared["sources"] + declared["tests"] + declared["docs"]
    for entry in declared.get("creates", []):
        path, kind = _declaration(entry)
        target = confined(root, path)
        if (target.exists() or target.is_symlink()) and (path, kind) not in accepted:
            raise WorkflowError(
                f"scope.json creates {entry}, which already exists; list only paths the unit creates."
            )
        # A directory fits when something inside it can match a scope pattern, as
        # tests/ holds tests/test_jobs.py and pkg/sub/ can hold pkg/**/*.go files;
        # the directory matching a file pattern itself does not count.
        # Nothing under a tool or cache folder is ever matched, so it is never in scope.
        in_scope = (
            not excluded(path)
            and any(patterns_overlap(f"{path}/*/**", pattern) for pattern in scoped)
            if kind == "directory"
            else matches(path, scoped)
        )
        if not in_scope:
            raise WorkflowError(
                f"scope.json creates {entry} outside the scope's sources, tests, and docs; add its location to the scope, or correct the path."
            )
        parent = Path(path).parent.as_posix()
        if parent != "." and not confined(root, parent).is_dir() and kinds.get(parent) != "directory":
            raise WorkflowError(
                f"scope.json creates {entry} under {parent}/, which does not exist; declare that directory in creates too."
            )


EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".venv", ".git", "node_modules"}


def excluded(path):
    """A path under a tool or cache folder, which no scope pattern ever matches."""
    return any(part in EXCLUDED_PARTS for part in Path(path).parts)


def exit_matches(expected, actual):
    """A check's expected exit code: an exact integer, or "nonzero" for any failure."""
    if expected == "nonzero":
        return type(actual) is int and actual != 0
    return type(actual) is int and actual == expected


def is_red(result):
    """Red evidence is a check that ran and exited non-zero."""
    return bool(result) and exit_matches("nonzero", result.get("exit_code"))


def matches(path, patterns):
    parts = Path(path).parts
    if excluded(path):
        return False

    def match_segments(actual, pattern):
        if not pattern:
            return not actual
        if pattern[0] == "**":
            return (
                match_segments(actual, pattern[1:])
                or bool(actual)
                and match_segments(actual[1:], pattern)
            )
        return (
            bool(actual)
            and fnmatch.fnmatchcase(actual[0], pattern[0])
            and match_segments(actual[1:], pattern[1:])
        )

    for pattern in patterns:
        pattern_parts = Path(pattern).parts
        if (
            not any(c in pattern for c in "*?[")
            and parts[: len(pattern_parts)] == pattern_parts
        ):
            return True  # a literal directory includes its descendants
        if match_segments(parts, pattern_parts):
            return True
    return False



def _segment_tokens(segment):
    tokens, i = [], 0
    while i < len(segment):
        char = segment[i]
        end = -1
        if char == "[":
            start = i + 1
            start += segment[start:start + 1] == "!"
            start += segment[start:start + 1] == "]"
            end = segment.find("]", start)
        if end != -1:
            tokens.append(("class", segment[i:end + 1]))
            i = end + 1
            continue
        tokens.append((char if char in "*?" else "literal", char))
        i += 1
    return tuple(tokens)


def _token_accepts(token, char):
    kind, text = token
    if kind == "literal":
        return char == text
    return kind == "?" or fnmatch.fnmatchcase(char, text)


def _tokens_share(first, second):
    """Whether one character satisfies both single-character tokens, judged by
    fnmatch itself so class semantics (ranges, negation, malformed or descending
    ranges) cannot drift from ``matches``. A class's member set is a union of
    ranges whose ends are characters written in it; if two such sets (or their
    complements) share a character, they share one at a written character or its
    neighbor, so those candidates suffice."""
    for token, other in ((first, second), (second, first)):
        if token[0] == "literal":
            return _token_accepts(other, token[1])
    candidates = {"a"}
    for kind, text in (first, second):
        if kind == "class":
            for char in text:
                code = ord(char)
                candidates.update(chr(c) for c in (code - 1, code, code + 1) if 0 <= c <= 0x10FFFF)
    candidates.discard("/")  # a path segment never holds a separator
    return any(_token_accepts(first, c) and _token_accepts(second, c) for c in candidates)


def _segments_overlap(first, second):
    """Whether some file name matches both glob segments."""
    from functools import lru_cache

    a, b = _segment_tokens(first), _segment_tokens(second)

    @lru_cache(maxsize=None)
    def overlap(i, j):
        # A star absorbs only a token some character satisfies; [z-a] matches nothing.
        if i < len(a) and a[i][0] == "*":
            return overlap(i + 1, j) or j < len(b) and absorbable(b[j]) and overlap(i, j + 1)
        if j < len(b) and b[j][0] == "*":
            return overlap(i, j + 1) or i < len(a) and absorbable(a[i]) and overlap(i + 1, j)
        if i == len(a) or j == len(b):
            return i == len(a) and j == len(b)
        return _tokens_share(a[i], b[j]) and overlap(i + 1, j + 1)

    def absorbable(token):
        return token[0] == "*" or _tokens_share(token, ("?", "?"))

    return overlap(0, 0)


def patterns_overlap(first, second):
    """Whether any path can match both scope patterns, with the matching rules
    of ``matches``: ``**`` spans folders and a literal folder includes its descendants."""

    def parts(pattern):
        result = Path(pattern).parts
        return result if any(c in pattern for c in "*?[") else result + ("**",)

    a, b = parts(first), parts(second)

    def overlap(i, j):
        # ** absorbs only a segment some name matches.
        if i < len(a) and a[i] == "**":
            return overlap(i + 1, j) or j < len(b) and absorbable(b[j]) and overlap(i, j + 1)
        if j < len(b) and b[j] == "**":
            return overlap(i, j + 1) or i < len(a) and absorbable(a[i]) and overlap(i + 1, j)
        if i == len(a) or j == len(b):
            return i == len(a) and j == len(b)
        return _segments_overlap(a[i], b[j]) and overlap(i + 1, j + 1)

    def absorbable(segment):
        return segment == "**" or _segments_overlap(segment, "*")

    return overlap(0, 0)

def expand(root, patterns):
    files = set()
    for pattern in patterns:
        target = confined(root, pattern)
        candidates = (
            Path(root).glob(pattern) if any(c in pattern for c in "*?[") else [target]
        )
        for path in candidates:
            paths = path.rglob("*") if path.is_dir() else [path]
            for p in paths:
                if excluded(p.relative_to(root)):
                    continue
                relative = p.relative_to(root).as_posix()
                confined(root, relative)
                if p.is_file() and matches(relative, [pattern]):
                    files.add(relative)
    return sorted(files)


def symlink_targets(root, paths):
    """Each path that is a symbolic link, with the target it names. A fingerprint reads
    through a link, so a link retargeted between equal files is told apart by this."""
    import os

    return {relative: os.readlink(confined(root, relative))
            for relative in sorted(set(paths)) if confined(root, relative).is_symlink()}


def file_hashes(root, paths):
    result = {}
    for relative in sorted(set(paths)):
        path = confined(root, relative)
        try:
            result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise WorkflowError(
                f"Missing or unreadable evidence {relative}: {exc}"
            ) from exc
    return result


def subject(root, record, phase):
    """Cumulative input closure makes upstream changes invalidate downstream evidence.
    The checkpoint reads what breakdown accepted plus every scoped test."""
    if phase == CHECKPOINT:
        # A region-bearing file is read whole; the revision fingerprints only its region.
        files = subject(root, record, "breakdown")
        return {**files, **file_hashes(root, test_files(root, scope(root, record["unit"])))}
    base = unit_dir(root, record["unit"]).relative_to(root).as_posix()
    own = {
        "intent": [f"{base}/prd.md"],
        "design": [f"{base}/design"],
        "spec": [f"{base}/spec.md", f"{base}/scope.json"],
        "breakdown": [f"{base}/tasks.json"],
        "implement": [],
    }
    selected = []
    for p in phases(record):
        for pattern in own[p]:
            files = expand(root, [pattern])
            if not files:
                raise WorkflowError(
                    f"Unit {record['unit']}: create {pattern} before closing {phase}."
                )
            selected.extend(files)
        if p == phase:
            break
    if phase in {"spec", "breakdown", "implement"}:
        declared = scope(root, record["unit"])
        for pattern in declared.get("context", []):
            contexts = expand(root, [pattern])
            if not contexts:
                raise WorkflowError(f"Missing required context: {pattern}")
            selected.extend(contexts)
    if phase == "implement":
        declared = scope(root, record["unit"])
        selected.extend(
            expand(root, declared["sources"] + declared["tests"] + declared["docs"])
        )
    return file_hashes(root, selected)


def revision_inputs(root, record, phase):
    """Everything a phase revision digests; callers may narrow it before hashing."""
    from . import decisions

    if phase == CHECKPOINT:
        # Production code is left out, so writing code never makes an accepted checkpoint stale.
        # The governing decisions its reviewer reads are in; process records and dispositions are not.
        governing = {
            row["id"] for row in decisions.active(record)
            if row.get("kind", "governs") == "governs" and not row.get("dispositions")
        }
        bound = [row for row in decisions.binding(root, record, phase) if row["id"] in governing]
        declared = scope(root, record["unit"])
        return {
            "breakdown": revision(root, record, "breakdown"),
            "tests": held_tests(declared, test_fingerprints(root, declared)),
            **({"decisions": bound} if bound else {}),
        }

    # A decision carrying dispositions answers a review's findings; it changes nothing the
    # review read, so it leaves the revision alone and a recorded review stays reusable.
    answering = {row["id"] for row in record.get("decisions", []) if row.get("dispositions")}
    decision_inputs = [
        row for row in decisions.binding(root, record, phase) if row["id"] not in answering
    ]
    applicable = phases(record)
    selected = {
        p: record.get("review_plans", {}).get(p)
        for p in applicable[: applicable.index(phase) + 1]
        if record.get("review_plans", {}).get(p)
    }
    return {
        "files": subject(root, record, phase),
        "design": record["design"],
        "parent": record.get("parent_evidence"),
        **({"review_plans": selected} if selected else {}),
        **({"decisions": decision_inputs} if decision_inputs else {}),
    }


def revision(root, record, phase):
    return digest(revision_inputs(root, record, phase))


def supporting_current(root, accepted):
    """Original supporting contracts remain dependencies after acceptance."""
    result = accepted.get("review") or {}
    if "supporting_files" not in result:
        return True  # Historical acceptance is retained until explicitly reopened.
    from . import review_context

    return review_context.supporting_fresh(root, result)


def structural(root, record, phase):
    files = subject(root, record, phase)
    for path in files:
        if path.endswith(".md") and not confined(root, path).read_text().strip():
            raise WorkflowError(
                f"Empty artifact {path}; write the phase's work product."
            )
    if phase in {"spec", "breakdown", "implement", CHECKPOINT}:
        declared = scope(root, record["unit"])
        if record["kind"] == "feature" and not (
            declared["sources"] and declared["checks"]
            and (declared["tests"] or declared.get("test_regions"))
        ):
            raise WorkflowError(
                "Feature scope.json must declare sources, tests or test_regions, and executable checks."
            )
    if phase in {"breakdown", "implement", CHECKPOINT}:
        tasks = read_json(unit_dir(root, record["unit"]) / "tasks.json")
        if not isinstance(tasks, list) or not tasks:
            raise WorkflowError("tasks.json must contain a nonempty task array.")
        ids = set()
        for task in tasks:
            if (
                not isinstance(task, dict)
                or not isinstance(task.get("id"), str)
                or not task["id"]
                or task["id"] in ids
                or not isinstance(task.get("description"), str)
                or not task["description"].strip()
                or not isinstance(task.get("files"), list)
                or not task["files"]
                or not isinstance(task.get("depends_on", []), list)
                or any(not isinstance(d, str) for d in task.get("depends_on", []))
            ):
                raise WorkflowError(
                    "Each task needs a unique id, description, files, and depends_on array."
                )
            ids.add(task["id"])
            for path in task["files"]:
                if not isinstance(path, str):
                    raise WorkflowError(
                        "Task files must be repository-relative strings."
                    )
                confined(root, path)
                if not matches(
                    path, declared["sources"] + declared["tests"] + declared["docs"]
                ):
                    raise WorkflowError(
                        f"Task {task['id']} names {path} outside scope.json."
                    )
        pending = {t["id"]: set(t.get("depends_on", [])) for t in tasks}
        if any(deps - ids for deps in pending.values()):
            raise WorkflowError("Task dependency names an unknown task.")
        while pending:
            ready = {i for i, deps in pending.items() if not deps}
            if not ready:
                raise WorkflowError(
                    "Task dependency cycle; break the cycle before implementation."
                )
            pending = {i: deps - ready for i, deps in pending.items() if i not in ready}
    return files
