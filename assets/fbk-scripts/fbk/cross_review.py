"""Cross-model review runner.

Invokes the Codex CLI against a prompt file, captures the output to a dated
report file in the configured report directory, and prints a single JSON status
object on stdout.  The runner never calls sys.exit with a non-zero code; every
path returns 0 so the dispatch chokepoint records the invocation as outcome=pass.

JSON output shape:
    {"status": "success"|"failed"|"skipped", "report_path": <str|null>, "cause": <str|null>}
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # handled at runtime — config read returns failed if yaml unavailable


# ---------------------------------------------------------------------------
# Public interface required by tests
# ---------------------------------------------------------------------------

def _timestamp() -> str:
    """Return a YYYY-MM-DD-HHMMSS timestamp string used to name report files.

    Exposed as a module-level function so tests can patch it to control
    filenames deterministically.
    """
    return datetime.now().strftime("%Y-%m-%d-%H%M%S")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_CONFIG_REL = os.path.join(".claude", "automation", "config.yml")
_AUTH_MARKERS = ("401", "unauthorized", "not logged in", "login")
_SAFE_CHAR = re.compile(r"[^A-Za-z0-9._-]")


def _safe_segment(value: str) -> str:
    """Replace characters outside [A-Za-z0-9._-] with '-'; fall back to 'x'."""
    sanitized = _SAFE_CHAR.sub("-", value)
    return sanitized if sanitized else "x"


def _load_config(project_root: str) -> tuple[dict | None, str | None]:
    """Load and parse .claude/automation/config.yml from project_root.

    Returns (config_dict, error_cause):
    - (dict, None)  on success (may be empty dict)
    - (None, cause) on parse error
    - ({}, None)    when file is absent
    """
    if yaml is None:
        return None, "PyYAML not available; install pyyaml"

    config_path = os.path.join(project_root, _CONFIG_REL)
    if not os.path.exists(config_path):
        return {}, None

    try:
        with open(config_path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return None, f"config parse error: {exc}"

    if data is None:
        # Empty file → treated as absent config (skip downstream).
        return {}, None
    if not isinstance(data, dict):
        # A non-mapping root (e.g. a bare `true` or a list) is malformed config.
        return None, "config root is malformed: expected a mapping"
    return data, None


def _has_auth_marker(text: str) -> bool:
    lowered = text.lower()
    return any(m in lowered for m in _AUTH_MARKERS)


def _result(status: str, report_path: str | None = None, cause: str | None = None) -> dict:
    return {"status": status, "report_path": report_path, "cause": cause}


def _skipped(cause: str | None = None) -> dict:
    return _result("skipped", cause=cause)


def _failed(cause: str) -> dict:
    return _result("failed", cause=cause)


def _success(report_path: str) -> dict:
    return _result("success", report_path=report_path)


def _unique_report_path(report_dir: Path, stem: str) -> Path:
    """Return a path that does not yet exist, appending -2/-3/... when needed."""
    candidate = report_dir / f"{stem}.md"
    if not candidate.exists():
        return candidate
    counter = 2
    while True:
        candidate = report_dir / f"{stem}-{counter}.md"
        if not candidate.exists():
            return candidate
        counter += 1


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

def _run_cross_review(
    project_root: str,
    prompt_file: str | None,
    review_type: str | None,
    report_dir: str | None,
    target_label: str | None,
    check_opt_in: bool,
) -> dict:
    """Execute the cross-model review and return the result dict."""

    # --- 1. Load config ---
    config_data, parse_error = _load_config(project_root)
    if config_data is None:
        return _failed(parse_error or "config parse error")

    raw_cr = config_data.get("cross_model_review")
    # An absent block (None) means "not opted in" → skip below. A present but
    # structurally invalid block (e.g. `cross_model_review: true`) is malformed
    # config and must fail visibly, not be silently treated as not opted in.
    if raw_cr is not None and not isinstance(raw_cr, dict):
        return _failed(
            "cross_model_review block is malformed: expected a mapping of "
            "enabled/harness/model/effort"
        )
    cr_cfg = raw_cr or {}

    # --- 2. Opt-in check (always first) ---
    enabled = cr_cfg.get("enabled")
    if enabled is not True:
        if check_opt_in:
            # Spec: --check-opt-in not-opted-in → skipped, cause null
            return _skipped(cause=None)
        return _skipped(cause="cross_model_review.enabled is not true")

    if check_opt_in:
        # Opted in; return success without running anything
        return _result("success")

    # --- 3. Config field validation ---
    harness = cr_cfg.get("harness", "")
    if harness != "codex":
        return _failed(f"unsupported harness: {harness!r}; only 'codex' is supported")

    model = cr_cfg.get("model") or ""
    if not model:
        return _failed("missing field: model is required")

    effort = cr_cfg.get("effort") or ""
    if not effort:
        return _failed("missing field: effort is required")
    # effort is interpolated into Codex's `-c model_reasoning_effort="..."` config
    # value. Reject characters that could break out of that config mini-language
    # (quotes, whitespace, control chars); a conservative safe-char set keeps the
    # value space open (low/medium/high/xhigh all pass) while closing injection.
    if not re.fullmatch(r"[A-Za-z0-9._-]+", str(effort)):
        return _failed("invalid effort value: only letters, digits, '.', '_', '-' are allowed")

    # Resolve prompt file: CLI arg only (config does not supply this per IF-D-01)
    if not prompt_file:
        return _failed("missing required argument: --prompt-file")
    resolved_prompt_file = prompt_file
    if not os.path.isabs(resolved_prompt_file):
        resolved_prompt_file = os.path.join(project_root, resolved_prompt_file)

    prompt_path = Path(resolved_prompt_file)
    if not prompt_path.exists():
        return _failed(f"prompt file not found: {resolved_prompt_file}")
    try:
        prompt_text = prompt_path.read_text(encoding="utf-8")
    except OSError as exc:
        return _failed(f"failed to read prompt file: {exc}")
    if not prompt_text.strip():
        return _failed(f"prompt file is empty: {resolved_prompt_file}")

    # Resolve report dir: CLI arg, defaulting to project root
    resolved_report_dir = report_dir or project_root
    if not os.path.isabs(resolved_report_dir):
        resolved_report_dir = os.path.join(project_root, resolved_report_dir)

    # Resolve review type: CLI arg, defaulting to "review"
    resolved_review_type = review_type or "review"

    # --- 4. Precondition: codex binary ---
    if shutil.which("codex") is None:
        return _failed("codex not found; install the Codex CLI and ensure it is on PATH")

    # --- 5. Build argv and run ---
    report_dir_path = Path(resolved_report_dir)
    try:
        report_dir_path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _failed(f"failed to create report directory: {exc}")

    # Temp file for codex output (in report dir so os.replace is same-filesystem)
    try:
        fd, temp_out = tempfile.mkstemp(suffix=".tmp", dir=str(report_dir_path))
        os.close(fd)
    except OSError as exc:
        return _failed(f"failed to create temp file: {exc}")

    argv = [
        "codex", "exec",
        "-m", model,
        "-c", f'model_reasoning_effort="{effort}"',
        "-C", project_root,
        "-s", "read-only",
        "--skip-git-repo-check",
        "--color", "never",
        "-o", temp_out,
        "-",
    ]

    try:
        proc = subprocess.run(
            argv,
            input=prompt_text,
            capture_output=True,
            text=True,
            errors="replace",  # non-UTF-8 stdout/stderr must not raise during decode
            timeout=600,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        # Clean up the empty temp file before returning
        try:
            os.remove(temp_out)
        except OSError:
            pass
        return _failed("codex invocation timeout: exceeded 600 seconds")
    except OSError as exc:
        try:
            os.remove(temp_out)
        except OSError:
            pass
        return _failed(f"failed to launch codex: {exc}")
    except Exception as exc:  # noqa: BLE001 — backstop: must not leave temp_out behind
        try:
            os.remove(temp_out)
        except OSError:
            pass
        return _failed(f"codex invocation error: {exc}")

    # --- 6. Adjudicate outcome ---
    out_content = ""
    if os.path.exists(temp_out):
        try:
            # errors="replace" so non-UTF-8 Codex output never raises and never
            # escapes leaving the temp file behind (no-partial-on-failure invariant).
            out_content = Path(temp_out).read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass

    if proc.returncode != 0 or not out_content.strip():
        # Failure path: scan for auth markers
        combined = (proc.stdout or "") + (proc.stderr or "")
        cause = f"codex exited with code {proc.returncode}" if proc.returncode != 0 else "codex produced empty output"
        if _has_auth_marker(combined):
            cause += ". Run `codex login` to re-authenticate the Codex CLI, then retry."
        try:
            os.remove(temp_out)
        except OSError:
            pass
        return _failed(cause)

    # --- 7. Write report ---
    ts = _timestamp()
    safe_review_type = _safe_segment(resolved_review_type)
    safe_model = _safe_segment(model)
    stem = f"fbk-cross-review-{safe_review_type}-{safe_model}-{ts}"

    label_line = target_label or "cross-model review"
    header = f"# {label_line} | model: {model} | date: {ts}\n\n"
    report_content = header + out_content

    # Write to a second temp file, then atomic-rename into final path
    try:
        report_fd, report_temp = tempfile.mkstemp(suffix=".tmp", dir=str(report_dir_path))
    except OSError as exc:
        try:
            os.remove(temp_out)
        except OSError:
            pass
        return _failed(f"failed to create report temp file: {exc}")
    try:
        with os.fdopen(report_fd, "w", encoding="utf-8") as fh:
            fh.write(report_content)
    except OSError as exc:
        try:
            os.remove(report_temp)
        except OSError:
            pass
        try:
            os.remove(temp_out)
        except OSError:
            pass
        return _failed(f"failed to write report: {exc}")

    # Remove the codex output temp file now that we've read it
    try:
        os.remove(temp_out)
    except OSError:
        pass

    final_path = _unique_report_path(report_dir_path, stem)

    try:
        os.replace(report_temp, str(final_path))
    except OSError as exc:
        try:
            os.remove(report_temp)
        except OSError:
            pass
        return _failed(f"failed to promote report file: {exc}")

    return _success(str(final_path))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """Parse argv, run the cross-model review, print JSON result, and return 0."""
    parser = argparse.ArgumentParser(
        description="Cross-model review runner — invokes Codex and captures the report."
    )
    parser.add_argument(
        "--project-root",
        default=os.getcwd(),
        help="Project root directory (default: cwd)",
    )
    parser.add_argument(
        "--prompt-file",
        default=None,
        help="Path to the review prompt file (overrides config)",
    )
    parser.add_argument(
        "--review-type",
        default=None,
        help="Review type label used in the report filename (overrides config)",
    )
    parser.add_argument(
        "--report-dir",
        default=None,
        help="Directory for report output (overrides config)",
    )
    parser.add_argument(
        "--target-label",
        default=None,
        help="Human-readable label for the artifact under review",
    )
    parser.add_argument(
        "--check-opt-in",
        action="store_true",
        help="Return only the opt-in decision; do not run Codex",
    )

    try:
        args = parser.parse_args()
    except SystemExit as exc:
        # argparse raises SystemExit(2) on an unknown/invalid flag. Honor the
        # always-return-JSON / exit-0 contract instead of leaking that exit.
        # A 0/None code (e.g. --help) keeps its normal behavior.
        if exc.code not in (0, None):
            print(json.dumps(_failed("invalid command-line arguments")))
            return 0
        raise

    try:
        result = _run_cross_review(
            project_root=args.project_root,
            prompt_file=args.prompt_file,
            review_type=args.review_type,
            report_dir=args.report_dir,
            target_label=args.target_label,
            check_opt_in=args.check_opt_in,
        )
    except Exception as exc:  # noqa: BLE001 — backstop: always-return-JSON contract
        result = _failed(f"unexpected error: {exc}")

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
