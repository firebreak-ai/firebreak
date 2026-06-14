# Spec: Deterministic Metrics Plane (Hook Harvesting)

Feature directory: `ai-docs/hook-harvesting/`
Upstream artifacts: `prd.md`, `behavior-inventory.yaml`, `design-manifest.md`, `design/*.md`, `design/contracts.md`.

This spec transcribes the approved design into an implementable contract and resolves the two items the design flagged for spec time: where the report command and token harvester live, and how the injector's retrospective path reconciles with the agent's. Both are settled below. The design's interface contracts (the `IF-D-NN` entries in `design/contracts.md`) are the authority for exact signatures; this spec references them rather than restating them.

---

## Problem

Firebreak's only performance record today is the retrospective markdown, which an agent appends by hand at the end of a development cycle. That record is anecdotal (narrated outcomes, no rates or denominators), unreliable (an instruction that erodes exactly in the long, error-prone sessions where measurement matters most), and not queryable (a paragraph cannot answer "what fraction of gate attempts passed on the first try in the last five cycles?"). The consequence is that the queue of features meant to reduce rework cannot be evaluated before and after they ship — improvement claims stay stories instead of evidence, and the only way to detect whether a harness change helped is a full benchmark run. The feature gives Firebreak a measurement plane that records pipeline facts from code, aggregates them into a table, and writes that table into the retrospective deterministically, so the agent interprets numbers it no longer has to construct from memory.

## Goals / Non-goals

**Goals**

- Capture pipeline events deterministically, from code, without relying on an agent to record them.
- Record the outcome of every gate attempt, park, verification run, code-review detection round, and subagent completion with enough precision to compute rates and ratios, not just lists.
- Harvest token spend per stage from session transcripts after the fact, joined to stages via the state engine's existing timestamps.
- Produce a report runnable at any point in a cycle for a spot check, and inject that report into the retrospective from code without agent involvement.
- Keep capture invisible to normal operation: no stdout, no broken tool calls, no pipeline command interrupted by a capture failure.
- Gate capture to projects that have opted in, so the globally-installed router records nothing in unrelated projects.

**Non-goals**

- No live telemetry collector — no streaming pipeline, no OpenTelemetry, no central server.
- No change to the agent's narrative role in the retrospective. The agent still writes interpretive prose; this feature adds the machine-written table it interprets. No agent-side recording instruction is added or removed.
- No cross-project aggregation write path. Joining data across projects is a manual sweep run outside sandboxes; the feature never writes to any shared or central location.
- No retirement of the existing per-spec audit log. Its two call sites move to the new event writer, but the old `.log` files and the `audit` module stay for backward compatibility.

## User-facing behavior

The operator here is a Firebreak developer running the SDL; the "user" surface is a command-line tool and a file on disk, not a GUI.

- **Run the report any time.** `python3 fbk.py report <spec>` prints a metrics table for the named spec. Run mid-cycle it shows partial rows (only stages that have run); run at the end it shows the full picture. No flag, mode, or stage requirement is needed to invoke it.
- **Read the table in the retrospective.** After each working stage completes, a metrics block for that stage appears in `ai-docs/<spec>/<spec>-retrospective.md` under a heading like `## IMPLEMENTING — metrics`, opened by an HTML-comment provenance marker. The agent's interpretive prose lives under the plain `## IMPLEMENTING` heading; the two coexist, neither overwrites the other.
- **Unavailable is not zero.** When a session transcript for a cycle is missing, the tokens-per-stage row reads `unavailable`, never `0`. When no event of a kind occurred (for example, no parks), that row is legitimately empty — it exists and reflects the true count.
- **Opt a project in.** Capture runs only in a Firebreak-managed project (one with a `.claude/automation/` directory) or any project carrying a `.fbk-capture/capture.cfg` file. In every other project the globally-installed router exits immediately and records nothing. To raise a project to full capture, the operator writes `capture_level=full` into that file; the default inside a Firebreak project is `standard`.
- **Protect a baseline.** The capture file self-prunes at a size cap. Before setting up a before/after comparison, the operator drops an empty file named after the baseline spec into `.fbk-capture/locked/`; pruning never drops a locked spec's lines.
- **Failures are silent.** If a capture write fails for any reason — permissions, full disk, sandbox restriction — the operator sees nothing: no error, no stderr from the capture path on the hot router path, and the triggering tool call or pipeline command completes normally.

## Technical approach

The feature is brownfield: it extends the installed `fbk-scripts` Python package, the installer at `installer/install.sh` (and its settings-merge helper `installer/merge-settings.py` plus the `assets/settings.json` template), and it modifies the code-review skill (a context asset). A working prototype of the router, the transcript harvester, and the report aggregation exists in `ai-docs/hook-harvesting/` (`hooks/hook_router.py`, `transcript_harvest.py`, `fbk_report_prototype.py`); these are the baseline to port and harden, not a design to reproduce from scratch.

> **Spec-review corrections (2026-06-10).** The first review pass read this spec against the real source and found that several integration points were described against an idealized version of the code. The corrections are folded in below and flagged inline where they change a contract or an acceptance criterion: the real installer location and its add-only merge engine; the injection predicate firing on park as well as completion; the capture gate's reliance on a shared directory name; the router's unpinned working directory; symlink confinement; the (non-existent) "retired tests"; and a third audit call site. The threat model artifact (`hook-harvesting-threat-model.md`) carries the security analysis behind the gate-hardening and confinement changes.

### Module layout (resolved this phase)

New capture subsystem under `fbk/capture/` (a cohesive subsystem, consistent with the existing `fbk/gates/` and `fbk/hooks/` subpackages):

- `fbk/capture/event_writer.py` — the single append path to `.fbk-capture/events.jsonl` (contract: the event-writer entry, `IF-D-02`).
- `fbk/capture/schema.py` — envelope shape, the closed event-type vocabulary, the build/test-time drift check, and the writer's runtime discard-unknown (contract: the event-envelope entry, `IF-D-01`).
- `fbk/capture/gate_check.py` — the per-project capture gate and capture-level resolver (contract: the capture-gate entry, `IF-D-03`).
- `fbk/capture/retention.py` — the size-cap pruner with baseline locks (contract: the retention-pruner entry, `IF-D-08`).
- `fbk/capture/known_agents.py` — the known-Firebreak-agent set derived from installed persona files (contract: the known-agent-set entry, `IF-D-10`).
- `fbk/capture/hook_router.py` — the standalone globally-installed router.
- `fbk/capture/chokepoint.py` — the dispatch wrapper (contract: the chokepoint entry, `IF-D-04`).
- `fbk/capture/token_harvester.py` — the post-hoc transcript reader, ported from the prototype's `harvest_session()`.
- `fbk/capture/retro_injector.py` — the per-stage retrospective injector (contract: the stage-summary-and-injection entry, `IF-D-07`).

The report command lives flat as `fbk/report.py`, matching the existing flat single-command convention (`pipeline.py`, `config.py`, `state.py`, `retro.py`), and is registered in `COMMAND_MAP` as `report`. The token harvester sits inside `fbk/capture/` because it is part of the capture subsystem even though it only reads. *(Decision resolved this phase — see "Decisions resolved during scoping.")*

### Data flow

Five producers write through one writer into one shared stream; a sixth source is derived at read time and produces no events.

- The **hook router** (`hook_router.py`) is a standalone script fired by Claude's hook runtime, not routed through `fbk.py` (routing it through the dispatcher would require the dispatcher to instrument itself before loading). On each invocation it reads the hook event from stdin, resolves **one** working directory (see "router working-directory pinning" below), runs the capture gate against that directory, resolves the level, assembles an envelope for the Claude-level event, filters subagent events by agent identity, writes the event **under that same resolved directory**, and exits `0`. It never writes to stdout and never raises. At `standard` it strips tool-call payloads and prompt text; at `full` it records them.
  - **Router working-directory pinning** *(review correction)*: the router gates and writes against a single resolved path, and the two must be identical (AC-21). The prototype read the directory from the hook payload (`payload['cwd']`) for the stage and from `$CLAUDE_PROJECT_DIR` for the write — a divergence that lets the gate evaluate one project while the write lands in another. The ported router pins one source with explicit precedence (`os.getcwd()` as the authority; `$CLAUDE_PROJECT_DIR`/`payload['cwd']` are not silently trusted over it), gates that path, and writes only under it.
  - **Router process path bootstrap** *(review correction)*: because the router runs as its own process by absolute path — not through `fbk.py`, which is where `sys.path` is set up — it must replicate `fbk.py`'s bootstrap (insert the fbk-scripts dir and the venv site-packages onto `sys.path`) before importing `fbk.capture.*`, or its imports fail in production while passing in tests. This bootstrap is part of the hook-router slice.
- The **dispatch chokepoint** (`chokepoint.py`) wraps the single `module.main()` dispatch in `fbk.py` and records a `PIPELINE_COMMAND` event for every gate, hook, and state command: name, args, outcome, exit code, duration, and the gate-result payload (summarized at standard, verbatim at full). It must preserve the gates' print-JSON-then-exit contract; the mechanism is fixed in the chokepoint contract (`IF-D-04`) and reproduced under "the stdout-and-exit seam" below.
- The **verification hook** (`fbk/hooks/task_completed.py`, modified) writes a `VERIFICATION_RESULT` event — test pass/fail with failing count, lint-error count, and the list of files touched outside declared scope — as a fail-silent side effect before its existing exit. Because the hook is itself dispatched as `fbk.py task-completed`, the chokepoint also records a `PIPELINE_COMMAND` event for it; the two events are complementary (the command event records that verification ran; the verification event records what it found).
- The **code-review gate** (`fbk/gates/code_review.py`, modified) reads a new file, `.code-review-rounds.json`, that the code-review skill writes during its run, and emits a `CODE_REVIEW_ROUNDS` event (per-round raised/survived/severity, rounds-to-quiet, totals). This is a trust boundary: an agent-mediated skill writes a file a deterministic gate consumes (contract: the round-log entry, `IF-D-06`). Absent file → no event, gate logic unaffected; malformed file → no event plus a stderr warning.
- The **spec and task-reviewer gates** replace their two existing `audit.log_event` call sites with event-writer calls using the shared envelope. The old per-spec `.log` files are preserved but receive no new writes. *(Review correction: these two call sites are wrapped in bare `try/except` and are **not** asserted by any existing test, so nothing is "retired" — the slice instead adds new assertions that each gate writes a correctly-stamped envelope. A **third** live `audit.log_event` caller exists in `fbk/hooks/dispatch_status.py`; it deliberately stays on the old `audit` path — only the two gate sites migrate.)*
- **Parks and rework (`B-017`)** produce no events — the report derives them at read time from the state engine's existing error history (parks, reasons) and stage timestamps (rework = stage re-entry). This depends on the state engine retaining *repeated* stage entries (re-entry timestamps and the append-only `error_history`) rather than overwriting on re-entry; the report's rework and after-rework rows are computable only because that history is retained, and a test asserts a re-entered stage produces a non-empty rework row.

The **join key throughout is `(spec, stage)`**. The report emits one row group per stage; the per-stage injector emits one block for the stage that just completed.

**Nested seams on the state command** *(review correction)*: `fbk.py state transition` is itself a dispatched command, so a single transition runs through the chokepoint redirect *and* the in-function injector. The two are complementary (the chokepoint records the `PIPELINE_COMMAND`; the injector writes the metrics block to a file). Because the injector can run inside the chokepoint's stdout-redirect frame, the injector must never write to stdout. If the pipeline ever calls `transition_state` in-process rather than via `fbk.py`, the injector still fires but the chokepoint does not — that asymmetry is acceptable and intended.

### The stdout-and-exit seam (the hardest integration point)

Gates print a single JSON result to stdout and then raise `SystemExit` from inside `main()`, which short-circuits `with`-block and `atexit` cleanup. The chokepoint cannot rely on `run_fn()` returning normally. The fixed mechanism (contract `IF-D-04`): save the real stdout, install an in-memory buffer, call `run_fn()` inside a `try` that catches both a normal return and `SystemExit`, and in a `finally` block restore the real stdout and flush the buffered bytes to it. Only after the buffer is flushed does the wrapper write the event, then re-raise the original `SystemExit` (or return the normal result) with the same exit code. When the project is not instrumented, the wrapper calls `run_fn()` and returns directly, recording nothing. If the redirect cannot be installed or any capture step fails, the failure is discarded and the gate's output and exit code are never suppressed. `cwd` is supplied by `fbk.py` as `os.getcwd()` (the project root, where fbk is always invoked).

**Constraint this places on producers:** gates must print only their final JSON to stdout (diagnostics go to stderr), must not depend on `with`/`atexit` cleanup that a `SystemExit` would skip, and must not depend on incremental stdout flushing being visible mid-execution.

### Retrospective path reconciliation (resolved this phase)

The injector resolves the retrospective path internally from `os.getcwd()` as project root and the spec name, with no path parameter. The canonical convention — used by the retrospective skill instructions and the existing `retro.append_section` callers — is `ai-docs/<spec>/<spec>-retrospective.md`. The injector uses exactly that path, so its machine block and the agent's prose land in the same file. *(This closes the flagged item in contract `IF-D-09`.)*

### Capture levels, config, and retention

The capture level lives in a plain `key=value` file at `.fbk-capture/capture.cfg` containing one line, `capture_level=<off|standard|full>` (contract: the capture-config entry, `IF-D-05`). The presence of that file is *also* the explicit opt-in marker for a non-Firebreak project — one file is both the opt-in signal and the level declaration. This is a deliberate departure from the `.claude/automation/config.yml` surface: the gate runs on the hot path of every Claude tool call, so it does only filesystem existence checks plus one **bounded single-line read** (read one line, not the whole file, so a hostile multi-gigabyte `capture.cfg` cannot stall every tool call) — no YAML, no state-engine import. An unrecognized value is treated as `standard` with a stderr warning; an absent or unreadable file means "default for this project type." Retention is a **size cap only** (default ~5MB): when the events file exceeds the cap, the pruner drops the oldest lines, except lines whose spec has an empty lock file under `.fbk-capture/locked/`. *(Size-only, no age cap — decision resolved this phase.)*

**Capture-gate hardening** *(review corrections — full analysis in the threat model).* The gate is the single control standing between "measure my own pipeline" and "record prompts in every repo I open," so three weaknesses are closed here:

- **Firebreak-managed detection uses a Firebreak-specific marker, not a shared directory name** (AC-22). `.claude/automation/` is a shared Claude namespace; a hostile repo could ship one and trigger capture the instant the operator opens it. The gate instead keys on a Firebreak-specific marker the installer writes (a sentinel file under `.claude/automation/`, e.g. `.fbk-managed`), not the bare directory.
- **The privileged `full` level requires an out-of-tree operator signal** (AC-22, second-pass correction). Any file inside the repo working tree — including `.fbk-capture/capture.cfg` and the marker sentinel — is attacker-shippable, so an in-tree signal can never establish that the *operator* (not a cloned repo) asked for full payload capture. Git-tracked-ness is **not** a usable proxy: the writer self-creates a `*` gitignore (AC-24), so every in-tree `capture.cfg` reads as gitignored, and the correct git-index query would cost a process spawn on every tool call — outside the hot-path budget. Therefore `full` is honored **only** when an operator-controlled signal that lives outside the repo working tree corroborates it: an environment variable (e.g. `FBK_CAPTURE_LEVEL=full`) the operator sets in their session, or a marker the installer/operator places in the operator's global Claude directory keyed to the project path. The gate *reads* that signal (reading the read-only global dir or an env var is cheap and sandbox-safe — only *writes* to the global dir are forbidden). An in-tree `capture.cfg` requesting `full` without the out-of-tree corroboration is clamped to `standard`. The exact form of the out-of-tree signal is an implementation detail; the security property it must satisfy is that a repository the operator clones and opens cannot supply it. The low-harm off/standard opt-in stays in-tree: standard records no payloads (AC-26) and the events file is self-gitignored, so a repo forcing *standard* on open leaks nothing sensitive and cannot commit the file back.
- **The capture directory and config are realpath-confined under the project root** (AC-23). A symlinked `.fbk-capture/` or `capture.cfg` would let the level read and the write follow the link outside the project tree, escaping the gitignore confinement. The gate `realpath`-confines `.fbk-capture/` to a real directory under the resolved project root and refuses a symlinked `capture.cfg`, treating either as uninstrumented.
- **The writer self-creates the capture dir's gitignore** (AC-24). Because capture can begin (full, prompt text on disk) before the installer's per-project gitignore step has run — or in an explicit-marker project the installer never touched — the writer creates `.fbk-capture/.gitignore` containing `*` as part of creating the capture directory, so the directory self-confines regardless of install order or a hostile project `.gitignore`. The installer-level gitignore stays as defense in depth.

**Retention baseline-lock bound** *(review correction).* Locked lines are never pruned, and the size cap is otherwise the only bound — so a lock (writable by sandboxed agents) could grow the file without limit and exhaust the disk. The pruner therefore caps total protected bytes at a defined fraction of the size cap; past that ceiling it drops oldest locked lines too and surfaces a warning in the report (AC-25).

**Central level-based redaction** *(review correction).* The "payloads only at full" guarantee is enforced **once, in the writer** (or a shared `redact(data, level)` the schema module owns), not duplicated across the producers — so no single producer can leak by forgetting to strip. This governs tool-call arguments, prompt text, the verification hook's out-of-scope file paths, and the code-review round detail alike. A drift-style test asserts no `standard`-level record carries a free-text payload field (AC-26).

### Known-agent list and subagent filtering

`known_agents.is_known_agent()` is backed by a set derived at import time from a one-time glob over installed persona files (reading their agent-type frontmatter key), so adding an agent persona updates the filter with no separate maintenance step. The scan root is parameterizable (an argument or environment override) so a test can point it at a fixture persona directory and exercise the non-fallback branch — without that, an absent persona tree under pytest would force `STALE_FALLBACK` on every run. A hardcoded fallback covers the current agents when the scan fails, and a `STALE_FALLBACK` flag surfaces as a warning in the report. The filter applies at report aggregation time and, for the router's subagent path, at capture time; events with an empty or unrecognized agent identity are still recorded but excluded from any aggregated subagent count or result.

### Install-time registration and migration

*(Review correction: the installer is `installer/install.sh`, which delegates the settings merge to `installer/merge-settings.py` merging the `assets/settings.json` template — there is no `install.sh` under the fbk-scripts tree.)* The installer gains three changes:

1. **Register the router** for the Claude hook events by adding entries to the `assets/settings.json` template that `merge-settings.py` merges. The command must resolve to the router under the **global** fbk-scripts tree; because `install.sh`'s `sed` transform rewrites `$HOME/.claude/` to `$CLAUDE_PROJECT_DIR/.claude/` on project-scoped installs, the router command must be written in a form that resolves to the single global path on both global and project installs — otherwise the rewrite re-introduces the project-vs-global divergence the migration removes.
2. **Gitignore `.fbk-capture/`** (data, `capture.cfg`, and `locked/`).
3. **Remove any leftover project-level router registration** from the earlier capture experiment, anchored to the exact old command string, leaving every other hook entry byte-intact and idempotent across re-runs. **This is net-new logic** — `merge-settings.py`'s `merge_hooks` is today add-only (canonicalize-and-append, no removal path), so the removal is a new capability with its own home (an added removal pass in `merge-settings.py` or a dedicated migration step in `install.sh`), not an extension of the existing merge.

The human operator must apply any configuration change that Claude Code's self-modification gate prevents the agent from applying autonomously.

### Integration seams

Endpoints below use bare module/function tokens that recur in the contract entries of the Interface contracts section, so each seam maps to a named contract.

- [ ] fbk.py → chokepoint.record_dispatch: the dispatch point (`module.main()` at `fbk.py:42`) is wrapped; the command name, remaining args, the `run_fn` closure over `module.main`, and `cwd = os.getcwd()` are passed. The wrapper returns the int exit code (or re-raises `SystemExit`) that `fbk.py:43` already consumes. (contract IF-D-04)
- [ ] chokepoint → event_writer.write: the chokepoint hands a fully-assembled `PIPELINE_COMMAND` envelope to the one writer, with `spec` and `stage` stamped before handing over (the writer never imports the state engine). (contracts IF-D-04, IF-D-02, IF-D-01)
- [ ] hook_router → event_writer.write: the router assembles a Claude-level event envelope and hands it to the same writer; the `event_type` is a member of the fixed vocabulary the schema module guards (`PIPELINE_COMMAND`, `VERIFICATION_RESULT`, `CODE_REVIEW_ROUNDS`, `TOOL_USE`, `SUBAGENT_STOP`, `LIFECYCLE`). (contracts IF-D-02, IF-D-01)
- [ ] task_completed → event_writer.write: the verification hook hands a `VERIFICATION_RESULT` envelope to the writer as a fail-silent side effect before its existing exit. (contracts IF-D-02, IF-D-01)
- [ ] code-review skill → code-review gate: the skill writes `.code-review-rounds.json` in the feature directory with fields `{schema_version, spec, rounds:[{round, raised, survived, severity_breakdown}]}`; the gate reads that exact path and shape at check time, then hands a `CODE_REVIEW_ROUNDS` envelope to event_writer.write. (contracts IF-D-06, IF-D-02)
- [ ] transition_state → retro_injector.inject_stage_metrics: the state engine calls the injector inside a try/except after `save_state()`, only when **both** hold — the previous state is one of the eight working stages (those whose `VALID_TRANSITIONS` entry contains `PARKED`: `VALIDATING`, `REVIEWING`, `BREAKING_DOWN`, `TASK_REVIEWING`, `TESTING`, `TEST_REVIEWING`, `IMPLEMENTING`, `VERIFYING`) **and** the new state is not `PARKED`. The working-stage set is read from `VALID_TRANSITIONS`, not hardcoded; the call site passes the local `prev_state`, not the persisted `current_state`. *(Review correction: a working stage goes to `PARKED` on failure with the same working previous state, so keying on the previous state alone would inject a "completed" block on every park.)* (contract IF-D-07)
- [ ] retro_injector → retro.append_section: the injector passes the path `ai-docs/<spec>/<spec>-retrospective.md` (resolved from `os.getcwd()`) and the heading `<STAGE> — metrics`, distinct from the plain `<STAGE>` heading the skill uses for prose. (contracts IF-D-07, IF-D-09)
- [ ] report → known_agents.is_known_agent: the report consults the known-agent set for subagent aggregation and surfaces the `STALE_FALLBACK` warning when the derivation scan failed; the router consults the same set on its subagent capture path. (contract IF-D-10)
- [ ] installer → hook_router.py: the installer registers the router for the Claude hook events by merging entries into the `settings.json` template. The event names the router records are read from each payload's `hook_event_name`; the registered set covers tool use (`PreToolUse`, `PostToolUse`, `PostToolUseFailure`), prompt submission (`UserPromptSubmit`), subagent lifecycle (`SubagentStart`, `SubagentStop`), and session lifecycle (`SessionStart`, `SessionEnd`, `Stop`, `Notification`). The global install replaces the prototype's `$CLAUDE_PROJECT_DIR/hooks/hook_router.py` path with the global fbk-scripts path. (contract IF-S-03)

### Provenance marker (exact runtime value)

Each injected block opens with a marker of exactly the form `<!-- fbk-metrics stage=<STAGE> spec=<SPEC> generated=<ISO-8601> -->` (no trailing space). The success-criterion automated check matches it after stripping surrounding whitespace.

### Module touch policy

- [ ] `fbk.py`: refactor-then-extend — wrap the existing single dispatch call (`module.main()` at lines 40–43) in `chokepoint.record_dispatch`. The structural change is interposing the wrapper between `importlib.import_module` and the result/exit handling; the existing exit-code contract is preserved.
- [ ] `fbk/state.py` (`transition_state`): extend — add a guarded `inject_stage_metrics` call after `save_state()`, passing the local `prev_state`; fire only when `prev_state` is a working stage (read from `VALID_TRANSITIONS`) AND `new_state != "PARKED"`. No change to transition semantics.
- [ ] `fbk/hooks/task_completed.py`: extend — add a fail-silent `VERIFICATION_RESULT` write before the existing exit; exit codes (2 on fail, 0 on pass) unchanged.
- [ ] `fbk/gates/code_review.py`: extend — add a new read of `.code-review-rounds.json` and a `CODE_REVIEW_ROUNDS` write at check time; existing artifact-check and pass/fail logic unchanged.
- [ ] `fbk/gates/spec.py`, `fbk/gates/task_reviewer.py`: refactor-then-extend — replace the two `audit.log_event` call sites with event-writer calls using the shared envelope. The structural change is the call-site swap; the gates' pass/fail output is unchanged. New assertions cover the event-writer call (no existing test asserts the old audit call).
- [ ] `fbk/hooks/dispatch_status.py`: leave alone — a third `audit.log_event` caller; stays on the old `audit` path (only the two gate sites migrate).
- [ ] `fbk/retro.py` (`append_section`): leave alone — reused as-is by the injector. (On rework, the injector calls it twice for the same stage, producing two marked metrics blocks — intended; each pass has its own metrics, distinguished by the provenance timestamp.)
- [ ] `fbk/audit.py`: leave alone — kept for backward compatibility; no new call sites.
- [ ] `installer/install.sh` and `installer/merge-settings.py` and the `assets/settings.json` template: refactor-then-extend — add router registration to the template, capture-dir gitignore, and the net-new duplicate-registration removal (the merge engine is add-only today, so removal is new logic with its own home).
- [ ] code-review skill (context asset): extend — add an instruction to write `.code-review-rounds.json` during orchestration.

## Testing strategy

The package has an established `pytest` suite under `fbk-scripts/tests/`. Tests for new modules are unit tests against pure functions and fail-silent contracts; seam coverage is integration-level.

### New tests needed

**Event foundation**
- Unit: `event_writer.write` appends exactly one JSONL line on success and runs the prune check after append — covers the verification of the report's data source (`AC-15`).
- Unit: `event_writer.write` discards a record with an out-of-vocabulary `event_type` and warns on stderr, writing nothing — covers the schema guard (`AC-13`).
- Unit: `event_writer.write` swallows an unwritable-path / full-buffer failure, returns `None`, never raises, never writes stdout — covers fail-silent capture (`AC-11`).
- Unit: the build/test-time drift check fails when a capture module references an event type absent from the canonical vocabulary — covers schema-drift detection (`AC-13`).
- Unit: `gate_check.project_is_instrumented` returns true for a dir with `.claude/automation/`, true for a dir with `.fbk-capture/capture.cfg`, false otherwise, and false on a filesystem error — covers the per-project gate (`AC-01`).
- Unit: `gate_check.resolve_capture_level` returns the cfg value when valid, `standard` for a Firebreak project with no/invalid cfg (with stderr warning on invalid), and `off` for an uninstrumented project — covers capture-level resolution and the shipped default (`AC-09`, `AC-10`).
- Unit: `retention.prune_if_needed` drops oldest lines past the cap, never drops a line whose spec is in `protect_specs`, and leaves the file intact on any failure — covers the bounded-file and baseline-protection behavior (`AC-14`).
- Integration: a report run over an event stream that was pruned past the protected-bytes ceiling renders the over-cap warning in the table (the same way the `STALE_FALLBACK` warning surfaces), so an operator sees why locked lines were dropped — covers the report-side surfacing half of the retention bound (`AC-25`).
- Unit: `known_agents.is_known_agent` matches a known persona (scan root pointed at a fixture persona dir), rejects empty/unknown identity, and sets `STALE_FALLBACK` when the scan fails — covers subagent identity filtering (`AC-16`).

**Gate hardening and confinement** *(review additions)*
- Unit: `project_is_instrumented` returns false for a dir with `.claude/automation/` but **no** Firebreak marker sentinel, and true once the sentinel is present — covers the Firebreak-specific-marker hardening (`AC-22`).
- Unit: `resolve_capture_level` clamps an in-tree `capture.cfg` requesting `full` to `standard` when the out-of-tree operator signal is absent, and returns `full` only when the env var / global-dir marker corroborates it — covers the repo-supplied-full refusal via an out-of-tree signal a cloned repo cannot ship (`AC-22`).
- Unit: a symlinked `.fbk-capture/` directory or a symlinked `capture.cfg` is refused — the gate treats the project as uninstrumented and the writer never follows the link outside the realpath-confined project root — covers symlink confinement (`AC-23`).
- Unit: the writer, on first creating `.fbk-capture/`, writes `.fbk-capture/.gitignore` containing `*` — covers gitignore self-creation independent of installer order (`AC-24`).
- Unit: `prune_if_needed` with locked lines exceeding the protected-bytes ceiling drops oldest locked lines too and the report surfaces the over-cap warning, so a lock cannot grow the file unbounded — covers the retention baseline-lock bound (`AC-25`).
- Unit (central redaction): across every producer, no `standard`-level record carries a free-text payload field (tool args, prompt text, scope-violation paths, or round detail). The producer enumeration is **derived dynamically** — from the same source the event-type drift check uses (the registered sources in the schema module), not a hand-maintained list — so a new producer that skips the central writer is caught rather than silently invisible. Covers central level-based redaction (`AC-26`).
- Unit (overhead budget): `project_is_instrumented` on an uninstrumented `tmp_path` completes within a generous wall-clock upper bound (e.g. under 100ms, well inside the PRD's "well under a second" budget), measured by the test harness's own timer — gives the no-ambient-overhead claim a falsifiable threshold rather than an assertion. Because wall-clock assertions can flake on shared CI, this test is marked quarantine-on-flake (non-gating) rather than blocking the suite on a single slow run.

**Hook router**
- Integration: the router, fed a `PostToolUse` payload on stdin in an instrumented project at `standard`, writes a `TOOL_USE` event with the payload stripped, and at `full` writes it with the payload present — covers payload-only-at-full capture (`AC-08`, `AC-12`).
- Integration: the router fed any payload in an uninstrumented project writes nothing and emits no stdout — covers the uninstrumented-project exit (`AC-01`).
- Integration: the router fed a `SubagentStop` payload with an empty agent identity records the event but the report excludes it from subagent counts — covers identity filtering at capture and report time (`AC-16`).
- Integration: the router fed an event while no SDL run is active writes the event with `stage` null (not absent) — covers stage stamping outside a run (`AC-12`).
- Integration: the router writes its event under the project `cwd` (`<tmp_project>/.fbk-capture/events.jsonl`) and creates **no** file under a fixture global-config path — covers the never-write-global-dir guarantee (`AC-02`).
- Integration: the router gates and writes against the same resolved directory; given a payload whose `cwd`/`$CLAUDE_PROJECT_DIR` points elsewhere, the gate decision and the write path both follow the pinned `os.getcwd()` authority, never diverging — covers working-directory pinning (`AC-21`).
- Integration (fail-silent): the router fed a valid payload with the events path pointing at an unwritable location exits `0`, emits no stdout, and raises nothing — covers the router process's own fail-silent contract (`AC-11`, `AC-02`).

**Chokepoint**
- Integration: wrapping a stub `run_fn` that prints JSON and raises `SystemExit(0)` re-emits the JSON to the real stdout, writes one `PIPELINE_COMMAND` event, and re-raises `SystemExit(0)` — covers the stdout-and-exit seam (`AC-03`).
- Integration: the same with `SystemExit(2)` preserves exit code 2 and records outcome `fail` — covers outcome capture (`AC-03`).
- Integration: in an uninstrumented project the wrapper calls `run_fn`, returns its result, and records nothing — covers gated chokepoint (`AC-01`).
- Integration: a capture-machinery failure inside the wrapper still flushes `run_fn`'s stdout and preserves its exit code — covers fail-silent under the seam (`AC-11`).
- Integration (real producer, normal return): driving a real `fbk.py state transition` end-to-end — which prints multi-line indented JSON and returns an int rather than raising — re-emits the buffered multi-line stdout byte-for-byte, propagates the int exit code, and writes one `PIPELINE_COMMAND` event. Covers the normal-return path (every hook and the state command) and the multi-line-stdout case the stub does not exercise (`AC-03`).

**Verification persistence**
- Integration: `task_completed`, fed a completion payload with failing tests and an out-of-scope file, writes a `VERIFICATION_RESULT` event carrying the failing-test count, lint-error count, and out-of-scope file list, and still exits 2 — covers verification persistence (`AC-04`).
- Integration (fail-silent): `task_completed` with an unwritable events path still exits with its normal code, emits no stdout, and raises nothing — covers the verification hook's fail-silent write (`AC-11`).

**Code-review rounds**
- Integration: the code-review gate with a valid `.code-review-rounds.json` present emits a `CODE_REVIEW_ROUNDS` event with per-round and total counts; with the file absent emits no event and its pass/fail is unchanged; with a malformed file emits no event and warns on stderr — covers round logging and its trust boundary (`AC-05`).
- Unit: a round file with an out-of-range value (non-integer or negative count), a rounds list past the max length, or a file past the max size is treated as malformed — no event, stderr warning, gate pass/fail unaffected — covers the round-log bounds (`AC-27`).

**Token harvester**
- Unit: `token_harvester` attributes a turn whose timestamp is strictly before a transition boundary to the earlier stage and a turn at-or-after to the later stage (the hard split) — covers stage attribution (`AC-06`).
- Unit: with a transcript absent or unreadable, the affected stage's token row is marked `unavailable`, never `0` — covers the unavailable-vs-zero distinction (`AC-06`, `AC-17`).
- Unit: token and tool counts from two session transcripts for one cycle aggregate into one set of per-stage totals — covers cross-session aggregation (`AC-06`).
- Unit: the harvester emits, per stage, a count of boundary-adjacent turns (turns within one transition-interval of a stage boundary) alongside the token totals, so a consumer can see how much of a stage's total sits near a boundary; the report labels tokens-per-stage as a coarse indicator — covers the cross-cycle-comparison honesty correction (`AC-06`).

**Report and state-derived rows**
- Integration: `fbk.py report <spec>` over a fixture event stream plus a fixture state file prints a table with per-stage duration, gate first-try and after-rework rates, parks-with-reasons, tasks completed/reworked, scope violations, detection rounds with raised-to-confirmed counts and kill rate, and tokens-per-stage — covers the report contract (`AC-07`).
- Unit: a gate attempt before any park for a stage classifies first-try; the first attempt after a ready re-entry classifies after-rework — covers the first-try/after-rework split (`AC-07`).
- Unit (rate arithmetic): a stage with three first-try attempts (fail, fail, pass) before any park yields the **exact** first-try pass rate the spec's formula defines (attempts that passed over first-try attempts made = 1/3), not just the label — covers the rate-denominator definition (`AC-07`).
- Unit (kill-rate value): a fixed `.code-review-rounds.json` fixture with known per-round raised/survived yields the **exact** kill-rate value `(total_raised − total_confirmed) / total_raised`, and the report renders the acknowledged-true-positive caveat label — covers the kill-rate definition and its surfaced caveat (`AC-07`).
- Unit: a park with an empty reason renders a visible "(no reason recorded)" row rather than being dropped; rework is derived from a repeated stage timestamp — covers state-derived parks/rework (`AC-17`).
- Unit (rework needs history): a fixture state file with a re-entered stage (the stage appears twice in the timestamps / `error_history`) produces a non-empty rework row and after-rework classification — guards against a regression if the state store ever became last-write-wins (`AC-17`).
- Integration (literal rendering): the report over a fixture where one stage's transcript is missing and another stage had zero parks renders the literal token `unavailable` (not `0`) in that token cell and a present-but-empty parks row — covers the unavailable-vs-zero and empty-row rendering, end to end (`AC-06`, `AC-17`).
- Integration: run mid-cycle, the report prints partial rows for stages that have run and omits the rest with no error — covers ad-hoc invocation (`AC-08`).
- Integration (empty vs absent discriminator): over a fixture distinguishing a stage that ran its parks-producing path with zero parks (row present and empty) from a stage whose producing step never executed (row absent), the report renders present-and-empty in the first case and omits the row in the second — pins the discriminator so a renderer that simply drops all-zero rows does not pass (`AC-17`).

**Retro injection**
- Integration: a `IMPLEMENTING` → `IMPLEMENTED` transition appends a metrics block under `## IMPLEMENTING — metrics` opened by the exact provenance marker, without disturbing an existing `## IMPLEMENTING` prose section — covers deterministic injection and coexistence (`AC-09`-injection, `AC-18`).
- Unit (predicate): injection fires on a working-stage → checkpoint transition (`IMPLEMENTING` → `IMPLEMENTED`); injection does **not** fire on a working-stage → `PARKED` transition (`IMPLEMENTING` → `PARKED`), nor when leaving a checkpoint state, `QUEUED`, `PARKED`, or `READY` — covers the corrected pair-keyed predicate, including the park-exclusion that the single-state predicate missed (`AC-18`).
- Integration (rework): a rework sequence (`IMPLEMENTING` → `IMPLEMENTED`, park, `READY` → `IMPLEMENTING` → `IMPLEMENTED`) injects on the first completion and again on the redone completion, producing two marked `## IMPLEMENTING — metrics` blocks distinguished by their provenance timestamps, with no injection on the intervening park or resume — covers rework injection and the intended two-block outcome (`AC-18`).
- Integration: an injector exception is swallowed and the state transition still succeeds — covers fail-silent injection (`AC-11`).

**Installer migration**
- Integration: a `settings.json` carrying a leftover project-level router registration has it removed after the install merge, leaving exactly one (global) registration; an unrelated operator-added hook entry is left byte-intact; a second installer run is idempotent (no further change); `.fbk-capture/` is gitignored — covers duplicate-registration removal, anchored and idempotent (`AC-19`).

**End-to-end seam**
- E2e: a fixture cycle producing both router events and chokepoint events yields one report table whose rows draw on both sources with consistent envelope fields — covers the cross-source join (`AC-15`, `AC-20`).
- E2e: a session run in a project that is neither Firebreak-managed nor marked produces no entries in any capture file and no router output — covers the governing privacy constraint end to end (`AC-01`).

### Existing tests impacted

- `tests/test_dispatcher.py` — covers `fbk.py`'s dispatch and exit-code handling. Two updates: the chokepoint wrap interposes between `import_module` and the result handling, so update assertions to expect the wrapped call path and confirm exit codes still propagate unchanged; **and** the command-count assertion is a hard-coded `len(COMMAND_MAP) == 18`, which registering `report` makes 19 — update the count to 19 and add `report` to the expected-commands set. *(Review correction: the original spec omitted the count-assertion impact.)*
- `tests/test_state.py` — covers `transition_state`. Add coverage for the guarded injector call; confirm existing transition assertions still pass (injection is additive and fail-silent).
- `tests/test_hooks_task_completed.py` — covers the verification hook. Confirm exit codes unchanged; add the `VERIFICATION_RESULT` side-effect assertion.
- `tests/test_gates_code_review.py` — covers the code-review gate. Confirm pass/fail unchanged when the round file is absent; add the round-event assertion when present.
- `tests/test_gates_spec.py`, `tests/test_gates_task_reviewer.py` — *(Review correction: the original spec wrongly claimed these assert the `audit.log_event` calls. Verified — neither file references `audit` or `log_event`; the real call sites sit in bare `try/except` and are untested.)* So **nothing is retired**: the call-site swap to the event writer would otherwise ship with zero coverage. These tests gain **new** integration assertions that each gate, on pass and on fail, writes a correctly-stamped envelope (run the gate, assert a line lands in the events file). Existing pass/fail assertions are unaffected.
- `tests/test_retro.py` — covers `append_section`. No change expected (the function is reused as-is); run to confirm the injector's heading does not regress append behavior.
- `tests/test_audit.py` — covers the `audit` module, which stays. No change expected; run to confirm backward compatibility.

### Test infrastructure changes

- A fixture builder for `.fbk-capture/events.jsonl` event streams (envelopes of each type) and a matching fixture state file, so report and harvester tests run against known input.
- A fixture set of session/subagent transcript files (small, hand-authored JSON) for the token harvester, including one missing/unreadable transcript to exercise the `unavailable` path.
- A temporary-project fixture (a `tmp_path` dir with/without `.claude/automation/` and `.fbk-capture/capture.cfg`) to exercise the capture gate and the router's gated paths.
- A stdin-payload helper that feeds hook-event JSON to the router process for the router integration tests.

**Mocking justifications:** none required. Every collaborator here is code we own (the writer, gate, state engine, retro module) or the real file system exercised through `tmp_path` — pytest's real-filesystem fixture, not a stand-in. Transcript and event inputs are real fixture files, not mocks. The clock is not mocked: tests assert marker *shape* and presence, not a specific timestamp value. No external service, network, or third-party side effect is involved, so there is nothing that meets the "code we don't own" bar for a stand-in.

### User verification steps

- UV-1: In a Firebreak project, run a partial SDL cycle, then `python3 fbk.py report <spec>` → a metrics table prints with rows for the stages that ran and partial/empty rows for the rest, with no error. (covers `AC-07`, `AC-08`)
- UV-2: Complete a working stage (e.g. implementation) → open `ai-docs/<spec>/<spec>-retrospective.md` and see a `## <STAGE> — metrics` section opened by the `<!-- fbk-metrics ... -->` marker, separate from any agent prose section. (covers `AC-09`-injection, `AC-18`)
- UV-3: Inspect `.fbk-capture/events.jsonl` → it contains events from both the router and the chokepoint with the same envelope fields, and the directory is gitignored. (covers `AC-15`, `AC-20`)
- UV-4: Open a non-Firebreak project with no `.fbk-capture/capture.cfg`, run any tool calls → no `.fbk-capture/` events file is created and the router produces no output. (covers `AC-01`)
- UV-5: Set `capture_level=full` in `.fbk-capture/capture.cfg`, run a tool call → the recorded `TOOL_USE` event includes the tool-call payload; with `capture_level=standard` the same event has the payload stripped. (covers `AC-08`-levels, `AC-12`)
- UV-6: Drop an empty `<spec>` file into `.fbk-capture/locked/`, then drive the events file past the size cap → the locked spec's lines survive while older unlocked lines are pruned. (covers `AC-14`)
- UV-7: In a project carrying a leftover project-level router registration, run the installer → afterward exactly one (global) registration remains and a single tool call records one event, not two. (covers `AC-19`)

**Explicit UV-to-test mapping** *(review addition).* Each UV step is backed by a named automated test above, so a regression is caught before a human runs the step:
- UV-1 → "Report and state-derived rows" mid-cycle integration test.
- UV-2 → "Retro injection" provenance-marker integration test.
- UV-3 → "End-to-end seam" two-source-join e2e test (consistent envelope fields) **plus** the installer-migration test's gitignore assertion (the two halves of UV-3's compound claim).
- UV-4 → "End-to-end seam" uninstrumented-project e2e test, plus the router's no-write-global integration test.
- UV-5 → "Hook router" standard-vs-full payload integration test.
- UV-6 → "Event foundation" retention unit test (`prune_if_needed` protect-specs), with the over-cap bound test for the lock ceiling.
- UV-7 → "Installer migration" anchored-and-idempotent integration test, including the one-event-not-two assertion.

## Documentation impact

**Project documents to update**
- `docs/architecture-overview.md` — add the capture/metrics-plane subsystem (the shared event stream, the router, the chokepoint, the report, the per-stage injection) and the governing per-project capture constraint. (The working notes for this already exist as staged edits on this branch.)
- `docs/decisions-log.md` — the design-phase decisions are already recorded under 2026-06-10; append the two spec-phase resolutions (flat report/harvester module homes; size-only retention cap).
- `GLOSSARY.md` — add entries for "capture level," "capture gate," "event envelope," "chokepoint," and "metrics plane" if not already present.
- Installer/operator documentation — document `capture.cfg` (where it lives, the three levels, how to opt a non-Firebreak project in), the `.fbk-capture/locked/` baseline-lock step, and that activating the global router is a human step because of the self-modification gate. Surface the lock step exactly where an operator sets up a before/after evaluation.
- The retrospective skill guide — note that a machine-written `## <STAGE> — metrics` section will coexist with the agent's prose section and must not be overwritten or hand-edited.

**New documentation to create**
- A short capture/metrics-plane operator section (capture levels, opt-in, baseline locks, reading the report) — may live in the README or a dedicated doc per the README-discussion rule in the project instructions.
- The code-review skill instructions gain the requirement to write `.code-review-rounds.json`; record the file's schema there for skill authors.

## Acceptance criteria

- AC-01: In a project that is neither Firebreak-managed (`.claude/automation/` absent) nor marked (`.fbk-capture/capture.cfg` absent), the router and chokepoint record nothing and the router emits no output.
- AC-02: When the gate passes, the router records Claude-level events (tool use, lifecycle, subagent stop, prompt submit) to `.fbk-capture/events.jsonl` in the project, never to the global config dir.
- AC-03: The chokepoint records one `PIPELINE_COMMAND` event per dispatched command (name, args, outcome, exit code, duration, gate-result payload) while re-emitting the command's stdout and preserving its exit code, including across a `SystemExit` raised inside `main()`.
- AC-04: After a task completes, a `VERIFICATION_RESULT` event records test pass/fail with failing-test count, lint-error count, and the list of files touched outside declared scope; the hook's exit codes are unchanged.
- AC-05: When `.code-review-rounds.json` is present and valid, the code-review gate emits a `CODE_REVIEW_ROUNDS` event with per-round raised/survived/severity and totals; when absent, no event and unchanged pass/fail; when malformed, no event plus a stderr warning.
- AC-06: The token harvester attributes each transcript turn to the stage active at its timestamp by a hard split on transition timestamps, aggregates across multiple session/subagent transcripts of one cycle into one per-stage total set, and marks a missing/unreadable transcript's rows the literal `unavailable` rather than `0`. It also emits, per stage, a count of boundary-adjacent turns (within one transition-interval of a boundary), and the report labels tokens-per-stage a coarse indicator — so a consumer can judge how much of a stage's total sits near a boundary rather than trusting an unstated cross-cycle invariance.
- AC-07: `python3 fbk.py report <spec>` prints one table aggregating all sources with at least these rows: per-stage duration; per-gate first-try and after-rework pass rates; parks per stage with reason; tasks completed and reworked; scope violations; detection rounds with raised-to-confirmed counts and kill rate; tokens per stage. Each gate rate has a defined formula — first-try rate is first-try attempts that passed over first-try attempts made, where "first-try" is every attempt before the stage's first park and "after-rework" is every attempt from the first ready re-entry onward — and the report computes the exact value, not just a label. The kill rate is `(total_raised − total_confirmed) / total_raised` and is presented as a relative trend signal, not an absolute correctness measure, with the acknowledged-true-positive caveat surfaced in the table.
- AC-08: The report command runs at any pipeline point with no special mode and produces partial rows mid-cycle; capture-level `standard` records events without tool-call payloads or prompt text, `full` records them.
- AC-09: The shipped default capture level inside a Firebreak project is `standard`; `full` requires an explicit operator action; uninstrumented projects resolve to `off` regardless of any setting. (Injection arm: a completed working stage's metrics block is written into the retrospective from code, independent of the agent.)
- AC-10: `resolve_capture_level` returns the `capture.cfg` value when valid, `standard` for a Firebreak project with an absent or invalid file (warning on invalid), and `off` for an uninstrumented project — completing using only filesystem checks plus one single-line read.
- AC-11: Any capture write failure — writer, chokepoint, verification hook, or injector — is caught and discarded; it never causes a tool call or pipeline command to fail and never emits to stdout.
- AC-12: Every event carries the full envelope fields with `spec`/`stage` null (not absent) when no SDL run is active; the event is still recorded when no stage is active.
- AC-13: Every written `event_type` is a member of the fixed vocabulary; the build/test-time drift check fails on any drift, and the writer discards an out-of-vocabulary record at runtime with a stderr warning rather than writing it.
- AC-14: The events file self-prunes by dropping oldest lines once it exceeds the size cap, and never drops a line whose spec has an empty lock file under `.fbk-capture/locked/`.
- AC-15: `.fbk-capture/events.jsonl` contains events from both the router and the chokepoint with consistent envelope fields, joinable by the report on `(spec, stage)`.
- AC-16: The report counts only subagent-completion events whose agent identity matches a known Firebreak agent; events with empty or unrecognized identity are recorded but excluded from aggregated subagent counts and results, and a stale-fallback condition surfaces as a report warning.
- AC-17: A row for which no event of a kind occurred is present and reflects the true count (for example, an empty parks row, or a park with an empty reason rendered "(no reason recorded)"); rework is derived from stage re-entry in the state timestamps.
- AC-18: Injection fires exactly when the previous state is one of the eight working stages (read from `VALID_TRANSITIONS`) **and** the new state is not `PARKED`, under the heading `<STAGE> — metrics` distinct from the agent's plain `<STAGE>` heading, opened by the exact provenance marker `<!-- fbk-metrics stage=<STAGE> spec=<SPEC> generated=<ISO-8601> -->`; it does not fire when a working stage transitions to `PARKED`, nor when leaving a checkpoint state, `QUEUED`, `PARKED`, or `READY`. A reworked stage that completes again produces a second marked block.
- AC-19: After the installer runs, no project-level router registration that would duplicate the global one remains, an unrelated operator-added hook entry is left byte-intact, a second run is idempotent, and `.fbk-capture/` is gitignored.
- AC-20: A single end-to-end cycle produces a report whose rows draw on both capture sources and the state engine, populating at minimum — for the stages that actually ran — the per-stage duration, gate first-try/after-rework, parks, tasks, scope-violation, and detection-round rows from AC-07 (tokens-per-stage populated when the transcript is present, `unavailable` otherwise); and the retrospective for that cycle contains the machine-marked metrics blocks. The provenance marker is matched by structure — the fixed prefix and field shape with the `generated=` timestamp as a free field — not by exact string equality.
- AC-21: The router resolves a single working directory and both gates and writes against that same resolved path; the gate-decision directory and the write directory are always identical, and neither silently trusts `payload['cwd']` or `$CLAUDE_PROJECT_DIR` over `os.getcwd()`.
- AC-22: Firebreak-managed detection requires a Firebreak-specific marker the installer writes (a sentinel under `.claude/automation/`), not the bare presence of `.claude/automation/`; and the `full` level is honored only when corroborated by an operator-controlled signal that lives **outside the repo working tree** (an environment variable, or a marker in the operator's global Claude directory) — an in-tree `capture.cfg` requesting `full` without that corroboration is clamped to `standard`, so a repository the operator clones and opens cannot raise capture to full.
- AC-23: The capture directory and `capture.cfg` are realpath-confined under the resolved project root; a symlinked capture directory or config is refused and the project is treated as uninstrumented, so a write never follows a link outside the project tree.
- AC-24: The writer creates `.fbk-capture/.gitignore` containing `*` when it first creates the capture directory, so the directory self-confines from version control regardless of installer order or a project's own `.gitignore`.
- AC-25: Retention caps total protected (locked) bytes at a defined fraction of the size cap; past that ceiling it drops oldest locked lines too and surfaces a warning in the report, so a baseline lock cannot grow the events file unbounded.
- AC-26: Level-based payload redaction is enforced centrally (in the writer or a shared redactor), so no `standard`-level record carries a free-text payload field — tool arguments, prompt text, scope-violation file paths, or round detail — verified across all producers.
- AC-27: The code-review round log's values are bounded — integer types, non-negative ranges, a maximum rounds-list length, and a maximum file size — and a file violating any bound is treated as malformed: no event, a stderr warning, and unchanged gate pass/fail.

## Open questions

None.

## Dependencies

- **State engine timestamps** (`fbk/state.py`) — the report and the token harvester attribute events and tokens to stages via the existing per-stage timestamps and error history. No change to these is required.
- **Retrospective append mechanism** (`fbk/retro.py`, `append_section`) — reused as-is for per-stage injection.
- **Session and subagent transcripts** — produced by Claude Code's normal operation, read post-hoc by the token harvester from the project's transcript store.
- **Global hook registration** — the router needs a hooks entry in the global Claude configuration, placed by the installer; the human operator must apply any change the self-modification gate blocks.
- **Code-review skill** (context asset) — must be updated to write `.code-review-rounds.json` during orchestration; the gate's round logging depends on it.
- **Capture-experiment prototype** (`ai-docs/hook-harvesting/hooks/hook_router.py`, `transcript_harvest.py`, `fbk_report_prototype.py`) — the validated baseline to port and harden.
- **Python 3.11+ and the existing `fbk-scripts` venv** — the package's current runtime; no new third-party dependency is introduced (the hot-path config read is deliberately dependency-free).

---

## Decisions resolved during scoping

- **Report and harvester module homes.** The report command lives flat as `fbk/report.py` (registered `report` in `COMMAND_MAP`) and the token harvester lives at `fbk/capture/token_harvester.py`, rather than the design's tentative `fbk/commands/report.py` and `fbk/harvest/token_harvester.py`. Rationale: existing single-command modules sit flat in `fbk/`; only cohesive multi-module subsystems get their own folder, and the harvester belongs to the capture subsystem. This avoids two single-file package folders and keeps the layout consistent with current convention.
- **Retention is a size cap only.** The events file self-prunes by dropping oldest lines past a ~5MB size cap, with no age cap. Rationale: the before/after-comparison use case is protected by the baseline-lock mechanism, not by recency; a second age threshold would add a tunable and a second way a forgotten baseline could vanish.
- **Retrospective path reconciliation.** The injector resolves `ai-docs/<spec>/<spec>-retrospective.md` from `os.getcwd()`, the same path the retrospective skill and existing `append_section` callers use, so the machine block and agent prose share one file. This closes the item flagged in contract `IF-D-09`.

---

## Interface contracts

All ten design contracts from `design/contracts.md` are carried unchanged; three spec-originated contracts are minted for interfaces the design described as modules but did not pin (the token harvester, the report command, and the installer migration). Signatures and full invariants are authoritative in `design/contracts.md`; entries here carry the id, name, a signature summary, the key invariant, the acceptance criteria covered, and the design anchor.

- id: IF-D-01
  name: Event envelope
  signature: One JSON object per line in `.fbk-capture/events.jsonl` with fields schema_version, event_type, timestamp, spec, stage, source, capture_level, data; fixed event_type vocabulary guarded by the schema drift check.
  invariants: event_type must be a vocabulary member; every record carries all envelope fields; spec and stage are null (not absent) when no SDL run is active; both the router and the chokepoint produce this shape so the report joins them on (spec, stage).
  covers: [AC-02, AC-12, AC-15]
  design-ref: design/contracts.md#if-d-01
- id: IF-D-02
  name: Event writer
  signature: event_writer.write(event_type, source, data, spec, stage, capture_level, events_path) appends exactly one JSONL line then runs the retention prune check.
  invariants: Consumed by the chokepoint, hook_router, task_completed verification hook, the code-review gate, and the spec and task-reviewer gates; any failure is caught and discarded, never propagated, never written to stdout; an out-of-vocabulary event_type is discarded with a stderr warning; the writer enforces level-based payload redaction centrally so no standard-level record carries a free-text payload; it creates `.fbk-capture/` and writes its files only after the directory is realpath-confirmed under the project root (so the directory-creation and the self-gitignore write themselves cannot follow a symlink out of tree), and on first creating the directory it writes a `.gitignore` containing `*`.
  covers: [AC-04, AC-11, AC-13, AC-24, AC-26]
  design-ref: design/contracts.md#if-d-02
- id: IF-D-03
  name: Per-project capture gate
  signature: gate_check.project_is_instrumented(cwd) -> bool and gate_check.resolve_capture_level(cwd) -> off|standard|full.
  invariants: instrumented only when a Firebreak-specific marker sentinel under `.claude/automation/` (not the bare directory) or a `.fbk-capture/capture.cfg` is present; resolve returns the cfg value when valid for off/standard, else standard for a Firebreak project, else off; the `full` level is honored only when an operator-controlled out-of-tree signal (an environment variable or a marker in the operator's global Claude directory) corroborates it — an in-tree cfg requesting full without it is clamped to standard, since any in-tree file is attacker-shippable and git-tracked-ness is not a usable proxy (the writer self-creates a `*` gitignore, and a git-index query would exceed the hot-path budget); the gate and the router gate-and-write against one pinned working directory (os.getcwd() authority, never silently trusting payload cwd or $CLAUDE_PROJECT_DIR), realpath-confined under the project root with symlinked dir/config refused; both complete using only filesystem checks plus one bounded single-line read (and a cheap env/global-marker read for the full corroboration; reading the read-only global dir is permitted, only writes there are forbidden) and return the safe default on any error.
  covers: [AC-01, AC-10, AC-21, AC-22, AC-23]
  design-ref: design/contracts.md#if-d-03
- id: IF-D-04
  name: Chokepoint dispatch wrapper
  signature: chokepoint.record_dispatch(command_name, args, run_fn, cwd) -> int, where cwd is supplied by fbk.py as os.getcwd().
  invariants: When instrumented, the buffered stdout is restored and re-emitted in a finally block (surviving a SystemExit raised inside run_fn) before the event is written and before return or re-raise; a SystemExit is re-raised with the same code; when not instrumented run_fn is called and returned with nothing recorded; any capture failure never suppresses run_fn output or exit code.
  covers: [AC-03]
  design-ref: design/contracts.md#if-d-04
- id: IF-D-05
  name: Capture config file
  signature: A plain text file at `.fbk-capture/capture.cfg` containing the single line capture_level=<off|standard|full>.
  invariants: Its presence with a valid level is both the explicit capture marker and the level declaration; absence means default for this project type; an unrecognized value is treated as standard with a stderr warning; no Firebreak module writes it autonomously.
  covers: [AC-08, AC-09]
  design-ref: design/contracts.md#if-d-05
- id: IF-D-06
  name: Code-review round log
  signature: A JSON file `.code-review-rounds.json` in the feature directory with schema_version, spec, and a rounds list of round, raised, survived, severity_breakdown.
  invariants: Written by the code-review skill during orchestration, before the code-review gate runs; the gate reads it at check time and emits a CODE_REVIEW_ROUNDS event; values are bounded (integer types, non-negative ranges, max rounds-list length, max file size) and a file violating any bound is treated as malformed; absent or malformed file means no event (plus a stderr warning for malformed) and unchanged pass/fail. This is the agent-to-deterministic trust boundary.
  covers: [AC-05, AC-27]
  design-ref: design/contracts.md#if-d-06
- id: IF-D-07
  name: Stage summary and retrospective injection
  signature: report.stage_summary(spec, stage) -> str and retro_injector.inject_stage_metrics(spec, completed_stage) -> None, the injector resolving the retrospective path internally from os.getcwd().
  invariants: inject_stage_metrics is called from transition_state only when the previous state is one of the eight working stages AND the new state is not PARKED, with the local prev_state passed (not the persisted current_state); it appends the block via retro.append_section under the heading STAGE — metrics, distinct from the agent's plain STAGE heading, and a reworked stage produces a second marked block; every exception inside it is caught so a failed injection never prevents the transition.
  covers: [AC-18]
  design-ref: design/contracts.md#if-d-07
- id: IF-D-08
  name: Retention pruner
  signature: retention.prune_if_needed(events_path, max_bytes, protect_specs) -> None.
  invariants: When the file exceeds max_bytes the oldest lines are dropped until under the cap, except lines whose spec is in protect_specs (the set with an empty lock file under `.fbk-capture/locked/`); protected lines are themselves capped at a defined fraction of max_bytes, past which oldest locked lines are dropped too and the report surfaces a warning, so a lock cannot grow the file unbounded; any failure is caught and leaves the file intact rather than corrupting it.
  covers: [AC-14, AC-25]
  design-ref: design/contracts.md#if-d-08
- id: IF-D-09
  name: Retrospective file path and provenance marker
  signature: The injected block's first line is exactly `<!-- fbk-metrics stage=<STAGE> spec=<SPEC> generated=<ISO-8601> -->` with no trailing space; the retrospective path resolves by convention to ai-docs/<spec>/<spec>-retrospective.md from os.getcwd().
  invariants: The path convention matches the file the retrospective skill appends to via retro.append_section, so machine block and agent prose share one file; the marker is matched by structure — the fixed prefix and field shape with the generated= timestamp as a free field, not by exact string equality — so an automated check can confirm a block was machine-written.
  covers: [AC-20]
  design-ref: design/contracts.md#if-d-09
- id: IF-D-10
  name: Known-agent set
  signature: known_agents.is_known_agent(agent_type) -> bool, backed by a set derived at import from installed persona files, with a STALE_FALLBACK flag.
  invariants: Events whose agent identity is empty or not in the set are excluded from aggregated subagent counts and results though still recorded; when the derivation scan fails the fallback set is used and STALE_FALLBACK is true, which the report surfaces as a warning; a scan failure never raises.
  covers: [AC-16]
  design-ref: design/contracts.md#if-d-10
- id: IF-S-01
  name: Post-hoc token harvester
  signature: token_harvester reads session and subagent transcripts and returns per-stage token totals by type and model plus tool-call and tool-error counts, attributing each turn by a hard split on the state engine transition timestamps.
  invariants: A turn strictly before a boundary goes to the earlier stage, at-or-after to the later; multiple sessions of one cycle aggregate into one per-stage total set; a missing or unreadable transcript marks the affected rows the literal unavailable, never zero; it also emits a per-stage count of boundary-adjacent turns so the coarse-indicator nature of tokens-per-stage is visible rather than an unstated cross-cycle invariance; it is a pure reader and never writes events.
  covers: [AC-06]
  design-ref: none
- id: IF-S-02
  name: Report command
  signature: report (fbk.py report <spec>) aggregates events.jsonl, the state engine, and the harvester output into one table with per-stage duration, first-try and after-rework gate rates, parks with reasons, tasks completed and reworked, scope violations, detection rounds with counts and kill rate, and tokens per stage.
  invariants: Runnable at any pipeline point with no special mode, producing partial rows mid-cycle; each gate rate has a defined formula (first-try = first-try attempts passed over first-try attempts made; "first-try" = before the stage's first park, "after-rework" = from the first ready re-entry), computed as an exact value not a label; the kill rate is presented as a relative trend signal with the acknowledged-true-positive caveat surfaced; a row for which no event of a kind occurred is present and reflects the true count (an empty park reason renders a visible row), distinct from a row omitted because its producing step never ran.
  covers: [AC-07, AC-17]
  design-ref: none
- id: IF-S-03
  name: Installer hook registration and migration
  signature: installer/install.sh (with installer/merge-settings.py and the assets/settings.json template) registers hook_router.py for the Claude hook events, gitignores `.fbk-capture/`, and removes any leftover project-level router registration.
  invariants: The router command resolves to the one global fbk-scripts path on both global and project installs (reconciling install.sh's $HOME-to-$CLAUDE_PROJECT_DIR sed rewrite); removal is net-new logic (merge-settings.py's merge_hooks is add-only) anchored to the exact old command string, leaving other hook entries byte-intact and idempotent across re-runs, so a single tool call records one event not two; `.fbk-capture/` (data, capture.cfg, and locked) never enters version control; a configuration change the self-modification gate blocks is left for the human operator to apply.
  covers: [AC-19]
  design-ref: none

## Slices

```yaml
slices:
  - name: event-foundation
    description: The shared event writer, the versioned envelope with its closed vocabulary and drift check plus runtime discard-unknown, the per-project capture gate and level resolver, the size-cap retention pruner with baseline locks, and the known-Firebreak-agent set.
    test-discipline: new-contract
    covers: [B-001, B-010, B-011, B-012, B-014, B-016]

  - name: hook-router
    description: The standalone globally-installed router — capture gate on the hot path, envelope assembly for Claude-level events, payload stripping by level, subagent identity filtering at capture time, stage stamping, fail-silent, exits zero, never writes stdout.
    test-discipline: new-contract
    covers: [B-002, B-013, B-016]

  - name: chokepoint-and-gate-event-logging
    description: Wrap the single fbk.py dispatch point to record a PIPELINE_COMMAND event per command via the stdout-redirect-and-flush mechanism (including the real multi-line-JSON normal-return path), summarized or verbatim by level; and move the two existing audit.log_event call sites in the spec and task-reviewer gates onto the shared event writer. No tests are retired — neither gate test asserts the old audit call (verified) — so this adds new event-writer assertions rather than retiring any.
    test-discipline: new-contract
    covers: [B-003, B-012, B-013]

  - name: verification-persistence
    description: The per-task verification hook writes a VERIFICATION_RESULT event (test pass/fail with failing count, lint-error count, out-of-scope file list) as a fail-silent side effect before its existing exit; exit codes unchanged.
    test-discipline: new-contract
    covers: [B-004]

  - name: code-review-rounds
    description: The code-review gate reads the skill-written .code-review-rounds.json at check time and emits a CODE_REVIEW_ROUNDS event (per-round raised/survived/severity, rounds-to-quiet, totals); absent file means no event and unchanged pass/fail, malformed file means no event plus a stderr warning. Includes the skill-side instruction to write the file.
    test-discipline: new-contract
    covers: [B-005]

  - name: token-harvester
    description: The post-hoc transcript reader — extracts tokens by type and model, tool calls and errors, attributes each turn to a stage by a hard split on transition timestamps, aggregates across all sessions of a cycle, and marks a missing transcript's rows unavailable rather than zero.
    test-discipline: new-contract
    covers: [B-006]

  - name: report-and-state-derived
    description: The report command aggregating all sources into one table at any pipeline point, the reusable stage_summary, first-try vs after-rework gate classification keyed on park boundaries, report-time subagent identity filtering, and the state-derived parks-with-reasons and rework rows.
    test-discipline: new-contract
    covers: [B-007, B-008, B-016, B-017]

  - name: retro-injection
    description: The per-stage retrospective injector wired into transition_state, firing only when the previous state is a working stage (predicate read from VALID_TRANSITIONS), writing a provenance-marked metrics block under the STAGE — metrics heading distinct from agent prose, fully fail-silent.
    test-discipline: new-contract
    covers: [B-009]

  - name: install-migration
    description: Installer changes — register the global router for the Claude hook events, gitignore the .fbk-capture directory, and remove any leftover project-level router registration so a previously-instrumented project cannot double-record.
    test-discipline: new-contract
    covers: [B-015]

  - name: end-to-end-seam
    description: Seam tests that a cycle producing both router and chokepoint events yields one report table with consistent envelope fields joinable on (spec, stage), and that an uninstrumented project records nothing end to end.
    test-discipline: cross-cutting
    covers: [B-001, B-012]
```
