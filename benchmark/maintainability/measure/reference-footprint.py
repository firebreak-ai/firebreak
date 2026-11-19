#!/usr/bin/env -S uv run -q --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["radon==6.0.1", "cognitive_complexity==1.3.0"]
# ///
"""Footprint of a change's reference implementation: reference-footprint.py <change-dir> <base-repo>   (prints JSON)

<change-dir> is the change's folder under local/. Applies <change-dir>/reference.patch to a throwaway clone of the base at its HEAD and reports measure.py's "landed" and
"difficulty" numbers for it (same definitions), so maintainer runs can be read against them. Only meaningful on a base
that is the unmodified reference program, such as local/anchors/circuit_eval/middle. The patch is applied exactly, or else
with 2 lines of matching context ("applied" says which): the anchors drop the reference's 6-line file header, which the
first hunk of some files leans on.
"""
import json, pathlib, subprocess, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from measure import footprint, git

change, base = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve()
with tempfile.TemporaryDirectory() as tmp:
    subprocess.run(["git", "clone", "-q", str(base), tmp], check=True)
    for opts in ([], ["-C2"], None):
        if opts is None:
            sys.exit(f"reference.patch does not apply to {base}")
        if subprocess.run(["git", "-C", tmp, "apply", *opts, str(change / "reference.patch")], capture_output=True).returncode == 0:
            break
    git(tmp, "add", "-A"); git(tmp, "-c", "user.name=x", "-c", "user.email=x@x", "commit", "-q", "-m", "reference")
    landed, difficulty = footprint(tmp, "HEAD~1")
print(json.dumps({"change": change.name, "base": base.name, "base_commit": git(base, "rev-parse", "HEAD").strip(),
                  "applied": "exact" if not opts else "with 2 lines of context", "landed": landed, "difficulty": difficulty}, indent=1))
