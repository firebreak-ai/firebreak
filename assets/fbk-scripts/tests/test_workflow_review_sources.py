"""Review snapshots follow repository inputs, not incidental local build state."""

import os
import subprocess

import pytest

from fbk.workflow import review_context


@pytest.fixture
def repository(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    root = tmp_path / "project"
    root.mkdir()
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    for relative, content in {
        ".gitignore": "build/\n*.generated.py\n",
        "src/main.py": "from .contract import VERSION\n",
        "src/contract.py": "VERSION = 1\n",
        "src/schema.generated.py": "# Checked-in generated protocol definition.\n",
        "CLAUDE.md": "Preserve the public protocol.\n",
        "build/output.txt": "Temporary compiler output.\n",
        "build/contract.json": '{"version": 1}\n',
    }.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    # Tracked generated code remains reviewable even when its name matches an
    # ignore rule. New, untracked source files must remain reviewable too.
    subprocess.run(
        ["git", "-C", str(root), "add", "-f", "src/schema.generated.py"],
        check=True,
    )
    return root


def test_snapshot_excludes_ignored_output_and_keeps_repository_context(repository):
    with review_context.snapshot(repository, ["src/main.py"]) as (snapshot, manifest):
        for relative in [
            "src/main.py",
            "src/contract.py",
            "src/schema.generated.py",
            "CLAUDE.md",
        ]:
            assert relative in manifest
            assert (snapshot / relative).read_bytes() == (
                repository / relative
            ).read_bytes()
        assert "build/output.txt" not in manifest
        assert not (snapshot / "build/output.txt").exists()


def test_explicitly_required_ignored_input_is_preserved(repository):
    required = "build/contract.json"
    with review_context.snapshot(repository, [required]) as (snapshot, manifest):
        assert required in manifest
        assert (snapshot / required).read_bytes() == (repository / required).read_bytes()
        review = {
            "source_policy": "original-snapshot-v1",
            "required_files": [required],
            "snapshot_files": manifest,
        }
    assert review_context.snapshot_fresh(repository, review)
    (repository / required).write_text('{"version": 2}\n')
    assert not review_context.snapshot_fresh(repository, review)


def test_ignored_external_cache_symlink_does_not_prevent_review(repository, tmp_path):
    cache = tmp_path / "shared-cache"
    cache.mkdir()
    (cache / "entry.txt").write_text("Machine-local cache entry.\n")
    (repository / "build/cache").symlink_to(cache, target_is_directory=True)

    with review_context.snapshot(repository, ["src/main.py"]) as (snapshot, manifest):
        assert (snapshot / "src/main.py").read_bytes() == (
            repository / "src/main.py"
        ).read_bytes()
        assert not any(path.startswith("build/cache") for path in manifest)
        assert not (snapshot / "build/cache").exists()


def test_snapshot_freshness_ignores_build_changes_but_detects_source_changes(repository):
    required = ["src/main.py"]
    with review_context.snapshot(repository, required) as (_, manifest):
        review = {
            "source_policy": "original-snapshot-v1",
            "required_files": required,
            "snapshot_files": manifest,
        }
    assert review_context.snapshot_fresh(repository, review)

    (repository / "build/output.txt").write_text("Rebuilt output.\n")
    (repository / "build/new-output.txt").write_text("Additional build output.\n")
    assert review_context.snapshot_fresh(repository, review)

    (repository / "src/contract.py").write_text("VERSION = 2\n")
    assert not review_context.snapshot_fresh(repository, review)
