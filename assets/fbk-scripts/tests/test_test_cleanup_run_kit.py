"""The test cleanup kit runner: each kit change runs in a disposable copy, never the project."""

from pathlib import Path
import subprocess
import sys


RUN_KIT = Path(__file__).resolve().parents[1] / "run-kit.py"


def sh(*args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout


def make_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    sh("git", "init", "-q", cwd=project)
    sh("git", "config", "user.email", "t@example.com", cwd=project)
    sh("git", "config", "user.name", "t", cwd=project)
    (project / "value.txt").write_text("1\n")
    (project / "check.sh").write_text("grep -qx 1 value.txt && test ! -e leftover.txt\n")
    sh("git", "add", "-A", cwd=project)
    sh("git", "commit", "-qm", "start", cwd=project)
    return project


def patch(project: Path, kit: Path, name: str, new_value: str) -> None:
    """Write a kit patch changing value.txt, made against the committed state."""
    (project / "value.txt").write_text(new_value)
    (kit / f"{name}.patch").write_text(sh("git", "diff", cwd=project))
    sh("git", "checkout", "--", "value.txt", cwd=project)


def run_kit(project: Path, kit: Path, out: Path, command: str) -> dict:
    subprocess.run([sys.executable, str(RUN_KIT), "--root", str(project), "--kit", str(kit),
                    "--command", command, "--out", str(out)], check=True, capture_output=True)
    lines = (out / "summary.txt").read_text().splitlines()
    return dict(line.split("\t") for line in lines)


def test_each_change_is_judged_in_a_copy_and_the_project_is_untouched(tmp_path):
    project = make_project(tmp_path)
    kit = tmp_path / "kit"
    kit.mkdir()
    patch(project, kit, "wrong", "2\n")
    patch(project, kit, "rewrite", "1\n\n")
    (kit / "adds-file.patch").write_text(  # runs first; its new file must not reach later runs
        "diff --git a/leftover.txt b/leftover.txt\nnew file mode 100644\n"
        "--- /dev/null\n+++ b/leftover.txt\n@@ -0,0 +1 @@\n+x\n")
    (kit / "stale.patch").write_text(
        "--- a/missing.txt\n+++ b/missing.txt\n@@ -1 +1 @@\n-x\n+y\n")
    status_before = sh("git", "status", "--porcelain", cwd=project)

    summary = run_kit(project, kit, tmp_path / "out", "sh check.sh")

    assert summary == {"unchanged": "passed", "adds-file": "failed (exit 1)", "rewrite": "passed",
                       "stale": "did not apply", "wrong": "failed (exit 1)"}
    assert (project / "value.txt").read_text() == "1\n"
    assert sh("git", "status", "--porcelain", cwd=project) == status_before
    assert len(sh("git", "worktree", "list", cwd=project).splitlines()) == 1


def test_uncommitted_and_new_test_files_are_what_runs(tmp_path):
    project = make_project(tmp_path)
    kit = tmp_path / "kit"
    kit.mkdir()
    patch(project, kit, "wrong", "2\n")
    (project / "check.sh").write_text("sh new_check.sh\n")
    (project / "new_check.sh").write_text("grep -qx 2 value.txt\n")

    summary = run_kit(project, kit, tmp_path / "out", "sh check.sh")

    assert summary == {"unchanged": "failed (exit 1)", "wrong": "passed"}
