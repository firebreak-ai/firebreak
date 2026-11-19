"""The spec trim: before the spec's review, a fresh session cuts what catches nothing the
rest miss, and Firebreak lists the cuts in a closing section of the spec.

Every spec example becomes a test someone must keep working, and nothing else in the
workflow removes one. The trim runs once per spec draft (the phase's generation). A
session that ends without a result is retried once; if the retry fails too, the close
goes on with the untrimmed spec. A trimmed spec that fails a check goes back to its
author. Neither spends a review round or asks the human anything.
"""

import json
from pathlib import Path

from . import artifact_hygiene, decisions, review
from .store import WorkflowError, digest, event, load, now, project_config, save, transaction, unit_dir

BRIEF = "review/spec-trim.md"
SECTION = "## Removed on purpose"
OPENING = (
    "These were removed on purpose. A removed item is not a gap: do not report it or add it "
    "back during this unit. Only a later code review may restore one."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "removed": {
            "type": "array",
            "maxItems": 100,
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "string", "minLength": 1, "maxLength": 300},
                    "reason": {"type": "string", "minLength": 1, "maxLength": 300},
                },
                "required": ["item", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["removed"],
    "additionalProperties": False,
}


def split_section(text):
    """The spec without its removed-on-purpose section, and the items that section lists."""
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if line.strip() == SECTION), None)
    if start is None:
        return text, []
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    items = [line for line in lines[start + 1:end] if line.startswith("- ")]
    return "\n".join(lines[:start] + lines[end:]).rstrip("\n") + "\n", items


def with_section(text, items):
    if not items:
        return text
    return text.rstrip("\n") + f"\n\n{SECTION}\n\n{OPENING}\n\n" + "\n".join(items) + "\n"


def _flat(value):
    return " ".join(value.split())


def summary(trim):
    """The one line close and status report about the trim."""
    if trim["outcome"] == "not-run":
        return f"The spec trim did not run ({trim['reason']}); the spec goes to review untrimmed."
    if trim["outcome"] == "unchanged":
        return "The spec trim found nothing to cut."
    line = (f"The spec trim cut the spec from {trim['before']:,} to {trim['after']:,} characters; "
            f"{trim['removed']} item(s) listed under \"Removed on purpose\" at its end.")
    if trim["outcome"] == "failed-check":
        line += " The trimmed spec failed a check; fix it and close again. The trim does not run again for this draft."
    return line


def prompt(root, unit, rows, config):
    sections = review._brief_sections(BRIEF, ("Trim",))
    guides = (Path(review.__file__).resolve().parents[3] / "fbk-docs" / "workflow").as_posix()
    text = " ".join(sections["Trim"]).replace("{unit}", unit).replace(
        "{spec}", f".fbk/{unit}/spec.md").replace("{guides}", guides)
    base = unit_dir(root, unit)
    accepted = [path.relative_to(root).as_posix() for path in [base / "prd.md", *sorted((base / "design").glob("**/*.md"))]
                if path.is_file()]
    from .constraints import block_text, render

    packet = {
        "spec": f".fbk/{unit}/spec.md",
        "human_decisions": [decisions.lean(row) for row in rows],
        "accepted_documents": accepted,
    }
    return text + "\n" + json.dumps(packet, ensure_ascii=False) + block_text(render("spec-trim", config, SCHEMA))


def launch(root, unit, rows, config):
    """One trim session; returns its list of removed items, or raises when it gave no result."""
    timeout = review.bounded_number(config, "review_timeout", 1200, 86400)
    turns = config.get("reviewer_max_turns", 100)
    spec = (root / ".fbk" / unit / "spec.md").resolve().as_posix()
    argv = [
        "claude", "-p", "--safe-mode", "--restricted",
        "--model", config.get("reviewer_model", "opus"),
        "--effort", config.get("reviewer_effort", "medium"),
        "--output-format", "json",
        "--json-schema", json.dumps(SCHEMA),
        "--tools", "Read,Glob,Grep,Edit",
        # The host denies an edit to any file but the spec.
        "--allowedTools", f"Read,Glob,Grep,Edit(/{spec})",
        "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
        "--permission-mode", "dontAsk",
        "--settings", '{"disableAllHooks":true}',
        "--setting-sources", "",
        "--max-turns", str(turns),
        "--no-session-persistence",
    ]
    with review.command_scope(root):
        result = review.run_command(argv, root, timeout, prompt(root, unit, rows, config))
    return _parse(result, turns)


def _parse(result, turns):
    try:
        envelope = json.loads(result["stdout"])
    except (ValueError, TypeError):
        envelope = None
    if isinstance(envelope, dict) and envelope.get("subtype") == "error_max_turns":
        # constraint: trim-limits
        raise WorkflowError(f"the session reached its {turns} turn ceiling")
    if result["exit_code"]:
        detail = (result["stderr"].strip() or result["stdout"].strip())[-300:]
        # constraint: n/a host process failure, not model output
        raise WorkflowError(f"the session failed (exit {result['exit_code']}): {detail}")
    if not isinstance(envelope, dict) or envelope.get("is_error"):
        # constraint: n/a host envelope status, not model output
        raise WorkflowError("the session returned no result")
    data = envelope.get("structured_output")
    removed = data.get("removed") if isinstance(data, dict) else None
    if not isinstance(removed, list) or any(
        not isinstance(entry, dict) or set(entry) != {"item", "reason"}
        or not all(isinstance(entry[key], str) and entry[key].strip() for key in entry)
        for entry in removed
    ):
        # constraint: trim-removed-list
        raise WorkflowError("the session's list of removed items was missing or malformed")
    return removed


def _check(root, record, session, ready):
    """The trimmed spec passes the spec's structure and link checks and the invisible-character scan."""
    try:
        ready(root, record, "spec", session)
    except WorkflowError as exc:
        # constraint: trim-result-checks
        raise WorkflowError(str(exc)) from exc
    report = artifact_hygiene.scan_files(root, [f".fbk/{record['unit']}/spec.md"])
    if report["findings"]:
        # constraint: trim-result-checks
        raise WorkflowError(artifact_hygiene.failure_message(report))


def run(root, unit, session, ready):
    """Trim the spec once per draft. Returns the trim's record, or None when the trim
    already ran for this draft or the author's own spec is not ready for review; raises when
    the trimmed spec fails a check."""
    path = unit_dir(root, unit) / "spec.md"
    with transaction(root):
        record = load(root, unit)
        work = record["phases"]["spec"]
        if (work.get("trim") or {}).get("generation") == work["generation"]:
            return None
        # The author's own spec must pass first, so a later failure is the trim's.
        ready(root, record, "spec", session)
        if artifact_hygiene.scan_files(root, [f".fbk/{unit}/spec.md"])["findings"]:
            return None
        rows = decisions.governing_through(root, record, "spec")
        before = path.read_text(encoding="utf-8")
    config = project_config(root)
    body, kept = split_section(before)
    removed, failure = None, None
    for _attempt in range(2):
        path.write_text(body, encoding="utf-8")
        try:
            removed = launch(root, unit, rows, config)
            break
        except WorkflowError as exc:
            failure = str(exc)
    problem = None
    with transaction(root):
        record = load(root, unit)
        work = record["phases"]["spec"]
        trim = {"generation": work["generation"], "at": now(), "brief": digest(review._detection_guidance((BRIEF,))[BRIEF])}
        after = path.read_text(encoding="utf-8")
        if removed is None:
            path.write_text(before, encoding="utf-8")
            trim.update(outcome="not-run", reason=_flat(failure)[:300])
        elif after == body:
            path.write_text(before, encoding="utf-8")
            trim.update(outcome="unchanged")
        else:
            listed = [f"- {_flat(entry['item'])}: {_flat(entry['reason'])}" for entry in removed]
            path.write_text(with_section(after, kept + listed), encoding="utf-8")
            try:
                _check(root, record, session, ready)
                trim.update(outcome="trimmed")
            except WorkflowError as exc:
                problem = str(exc)
                trim.update(outcome="failed-check", reason=_flat(problem)[:300])
            trim.update(removed=len(listed))
        trim.update(before=len(before), after=len(path.read_text(encoding="utf-8")))
        work["trim"] = trim
        event(record, "spec-trimmed", session, **trim)
        save(root, record)
    if problem:
        raise WorkflowError(f"{summary(trim)}\n{problem}")
    return trim
