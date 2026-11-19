"""Uninstall must preserve files outside its target, even with unsafe entries."""

import json
import os
import subprocess
from pathlib import Path

import pytest


INSTALLER = Path(__file__).resolve().parents[3] / "installer/install.sh"


def uninstall(target, entries):
    (target / ".firebreak-manifest.json").write_text(
        json.dumps({"files": entries, "settings_entries": {}})
    )
    return subprocess.run(
        ["bash", str(INSTALLER), "--uninstall", "--target", str(target)],
        env={**os.environ, "HOME": str(target.parent)},
        capture_output=True,
        text=True,
        timeout=20,
    )


@pytest.mark.parametrize("escape", ["parent-traversal", "symlink-directory"])
def test_uninstall_preserves_files_outside_target(tmp_path, escape):
    target = tmp_path / "install"
    target.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    victim = outside / "user-document.txt"
    original = b"User-owned content that Firebreak must never delete.\n"
    victim.write_bytes(original)
    if escape == "parent-traversal":
        entry = "../outside/user-document.txt"
    else:
        (target / "linked").symlink_to(outside, target_is_directory=True)
        entry = "linked/user-document.txt"

    # Prove the fixture reaches a real external file before invoking the CLI.
    assert (target / entry).resolve() == victim
    result = uninstall(target, [entry])

    # Either rejecting the manifest or safely skipping its entry is acceptable.
    # Exit status alone cannot establish confinement.
    assert victim.is_file(), (
        f"uninstall deleted an external file via {escape}; "
        f"command={result.args!r}\nexit={result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert victim.read_bytes() == original


def test_uninstall_removes_owned_file_and_preserves_unlisted_neighbor(tmp_path):
    target = tmp_path / "install"
    owned = target / "skills/example/SKILL.md"
    owned.parent.mkdir(parents=True)
    owned.write_text("Installed asset\n")
    neighbor = owned.parent / "user-notes.md"
    neighbor.write_bytes(b"Keep these notes\n")

    result = uninstall(target, ["skills/example/SKILL.md"])

    assert result.returncode == 0, (
        f"expected successful uninstall; command={result.args!r}\n"
        f"exit={result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert not owned.exists()
    assert neighbor.read_bytes() == b"Keep these notes\n"
    assert not (target / ".firebreak-manifest.json").exists()


@pytest.mark.parametrize("external_path", ["settings.json", "fbk-scripts"])
def test_uninstall_rejects_external_cleanup_scope_before_removing_assets(tmp_path, external_path):
    target = tmp_path / "install"
    target.mkdir()
    owned = target / "owned.txt"
    owned.write_bytes(b"installed asset")
    outside = tmp_path / "outside"
    outside.mkdir()
    if external_path == "settings.json":
        victim = outside / "settings.json"
        original = b'{ "env": {"USER_SETTING": "keep"} }\n'
        victim.write_bytes(original)
        (target / external_path).symlink_to(victim)
    else:
        victim = outside / ".venv/user-data"
        victim.parent.mkdir()
        original = b"external environment data"
        victim.write_bytes(original)
        (target / external_path).symlink_to(outside, target_is_directory=True)

    result = uninstall(target, ["owned.txt"])

    assert result.returncode != 0, (
        f"unsafe uninstall must report refusal; command={result.args!r}\n"
        f"exit={result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert victim.read_bytes() == original
    assert owned.read_bytes() == b"installed asset", "refusal must precede deletion"
    assert (target / ".firebreak-manifest.json").is_file()
