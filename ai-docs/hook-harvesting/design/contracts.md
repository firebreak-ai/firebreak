# Contracts

This feature introduces contracts that cross process boundaries (the hook-router process writes events that a separate report process reads) and trust boundaries (an agent-mediated skill writes a file a deterministic gate reads). Each is recorded below.

## IF-D-01 — Event envelope

signature: A JSON object, one per line in `.fbk-capture/events.jsonl`, with fields: `schema_version` (string literal "1.0"), `event_type` (string, member of the fixed vocabulary below), `timestamp` (ISO-8601 UTC string), `spec` (string or null), `stage` (string or null), `source` (one of "hook_router", "chokepoint", "task_completed", "code_review"), `capture_level` (one of "standard", "full"), `data` (object, shape determined by `event_type`). Fixed `event_type` vocabulary: `PIPELINE_COMMAND`, `VERIFICATION_RESULT`, `CODE_REVIEW_ROUNDS`, `TOOL_USE`, `SUBAGENT_STOP`, `LIFECYCLE`.
invariants: Pre — `event_type` must be a member of the vocabulary; the drift check rejects any other value. Post — every record carries all envelope fields; `spec`/`stage` are null (not absent) when no SDL run is active. Error — a record whose `event_type` is outside the vocabulary is discarded by the writer with a stderr warning, never written. The format is versioned: a breaking change bumps `schema_version` and the drift check guards the vocabulary.
consumed-by: the report command, the token harvester's join, the retro injector (via the report's stage summary)
produced-by: the shared event writer (`fbk/capture/event_writer.py`)

## IF-D-02 — Event writer

signature: `write(event_type, source, data, spec, stage, capture_level, events_path) -> None`
invariants: Pre — `data` matches the per-type shape for `event_type`. Post — exactly one JSONL line is appended on success, and the retention prune check runs after the append. Error — any exception (unwritable file, full disk, sandbox restriction) is caught and discarded; the function returns None regardless and never propagates a failure to its caller. No write to stdout, ever; no write outside `events_path`.
consumed-by: the chokepoint recorder, the hook router, the modified verification hook, the modified code-review gate, the spec and task-reviewer gates
produced-by: `fbk/capture/event_writer.py`

## IF-D-03 — Per-project capture gate

signature: `project_is_instrumented(cwd: str) -> bool` and `resolve_capture_level(cwd: str) -> Literal["off","standard","full"]`
invariants: Pre — `cwd` is an arbitrary path that may not exist or may be unreadable. Post — `project_is_instrumented` returns true only when a Firebreak-specific marker sentinel under `.claude/automation/` (not the bare directory — hardened at spec time, see spec AC-22) or a `.fbk-capture/capture.cfg` is present; `resolve_capture_level` returns the value from `capture.cfg` for off/standard when present and valid, else "standard" for Firebreak-managed projects, else "off", and honors `full` only when an operator-controlled out-of-tree signal corroborates it (spec AC-22); the resolved directory is realpath-confined under the project root with symlinks refused (spec AC-23), and the router gates and writes against one pinned directory (spec AC-21). Both complete in well under a second using only filesystem existence checks plus one bounded single-line read (and a cheap env/global-marker read for full) — no YAML, no state-engine import. Error — both return their safe default (false / "off") on any filesystem error and never raise.
consumed-by: the hook router, the chokepoint recorder
produced-by: `fbk/capture/gate_check.py`

## IF-D-04 — Chokepoint dispatch wrapper

signature: `record_dispatch(command_name: str, args: list[str], run_fn: Callable[[], int | None], cwd: str) -> int`. `cwd` is supplied by `fbk.py` as `os.getcwd()` — the project root where fbk is always invoked.
invariants: Pre — `run_fn` is the gate/hook/command's `main()`, which may return an int, return None, or raise SystemExit, and which prints its JSON result to stdout before exiting. Post — when the project is instrumented, the buffered stdout is restored and re-emitted to the real stdout in a `finally` block (so it survives a `SystemExit` raised inside `run_fn`) before the event is written and before the call returns or re-raises; one `PIPELINE_COMMAND` event is written with command name, args, outcome, exit code, duration, and the gate-result payload (summarized at standard, verbatim at full); when not instrumented, `run_fn` is called and its result returned with nothing recorded. A SystemExit from `run_fn` is re-raised with the same code after the buffer is flushed. Error — if the stdout redirect cannot be installed, capture is skipped and `run_fn` is called directly; any failure in the capture machinery is discarded and never suppresses `run_fn`'s output or exit code. Constraint on producers: gates must print only their final JSON to stdout (diagnostics go to stderr), must not rely on `with`/`atexit` cleanup that a `SystemExit` would skip mattering to the caller, and must not rely on incremental stdout flushing being visible mid-execution.
consumed-by: `fbk.py` (the dispatch point)
produced-by: `fbk/capture/chokepoint.py`

## IF-D-05 — Capture config file

signature: A plain text file at `.fbk-capture/capture.cfg` containing the single line `capture_level=<off|standard|full>`.
invariants: Pre — the file is optional and is writable by the operator and by sandboxed agents (project-local, sandbox-writable, gitignored). Post — its presence with a valid level is both the explicit capture marker and the level declaration; its absence means "default for this project type." Error — an unrecognized value is treated as "standard" with a stderr warning; a malformed or unreadable file is treated as absent.
consumed-by: the capture gate (`gate_check.py`)
produced-by: the operator, or the installer at opt-in time (no Firebreak module writes it autonomously)

## IF-D-06 — Code-review round log

signature: A JSON file `.code-review-rounds.json` in the feature directory: `{ "schema_version": "1.0", "spec": <string>, "rounds": [ { "round": <int>, "raised": <int>, "survived": <int>, "severity_breakdown": <object> }, ... ] }`
invariants: Pre — written by the code-review skill during its orchestration, before the code-review gate runs. Post — the gate reads it at check time, computes total raised, total confirmed, and rounds-to-quiet, and emits a `CODE_REVIEW_ROUNDS` event. Error — if the file is absent, no event is emitted and the gate's pass/fail logic is unaffected; if present but malformed or failing schema-version/required-field validation, the gate emits no event and warns on stderr. This is the trust boundary between agent-mediated skill output and deterministic gate consumption.
consumed-by: the code-review gate (`fbk/gates/code_review.py`)
produced-by: the code-review skill (a context asset; instructions must be updated to write this file)

## IF-D-07 — Stage summary and retrospective injection

signature: `report.stage_summary(spec: str, stage: str) -> str` (returns a markdown metrics block for one completed stage, tokens excluded) and `retro_injector.inject_stage_metrics(spec: str, completed_stage: str) -> None` (the injector resolves the retrospective path internally from `os.getcwd()`; the caller passes no path)
invariants: Pre — `inject_stage_metrics` is called from `transition_state()` only when **both** hold: the previous state is one of the eight working stages (the states whose `VALID_TRANSITIONS` entry contains `PARKED`) **and** the new state is not `PARKED`. The call site passes the local `prev_state`, not the persisted `current_state`. (Keying on the previous state alone would fire on a working-stage-to-`PARKED` failure transition, injecting a "completed" block for a stage that failed — a review caught this.) Post — `stage_summary` returns a block opening with the machine provenance marker; `inject_stage_metrics` appends that block via the retrospective append function under the heading `<STAGE> — metrics`, distinct from the plain `<STAGE>` heading the skill uses for agent prose, coexisting without overwrite (a reworked stage produces a second marked block, distinguished by its provenance timestamp). Error — every exception inside `inject_stage_metrics` is caught and discarded so a failed injection never prevents the state transition from succeeding.
consumed-by: the state engine's `transition_state()` (calls the injector); the report command (reuses `stage_summary` for the full table)
produced-by: `fbk/report.py` (`stage_summary`; flat module, superseding the earlier `fbk/commands/report.py` per the spec-phase decision); `fbk/capture/retro_injector.py` (`inject_stage_metrics`). The injector's use of `stage_summary` must be a function-level import to avoid a module-load cycle (`report` imports `fbk.capture.*`; `retro_injector` imports `report`).

## IF-D-08 — Retention pruner

signature: `prune_if_needed(events_path: str, max_bytes: int, protect_specs: set[str]) -> None`
invariants: Pre — `protect_specs` is the set of spec names with an empty lock file under `.fbk-capture/locked/`. Post — when the file exceeds `max_bytes`, the oldest lines are dropped until it is under the cap, except lines whose spec is in `protect_specs`, which are never dropped. Error — any failure is caught and discarded; a failed prune leaves the file intact rather than corrupting it.
consumed-by: the event writer (called after each successful append)
produced-by: `fbk/capture/retention.py`

## IF-D-09 — Retrospective file path and provenance marker

signature: The injected block's first line is a marker of exactly the form `<!-- fbk-metrics stage=<STAGE> spec=<SPEC> generated=<ISO-8601> -->` with no trailing space; the automated check matches it after stripping surrounding whitespace. The retrospective file path is resolved by convention from the spec name and `os.getcwd()` as project root.
invariants: Pre — the path convention must match the file the skill instructions append to for the same spec. Post — the marker is stable and parseable, so an automated check (and any reader) can confirm a block was machine-written rather than hand-authored. Error — if the path convention and the existing `<feature>-retrospective.md` naming disagree, the injected block and the agent's prose would land in different files; this mismatch must be reconciled at spec time before implementation, naming one canonical retrospective filename that both the injector and the skill instructions use.
consumed-by: the success-criterion automated check; any reader distinguishing machine from agent content
produced-by: `fbk/capture/retro_injector.py`

## IF-D-10 — Known-agent set

signature: `known_agents.is_known_agent(agent_type: str | None) -> bool` backed by a set derived at import from installed persona files; a `STALE_FALLBACK` flag indicates the hardcoded fallback is in use.
invariants: Pre — persona files declare an agent-type frontmatter key. Post — events whose agent identity is empty or not in the set are excluded from aggregated subagent counts and results, though still recorded; when the derivation scan fails, the fallback set is used and `STALE_FALLBACK` is true. Error — a scan failure never raises; it sets the fallback and the report surfaces the stale-fallback warning.
consumed-by: the hook router (subagent capture path), the report command (subagent aggregation)
produced-by: `fbk/capture/known_agents.py`
