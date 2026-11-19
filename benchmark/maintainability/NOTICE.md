# Credits and licenses

This kit stands on other people's work. Most of it is fetched or run when you use the kit and is not stored here.
Two small pieces are copied into tracked files; their license notice is at the end.

## SlopCodeBench

By Gabriel Orlanski and co-authors (Orlanski, Roy, Yun, Shin, Gu, Ge, Adila, Albarghouthi, Sala), "SlopCodeBench:
Measuring Code Erosion Under Iterative Specification Refinement", https://arxiv.org/abs/2603.24755.

- Tool: https://github.com/SprocketLab/slop-code-bench. MIT License, `Copyright (c) 2025 gabeorlanski`.
- Problem set: https://github.com/SprocketLab/scb-problems. Its `LICENSE` file is the Apache License 2.0 and carries
  no copyright line; its `CITATION.cff` states MIT.
- Quality checker: `scb-check` 0.1.3, https://github.com/gabeorlanski/scb-check, MIT.

What comes from it:

- The problem (`circuit_eval`), its checkpoint specifications, hidden tests and reference solutions. None of this is
  stored here: you fetch the problem set yourself. Its files carry a notice that they must never appear in training
  corpora, so nothing made from them is tracked either (see the README).
- The build design: one program built checkpoint by checkpoint, each checkpoint in a fresh session.
- The hidden-test procedure and the pass groups (core, functionality, error, regression): `build/hidden-tests.sh`
  follows the tool's pytest runner.
- The request wording: `setup/render-prompt.py` holds the text of the tool's `configs/prompts/just-solve.jinja`.
  This is copied material.
- The code-quality numbers erosion, verbosity, duplicated lines and source-line count: `build/quality.py` and
  `measure/state.py` run `scb-check` from PyPI.

## EXACT Coding / Agentic Coding Lab

By Marco Emrich. https://github.com/marcoemrich/agentic_coding_lab. MIT License, `Copyright (c) 2026 Marco Emrich`.

What comes from it:

- The Python project skeleton every build starts from, its install script and the Claude Code settings file the
  sessions run with. Read from your checkout when a build starts; not stored here.
- The EXACT workflow and the plain test-first workflow two of the approaches use. Copied into a build's work folder
  from your checkout; not stored here.
- The linter rule set and limits behind the smell counts: `RUFF_TOML` in `measure/state.py` is copied from the lab's
  `experiments/stacks/python-pytest/pyproject.toml`, and the four smell groups follow its `analyze-run.sh`. This is
  copied material.
- The choice of mutation engine and version, and the rule that a timed-out mutant counts as caught
  (`measure/mutants.py`, after the lab's `compute-mutation-score.py`).

## mutmut

By Anders Hovmöller. https://github.com/boxed/mutmut. BSD 3-Clause License, `Copyright (c) 2016, Anders Hovmöller`.

`measure/mutants.py` uses mutmut 3.8.0 as a library to list the small code changes it tries: the mutation operators
are mutmut's. It is installed when the script runs and is not stored here.

## Other tools the kit runs

Installed on demand, not stored here: radon 6.0.1 (cyclomatic complexity; MIT, Michele Lacchia),
cognitive_complexity 1.3.0 (cognitive complexity; MIT, Ilya Lebedev), ruff 0.16.8 (lint findings; MIT, Astral),
coverage.py, pytest and its plugins.

## MIT permission notice for the copied material

The request wording in `setup/render-prompt.py` (Copyright (c) 2025 gabeorlanski) and the linter settings in
`measure/state.py` (Copyright (c) 2026 Marco Emrich) are used under the MIT License:

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
