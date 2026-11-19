"""Run a project's tests against each scoring-kit change, in a disposable copy.

Usage:
    python3 run-kit.py --root <project> --kit <kit-folder> --command "<test command>" --out <log-folder>

The copy is a detached git worktree holding the project's current state,
uncommitted and untracked (not ignored) files included. The project's own
working tree and index are never changed. Each `.patch` file in the kit is
applied to a fresh copy of that state, the command runs from the copy's root,
and its exit code and output go to `<out>/<patch name>.log`. The unchanged
state runs first, as `unchanged`. `<out>/summary.txt` lists one line per run:
the name, a tab, and `passed`, `failed (exit N)`, `timed out` or `did not apply`.
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def git(*args, cwd, env=None, check=True):
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=check,
                          capture_output=True, text=True)


def snapshot_tree(root: Path) -> str:
    """Write the working tree's current state, untracked files included, as a git tree."""
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
        git("read-tree", "HEAD", cwd=root, env=env)
        git("add", "-A", cwd=root, env=env)
        return git("write-tree", cwd=root, env=env).stdout.strip()


def run_once(copy: Path, tree: str, patch: Path | None, command: str, timeout: int | None):
    git("read-tree", "-u", "--reset", tree, cwd=copy)
    git("clean", "-fdq", cwd=copy)
    if patch is not None:
        applied = git("apply", str(patch), cwd=copy, check=False)
        if applied.returncode != 0:
            return "did not apply", applied.stderr
    try:
        result = subprocess.run(command, shell=True, cwd=copy, capture_output=True,
                                text=True, errors="replace", timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        return "timed out", f"{exc.stdout or ''}{exc.stderr or ''}"
    outcome = "passed" if result.returncode == 0 else f"failed (exit {result.returncode})"
    return outcome, f"exit code: {result.returncode}\n{result.stdout}{result.stderr}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--kit", required=True, type=Path)
    parser.add_argument("--command", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=None, help="seconds per run")
    args = parser.parse_args()

    root = Path(git("rev-parse", "--show-toplevel", cwd=args.root).stdout.strip())
    patches = sorted(args.kit.resolve().glob("*.patch"))
    args.out.mkdir(parents=True, exist_ok=True)
    tree = snapshot_tree(root)

    copy = Path(tempfile.mkdtemp(prefix="run-kit-")) / "copy"
    git("worktree", "add", "--detach", "-q", str(copy), "HEAD", cwd=root)
    lines = []
    try:
        for patch in [None, *patches]:
            name = "unchanged" if patch is None else patch.stem
            outcome, log = run_once(copy, tree, patch, args.command, args.timeout)
            (args.out / f"{name}.log").write_text(log, encoding="utf-8")
            lines.append(f"{name}\t{outcome}")
            print(lines[-1], flush=True)
    finally:
        git("worktree", "remove", "--force", str(copy), cwd=root, check=False)
        git("worktree", "prune", cwd=root, check=False)
    (args.out / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
