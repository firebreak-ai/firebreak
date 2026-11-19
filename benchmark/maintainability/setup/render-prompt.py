"""Render SlopCodeBench's just-solve prompt for a checkpoint, as its local-py environment would: render-prompt.py <cp> [problem] [tests]
The prompt wording is SlopCodeBench's configs/prompts/just-solve.jinja (MIT, see NOTICE.md); the spec is read from SCB_PROBLEMS.
A third argument `tests` adds one line saying the project already has a passing test suite (for runs from a common start)."""
import pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from settings import setting

P = setting("SCB_PROBLEMS") or sys.exit("SCB_PROBLEMS is not set (see settings.example.env)")
cp, prob = int(sys.argv[1]), (sys.argv[2] if len(sys.argv) > 2 else "etl_pipeline")
spec = open(f"{P}/{prob}/checkpoint_{cp}.md").read()
cfg = open(f"{P}/{prob}/config.yaml").read()
entry = re.search(r"^entry_file:\s*(\S+)", cfg, re.M).group(1)
spec = re.sub(r"<!--.*?-->", "", spec, flags=re.S)          # benchmark canary comment
spec = spec.replace("%%%ENTRYPOINT:entry_file%%%", f"{entry}.py").replace("%%%ENTRYPOINT:entry_command%%%", f"python {entry}.py")
venv = ("Use a virtual environment and ensure that a `requirements.txt` is present with any dependencies you need to solve the problem."
        if cp == 1 else "Keep using the same virtual environment you started with, update `requirements.txt` with any new dependencies you need.")
tests = "\nThe project already has a test suite in `tests/` that passes; it is run with `.venv/bin/python -m pytest`." if sys.argv[3:] == ["tests"] else ""
print(f"Implement a program that 100% solves the specification. That is all you need to do.\n{venv}{tests}\n\nYour task is:\n{spec.strip()}")
