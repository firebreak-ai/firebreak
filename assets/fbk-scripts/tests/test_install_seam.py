"""E2E and integration seam guards for the installer.

Two tests verify that the install.sh script correctly arms the capture pipeline
with no manual step required:

1. test_install_arms_capture_with_no_manual_step — a fresh install creates the
   .fbk-managed sentinel, and a router event written immediately after confirms
   the gate is open and capture is recording at standard level.

2. test_settings_json_written_by_same_dir_rename — install over a pre-existing
   settings.json produces a new inode (rename, not cp), preserves unrelated
   operator hooks and env keys, creates a byte-equal backup, and leaves no temp
   file residue beside the target.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module-level paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parents[3]
INSTALL_SH = _REPO_ROOT / "installer" / "install.sh"
TEMPLATE_SETTINGS = _REPO_ROOT / "assets" / "settings.json"
ROUTER = Path(__file__).parent.parent / "fbk" / "capture" / "hook_router.py"

# ---------------------------------------------------------------------------
# Module-level skip guard — bail out immediately when prerequisites are absent.
# ---------------------------------------------------------------------------

if shutil.which("bash") is None or not INSTALL_SH.exists():
    pytest.skip(
        "bash not on PATH or install.sh not found — install-seam tests skipped",
        allow_module_level=True,
    )

# ---------------------------------------------------------------------------
# gate_check import — skip with a clear message when capture subsystem is absent.
# ---------------------------------------------------------------------------

try:
    from fbk.capture import gate_check
    _GATE_CHECK_AVAILABLE = True
except ImportError:
    _GATE_CHECK_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _GATE_CHECK_AVAILABLE,
    reason="fbk.capture.gate_check not yet implemented",
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _fake_uv_bin(tmp_path):
    """Create a no-op uv shim on PATH; return the bin directory as a str.

    uv is third-party code we don't own — a shim on PATH is the correct
    stand-in here so the installer's check_uv passes without a real uv install.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    uv_path = bin_dir / "uv"
    uv_path.write_text("#!/bin/sh\nexit 0\n")
    uv_path.chmod(0o755)
    return str(bin_dir)


def _minimal_source(tmp_path):
    """Create a source tree with only settings.json; return the source dir as a str.

    enumerate_assets skips settings.json, so this causes zero files to be
    installed — setup_python_venv warns and returns 0 — while merge_settings
    still runs the full production merge path.
    """
    source_dir = tmp_path / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(str(TEMPLATE_SETTINGS), str(source_dir / "settings.json"))
    return str(source_dir)


def _run_install(target_dir, source_dir, fake_bin):
    """Run install.sh with --target and --source; inject the fake uv shim on PATH.

    Returns a CompletedProcess with text stdout/stderr.
    """
    return subprocess.run(
        ["bash", str(INSTALL_SH), "--target", target_dir, "--source", source_dir],
        env={**os.environ, "PATH": fake_bin + os.pathsep + os.environ["PATH"]},
        capture_output=True,
        text=True,
        timeout=120,
    )


# ---------------------------------------------------------------------------
# Test 1 — fresh install arms capture with no manual step
# ---------------------------------------------------------------------------


def test_install_arms_capture_with_no_manual_step(tmp_path):
    """A fresh install creates the sentinel; the router records a standard-level event.

    Covers AC-11 (installer creates sentinel) and AC-16 (e2e test: install then
    router event confirms capture is armed).

    The seam under test is sentinel → gate_check → event_writer.  Running the
    router binary as a subprocess is the same production path as
    test_capture_e2e_seam.py — not a stand-in for owned code.
    """
    project = tmp_path / "proj"
    target = project / ".claude"
    project.mkdir()

    fake_bin = _fake_uv_bin(tmp_path / "uv-bin")
    source_dir = _minimal_source(tmp_path / "src")

    result = _run_install(str(target), source_dir, fake_bin)
    assert result.returncode == 0, (
        f"install.sh failed (rc={result.returncode})\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )

    # The sentinel must exist at the shared-token path — built from
    # gate_check.FBK_MARKER_SENTINEL, not a re-typed literal.
    sentinel_path = os.path.join(
        str(target), "automation", gate_check.FBK_MARKER_SENTINEL
    )
    assert os.path.exists(sentinel_path), (
        f"installer did not create sentinel at {sentinel_path!r}; "
        f"install stderr: {result.stderr}"
    )

    # Gate functions must agree: project is instrumented at standard level.
    assert gate_check.project_is_instrumented(str(project)) is True, (
        f"project_is_instrumented returned False after install; "
        f"sentinel path exists: {os.path.exists(sentinel_path)}"
    )
    assert gate_check.resolve_capture_level(str(project)) == "standard", (
        f"expected capture level 'standard', got "
        f"{gate_check.resolve_capture_level(str(project))!r}"
    )

    # No capture.cfg should have been written — standard level requires no manual cfg.
    assert not os.path.exists(project / ".fbk-capture" / "capture.cfg"), (
        "capture.cfg was created by the installer; standard level needs no hand-written cfg"
    )

    # Run the router as a subprocess from the installed project — same production
    # path as test_capture_e2e_seam.py.
    from tests import capture_fixtures  # noqa: PLC0415 — after module-level guard

    payload = capture_fixtures.hook_payload("PostToolUse", tool_name="Bash")
    router_result = subprocess.run(
        [sys.executable, str(ROUTER)],
        input=payload,
        cwd=str(project),
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert router_result.returncode == 0, (
        f"router exited {router_result.returncode}; stderr: {router_result.stderr!r}"
    )
    assert router_result.stdout == "", (
        f"expected no stdout from router, got: {router_result.stdout!r}"
    )

    # Exactly one event must appear in events.jsonl with the declared field values.
    events_path = project / ".fbk-capture" / "events.jsonl"
    assert events_path.exists(), (
        f"expected events.jsonl at {events_path!r} after router run; "
        f"capture dir contents: {list((project / '.fbk-capture').iterdir()) if (project / '.fbk-capture').exists() else 'absent'}"
    )

    with open(events_path) as f:
        lines = [line for line in f if line.strip()]
    assert len(lines) == 1, (
        f"expected exactly 1 event in events.jsonl, got {len(lines)}; lines={lines!r}"
    )

    event = json.loads(lines[0])

    assert event.get("event_type") == "TOOL_USE", (
        f"expected event_type 'TOOL_USE', got {event.get('event_type')!r}"
    )
    assert event.get("source") == "hook_router", (
        f"expected source 'hook_router', got {event.get('source')!r}"
    )
    assert event.get("capture_level") == "standard", (
        f"expected capture_level 'standard', got {event.get('capture_level')!r}"
    )
    # No SDL run is active: spec and stage must be null (present but null, not absent).
    assert "spec" in event and event["spec"] is None, (
        f"expected spec=null (key present, value None), got event[spec]={event.get('spec')!r}"
    )
    assert "stage" in event and event["stage"] is None, (
        f"expected stage=null (key present, value None), got event[stage]={event.get('stage')!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — settings.json written via same-directory rename
# ---------------------------------------------------------------------------


def test_settings_json_written_by_same_dir_rename(tmp_path):
    """Install over existing settings.json uses a same-dir rename, not a cp.

    Covers AC-20: an interrupted install cannot leave settings.json truncated
    because the write is a rename-into-place from a temp file in the same
    directory (atomic on POSIX when src and dst are on the same filesystem).

    The correctness divergence is inode change: a rename creates a new inode;
    the pre-fix cp truncates and rewrites the same inode.  This is a structural
    check, not a timing test.
    """
    project = tmp_path / "proj"
    target = project / ".claude"
    project.mkdir()
    target.mkdir(parents=True)

    # Pre-populate settings.json with content the installer must preserve.
    pre_existing = {
        "hooks": {
            "PreToolUse": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 /usr/local/bin/my-custom-hook.py",
                        }
                    ]
                }
            ]
        },
        "env": {"KEEP": "1"},
    }
    settings_path = target / "settings.json"
    settings_path.write_text(json.dumps(pre_existing, indent=2))
    original_bytes = settings_path.read_bytes()
    original_inode = os.stat(settings_path).st_ino

    fake_bin = _fake_uv_bin(tmp_path / "uv-bin")
    source_dir = _minimal_source(tmp_path / "src")

    result = _run_install(str(target), source_dir, fake_bin)
    assert result.returncode == 0, (
        f"install.sh failed (rc={result.returncode})\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )

    # Parse the resulting settings.json and verify content preservation.
    merged = json.loads(settings_path.read_text())

    # The unrelated operator hook command must survive the merge unchanged.
    all_commands = [
        hook["command"]
        for entries in merged.get("hooks", {}).values()
        for group in entries
        for hook in group.get("hooks", [])
    ]
    assert "python3 /usr/local/bin/my-custom-hook.py" in all_commands, (
        f"unrelated operator hook was not preserved after merge; "
        f"commands found: {all_commands!r}"
    )

    # The unrelated env key must survive unchanged.
    assert merged.get("env", {}).get("KEEP") == "1", (
        f"env key 'KEEP' was not preserved; env after merge: {merged.get('env')!r}"
    )

    # The template's router registration must have been added (presence bound).
    router_commands = [c for c in all_commands if "hook_router.py" in c]
    assert len(router_commands) >= 1, (
        f"expected at least one hook_router.py command after merge; "
        f"commands found: {all_commands!r}"
    )

    # A rename into place creates a new inode; the pre-fix cp truncates and
    # rewrites the same inode — that is the truncation hazard this test detects.
    new_inode = os.stat(settings_path).st_ino
    assert new_inode != original_inode, (
        f"settings.json inode did not change (old={original_inode}, new={new_inode}); "
        "install.sh used cp (truncate-in-place) instead of a same-directory mv rename"
    )

    # The backup must exist and be byte-equal to the original settings.json.
    backup_path = target / "settings.json.pre-firebreak"
    assert backup_path.exists(), (
        f"expected backup at {backup_path!r}; "
        f"target dir contents: {sorted(os.listdir(target))!r}"
    )
    assert backup_path.read_bytes() == original_bytes, (
        "backup settings.json.pre-firebreak does not match the original bytes"
    )

    # No temp file residue: no entry in target contains "tmp", and the only
    # settings.json-prefixed entries are the live file and the pre-firebreak backup.
    entries = os.listdir(str(target))
    temp_residue = [e for e in entries if "tmp" in e]
    assert temp_residue == [], (
        f"unexpected temp file residue in target dir: {temp_residue!r}"
    )

    settings_prefixed = {e for e in entries if e.startswith("settings.json")}
    allowed = {"settings.json", "settings.json.pre-firebreak"}
    assert settings_prefixed <= allowed, (
        f"unexpected settings.json-prefixed entries: {settings_prefixed - allowed!r}"
    )
    # Presence bound: confirm the live settings.json is actually there.
    assert "settings.json" in entries, (
        "settings.json is missing from target dir after install"
    )
