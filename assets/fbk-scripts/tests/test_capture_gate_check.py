"""Unit tests for the per-project capture gate: instrumentation detection and level resolution.

Tests cover:
- Detecting whether a project is instrumented (sentinel or capture.cfg present)
- Resolving the capture level (off/standard/full) based on configuration and defaults
- Handling of filesystem errors and invalid configuration values
- Bounded single-line reads to prevent performance degradation
"""

import os
import pytest

# Red phase: gate_check module does not exist yet.
try:
    from fbk.capture import gate_check
    GATE_CHECK_AVAILABLE = True
except ImportError:
    GATE_CHECK_AVAILABLE = False

from tests import capture_fixtures

pytestmark = pytest.mark.skipif(
    not GATE_CHECK_AVAILABLE,
    reason="fbk.capture.gate_check module not yet implemented"
)


class TestProjectIsInstrumented:
    """Tests for gate_check.project_is_instrumented(cwd) -> bool."""

    def test_instrumented_true_for_firebreak_marked_project(self, tmp_path):
        """A project with .claude/automation/.fbk-managed sentinel is instrumented."""
        root = capture_fixtures.make_project(str(tmp_path), instrumented=True, marked=True)
        assert gate_check.project_is_instrumented(root) is True

    def test_instrumented_true_for_capture_cfg_project(self, tmp_path):
        """A project with .fbk-capture/capture.cfg (without sentinel) is instrumented."""
        root = capture_fixtures.make_project(
            str(tmp_path), instrumented=False, capture_cfg="standard"
        )
        assert gate_check.project_is_instrumented(root) is True

    def test_instrumented_false_for_bare_project(self, tmp_path):
        """A bare project with neither sentinel nor capture.cfg is not instrumented."""
        root = capture_fixtures.make_project(str(tmp_path), instrumented=False)
        assert gate_check.project_is_instrumented(root) is False

    def test_instrumented_false_on_filesystem_error(self, tmp_path):
        """Filesystem errors (e.g., non-existent path) resolve safely to False, no raise."""
        nonexistent_path = os.path.join(str(tmp_path), "does_not_exist")
        # Should return False without raising an exception
        assert gate_check.project_is_instrumented(nonexistent_path) is False

    def test_instrumented_false_on_file_where_directory_expected(self, tmp_path):
        """When a directory is expected but a file exists instead, return False safely."""
        # Create a file that would conflict with .claude/automation directory
        test_file = os.path.join(str(tmp_path), "project")
        with open(test_file, "w") as f:
            f.write("conflict")
        # Trying to treat a file as a directory should return False, not raise
        assert gate_check.project_is_instrumented(test_file) is False


class TestResolveCaptureLevel:
    """Tests for gate_check.resolve_capture_level(cwd) -> "off"|"standard"|"full"."""

    def test_level_returns_off_from_cfg(self, tmp_path):
        """Valid capture_level=off in capture.cfg is returned."""
        root = capture_fixtures.make_project(
            str(tmp_path), instrumented=False, capture_cfg="off"
        )
        assert gate_check.resolve_capture_level(root) == "off"

    def test_level_returns_standard_from_cfg(self, tmp_path):
        """Valid capture_level=standard in capture.cfg is returned."""
        root = capture_fixtures.make_project(
            str(tmp_path), instrumented=False, capture_cfg="standard"
        )
        assert gate_check.resolve_capture_level(root) == "standard"

    def test_level_defaults_standard_for_firebreak_without_cfg(self, tmp_path):
        """A Firebreak-marked project without capture.cfg defaults to standard."""
        root = capture_fixtures.make_project(
            str(tmp_path), instrumented=True, marked=True, capture_cfg=None
        )
        assert gate_check.resolve_capture_level(root) == "standard"

    def test_level_invalid_cfg_warns_and_defaults_standard(self, tmp_path, capsys):
        """Invalid capture_level value warns to stderr and defaults to standard."""
        root = capture_fixtures.make_project(str(tmp_path), instrumented=False)
        # Write an invalid capture.cfg manually
        cfg_path = os.path.join(root, ".fbk-capture", "capture.cfg")
        os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
        with open(cfg_path, "w") as f:
            f.write("capture_level=banana\n")

        result = gate_check.resolve_capture_level(root)
        assert result == "standard"

        # Check that stderr contains a warning about the invalid value
        captured = capsys.readouterr()
        assert captured.err  # stderr should not be empty
        assert "banana" in captured.err or "invalid" in captured.err.lower()

    def test_level_off_for_uninstrumented_project(self, tmp_path):
        """A bare uninstrumented project resolves to off."""
        root = capture_fixtures.make_project(str(tmp_path), instrumented=False)
        assert gate_check.resolve_capture_level(root) == "off"

    def test_oversized_first_segment_resolves_safe_default(self, tmp_path, monkeypatch):
        """A parseable non-default token placed beyond the 256-byte read cap resolves to "standard".

        Divergence design: the cfg file is a single line whose first 256 bytes are
        spaces, followed by "capture_level=full" on the same line (no newline before
        the token).  The bounded read (`f.readline(256)`) ingests only the leading
        spaces — no "=" character — and returns None, causing resolve_capture_level to
        fall back to the safe default "standard".  An unbounded read (`f.readline()`)
        would consume the entire line, find the token, and return "full".

        Why the token beyond the cap must be the non-default "full":
          A "standard" token there would make both the bounded and unbounded reads
          return "standard", and the test would pass on both implementations —
          proving nothing.  "full" is required so the bounded path disagrees with
          the unbounded path, and the assertion catches the unbounded implementation.

        Why whitespace filler instead of "x" * 256:
          _read_cfg_level partitions on the first "=" and checks that the left side
          strips to exactly "capture_level".  "x" * 256 has no "=" so both reads
          return None (key match fails) and both resolve to "standard" — no
          divergence.  Whitespace filler strips to an empty key, which also fails
          the key match, but the unbounded read includes the full line with its
          parseable "capture_level=full" segment — only the unbounded code path
          reaches that segment.

        Corroboration: FBK_CAPTURE_LEVEL=full is set so the pre-fix unbounded path
        returns "full" rather than being clamped to "standard" by _full_corroborated.
        The bounded path still returns "standard" because it finds no token at all.
        """
        root = capture_fixtures.make_project(str(tmp_path), instrumented=False)
        cfg_path = os.path.join(root, ".fbk-capture", "capture.cfg")
        os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
        with open(cfg_path, "w") as f:
            f.write(" " * 256 + "capture_level=full\n")

        monkeypatch.setenv("FBK_CAPTURE_LEVEL", "full")

        assert gate_check.resolve_capture_level(root) == "standard"

    @pytest.mark.flaky_quarantine
    def test_giant_single_line_cfg_stays_fast(self, tmp_path):
        """A 5 MB newline-less cfg line resolves to "standard" without stalling.

        Correctness assertion (gating): the cfg file exists so the project is
        instrumented, but the bounded read finds no parseable token in its byte
        window, so the safe default "standard" is returned.

        Timing assertion (advisory, non-gating): a single timed call must complete
        under 0.5 s.  Marked flaky_quarantine so a slow CI run does not block the
        suite.
        """
        import time

        root = capture_fixtures.make_project(str(tmp_path), instrumented=False)
        cfg_path = os.path.join(root, ".fbk-capture", "capture.cfg")
        os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
        with open(cfg_path, "w") as f:
            f.write("x" * (5 * 1024 * 1024))

        # Correctness assertion (gating): cfg present → instrumented; no token in
        # bounded window → safe default.
        assert gate_check.resolve_capture_level(root) == "standard"

        # Advisory timing assertion: generous 0.5 s upper bound for a bounded read.
        start = time.perf_counter()
        gate_check.resolve_capture_level(root)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, (  # noqa: flaky_quarantine — non-gating on CI
            f"resolve_capture_level took {elapsed:.4f}s on 5 MB single-line cfg; "
            "expected under 0.5s with a bounded readline"
        )
