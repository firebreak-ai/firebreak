---
feature: python-uv-migration
status: draft
category: feature
---

# Python Migration

## Problem

Firebreak's hook scripts are written in bash, which limits the user base to Linux and macOS (and behaves inconsistently across macOS bash versions). Claude Code runs cross-platform, but Firebreak's executable infrastructure does not. Additionally, the bash scripts contain embedded Python heredocs — the bash layer adds no logic beyond argument parsing and subprocess wiring. This dual-language approach makes the scripts harder to test and prevents shared imports between modules. Converting to Python eliminates the platform constraint and consolidates all executable code into a single language with proper module structure.

## Goals / Non-goals

**Goals:**

- Convert all 7 bash hook scripts to Python modules
- Consolidate all Firebreak Python code into a single project at `assets/fbk-scripts/`
- Provide a single dispatcher script (`fbk.py`) as the entry point for all context asset invocations
- Update all skill and settings.json references to use the dispatcher
- Maintain behavioral parity: each converted script produces identical output (stdout/stderr, exit codes) for the same inputs
- Cross-platform execution: scripts run on Linux, macOS, and Windows wherever Python 3.11+ is available

**Non-goals:**

- Modifying the installer (`installer/install.sh`, `installer/merge-settings.py`) — the existing file-copy mechanism handles the new directory structure without changes
- Adding new functionality to any script during conversion — this is a structural migration, not a feature enhancement
- Converting JSON config files (`settings.json`, `fbk-presets.json`) — these are data, not executables
- Building the state machine harness — this migration creates the project structure it will use
- Requiring uv or any package manager at runtime — scripts use only Python stdlib and PyYAML

## User-facing behavior

No change to user-visible behavior. Gate scripts produce the same pass/fail output. Hooks fire on the same events. Skill invocations call the same logical scripts.

Observable differences:

- Error messages from argument validation may differ in formatting (argparse vs. hand-rolled bash messages) but convey the same information
- Scripts now require Python 3.11+ and PyYAML — they fail with a clear error if either is missing

## Technical approach

### Source layout

Create `assets/fbk-scripts/` with a dispatcher at the root and the `fbk` package as a sibling:

```
assets/fbk-scripts/
├── fbk.py                   # single dispatcher — all context assets point here
├── pyproject.toml            # project metadata; dev dependencies (pytest)
└── fbk/
    ├── __init__.py
    ├── gates/
    │   ├── __init__.py
    │   ├── spec.py          # from spec-gate.sh
    │   ├── review.py        # from review-gate.sh
    │   ├── breakdown.py     # from breakdown-gate.sh
    │   ├── task_reviewer.py # from task-reviewer-gate.sh
    │   └── test_hash.py     # from test-hash-gate.sh
    ├── hooks/
    │   ├── __init__.py
    │   ├── task_completed.py  # from task-completed.sh
    │   └── dispatch_status.py # from dispatch-status.sh
    ├── council/
    │   ├── __init__.py
    │   ├── session_logger.py  # from skills/fbk-council/session-logger.py
    │   ├── session_manager.py # from skills/fbk-council/session-manager.py
    │   └── ralph.py           # from skills/fbk-council/ralph-council.py
    ├── data/
    │   └── fbk-presets.json  # from config/fbk-presets.json
    ├── audit.py       # from hooks/fbk-sdl-workflow/audit-logger.py
    ├── config.py      # from hooks/fbk-sdl-workflow/config-loader.py
    ├── state.py       # from hooks/fbk-sdl-workflow/state-engine.py
    └── pipeline.py    # from scripts/fbk-pipeline.py
```

### Dispatcher (`fbk.py`)

A single entry-point script at the root of `fbk-scripts/`. It:

1. Resolves its own location via `os.path.realpath(__file__)` to handle symlinks correctly, then adds the parent directory to `sys.path[1]` (after `""`, to avoid masking stdlib modules) — the `fbk/` package is a sibling of `fbk.py`, so no `src/` indirection is needed
2. Checks `sys.version_info >= (3, 11)` and exits with a clear error message if the Python version is too old
3. Maps command names to module paths (e.g., `"spec-gate"` → `"fbk.gates.spec"`)
4. Dynamically imports the target module and calls its `main()` function
5. Sets `sys.argv` to `[command_name, ...remaining_args]` before calling `main()` so each module's argparse sees its own arguments starting from position 0. Modules with subcommands (e.g., `pipeline run --preset x`) receive `["pipeline", "run", "--preset", "x"]`
6. Does not read stdin — stdin is passed through unmodified to the target module (required by `task-completed` which reads Claude Code hook event data from stdin)

Context assets reference only this script. The dispatcher resolves paths relative to itself, eliminating the path-resolution mismatch where context assets must guess the agent's working directory.

Command map:

| Command | Module |
|---|---|
| `spec-gate` | `fbk.gates.spec` |
| `review-gate` | `fbk.gates.review` |
| `breakdown-gate` | `fbk.gates.breakdown` |
| `task-reviewer-gate` | `fbk.gates.task_reviewer` |
| `test-hash-gate` | `fbk.gates.test_hash` |
| `task-completed` | `fbk.hooks.task_completed` |
| `dispatch-status` | `fbk.hooks.dispatch_status` |
| `pipeline` | `fbk.pipeline` |
| `audit` | `fbk.audit` |
| `config` | `fbk.config` |
| `state` | `fbk.state` |
| `session-logger` | `fbk.council.session_logger` |
| `session-manager` | `fbk.council.session_manager` |
| `ralph` | `fbk.council.ralph` |

Exit behavior: the dispatcher exits with the return code from `main()`. If the command is unrecognized, it prints available commands to stderr and exits 2.

### pyproject.toml

Used for project metadata and dev tooling only — not required at runtime. Scripts are invoked directly via the dispatcher, not through installed entry points.

```toml
[project]
name = "fbk-scripts"
version = "0.4.0"
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### Conversion approach

The 7 bash scripts fall into three categories by conversion effort:

**Mostly bash with embedded Python heredoc** (3 scripts — significant rewrite): `spec-gate.sh`, `breakdown-gate.sh`, `task-reviewer-gate.sh`. These have substantial bash logic beyond the heredoc. `spec-gate.sh` has 126 lines of bash (heading detection via awk, section body extraction, open-questions rationale parsing, AC format validation, testing strategy traceability) plus 100 lines of embedded Python for injection detection. `breakdown-gate.sh` has a 23-line bash preamble constructing a JSON map of task file contents via bash loops before feeding to the Python heredoc. Conversion requires reimplementing the bash logic in Python, not just extracting the heredoc.

**Thin bash wrapper around embedded Python** (2 scripts — heredoc extraction): `dispatch-status.sh`, `test-hash-gate.sh`. The bash layer is minimal argument parsing and audit-logger invocation. Conversion extracts the embedded Python into proper modules, replaces bash argument parsing with `argparse`, and replaces `$SCRIPT_DIR`-relative subprocess calls to `audit-logger.py` with direct `from fbk.audit import log_event` imports. Note: `test-hash-gate.sh` uses `sha256sum` (GNU coreutils) and `mapfile` (bash 4.0+); the Python conversion replaces these with `hashlib.sha256` and standard file reading, resolving both macOS compatibility issues.

**Pure bash** (2 scripts — full rewrite): `review-gate.sh`, `task-completed.sh`. These must be rewritten in Python. `review-gate.sh` does regex matching and section extraction on markdown files — straightforward in Python with `re`. `task-completed.sh` detects test runners and linters, runs them, and checks file scope — requires `subprocess.run` calls.

### Shared module consolidation

Three utility modules currently live in `assets/hooks/fbk-sdl-workflow/` and are called as subprocesses by the bash scripts:

- `audit-logger.py` → `fbk.audit` — called by spec-gate, dispatch-status, task-reviewer-gate for structured logging. After conversion, callers import directly instead of subprocess invocation.
- `config-loader.py` → `fbk.config` — called by skills for configuration loading. Already has `import yaml`.
- `state-engine.py` → `fbk.state` — called by skills for pipeline state transitions.

Three scripts in `assets/skills/fbk-council/`:

- `session-logger.py` → `fbk.council.session_logger`
- `session-manager.py` → `fbk.council.session_manager`
- `ralph-council.py` → `fbk.council.ralph`

One script in `assets/scripts/`:

- `fbk-pipeline.py` → `fbk.pipeline`

One data file in `assets/config/`:

- `fbk-presets.json` → `fbk/data/fbk-presets.json` — used by `fbk.pipeline` for preset loading. `pipeline.py` path resolution changes from `Path(__file__).parent.parent / "config" / "fbk-presets.json"` to `Path(__file__).parent / "data" / "fbk-presets.json"`.

All relocate into the single project. Existing `if __name__ == "__main__"` blocks become `main()` functions callable by the dispatcher.

### Execution model

All script invocations use the absolute path `"$HOME"/.claude/fbk-scripts/fbk.py` with `python3`. This eliminates the agent's need to resolve paths relative to its working directory — the dispatcher path is fixed at install time.

Canonical invocation format:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py <command> [args...]
```

Hook commands in `settings.json` change from:

```json
"command": "\"$HOME\"/.claude/hooks/fbk-sdl-workflow/task-completed.sh"
```

to:

```json
"command": "python3 \"$HOME\"/.claude/fbk-scripts/fbk.py task-completed"
```

### Context asset reference map

Every script reference across all context assets must update to the dispatcher. The current codebase uses three inconsistent path conventions (relative `.claude/...`, `~/.claude/...`, and `"$HOME"/.claude/...`). All standardize to the `"$HOME"` form.

**`assets/skills/fbk-spec/SKILL.md`** (1 reference):
- Line 37: `.claude/hooks/fbk-sdl-workflow/spec-gate.sh <spec-path>` → `python3 "$HOME"/.claude/fbk-scripts/fbk.py spec-gate <spec-path>`

**`assets/skills/fbk-spec-review/SKILL.md`** (2 references):
- Line 21: `.claude/hooks/fbk-sdl-workflow/spec-gate.sh ai-docs/...` → `python3 "$HOME"/.claude/fbk-scripts/fbk.py spec-gate ai-docs/...`
- Line 69: `.claude/hooks/fbk-sdl-workflow/review-gate.sh \` → `python3 "$HOME"/.claude/fbk-scripts/fbk.py review-gate \`

**`assets/skills/fbk-breakdown/SKILL.md`** (3 references):
- Line 22: `.claude/hooks/fbk-sdl-workflow/review-gate.sh \` → `python3 "$HOME"/.claude/fbk-scripts/fbk.py review-gate \`
- Line 75: `.claude/hooks/fbk-sdl-workflow/task-reviewer-gate.sh "ai-docs/..."` → `python3 "$HOME"/.claude/fbk-scripts/fbk.py task-reviewer-gate "ai-docs/..."`
- Line 83: `.claude/hooks/fbk-sdl-workflow/breakdown-gate.sh \` → `python3 "$HOME"/.claude/fbk-scripts/fbk.py breakdown-gate \`

**`assets/skills/fbk-implement/SKILL.md`** (1 reference):
- Line 29: `.claude/hooks/fbk-sdl-workflow/breakdown-gate.sh \` → `python3 "$HOME"/.claude/fbk-scripts/fbk.py breakdown-gate \`

**`assets/skills/fbk-code-review/SKILL.md`** (3 references):
- Line 83: `uv run "$HOME/.claude/scripts/fbk-pipeline.py" run --preset <preset> --min-severity <threshold>` → `python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline run --preset <preset> --min-severity <threshold>`
- Line 85: `uv run "$HOME/.claude/scripts/fbk-pipeline.py" validate` → `python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline validate`
- Line 87: `uv run "$HOME/.claude/scripts/fbk-pipeline.py" to-markdown` → `python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline to-markdown`

**`assets/skills/fbk-council/SKILL.md`** (22 references):
- Lines 91, 527, 534: `python3 ~/.claude/skills/fbk-council/session-manager.py` → `python3 "$HOME"/.claude/fbk-scripts/fbk.py session-manager`
- Lines 92, 376, 730, 733, 734, 737, 740, 743, 744, 747, 750, 753, 756, 759, 760, 763, 772: `python3 ~/.claude/skills/fbk-council/session-logger.py` → `python3 "$HOME"/.claude/fbk-scripts/fbk.py session-logger`
- Line 685: inline reference `session-logger.py self-eval` → `fbk.py session-logger self-eval`
- Line 707: `**Logger location**: ~/.claude/skills/fbk-council/session-logger.py` → `**Logger location**: "$HOME"/.claude/fbk-scripts/fbk.py session-logger`

**`assets/skills/fbk-code-review/references/existing-code-review.md`** (1 reference):
- Line 29: `spec-gate.sh` → `python3 "$HOME"/.claude/fbk-scripts/fbk.py spec-gate`

**`assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md`** (2 references):
- Line 99: `uv run fbk-pipeline.py run --preset <preset>` → `python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline run --preset <preset>`
- Line 103: `uv run fbk-pipeline.py to-markdown` → `python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline to-markdown`

**`assets/fbk-docs/fbk-sdl-workflow/verify-yml-schema.md`** (1 reference):
- Line 35: `bash .claude/hooks/fbk-sdl-workflow/test-hash-gate.sh ai-docs/$FEATURE/` → `python3 "$HOME"/.claude/fbk-scripts/fbk.py test-hash-gate ai-docs/$FEATURE/`

**`assets/fbk-docs/fbk-sdl-workflow/corrective-workflow.md`** (1 reference):
- Line 51: `.claude/hooks/fbk-sdl-workflow/task-reviewer-gate.sh` → `python3 "$HOME"/.claude/fbk-scripts/fbk.py task-reviewer-gate`

**`assets/settings.json`** (1 reference):
- Line 8: `"$HOME"/.claude/hooks/fbk-sdl-workflow/task-completed.sh` → `python3 "$HOME"/.claude/fbk-scripts/fbk.py task-completed`

**Total: 38 references across 11 files.**

### Integration seam declaration

- [ ] All 38 context asset references → dispatcher: path convention standardized to `python3 "$HOME"/.claude/fbk-scripts/fbk.py <command>` — no relative paths, no `~` shorthand
- [ ] settings.json hook commands → dispatcher: command string format, stdin/stdout/exit-code contract
- [ ] SKILL.md gate invocations → dispatcher: argument order and output format (JSON on stdout, errors on stderr, exit code 0/2)
- [ ] SKILL.md council script invocations → dispatcher: argument interface and JSON output format
- [ ] SKILL.md code-review pipeline invocations → dispatcher: `run`, `validate`, `to-markdown` subcommands with `--preset` and `--min-severity` flags
- [ ] fbk.gates.* → fbk.audit: `log_event()` function signature replacing subprocess call convention
- [ ] Installer file enumeration → assets/fbk-scripts/ directory: installer copies all files; no additional install step required. Note: existing installations retain old hook command until upgrade — `merge-settings.py` deduplication may create duplicate hooks (see R-05 in review)
- [ ] tests/sdl-workflow/ → dispatcher: 14 test scripts update path variables from direct script paths to `python3 fbk.py <command>` invocation; test assertions unchanged
- [ ] tests/installer/ → assets/fbk-scripts/: 4 test scripts update mock file creation from `hooks/fbk-sdl-workflow/task-completed.sh` to `fbk-scripts/` structure; settings.json assertions update to new command format
- [ ] tests/sdl-workflow/ integration tests → context assets: 5 tests update grep patterns to match new dispatcher references in SKILL.md and fbk-docs

### Files removed after migration

- `assets/hooks/fbk-sdl-workflow/spec-gate.sh`
- `assets/hooks/fbk-sdl-workflow/review-gate.sh`
- `assets/hooks/fbk-sdl-workflow/breakdown-gate.sh`
- `assets/hooks/fbk-sdl-workflow/task-reviewer-gate.sh`
- `assets/hooks/fbk-sdl-workflow/test-hash-gate.sh`
- `assets/hooks/fbk-sdl-workflow/task-completed.sh`
- `assets/hooks/fbk-sdl-workflow/dispatch-status.sh`
- `assets/hooks/fbk-sdl-workflow/audit-logger.py`
- `assets/hooks/fbk-sdl-workflow/config-loader.py`
- `assets/hooks/fbk-sdl-workflow/state-engine.py`
- `assets/scripts/fbk-pipeline.py`
- `assets/skills/fbk-council/session-logger.py`
- `assets/skills/fbk-council/session-manager.py`
- `assets/skills/fbk-council/ralph-council.py`
- `assets/config/fbk-presets.json`

The `assets/hooks/`, `assets/scripts/`, and `assets/config/` directories become empty and are removed. `assets/skills/fbk-council/` retains `SKILL.md` only.

### Installer interaction

The existing installer uses `find "$SOURCE_DIR" -type f` to enumerate assets and copies them preserving directory structure. The new `assets/fbk-scripts/` directory is automatically discovered and copied to `~/.claude/fbk-scripts/`. No installer code changes are needed.

### Cross-platform compatibility

`session-manager.py` uses `fcntl.flock()` for file locking, which is Unix-only. The conversion introduces a platform-conditional locking abstraction:

```python
import sys

if sys.platform == "win32":
    import msvcrt
    def lock_file(f):
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
    def unlock_file(f):
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl
    def lock_file(f):
        fcntl.flock(f, fcntl.LOCK_EX)
    def unlock_file(f):
        fcntl.flock(f, fcntl.LOCK_UN)
```

This lives in `fbk.council.session_manager` (the only module that uses file locking). If other modules need locking in the future, extract to a shared `fbk._compat` module.

Additionally, `session-logger.py` uses `os.chmod(path, 0o600)` which is a no-op on Windows but does not crash — no change needed.

### PyYAML handling

Only two modules require PyYAML: `fbk.config` (config loading) and `fbk.gates.task_reviewer` (frontmatter parsing). All other modules use stdlib only.

Modules that import `yaml` use a try/except at import time and fail with a clear error message if PyYAML is not installed:

```python
try:
    import yaml
except ImportError:
    print("Error: PyYAML required. Install: pip install pyyaml", file=sys.stderr)
    sys.exit(2)
```

This keeps all modules functional without PyYAML except the two that genuinely need it.

## Testing strategy

### New tests needed

- Unit test: `fbk.gates.spec` `check_section()` returns failure for missing/empty sections — covers AC-01, AC-08
- Unit test: `fbk.gates.spec` `check_open_questions()` detects bare questions without rationale — covers AC-01, AC-08
- Unit test: `fbk.gates.spec` injection detection returns warning count for control characters, zero-width chars, HTML comments, and embedded instructions — covers AC-01, AC-08
- Unit test: `fbk.gates.review` validates perspective coverage, severity tags, and threat model determination — covers AC-01, AC-08
- Unit test: `fbk.gates.breakdown` validates AC coverage, DAG acyclicity, wave ordering, test-before-impl, and file scope conflicts — covers AC-01, AC-08
- Unit test: `fbk.gates.task_reviewer` validates frontmatter fields, AC coverage, and file scope conflicts — covers AC-01, AC-08
- Unit test: `fbk.gates.test_hash` creates manifest on first run and detects modifications on subsequent runs — covers AC-01, AC-08
- Unit test: `fbk.hooks.task_completed` detects test runners and linters for each supported project type — covers AC-01, AC-08
- Unit test: `fbk.hooks.dispatch_status` formats state output correctly for each pipeline state — covers AC-01, AC-08
- Unit test: `fbk.audit` `log_event()` appends structured JSON line to log file — covers AC-02
- Unit test: `fbk.config` `load_config()` merges layered configs with correct precedence — covers AC-02
- Unit test: `fbk.state` `transition_state()` enforces valid transitions and rejects invalid ones — covers AC-02
- Unit test: `fbk.pipeline` validates type-severity combinations — covers AC-02
- Integration test: dispatcher resolves every command in the command map without import errors — covers AC-03, AC-04
- Integration test: dispatcher rejects Python < 3.11 with exit code 2 and clear error message — covers AC-04
- Integration test: `python3 fbk.py spec-gate <valid-fixture>` produces `{"gate":"spec","result":"pass",...}` on stdout and exits 0 — covers AC-08
- Integration test: `python3 fbk.py spec-gate <invalid-fixture>` produces failure messages on stderr and exits 2 — covers AC-08
- Integration test: `python3 fbk.py review-gate <valid-fixture> <perspectives>` produces correct pass/fail — covers AC-08
- Integration test: `python3 fbk.py state create <name>` creates state file and outputs valid JSON — covers UV-3
- Integration test: `python3 fbk.py session-logger init <id> --tier quick --task "test"` creates session log at expected location — covers UV-5
- Integration test: `python3 fbk.py session-manager register <id> quick` creates a session registry entry for `<id>`; `python3 fbk.py session-manager unregister <id>` removes the entry and the registry contains no record for `<id>` — covers AC-02, UV-5
- Integration test: `assets/settings.json` contains `python3 "$HOME"/.claude/fbk-scripts/fbk.py task-completed` — covers AC-05
- Integration test: grep all 11 context asset files for old path patterns (`hooks/fbk-sdl-workflow`, `scripts/fbk-pipeline`, `uv run.*pipeline`, `~/.claude/skills/fbk-council`); assert zero matches — covers AC-06
- Integration test: `assets/skills/fbk-council/SKILL.md` contains `python3 "$HOME"/.claude/fbk-scripts/fbk.py session-manager` and `python3 "$HOME"/.claude/fbk-scripts/fbk.py session-logger`; assert no `~/.claude/skills/fbk-council/` script references — covers AC-06
- Integration test: assert `assets/hooks/fbk-sdl-workflow/` contains no `.sh` or `.py` files; assert `assets/scripts/` is empty or absent; assert `assets/skills/fbk-council/` contains no `.py` files — covers AC-07
- Unit test: patch `yaml` as unimportable in `fbk.config`, verify exit code 2 and stderr contains "PyYAML required" — covers AC-09
- E2e test: `python3 fbk.py spec-gate <fixture>` produces the same JSON output and exit code as the original `bash spec-gate.sh <fixture>` for 3 test fixtures (valid spec, spec with missing sections, spec with injection markers) — covers UV-1, UV-2
- E2e test: `python3 fbk.py breakdown-gate <fixture-spec> <fixture-tasks>` produces the same pass/fail result as the original bash script — covers UV-1, UV-2
- UV-4 (full SDL pipeline run) is manual verification only — requires a live Claude Code session with skills loaded. Cannot be automated without a full Claude Code test harness.

### Existing tests impacted

**Tests that directly invoke scripts being moved (14 tests)** — These hardcode paths to the scripts under test. Each must update its path variable to invoke through the dispatcher.

Non-pipeline tests (7) — path variable update only:

- `tests/sdl-workflow/test-audit-logger.sh` — `LOGGER="$PROJECT_ROOT/assets/hooks/fbk-sdl-workflow/audit-logger.py"` → `python3 "$PROJECT_ROOT/assets/fbk-scripts/fbk.py" audit`
- `tests/sdl-workflow/test-config-loader.sh` — `LOADER="$PROJECT_ROOT/assets/hooks/fbk-sdl-workflow/config-loader.py"` → `python3 "$PROJECT_ROOT/assets/fbk-scripts/fbk.py" config`
- `tests/sdl-workflow/test-hash-gate.sh` — `GATE="$PROJECT_ROOT/assets/hooks/fbk-sdl-workflow/test-hash-gate.sh"` → `python3 "$PROJECT_ROOT/assets/fbk-scripts/fbk.py" test-hash-gate`
- `tests/sdl-workflow/test-state-engine.sh` — `ENGINE="$PROJECT_ROOT/assets/hooks/fbk-sdl-workflow/state-engine.py"` → `python3 "$PROJECT_ROOT/assets/fbk-scripts/fbk.py" state`
- `tests/sdl-workflow/test-spec-validator.sh` — `GATE="$PROJECT_ROOT/assets/hooks/fbk-sdl-workflow/spec-gate.sh"` → `python3 "$PROJECT_ROOT/assets/fbk-scripts/fbk.py" spec-gate`
- `tests/sdl-workflow/test-status-command.sh` — `CMD="$PROJECT_ROOT/assets/hooks/fbk-sdl-workflow/dispatch-status.sh"` → `python3 "$PROJECT_ROOT/assets/fbk-scripts/fbk.py" dispatch-status`
- `tests/sdl-workflow/test-task-reviewer.sh` — `GATE="$PROJECT_ROOT/assets/hooks/fbk-sdl-workflow/task-reviewer-gate.sh"` → `python3 "$PROJECT_ROOT/assets/fbk-scripts/fbk.py" task-reviewer-gate`

Pipeline tests (7) — invocation pattern change across 60+ lines. Every `uv run "$PIPELINE" <subcommand>` becomes `python3 "$DISPATCHER" pipeline <subcommand>`. Additionally, `test-pipeline-validate.sh` Test 1 (file existence check at old path) must change to verify the dispatcher and `fbk/pipeline.py` exist instead:

- `tests/sdl-workflow/test-pipeline-validate.sh`
- `tests/sdl-workflow/test-pipeline-run.sh`
- `tests/sdl-workflow/test-pipeline-severity-filter.sh`
- `tests/sdl-workflow/test-pipeline-domain-filter.sh`
- `tests/sdl-workflow/test-pipeline-to-markdown.sh`
- `tests/sdl-workflow/test-pipeline-integration.sh`
- `tests/sdl-workflow/test-type-severity-matrix.sh`

**Integration tests that check string references in context assets (5 tests)** — These grep SKILL.md or fbk-docs files for specific script names. Assertions must update to match the new dispatcher-based references. Note: regex patterns may need redesign, not just string swaps (e.g., `pipeline\.py|uv run` must change to match `fbk\.py.*pipeline|python3`).

- `tests/sdl-workflow/test-guide-precision-alignment.sh` — Test 11 greps for `pipeline\.py|uv run`; regex must change to match dispatcher format (e.g., `fbk\.py.*pipeline`)
- `tests/sdl-workflow/test-orchestrator-pipeline-integration.sh` — Test 1 checks SKILL.md for `fbk-pipeline.py`; Test 2 explicitly asserts `uv run` presence. Both assertions change: Test 1 matches `fbk.py`, Test 2 matches `python3` instead of `uv run`
- `tests/sdl-workflow/test-breakdown-integration.sh` — checks SKILL preserves `breakdown-gate` invocation; string still present in dispatcher format
- `tests/sdl-workflow/test-code-review-integration.sh` — checks existing-code-review.md references `spec-gate`; string still present in dispatcher format
- `tests/sdl-workflow/test-review-integration.sh` — checks SKILL references `review-gate`; string still present in dispatcher format

**Installer tests (4 tests + 1 fixture)** — These create mock source structures and verify install/uninstall behavior. The mock directory layout, file existence assertions, and settings.json command strings all change.

- `tests/installer/test-install.sh` — `setup_mock_source()` creates `assets/hooks/fbk-sdl-workflow/task-completed.sh` → must create `assets/fbk-scripts/fbk.py` instead; Test 1 asserts `[ -f "$TARGET/hooks/fbk-sdl-workflow/task-completed.sh" ]` → assert `[ -f "$TARGET/fbk-scripts/fbk.py" ]`; settings.json command string changes
- `tests/installer/test-upgrade-uninstall.sh` — same mock structure change; Test 5 checks `task-completed.sh` absence after uninstall → check `fbk-scripts/` absence; Test 10 checks `hooks/fbk-sdl-workflow` directory removal → check `fbk-scripts/` removal
- `tests/installer/test-e2e-lifecycle.sh` — same mock structure change; Test assertion at line 108 changes from `task-completed.sh` presence to `fbk-scripts/fbk.py` presence
- `tests/installer/test-json-merge-hooks.sh` — Test 1 checks for `fbk-sdl-workflow/task-completed.sh` in merge output → check for `fbk-scripts/fbk.py task-completed`; Test 4 hardcodes old command inline → update command string
- `tests/fixtures/installer/firebreak-settings.json` — update command from `task-completed.sh` path to `python3 ... fbk.py task-completed`

**Preset config test (1 test)** — Hardcodes path to `assets/config/fbk-presets.json` which is being relocated to `fbk-scripts/fbk/data/fbk-presets.json`:

- `tests/sdl-workflow/test-preset-config.sh` — `PRESETS="$PROJECT_ROOT/assets/config/fbk-presets.json"` → `PRESETS="$PROJECT_ROOT/assets/fbk-scripts/fbk/data/fbk-presets.json"`

**Benchmark tests (2 tests — not directly impacted, include for awareness)**:

- `tests/sdl-workflow/test-benchmark-infrastructure.sh` — Test 12 greps `run_reviews.sh` for `pipeline.py|uv run`. This checks benchmark infrastructure, not Firebreak scripts. `run_reviews.sh` is not being migrated, so this test likely passes unchanged. No action required unless `run_reviews.sh` is updated separately.
- `tests/sdl-workflow/test-inject-script.sh` — uses `uv run` for `inject_results.py` in `ai-docs/`. This script is benchmark tooling, not Firebreak. No action required.

### Test infrastructure changes

- Add `pytest` as a dev dependency in `pyproject.toml` under `[dependency-groups]`
- Create `tests/` directory in `assets/fbk-scripts/` with `conftest.py` for the new Python unit tests
- Create test fixtures: sample spec files (valid, missing sections, with injections), sample task.json, sample review files, sample state files
- For development: `pip install -e ".[dev]"` or `pip install pytest pyyaml` provides the test environment
- Update 23 existing bash test scripts and 1 fixture to reference the new dispatcher paths (7 pipeline tests require invocation pattern changes across 60+ lines, not just path variable updates)

### User verification steps

- UV-1: Run `python3 assets/fbk-scripts/fbk.py spec-gate ai-docs/<any-existing-spec>/<spec>-spec.md` → gate produces pass/fail JSON output identical to current `bash assets/hooks/fbk-sdl-workflow/spec-gate.sh <same-spec>`
- UV-2: Run `python3 assets/fbk-scripts/fbk.py spec-gate /dev/null` → exits with code 2 and descriptive error on stderr
- UV-3: Run `python3 assets/fbk-scripts/fbk.py state create test-feature` → creates state file and outputs JSON
- UV-4: Run full SDL pipeline (`/spec` → gate pass) with the new scripts in place → pipeline completes without errors
- UV-5: Run `python3 assets/fbk-scripts/fbk.py session-logger init test-session --tier quick --task "test"` → session log created at expected location

## Documentation impact

### Project documents to update

- `CHANGELOG.md` — Add entry under 0.4.0: "Converted all bash hook scripts to Python; consolidated into `fbk-scripts/` with single dispatcher entry point"
- `README.md` — Add Python 3.11+ and PyYAML to prerequisites; update any script invocation examples
- `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md` — Update `uv run fbk-pipeline.py run` and `uv run fbk-pipeline.py to-markdown` references to dispatcher invocation
- `assets/fbk-docs/fbk-sdl-workflow/verify-yml-schema.md` — Update `bash .claude/hooks/fbk-sdl-workflow/test-hash-gate.sh` example to dispatcher invocation
- `assets/fbk-docs/fbk-sdl-workflow/corrective-workflow.md` — Update `.claude/hooks/fbk-sdl-workflow/task-reviewer-gate.sh` reference to dispatcher invocation
- `assets/skills/fbk-code-review/references/existing-code-review.md` — Update `spec-gate.sh` reference to dispatcher invocation

### New documentation to create

None — the dispatcher prints available commands with `python3 fbk.py` (no args), and each subcommand supports `--help` via argparse. Existing SKILL.md files are updated in-place.

## Acceptance criteria

- AC-01: All 7 bash hook scripts (`spec-gate.sh`, `review-gate.sh`, `breakdown-gate.sh`, `task-reviewer-gate.sh`, `test-hash-gate.sh`, `task-completed.sh`, `dispatch-status.sh`) are converted to Python modules in `assets/fbk-scripts/fbk/`
- AC-02: All existing Python modules (`audit-logger.py`, `config-loader.py`, `state-engine.py`, `fbk-pipeline.py`, `session-logger.py`, `session-manager.py`, `ralph-council.py`) are relocated into the same project
- AC-03: `fbk.py` dispatcher maps all 14 commands to their modules and resolves imports via `sys.path` relative to `__file__`
- AC-04: Every command in the dispatcher is callable via `python3 fbk.py <command>` without import errors
- AC-05: `assets/settings.json` hook commands use `python3 "$HOME"/.claude/fbk-scripts/fbk.py <command>` format
- AC-06: All 38 script references across 11 context asset files are updated to use `python3 "$HOME"/.claude/fbk-scripts/fbk.py <command>` — no relative paths, no `~` shorthand, no `uv run`
- AC-07: No bash scripts or Python modules remain at the old locations (`assets/hooks/fbk-sdl-workflow/*.sh`, `assets/hooks/fbk-sdl-workflow/*.py`, `assets/scripts/*.py`, `assets/skills/fbk-council/*.py` excluding SKILL.md)
- AC-08: Gate scripts produce identical JSON output (stdout) and exit codes for the same inputs — behavioral parity with the bash originals
- AC-09: Modules that require PyYAML fail with a clear error message and exit code 2 if PyYAML is not installed
- AC-10: All existing tests (23 bash test scripts in `tests/sdl-workflow/` and `tests/installer/`, plus `tests/fixtures/installer/firebreak-settings.json`) pass after path updates

## Open questions

## Dependencies

- **Python** (>= 3.11) — required on target machines at runtime
- **PyYAML** (>= 6.0) — required by `fbk.config` and `fbk.gates.task_reviewer`; already an implicit dependency of the current bash scripts. Installed via `pip install pyyaml`
