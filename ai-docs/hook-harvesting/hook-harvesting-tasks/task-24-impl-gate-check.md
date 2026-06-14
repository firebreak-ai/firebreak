---
id: task-24
type: implementation
wave: 2
covers: [AC-01, AC-09, AC-10, AC-21, AC-22, AC-23]
files_to_create:
  - assets/fbk-scripts/fbk/capture/gate_check.py
test_tasks: [task-04, task-05, task-06]
completion_gate: "task-04, task-05, task-06 tests pass"
---

# 1 Objective

Produce the per-project capture gate: it answers "is this project instrumented?" and "what capture level resolves?" using only filesystem existence checks plus one bounded single-line read of `capture.cfg` and a cheap env/global-marker read — including all three security hardenings (Firebreak-specific marker sentinel, out-of-tree corroboration for the privileged `full` level, and realpath confinement with symlink refusal) in one cohesive file.

# 2 Context

The gate is the single control standing between "measure my own pipeline" and "record prompts in every repo I open," and it runs on the hot path of every Claude tool call — so it must be cheap, never raise, and return a safe default (not-instrumented / `off`) on any error. All of its responsibilities live in one file because they are one decision (is capture allowed here, and at what level) and share the same realpath-confinement and bounded-read machinery; splitting them would scatter a single security boundary across modules. That file-cohesion is the deliberate justification for this module carrying instrumentation, level resolution, and hardening together.

Pinned facts the producers rely on:
- A project is instrumented only when a Firebreak-specific marker sentinel exists under `.claude/automation/` (e.g. `.claude/automation/.fbk-managed`) OR a `.fbk-capture/capture.cfg` file exists. The bare `.claude/automation/` directory alone does NOT instrument the project (a hostile repo could ship that shared namespace).
- `capture.cfg` is a plain `key=value` file whose first line is `capture_level=<off|standard|full>`.
- The privileged `full` level is honored only when an operator-controlled signal that lives OUTSIDE the repo working tree corroborates an in-tree `capture.cfg=full`: primary signal is env `FBK_CAPTURE_LEVEL=full`; secondary is a marker in the operator's global Claude dir located via env `CLAUDE_CONFIG_DIR` (default `~/.claude`) keyed to the project path. An in-tree `full` without corroboration is clamped to `standard`. The low-harm off/standard opt-in stays in-tree.
- The capture dir and config are realpath-confined under the resolved project root; a symlinked `.fbk-capture/` or symlinked `capture.cfg` is refused and the project treated as uninstrumented.

The package's own `fbk.state` reads `STATE_DIR` from the environment; this gate must NOT import the state engine or any YAML — only `os`, `os.path`, and a bounded file read.

# 3 Instructions

1. Create `fbk/capture/gate_check.py`. Define a module constant for the sentinel name `FBK_MARKER_SENTINEL = ".fbk-managed"` and the capture dir/config names (`.fbk-capture`, `capture.cfg`).
2. Implement a private `_real_capture_dir(cwd) -> str | None`: compute `<cwd>/.fbk-capture`; if it does not exist return `None`; if it exists, realpath-confirm it resolves to a real directory whose realpath is under `os.path.realpath(cwd)` — if it is a symlink pointing outside the project root (or otherwise escapes), return `None` (refused). Completion: a symlinked `.fbk-capture/` returns `None`; a real in-tree dir returns its path.
3. Implement `project_is_instrumented(cwd: str) -> bool`. Wrap in `try/except Exception` returning `False` on any error. Return `True` when either (a) the Firebreak sentinel file `<cwd>/.claude/automation/.fbk-managed` exists, OR (b) a realpath-confined `.fbk-capture/capture.cfg` exists (use `_real_capture_dir` then check `capture.cfg` exists under it and is not itself a symlink escaping the tree). Otherwise `False`. Completion: marked project → True; capture.cfg project → True; bare project → False; bare `.claude/automation/` without sentinel → False; symlinked capture dir → False; error path → False, no raise.
4. Implement a private bounded single-line cfg read `_read_cfg_level(real_capture_dir) -> str | None`: open `capture.cfg` and read ONE line (`f.readline()`, not `f.read()`), strip it, parse `capture_level=<value>`; refuse a symlinked `capture.cfg` (return `None`). Return the raw value string or `None`. Completion: a cfg whose first line is `capture_level=standard` followed by megabytes of filler returns `"standard"` without reading the filler.
5. Implement `resolve_capture_level(cwd: str) -> str` returning one of `"off"`, `"standard"`, `"full"`. Wrap in `try/except Exception` returning `"off"`. Logic:
   - If not `project_is_instrumented(cwd)` → return `"off"`.
   - Read the cfg value via the bounded read (when a real capture dir + cfg exist).
   - If the cfg value is `"off"` → `"off"`. If `"standard"` → `"standard"`.
   - If the cfg value is `"full"` → honor it ONLY when an out-of-tree signal corroborates (see step 6); otherwise clamp to `"standard"`.
   - If the cfg is absent/unreadable but the project is Firebreak-instrumented (sentinel present) → default `"standard"`.
   - If the cfg value is an unrecognized string → print a warning to stderr naming the offending value and return `"standard"`.
   Completion: valid cfg `off`/`standard` returned verbatim; marked-no-cfg → `standard`; invalid value → `standard` + stderr warning; uninstrumented → `off`; giant trailing bytes do not change the answer.
6. Implement a private `_full_corroborated(cwd) -> bool` for the out-of-tree `full` signal. Return `True` when EITHER: env `FBK_CAPTURE_LEVEL` equals `"full"` (case-insensitive ok), OR a marker exists in the operator's global Claude dir (`os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude"))`) keyed to the project path. Define and document the exact global-marker shape: a file under `<CLAUDE_CONFIG_DIR>/fbk-capture-full/` whose name is a filesystem-safe encoding of `os.path.realpath(cwd)` (e.g. the realpath with path separators replaced by a chosen delimiter, or its hash) — state this exact form in a module comment so the test that writes the fixture marker matches it. Reading the global dir is permitted (read-only); never write there. Completion: in-tree `full` + `FBK_CAPTURE_LEVEL=full` → `full`; in-tree `full` + the keyed global marker under a fixture `CLAUDE_CONFIG_DIR` → `full`; in-tree `full` with neither → `standard`.
7. Performance: the whole gate must be cheap on a bare project — existence checks plus, at most, one bounded line read and a couple of env/dir reads. No recursion over the project, no whole-file reads. Completion: the overhead-budget test (task-06) measures a bare-project `project_is_instrumented` under its generous wall-clock bound.

# 4 Files to create/modify

- Create `fbk/capture/gate_check.py`

# 5 Test requirements

Makes task-04 (`tests/test_capture_gate_check.py` — instrumentation + level core), task-05 (`tests/test_capture_gate_check_hardening.py` — marker sentinel, out-of-tree full corroboration, symlink refusal), and task-06 (`tests/test_capture_gate_check_overhead.py` — bare-project cheapness, non-gating timing) pass.

# 6 Acceptance criteria

Primary: task-04, task-05, task-06 tests pass. Covers AC-01 (per-project gate + no-ambient-overhead), AC-09 (shipped default `standard` inside Firebreak), AC-10 (level resolution via filesystem + one single-line read), AC-21 (the gate decides against one pinned `cwd`), AC-22 (Firebreak-specific marker + out-of-tree `full` corroboration), AC-23 (realpath confinement + symlink refusal).

# 7 Model

Sonnet

# 8 Wave

2
