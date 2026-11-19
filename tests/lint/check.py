#!/usr/bin/env python3
"""Lint check for the Python that Firebreak installs: check.py [--lower]

Scope: every Python file under assets/fbk-scripts outside a tests folder, and installer/merge-settings.py.
Rules (ruff, one pinned version): likely bugs (F, B), complexity above 10 (C901), catch-everything handlers
(BLE001), subprocess calls with no failure check (PLW1510), files opened without being closed (SIM115).

Functions that were above the complexity limit when the check was set up are recorded with their score in
complexity-backlog.json. The record only tightens: a new function above the limit fails, a recorded function
scoring higher fails, and a recorded function scoring lower fails until --lower writes the lower number (or
removes the entry once the function is at or under the limit).

Prints three TAP rows, each with what to do when it fails. Exit status 1 when a row fails.
"""
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKLOG = Path(__file__).with_name("complexity-backlog.json")
RUFF = "ruff@0.17.5"
RULES = "F,B,C901,BLE001,PLW1510,SIM115"
LIMIT = 10
COMPLEX = re.compile(r"`(.+)` is too complex \((\d+) > \d+\)")


def files():
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", "assets/fbk-scripts/*.py"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.split("\n")
    scripts = [f for f in listed if f and "tests" not in Path(f).parts and (ROOT / f).is_file()]
    return sorted([*scripts, "installer/merge-settings.py"])


def findings():
    done = subprocess.run(
        ["uvx", "-q", RUFF, "check", "--isolated", "--select", RULES, "--config",
         f"lint.mccabe.max-complexity = {LIMIT}", "--output-format", "json", *files()],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    try:
        return json.loads(done.stdout)
    except ValueError:
        sys.exit(f"Bail out! ruff did not run: {done.stderr.strip() or done.stdout.strip()}")


def measure():
    """Other findings as printable lines; complexity scores as {"file::function": [scores, highest first]}."""
    other, scores = [], {}
    for item in findings():
        path = Path(item["filename"]).resolve().relative_to(ROOT).as_posix()
        match = COMPLEX.search(item["message"]) if item["code"] == "C901" else None
        if match:
            scores.setdefault(f"{path}::{match[1]}", []).append(int(match[2]))
        else:
            other.append(f"{path}:{item['location']['row']}: {item['code']} {item['message']}")
    return other, {key: sorted(found, reverse=True) for key, found in scores.items()}


def compare(recorded, scores):
    """New or worse functions, and recorded scores that are now too high."""
    worse, stale = [], []
    for key in sorted({*recorded, *scores}):
        was, now = Counter(recorded.get(key, [])), Counter(scores.get(key, []))
        if was == now:
            continue
        old, new = sorted(was.elements(), reverse=True), sorted(now.elements(), reverse=True)
        if len(new) > len(old) or any(n > o for n, o in zip(new, old, strict=False)):
            worse.append(f"{key} scores {new or 'at or under the limit'}; recorded {old or 'nothing'}")
        else:
            stale.append(f"{key} scores {new or 'at or under the limit'}; recorded {old}")
    return worse, stale


def row(number, passed, name, lines, advice):
    print(f"{'ok' if passed else 'not ok'} {number} - {name}")
    if not passed:
        for line in [*lines, advice]:
            print(f"# {line}")
    return passed


def main():
    recorded = json.loads(BACKLOG.read_text()) if BACKLOG.exists() else {}
    other, scores = measure()
    worse, stale = compare(recorded, scores)
    if sys.argv[1:] == ["--lower"]:
        if worse:
            sys.exit("Refused: the record only goes down.\n" + "\n".join(worse))
        BACKLOG.write_text(json.dumps(scores, indent=1, sort_keys=True) + "\n")
        print(f"Recorded {sum(map(len, scores.values()))} functions above the limit of {LIMIT}.")
        return 0
    passed = [
        row(1, not other, "no lint findings in the Python Firebreak installs", other,
            "Fix each finding. Where the code is right as it stands, say why beside it: `# noqa: <RULE> - <reason>`."),
        row(2, not worse, f"no function is newly above complexity {LIMIT} and no recorded one got worse", worse,
            "Split the function into named steps until it scores at or under the limit, or at or under its recorded score."),
        row(3, not stale, "the recorded complexity scores are current", stale,
            "A function got simpler: write the lower scores down with `python3 tests/lint/check.py --lower`."),
    ]
    print("1..3")
    return 0 if all(passed) else 1


if __name__ == "__main__":
    raise SystemExit(main())
