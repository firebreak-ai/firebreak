"""Tests for fbk.capture.gate_check — Firebreak-marker sentinel, out-of-tree full
corroboration, and realpath confinement."""

import os
import pytest

try:
    from fbk.capture import gate_check
except ImportError:
    gate_check = None

from tests import capture_fixtures


pytestmark = pytest.mark.skipif(
    gate_check is None,
    reason="fbk.capture.gate_check not yet implemented",
)


# ---------------------------------------------------------------------------
# Firebreak-specific marker hardening
# ---------------------------------------------------------------------------


def test_bare_automation_dir_is_not_instrumented(tmp_path):
    """A project with .claude/automation/ but no .fbk-managed sentinel is not instrumented."""
    root = capture_fixtures.make_project(tmp_path, instrumented=True, marked=False)

    assert gate_check.project_is_instrumented(root) is False


def test_sentinel_makes_project_instrumented(tmp_path):
    """Adding the .fbk-managed sentinel to .claude/automation/ marks the project as instrumented."""
    root = capture_fixtures.make_project(tmp_path, instrumented=True, marked=True)

    assert gate_check.project_is_instrumented(root) is True


# ---------------------------------------------------------------------------
# Out-of-tree full corroboration
# ---------------------------------------------------------------------------


def test_in_tree_full_clamped_to_standard_without_corroboration(tmp_path, monkeypatch):
    """capture.cfg requesting full with no env var and no global-dir marker is clamped to standard."""
    root = capture_fixtures.make_project(
        tmp_path, instrumented=True, marked=True, capture_cfg="full"
    )
    # Remove any ambient corroboration signals.
    monkeypatch.delenv("FBK_CAPTURE_LEVEL", raising=False)
    # Point CLAUDE_CONFIG_DIR at an empty directory so no global marker exists.
    empty_global = tmp_path / "empty-global"
    empty_global.mkdir()
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(empty_global))

    assert gate_check.resolve_capture_level(root) == "standard"


def test_full_honored_with_env_corroboration(tmp_path, monkeypatch):
    """capture.cfg requesting full is honored when FBK_CAPTURE_LEVEL=full is set."""
    root = capture_fixtures.make_project(
        tmp_path, instrumented=True, marked=True, capture_cfg="full"
    )
    monkeypatch.setenv("FBK_CAPTURE_LEVEL", "full")
    # Ensure no global-dir corroboration is present (env var alone should suffice).
    empty_global = tmp_path / "empty-global"
    empty_global.mkdir()
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(empty_global))

    assert gate_check.resolve_capture_level(root) == "full"


def test_full_honored_with_global_marker_corroboration(tmp_path, monkeypatch):
    """capture.cfg requesting full is honored when the operator global-dir marker is present.

    Marker shape: a file at <CLAUDE_CONFIG_DIR>/fbk-capture-level/<hash-or-slug>.cfg
    whose first line is the resolved project root path and whose second line (or key)
    is "capture_level=full".

    The gate reads <CLAUDE_CONFIG_DIR>/fbk-capture-level/ for a file whose content
    begins with the realpath of the project root.  The test writes that exact file so
    the implementation agent matches this shape precisely.
    """
    root = capture_fixtures.make_project(
        tmp_path, instrumented=True, marked=True, capture_cfg="full"
    )
    # Build a fixture global-dir that holds the operator marker.
    global_dir = tmp_path / "global-claude"
    marker_dir = global_dir / "fbk-capture-level"
    marker_dir.mkdir(parents=True)
    # File is named after a slug of the project path; content carries the real path
    # and the authorised level so the gate can verify path-binding.
    resolved_root = os.path.realpath(root)
    marker_file = marker_dir / "project.cfg"
    marker_file.write_text(f"{resolved_root}\ncapture_level=full\n")

    monkeypatch.delenv("FBK_CAPTURE_LEVEL", raising=False)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(global_dir))

    assert gate_check.resolve_capture_level(root) == "full"


# ---------------------------------------------------------------------------
# Realpath confinement — symlink refusal
# ---------------------------------------------------------------------------


def test_symlinked_capture_dir_treated_uninstrumented(tmp_path, monkeypatch):
    """A .fbk-capture/ directory that is a symlink pointing outside the project tree is refused."""
    # Ensure no ambient corroboration so resolve_capture_level can't escalate via env.
    monkeypatch.delenv("FBK_CAPTURE_LEVEL", raising=False)
    empty_global = tmp_path / "empty-global"
    empty_global.mkdir()
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(empty_global))

    # Build a plain project root (sentinel present so it would otherwise be instrumented).
    root = capture_fixtures.make_project(tmp_path, instrumented=True, marked=True)

    # Create a real capture directory outside the project tree.
    external_capture = tmp_path / "external-capture"
    external_capture.mkdir()
    cfg_path = external_capture / "capture.cfg"
    cfg_path.write_text("capture_level=standard\n")

    # Replace .fbk-capture with a symlink to the external directory.
    fbk_capture_link = os.path.join(root, ".fbk-capture")
    try:
        os.symlink(str(external_capture), fbk_capture_link)
    except (OSError, NotImplementedError):
        pytest.skip("Platform does not support symlinks")

    assert gate_check.project_is_instrumented(root) is False
    assert gate_check.resolve_capture_level(root) == "off"


def test_symlinked_config_refused(tmp_path, monkeypatch):
    """A capture.cfg that is a symlink pointing outside the project tree is refused."""
    # Ensure no ambient corroboration.
    monkeypatch.delenv("FBK_CAPTURE_LEVEL", raising=False)
    empty_global = tmp_path / "empty-global"
    empty_global.mkdir()
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(empty_global))

    # Build a plain project root with sentinel so it is otherwise instrumented.
    root = capture_fixtures.make_project(tmp_path, instrumented=True, marked=True)

    # Create a real .fbk-capture/ under the project root.
    capture_dir = os.path.join(root, ".fbk-capture")
    os.makedirs(capture_dir, exist_ok=True)

    # Write the real config outside the tree and symlink capture.cfg to it.
    external_cfg = tmp_path / "external-capture.cfg"
    external_cfg.write_text("capture_level=standard\n")
    cfg_link = os.path.join(capture_dir, "capture.cfg")
    try:
        os.symlink(str(external_cfg), cfg_link)
    except (OSError, NotImplementedError):
        pytest.skip("Platform does not support symlinks")

    assert gate_check.resolve_capture_level(root) == "off"
