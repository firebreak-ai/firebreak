"""Unit and end-to-end tests for fbk.cross_review — the `fbk cross-review` runner.

ALL tests in this file are RED until fbk/cross_review.py exists.  The file
imports the module lazily (inside each test or under a guarded try/except) so
that pytest collection succeeds even while the module is absent, and each test
fails on the missing module rather than erroring at collection time.
"""

import io
import json
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Lazy import guard — keeps collection green while the module is absent
# ---------------------------------------------------------------------------

try:
    import fbk.cross_review as _cross_review_mod
    _CROSS_REVIEW_AVAILABLE = True
except ImportError:
    _cross_review_mod = None
    _CROSS_REVIEW_AVAILABLE = False


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent.parent  # assets/fbk-scripts → repo root
_FBK_PY = Path(__file__).parent.parent / "fbk.py"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_CONFIG = {
    "cross_model_review": {
        "enabled": True,
        "harness": "codex",
        "model": "gpt-5.5",
        "effort": "high",
        "review_type": "spec",
        "prompt_file": ".claude/automation/cross-review-prompt.md",
        "report_dir": "ai-docs/cross-model-review/reports",
    }
}


def _write_config(tmp_path: Path, block: dict | str) -> Path:
    """Write a .claude/automation/config.yml into tmp_path; return the file path.

    Pass a dict to get a valid YAML structure, or a raw string for malformed
    YAML scenarios.
    """
    config_dir = tmp_path / ".claude" / "automation"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.yml"

    if isinstance(block, str):
        config_file.write_text(block)
    else:
        import yaml
        config_file.write_text(yaml.dump(block))

    return config_file


def _write_prompt(tmp_path: Path, content: str = "Review this code.\n") -> Path:
    """Write a non-empty prompt file at the path expected by the minimal config."""
    prompt_file = tmp_path / ".claude" / "automation" / "cross-review-prompt.md"
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text(content)
    return prompt_file


def _run_main(tmp_path: Path, extra_argv: list[str] | None = None) -> tuple[int | None, dict]:
    """Invoke fbk.cross_review.main() with sys.argv pointing at tmp_path project root.

    Returns (exit_code_or_None, parsed_json_output).
    exit_code_or_None is None when main() returns normally (correct), or the
    SystemExit code when a non-zero SystemExit escapes (incorrect per spec).

    Raises AssertionError when stdout is not parseable JSON — callers that
    expect valid JSON can rely on this.
    """
    if not _CROSS_REVIEW_AVAILABLE:
        pytest.fail("fbk.cross_review is not importable — module not yet implemented")

    argv = ["cross-review", "--project-root", str(tmp_path)]
    if extra_argv:
        argv += extra_argv

    captured = io.StringIO()
    exit_code = None

    with mock.patch.object(sys, "argv", argv):
        with redirect_stdout(captured):
            try:
                _cross_review_mod.main()
            except SystemExit as exc:
                exit_code = exc.code

    output = captured.getvalue().strip()
    parsed = json.loads(output)  # AssertionError-style fail when not valid JSON
    return exit_code, parsed


# ---------------------------------------------------------------------------
# Opt-in checks (absent block, disabled)
# ---------------------------------------------------------------------------

class TestOptIn:

    def test_absent_block_yields_skipped(self, tmp_path):
        """No cross_model_review block in config → status skipped, no report."""
        _write_config(tmp_path, {})  # config exists but has no cross_model_review key
        exit_code, result = _run_main(tmp_path)

        assert result["status"] == "skipped"
        assert result.get("report_path") is None
        assert exit_code is None, f"main() must not raise SystemExit; got code {exit_code}"

    def test_enabled_false_yields_skipped(self, tmp_path):
        """cross_model_review.enabled: false → status skipped."""
        cfg = {**_MINIMAL_CONFIG}
        cfg["cross_model_review"] = {**cfg["cross_model_review"], "enabled": False}
        _write_config(tmp_path, cfg)

        exit_code, result = _run_main(tmp_path)

        assert result["status"] == "skipped"
        assert exit_code is None


# ---------------------------------------------------------------------------
# Malformed config
# ---------------------------------------------------------------------------

class TestMalformedConfig:

    def test_malformed_yaml_yields_failed_valid_json(self, tmp_path):
        """Unparseable YAML → status failed; output is valid JSON; no non-zero SystemExit."""
        _write_config(tmp_path, "cross_model_review:\n  enabled: [unclosed")

        exit_code, result = _run_main(tmp_path)  # _run_main asserts JSON validity

        assert result["status"] == "failed"
        assert exit_code is None, (
            f"main() must return 0 even on bad config; got SystemExit({exit_code})"
        )


# ---------------------------------------------------------------------------
# Config field validation
# ---------------------------------------------------------------------------

class TestConfigValidation:

    def test_harness_not_codex_yields_failed(self, tmp_path):
        """harness set to an unsupported value → status failed (unsupported harness)."""
        cfg = {**_MINIMAL_CONFIG}
        cfg["cross_model_review"] = {**cfg["cross_model_review"], "harness": "openai"}
        _write_config(tmp_path, cfg)

        exit_code, result = _run_main(tmp_path)

        assert result["status"] == "failed"
        assert exit_code is None

    def test_model_missing_yields_failed_naming_field(self, tmp_path):
        """enabled: true with model absent → status failed; cause names the field."""
        cfg = dict(_MINIMAL_CONFIG)
        block = {k: v for k, v in cfg["cross_model_review"].items() if k != "model"}
        cfg["cross_model_review"] = block
        _write_config(tmp_path, cfg)

        exit_code, result = _run_main(tmp_path)

        assert result["status"] == "failed"
        assert "model" in (result.get("cause") or ""), (
            f"cause should name the missing field 'model'; got: {result.get('cause')!r}"
        )
        assert exit_code is None

    def test_effort_missing_yields_failed_naming_field(self, tmp_path):
        """enabled: true with effort absent → status failed; cause names the field."""
        cfg = dict(_MINIMAL_CONFIG)
        block = {k: v for k, v in cfg["cross_model_review"].items() if k != "effort"}
        cfg["cross_model_review"] = block
        _write_config(tmp_path, cfg)

        exit_code, result = _run_main(tmp_path)

        assert result["status"] == "failed"
        assert "effort" in (result.get("cause") or ""), (
            f"cause should name the missing field 'effort'; got: {result.get('cause')!r}"
        )
        assert exit_code is None


# ---------------------------------------------------------------------------
# Precondition failures (codex not found, missing/empty prompt)
# ---------------------------------------------------------------------------

class TestPreconditions:

    def test_codex_not_found_yields_failed(self, tmp_path):
        """shutil.which returning None → status failed, no report written."""
        _write_config(tmp_path, _MINIMAL_CONFIG)
        _write_prompt(tmp_path)

        with mock.patch("shutil.which", return_value=None):
            exit_code, result = _run_main(tmp_path)

        assert result["status"] == "failed"
        assert result.get("report_path") is None
        assert exit_code is None

    def test_missing_prompt_file_yields_failed(self, tmp_path):
        """Prompt file does not exist → status failed."""
        _write_config(tmp_path, _MINIMAL_CONFIG)
        # deliberately do not write a prompt file

        with mock.patch("shutil.which", return_value="/usr/bin/codex"):
            exit_code, result = _run_main(tmp_path)

        assert result["status"] == "failed"
        assert exit_code is None

    def test_empty_prompt_file_yields_failed(self, tmp_path):
        """Prompt file exists but is empty/whitespace → status failed."""
        _write_config(tmp_path, _MINIMAL_CONFIG)
        _write_prompt(tmp_path, content="   \n  ")

        with mock.patch("shutil.which", return_value="/usr/bin/codex"):
            exit_code, result = _run_main(tmp_path)

        assert result["status"] == "failed"
        assert exit_code is None


# ---------------------------------------------------------------------------
# Subprocess outcome handling
# ---------------------------------------------------------------------------

class TestSubprocessOutcomes:

    def _successful_run_mock(self, output_content: str = "# Review\n\nLooks good.\n"):
        """Return a mock for subprocess.run where codex writes non-empty output."""

        def _fake_run(cmd, **kwargs):
            # Write the output file that the runner passes via --output flag (or similar).
            # The runner is expected to pass an output-file path; we find it in cmd.
            out_path = None
            for i, arg in enumerate(cmd):
                if arg in ("--output", "-o") and i + 1 < len(cmd):
                    out_path = Path(cmd[i + 1])
                    break
            if out_path is not None:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(output_content)
            completed = mock.MagicMock()
            completed.returncode = 0
            completed.stdout = output_content
            completed.stderr = ""
            return completed

        return _fake_run

    def test_nonzero_returncode_yields_failed_no_report(self, tmp_path):
        """Codex exits non-zero → status failed, no report file."""
        _write_config(tmp_path, _MINIMAL_CONFIG)
        _write_prompt(tmp_path)

        failed_proc = mock.MagicMock()
        failed_proc.returncode = 1
        failed_proc.stdout = "error output"
        failed_proc.stderr = ""

        with mock.patch("shutil.which", return_value="/usr/bin/codex"):
            with mock.patch("subprocess.run", return_value=failed_proc):
                exit_code, result = _run_main(tmp_path)

        assert result["status"] == "failed"
        assert result.get("report_path") is None
        assert exit_code is None

    def test_empty_output_file_yields_failed_no_report(self, tmp_path):
        """Codex exits 0 but output file is whitespace-only → status failed, no report."""
        _write_config(tmp_path, _MINIMAL_CONFIG)
        _write_prompt(tmp_path)

        with mock.patch("shutil.which", return_value="/usr/bin/codex"):
            with mock.patch("subprocess.run", side_effect=self._successful_run_mock(output_content="   \n")):
                exit_code, result = _run_main(tmp_path)

        assert result["status"] == "failed"
        assert result.get("report_path") is None
        assert exit_code is None

    def test_timeout_expired_yields_failed(self, tmp_path):
        """subprocess.TimeoutExpired → status failed; cause names the timeout."""
        _write_config(tmp_path, _MINIMAL_CONFIG)
        _write_prompt(tmp_path)

        with mock.patch("shutil.which", return_value="/usr/bin/codex"):
            with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("codex", 300)):
                exit_code, result = _run_main(tmp_path)

        assert result["status"] == "failed"
        cause = result.get("cause") or ""
        assert "timeout" in cause.lower(), (
            f"cause should mention timeout; got: {cause!r}"
        )
        assert result.get("report_path") is None
        assert exit_code is None


# ---------------------------------------------------------------------------
# Auth-marker scan (failure path only)
# ---------------------------------------------------------------------------

class TestAuthMarkerScan:

    @pytest.mark.parametrize("marker", ["401", "unauthorized", "not logged in", "login"])
    def test_auth_marker_in_stdout_yields_failed_with_login_hint(self, tmp_path, marker):
        """Auth marker in failed run's stdout → status failed; cause mentions codex login."""
        _write_config(tmp_path, _MINIMAL_CONFIG)
        _write_prompt(tmp_path)

        failed_proc = mock.MagicMock()
        failed_proc.returncode = 1
        failed_proc.stdout = f"Error: {marker} — please authenticate"
        failed_proc.stderr = ""

        with mock.patch("shutil.which", return_value="/usr/bin/codex"):
            with mock.patch("subprocess.run", return_value=failed_proc):
                exit_code, result = _run_main(tmp_path)

        assert result["status"] == "failed"
        cause = result.get("cause") or ""
        assert "codex login" in cause.lower(), (
            f"cause should reference 'codex login' for auth marker {marker!r}; got: {cause!r}"
        )

    @pytest.mark.parametrize("marker", ["401", "unauthorized", "not logged in", "login"])
    def test_auth_marker_in_stderr_yields_failed_with_login_hint(self, tmp_path, marker):
        """Auth marker in failed run's stderr → status failed; cause mentions codex login."""
        _write_config(tmp_path, _MINIMAL_CONFIG)
        _write_prompt(tmp_path)

        failed_proc = mock.MagicMock()
        failed_proc.returncode = 1
        failed_proc.stdout = ""
        failed_proc.stderr = f"{marker}: authentication required"

        with mock.patch("shutil.which", return_value="/usr/bin/codex"):
            with mock.patch("subprocess.run", return_value=failed_proc):
                exit_code, result = _run_main(tmp_path)

        assert result["status"] == "failed"
        cause = result.get("cause") or ""
        assert "codex login" in cause.lower(), (
            f"cause should reference 'codex login' for stderr marker {marker!r}; got: {cause!r}"
        )

    def test_auth_marker_in_successful_run_is_ignored(self, tmp_path):
        """Auth marker in successful run's output → status success (scan is failure-path-only)."""
        _write_config(tmp_path, _MINIMAL_CONFIG)
        _write_prompt(tmp_path)

        def _fake_run(cmd, **kwargs):
            out_path = None
            for i, arg in enumerate(cmd):
                if arg in ("--output", "-o") and i + 1 < len(cmd):
                    out_path = Path(cmd[i + 1])
                    break
            if out_path is not None:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text("# Review\n\nlogin required context here.\n\nFindings: none.\n")
            completed = mock.MagicMock()
            completed.returncode = 0
            completed.stdout = "# Review\n\nlogin required context here.\n"
            completed.stderr = ""
            return completed

        fake_ts = mock.MagicMock(return_value="2026-01-01-120000")

        with mock.patch("shutil.which", return_value="/usr/bin/codex"):
            with mock.patch("subprocess.run", side_effect=_fake_run):
                with mock.patch("os.replace"):
                    with mock.patch.object(
                        _cross_review_mod, "_timestamp", fake_ts
                    ) if hasattr(_cross_review_mod, "_timestamp") else mock.patch(
                        "fbk.cross_review._timestamp", fake_ts, create=True
                    ):
                        exit_code, result = _run_main(tmp_path)

        assert result["status"] == "success", (
            "A successful run containing 'login' in its output must still be status success; "
            "auth-marker scan must only run on failure path"
        )


# ---------------------------------------------------------------------------
# Success path — report written
# ---------------------------------------------------------------------------

class TestSuccessPath:

    def _fake_run_writing(self, output_text: str):
        """Return a side_effect function that writes output_text to the --output path."""

        def _inner(cmd, **kwargs):
            out_path = None
            for i, arg in enumerate(cmd):
                if arg in ("--output", "-o") and i + 1 < len(cmd):
                    out_path = Path(cmd[i + 1])
                    break
            if out_path is not None:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(output_text)
            result = mock.MagicMock()
            result.returncode = 0
            result.stdout = output_text
            result.stderr = ""
            return result

        return _inner

    def test_success_uses_cross_review_model_not_default(self, tmp_path):
        """Distinctive cross_model_review.model (gpt-5.5) appears in filename and header; body = Codex output."""
        _write_config(tmp_path, _MINIMAL_CONFIG)  # model is gpt-5.5
        _write_prompt(tmp_path)

        codex_body = "# Cross-Model Review\n\nAll good.\n"
        fake_ts = "20260101-120000"

        with mock.patch("shutil.which", return_value="/usr/bin/codex"):
            with mock.patch("subprocess.run", side_effect=self._fake_run_writing(codex_body)):
                with mock.patch("os.replace", side_effect=lambda src, dst: Path(src).rename(dst)):
                    with mock.patch(
                        "fbk.cross_review._timestamp", return_value=fake_ts, create=True
                    ):
                        exit_code, result = _run_main(tmp_path)

        assert result["status"] == "success"
        report_path = result.get("report_path")
        assert report_path is not None, "report_path must be set on success"

        report_file = Path(report_path)
        assert report_file.exists(), f"Report file must exist at {report_path}"

        filename = report_file.name
        assert "gpt-5.5" in filename or "gpt-5-5" in filename, (
            f"Model name must appear in filename; got: {filename}"
        )
        content = report_file.read_text()
        assert "gpt-5.5" in content or "gpt-5-5" in content, (
            "Model name must appear in the report header"
        )
        assert codex_body.strip() in content, "Report body must contain the Codex output"
        assert exit_code is None

    def test_report_dir_absent_is_created(self, tmp_path):
        """Runner creates the report dir if it does not exist → status success."""
        cfg = {**_MINIMAL_CONFIG}
        cfg["cross_model_review"] = {
            **cfg["cross_model_review"],
            "report_dir": "ai-docs/cross-model-review/reports/new-subdir",
        }
        _write_config(tmp_path, cfg)
        _write_prompt(tmp_path)

        report_dir = tmp_path / "ai-docs" / "cross-model-review" / "reports" / "new-subdir"
        assert not report_dir.exists(), "precondition: dir must not exist"

        with mock.patch("shutil.which", return_value="/usr/bin/codex"):
            with mock.patch("subprocess.run", side_effect=self._fake_run_writing("# Review\n\nOK\n")):
                with mock.patch("os.replace", side_effect=lambda src, dst: Path(src).rename(dst)):
                    with mock.patch("fbk.cross_review._timestamp", return_value="20260101-120000", create=True):
                        exit_code, result = _run_main(tmp_path)

        assert result["status"] == "success"
        assert report_dir.exists(), "Runner must create the report dir"

    def test_path_unsafe_model_and_review_type_sanitized_in_filename(self, tmp_path):
        """model or review-type with / or spaces → filename contains no / or spaces."""
        cfg = {**_MINIMAL_CONFIG}
        cfg["cross_model_review"] = {
            **cfg["cross_model_review"],
            "model": "gpt/5.5 turbo",
            "review_type": "cross review",
        }
        _write_config(tmp_path, cfg)
        _write_prompt(tmp_path)

        with mock.patch("shutil.which", return_value="/usr/bin/codex"):
            with mock.patch("subprocess.run", side_effect=self._fake_run_writing("# Review\n\nOK\n")):
                with mock.patch("os.replace", side_effect=lambda src, dst: Path(src).rename(dst)):
                    with mock.patch("fbk.cross_review._timestamp", return_value="20260101-120001", create=True):
                        exit_code, result = _run_main(tmp_path)

        assert result["status"] == "success"
        report_path = result.get("report_path")
        assert report_path is not None
        filename = Path(report_path).name
        assert "/" not in filename, f"Filename must not contain '/': {filename}"
        assert " " not in filename, f"Filename must not contain spaces: {filename}"

    def test_write_failure_yields_failed_no_leftover_files(self, tmp_path):
        """os.replace raising → status failed, returns 0, no report file and no temp file left behind."""
        _write_config(tmp_path, _MINIMAL_CONFIG)
        _write_prompt(tmp_path)

        report_dir = tmp_path / "ai-docs" / "cross-model-review" / "reports"

        with mock.patch("shutil.which", return_value="/usr/bin/codex"):
            with mock.patch("subprocess.run", side_effect=self._fake_run_writing("# Review\n\nOK\n")):
                with mock.patch("os.replace", side_effect=OSError("disk full")):
                    with mock.patch("fbk.cross_review._timestamp", return_value="20260101-120002", create=True):
                        exit_code, result = _run_main(tmp_path)

        assert result["status"] == "failed"
        assert exit_code is None, "main() must return 0 even on write failure"

        if report_dir.exists():
            leftover_reports = list(report_dir.glob("fbk-cross-review-*.md"))
            assert leftover_reports == [], (
                f"No report files should remain after write failure; found: {leftover_reports}"
            )
            leftover_temps = list(report_dir.glob("*.tmp"))
            assert leftover_temps == [], (
                f"No temp files should remain after write failure; found: {leftover_temps}"
            )


# ---------------------------------------------------------------------------
# Subprocess construction
# ---------------------------------------------------------------------------

class TestSubprocessConstruction:

    def test_subprocess_called_as_list_no_shell(self, tmp_path):
        """Codex is invoked as a list (not a string), without shell=True, with model and effort as discrete args."""
        _write_config(tmp_path, _MINIMAL_CONFIG)
        _write_prompt(tmp_path)

        call_record: list = []

        def _capturing_run(cmd, **kwargs):
            call_record.append({"cmd": cmd, "kwargs": kwargs})
            # Write a minimal output file so the runner reaches the success path.
            out_path = None
            for i, arg in enumerate(cmd if isinstance(cmd, list) else []):
                if arg in ("--output", "-o") and i + 1 < len(cmd):
                    out_path = Path(cmd[i + 1])
                    break
            if out_path is not None:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text("# Review\n\nOK\n")
            result = mock.MagicMock()
            result.returncode = 0
            result.stdout = "# Review\n\nOK\n"
            result.stderr = ""
            return result

        with mock.patch("shutil.which", return_value="/usr/bin/codex"):
            with mock.patch("subprocess.run", side_effect=_capturing_run):
                with mock.patch("os.replace", side_effect=lambda src, dst: Path(src).rename(dst)):
                    with mock.patch("fbk.cross_review._timestamp", return_value="20260101-120003", create=True):
                        _run_main(tmp_path)

        assert call_record, "subprocess.run must have been called"
        call = call_record[0]
        cmd = call["cmd"]

        assert isinstance(cmd, list), (
            f"Codex must be invoked with a list, not a string; got: {type(cmd).__name__}"
        )
        assert call["kwargs"].get("shell") is not True, (
            "subprocess.run must not be called with shell=True"
        )

        cmd_str = " ".join(str(a) for a in cmd)
        assert "gpt-5.5" in cmd_str, (
            f"model 'gpt-5.5' must appear as a discrete arg; cmd: {cmd}"
        )
        assert "high" in cmd_str, (
            f"effort 'high' must appear as a discrete arg; cmd: {cmd}"
        )


# ---------------------------------------------------------------------------
# Filename collision — second file gets -2 suffix
# ---------------------------------------------------------------------------

class TestFilenameCollision:

    def test_collision_appends_suffix(self, tmp_path):
        """Two successful reviews with same timestamp → both files exist; second has -2 suffix."""
        _write_config(tmp_path, _MINIMAL_CONFIG)
        _write_prompt(tmp_path)

        call_count = [0]

        def _fake_run(cmd, **kwargs):
            call_count[0] += 1
            out_path = None
            for i, arg in enumerate(cmd if isinstance(cmd, list) else []):
                if arg in ("--output", "-o") and i + 1 < len(cmd):
                    out_path = Path(cmd[i + 1])
                    break
            if out_path is not None:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(f"# Review {call_count[0]}\n\nOK\n")
            result = mock.MagicMock()
            result.returncode = 0
            result.stdout = f"# Review {call_count[0]}\n\nOK\n"
            result.stderr = ""
            return result

        fixed_ts = "20260101-120004"

        with mock.patch("shutil.which", return_value="/usr/bin/codex"):
            with mock.patch("subprocess.run", side_effect=_fake_run):
                with mock.patch("os.replace", side_effect=lambda src, dst: Path(src).rename(dst)):
                    with mock.patch("fbk.cross_review._timestamp", return_value=fixed_ts, create=True):
                        exit_code1, result1 = _run_main(tmp_path)

                    with mock.patch("fbk.cross_review._timestamp", return_value=fixed_ts, create=True):
                        exit_code2, result2 = _run_main(tmp_path)

        assert result1["status"] == "success"
        assert result2["status"] == "success"

        path1 = Path(result1["report_path"])
        path2 = Path(result2["report_path"])

        assert path1.exists(), f"First report must exist: {path1}"
        assert path2.exists(), f"Second report must exist: {path2}"
        assert path1 != path2, "Collision must produce distinct filenames"
        assert "-2" in path2.name, (
            f"Second report filename must contain '-2' suffix; got: {path2.name}"
        )


# ---------------------------------------------------------------------------
# --check-opt-in mode
# ---------------------------------------------------------------------------

class TestCheckOptInMode:

    def test_check_opt_in_opted_in_no_subprocess(self, tmp_path):
        """--check-opt-in with enabled config → status success, subprocess.run never called."""
        _write_config(tmp_path, _MINIMAL_CONFIG)

        with mock.patch("subprocess.run") as mock_run:
            exit_code, result = _run_main(tmp_path, extra_argv=["--check-opt-in"])

        assert result["status"] == "success"
        assert result.get("report_path") is None
        assert result.get("cause") is None
        mock_run.assert_not_called()
        assert exit_code is None

    def test_check_opt_in_opted_out_no_subprocess(self, tmp_path):
        """--check-opt-in with disabled config → status skipped, subprocess.run never called."""
        cfg = {**_MINIMAL_CONFIG}
        cfg["cross_model_review"] = {**cfg["cross_model_review"], "enabled": False}
        _write_config(tmp_path, cfg)

        with mock.patch("subprocess.run") as mock_run:
            exit_code, result = _run_main(tmp_path, extra_argv=["--check-opt-in"])

        assert result["status"] == "skipped"
        mock_run.assert_not_called()
        assert exit_code is None


# ---------------------------------------------------------------------------
# End-to-end through fbk.py dispatcher
# ---------------------------------------------------------------------------

class TestEndToEnd:

    def test_dispatcher_cross_review_check_opt_in_exits_0_valid_json(self, tmp_path):
        """fbk.py cross-review --check-opt-in --project-root <opted-out> exits 0 with JSON status key.

        Uses an opted-out config so the subprocess (Codex) is never spawned.
        Proves the JSON output survives the dispatcher's stdout interposition.
        """
        cfg = {**_MINIMAL_CONFIG}
        cfg["cross_model_review"] = {**cfg["cross_model_review"], "enabled": False}
        _write_config(tmp_path, cfg)

        if not _FBK_PY.exists():
            pytest.skip(f"fbk.py not found at {_FBK_PY}")

        result = subprocess.run(
            [
                sys.executable,
                str(_FBK_PY),
                "cross-review",
                "--check-opt-in",
                "--project-root",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, (
            f"fbk.py cross-review exited {result.returncode}; stderr: {result.stderr}"
        )

        parsed = json.loads(result.stdout)
        assert "status" in parsed, (
            f"Output JSON must contain a 'status' key; got: {result.stdout!r}"
        )
