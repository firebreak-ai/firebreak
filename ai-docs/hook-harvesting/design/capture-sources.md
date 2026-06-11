# Capture Sources

Where events come from. Five producers write to one shared event stream through one writer; a sixth source (parks and rework) is derived at read time from the state engine and produces no events. All producers share a single versioned envelope.

## The shared event writer

One function, `event_writer.write(...)`, is the only path that appends to `.fbk-capture/events.jsonl`. It takes a fully-assembled envelope (event type, source, data, spec, stage, capture level), appends one JSON line, and runs the retention prune check. It holds no state, so it is safe to call both from the in-process chokepoint and from the short-lived hook-router process. It never raises: any write failure is caught and discarded, satisfying the fail-silent constraint. If the event type is not in the known vocabulary at write time, the writer discards the record and warns on stderr rather than writing a corrupt line.

Module: `fbk/capture/event_writer.py`. Depends on the schema module (envelope shape, vocabulary) and the retention module (pruning). It does not import the state engine — the caller stamps the stage before handing over the envelope.

## The per-project capture gate

The governing constraint for the whole feature. `gate_check.project_is_instrumented(cwd)` returns true only when the project is Firebreak-managed (`.claude/automation/` present) or carries an explicit marker (`.fbk-capture/capture.cfg` present). `gate_check.resolve_capture_level(cwd)` returns off, standard, or full. Both run on the hot path in every Claude tool call, including uninstrumented projects, so they do only filesystem existence checks plus one single-line read of `capture.cfg` — no YAML, no state-engine import. The prototype measured the gated-off router path at roughly 8ms per invocation, interpreter-startup-dominated; the gate check itself is a couple of `stat` calls on top of that. Both functions return the safe default (false / off) on any filesystem error and never raise.

Module: `fbk/capture/gate_check.py`. Imported by the hook router and the chokepoint recorder; never writes.

## The hook router

A standalone script registered in the global Claude configuration, fired by Claude's hook runtime — not routed through `fbk.py` (routing it through the dispatcher would require the dispatcher to instrument itself before loading). On each invocation it: reads the hook event from stdin, runs the capture gate, resolves the level, assembles an envelope for the Claude-level event (tool use, lifecycle, subagent stop, prompt submit), filters subagent events by agent identity, writes the event, and exits 0. It never writes to stdout and never raises.

At standard level a tool-use event records that a tool ran and its outcome, with the payload stripped; tool-call arguments and prompt text are recorded only at full level. Stage stamping reads the active stage from the state engine at write time; if no SDL run is active, the event carries no stage and is still recorded.

Module: `fbk/capture/hook_router.py`, installed under the global fbk-scripts tree.

## The dispatch chokepoint recorder

Every gate, hook, and state transition already routes through one dispatch point in `fbk.py` (the `module.main()` call). Wrapping that point records, for each command: name, arguments, outcome (pass/fail), exit code, and wall-clock duration — instrumenting all eight gates plus hooks and state transitions from one place.

The wrapper, `chokepoint.record_dispatch(command_name, args, run_fn, cwd)`, must preserve the gates' stdout-and-exit contract. Gates raise `SystemExit` from inside `main()` (for example, the code-review gate calls `sys.exit()` after printing its JSON), so the redirect cannot rely on `run_fn()` returning normally, nor on `with`-block or `atexit` cleanup — `SystemExit` would short-circuit those. The mechanism is explicit: save the real stdout, install an in-memory buffer, call `run_fn()` inside a `try` that catches both normal return and `SystemExit`, and in a `finally` block restore the real stdout and write the buffered bytes to it. Only after the buffer has been flushed to the real stdout does the wrapper write the event and then re-raise the original `SystemExit` (or return the normal result) with the same exit code. If the project is not instrumented, the wrapper calls `run_fn()` and returns directly, recording nothing. If the redirect cannot be installed, or any capture-machinery step fails, that failure is discarded and the gate's output and exit code are never suppressed. (See `contracts.md`, IF-D-04, for the full signature, the source of `cwd`, and the constraint this places on future gates.)

`cwd` is supplied by `fbk.py` as `os.getcwd()` — the project root, which is where fbk commands are always invoked. This is the same project-root assumption the report and injector use.

The gate result payload is stored summarized at standard capture (gate, result, failure count, finding count) and verbatim at full capture.

Module: `fbk/capture/chokepoint.py`; `fbk.py` lines 40–43 change to call it.

## Verification result persistence

The per-task verification hook already runs tests, lint, and a declared-file-scope check, then discards the results. This feature has it write a `VERIFICATION_RESULT` event instead: test pass/fail with the failing-test count, the lint-error count, and the list of files touched outside declared scope. Scope violations, today warned-and-forgotten, become a queryable data point. The hook's existing exit behavior (exit 2 on failure, exit 0 on pass) is unchanged; the new event write happens as a side effect before exit and is fail-silent.

This hook is registered in `settings.json` as `fbk.py task-completed`, so it is dispatched **through** the chokepoint like any other command — the chokepoint records a `PIPELINE_COMMAND` event for the dispatch (name, outcome, duration), while the hook module itself writes the richer `VERIFICATION_RESULT` event with the structured test/lint/scope data. The two events are complementary, not redundant: the command event records that verification ran; the verification event records what it found.

Module: `fbk/hooks/task_completed.py` (modified). The stdin payload is already parsed there.

## Code-review round logging

The deterministic code-review gate cannot see the detection/challenge rounds — the code-review skill orchestrates them. The handoff is file-based: the skill writes `.code-review-rounds.json` to the feature directory during its run; the gate reads that same feature directory for its existing artifact checks, and this feature adds a new read of the round file at check time, emitting a `CODE_REVIEW_ROUNDS` event (per-round raised/survived/severity, rounds to quiet, totals). The round-file read is a new code path in the gate, not an existing one — the gate today reads only the quality-scan, test-review, and hash-manifest artifacts. If the file is absent, no event is emitted and the gate's pass/fail logic is unaffected. The gate validates the file's schema version and required fields; a malformed file produces no event and a stderr warning.

The challenger kill rate is computed at report time as `(total_raised − total_confirmed) / total_raised`, where total_raised counts every raise across all rounds including re-raises — a detector-noise signal. Total confirmed is the count that survived to the final quiet round. Known limitation: if the review gate stops re-raising an issue once it is acknowledged and queued for remediation, that true positive would not appear in the final round and would read as killed rather than confirmed. This is documented for any reader who expects confirmed-anywhere semantics; resolving it would require the skill to emit per-issue confirmation status, deferred. Per-round counts are retained so the rate can be recomputed if the definition changes.

Module: `fbk/gates/code_review.py` (modified). The skill-side write is a separate dependency tracked in `configuration-and-lifecycle.md`.

## Retiring the old audit calls

The two existing per-spec `audit.log_event` call sites (spec gate, task-reviewer gate) are replaced with event-writer calls using the shared envelope. Existing per-spec `.log` files are preserved but receive no new writes. The old audit module stays for backward compatibility.

## The shared envelope, vocabulary, and drift check

Every event is one JSON object with a fixed set of fields and an `event_type` drawn from a closed vocabulary, carrying a `schema_version`. The vocabulary and the drift check live in `fbk/capture/schema.py`. There are two distinct guards, at two layers, and they are not the same mechanism:

- **The drift check** is a build/test-time validation: a test asserts that the set of event types referenced across the capture modules equals the canonical vocabulary, raising on any drift. This catches a developer adding a new event type to one producer without registering it — the same discipline applied to the slice-block vocabulary. It runs in CI, not on the write path.
- **The writer's discard-unknown** is the runtime safety net: if a record with an unregistered `event_type` somehow reaches `event_writer.write()`, the writer discards it with a stderr warning rather than writing a corrupt line. This never raises, consistent with fail-silent capture.

The full envelope schema and the vocabulary are recorded as contracts in `contracts.md`.
