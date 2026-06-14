# Feature brief: deterministic metrics plane for Firebreak

**Intent seed for `/fbk-intent`. Written 2026-06-10 from a read-only audit of `~/.claude/fbk-scripts/` (mounted RO in the /opt/code sandbox — line references should be re-verified against current source before implementation).**

## Problem

Firebreak's only performance record is the retrospective markdown, appended by agents. Agent-recorded data fails as a measurement plane: selection bias (anecdotes, not rates), no denominators (prose isn't queryable), unreliable (appending is an instruction; instructions drop under context pressure), unfalsifiable. Consequence: queued features that claim to reduce rework (interface-contracts, wave-commit-model) cannot be evaluated before/after, and harness changes in general can't be measured without a Martian-scale benchmark run.

## Existing plumbing (audit findings)

- `fbk/audit.py` — append-only JSONL event logger (`log_event(spec, event_type, json)`), per-spec files under `.claude/automation/logs/`. Wired into only **2 of 8 gates** (`gates/spec.py`, `gates/task_reviewer.py`) and 1 of 2 hooks (`hooks/dispatch_status.py`).
- `fbk.py` — single dispatch chokepoint: every gate/hook/state/council command routes through `COMMAND_MAP` and `importlib` dispatch (~lines 36–43).
- `fbk/state.py` — already records `stage_timestamps` per transition and `error_history` per park. Stage durations and rework-by-stage are derivable today, zero new logging.
- `fbk/hooks/task_completed.py` — deterministically runs test suite, lint, and declared-file-scope check per task, then **discards results** (stderr warnings + exit code only).
- `fbk/retro.py` — `append_section(path, stage, content)` exists; currently invoked at agent discretion.

## Proposed behaviors

1. **Universal event logging at the `fbk.py` chokepoint.** Wrap module dispatch: log command name, args, exit code, wall-clock duration, and — for gates, which print a JSON result — the result payload. One wrapper instruments all 8 gates + hooks + state transitions.
2. **Single events file.** Decision to grill: migrate `audit.py` from per-spec log files to one `events.jsonl` with `spec` as a field (aggregation across runs is the point), vs. keep per-spec and add a merge step in the report command. Lean: single file.
3. **TaskCompleted hook persists its results.** Three `log_event` calls: test pass/fail (+ failing count), lint errors, undeclared-files list. Scope violations are a leading drift indicator currently WARN-and-forgotten.
4. **Code-review loop counts.** Persist per detection round: sightings raised, survivors after challenge, severity mix, rounds-to-quiescence. Challenger kill rate is the cheap proxy metric that spares Martian runs for substantive changes.
5. **`fbk report <spec>` command.** Aggregates events + `state.py` stage timestamps into a metrics table: gate first-pass rates, parks per stage, stage durations, scope violations, kill rate. Injected into the retrospective **from code** via `retro.append_section()` — the agent interprets the table; it no longer records facts.
6. **Token/cost harvest (post-hoc).** Tokens aren't visible to the Python layer live. Adopt/adapt `transcript_harvest.py` (built and tested 2026-06-10, lives in /opt/code; parses session + `subagents/agent-*.jsonl`, reports tokens by type/model, tool calls, tool errors, wall-clock). Run at retrospective time; join to stages via `state.py` timestamps.
7. **Schema discipline.** Versioned event records, fixed `event_type` vocabulary, drift test — same treatment as the slice-block vocabulary fix (PR #2).

## Non-goals

- No live OTel collector (env-var opt-in exists if ever wanted; surfaces 1–2 suffice).
- No agent-side recording instructions added or removed — the retrospective's narrative role is unchanged.
- No new Claude-level hooks required for v1 (the universal hook router in /opt/code is a separate, generic capture tool; Firebreak's own chokepoint + fbk hooks cover the pipeline events).

## Global-install constraint (added after capture-run discussion)

Firebreak installs hooks into global `~/.claude/settings.json` — so a shipped hook router fires in **all** projects by default. Decision: **globally armed, per-project gated.** Router's first action is a deterministic marker check (project is Firebreak-managed via `.claude/automation/`, or explicit `.fbk-capture/enabled` marker); exit 0 immediately otherwise. Rationale: (a) privacy — UserPromptSubmit captures full prompt text; ambient global capture crosses consent boundaries in uninstrumented projects; (b) overhead — 2 interpreter spawns per tool call in every project is unjustifiable ambient cost; (c) sandbox writability — capture must land in the **project dir** (installer gitignores `.fbk-capture/`), never centrally in `~/.claude/`, because per-project sandboxes mount parts of `~/.claude` read-only; cross-project aggregation is a sweep outside sandboxes, not a central write path. Migration note: any project-level router registration (e.g. /opt/code's capture experiment) must be removed when the global install ships, or events duplicate — global and project hooks both run. Router envelope must share schema/event-type vocabulary with the fbk.py chokepoint events so `fbk report` joins both streams.

**Verbosity is user-configurable; the default is an empirical question.** The per-project gate carries a capture-level setting (sketch: `off` / `standard` / `full` — taxonomy itself is a grilling item). `full` = every event with payloads (verification runs, skill debugging); `standard` = the lean profile (lifecycle, failures, SubagentStop incl. `last_assistant_message`, chokepoint events). The shipped default is NOT decided in this brief: run `full` capture during Firebreak development, observe which signals the report command and the self-improvement loop (`/fbk-improve`, retrospectives) actually consume, and set the default to the level that preserves those signals at least cost. The /opt/code capture experiment is the first data source for that decision.

## Experiment results from /opt/code (2026-06-10, informs design defaults)

1. **Stage-stamp join validated end-to-end** against the real state engine: created `stamp-test-spec` via `fbk.py state`, transitioned it mid-session; tool-call events between transitions were correctly stamped `{spec, stage}` at hook-fire time. Open question 4 (stamp-at-log-time vs post-hoc join) now has evidence for stamp-at-log-time: it works, it's unambiguous under interleaving, and the coupling is one fail-silent file read.
2. **Volume by event type** (54-event sample, full capture): PostToolUse = 75% of bytes (avg 6.8KB/event with payloads), PreToolUse = 16%. A `standard` level dropping tool-call payloads retains all lifecycle/failure/subagent signals at ~9% of volume. Full-capture session ≈ 0.2–1MB — retention matters across projects, isn't urgent within one.
3. **Router overhead measured**: ~15ms/invocation full append, ~8ms early-exit (interpreter-dominated). Per tool call ≈ 30ms at full capture, ~16ms gated-off. Ambient global cost of the gate design is acceptable.
4. **`fbk report` prototype exists and runs** (`/opt/code/fbk_report_prototype.py`): joins hook capture + state-engine stage durations + transcript harvest into per-stage tool calls/errors/thrash, stage durations, parks, tokens, and subagent results. It surfaced real thrash on first run (two docs edited 3× each). Port, don't redesign.
5. **TaskCompleted did NOT fire for a background Bash task** — its trigger is task-list/SDL task completion, not background commands. Verify its exact trigger in the Firebreak project where the existing fbk TaskCompleted hook demonstrably fires.
6. **Caution — harness-internal subagents pollute SubagentStop**: events with empty `agent_type` appeared (internal helpers, e.g. title/suggestion generation), with `last_assistant_message` set. Metrics must filter `agent_type` to known Firebreak agent names or non-empty values, or subagent counts and results will include phantoms.

## Open questions for grilling

1. Single `events.jsonl` vs. per-spec files + merge?
2. Should the chokepoint wrapper capture gate JSON results verbatim or a summarized envelope (results can embed long finding lists)?
3. Where does `fbk report` land in the SDL — retrospective stage only, or also runnable mid-pipeline?
4. Stage stamp inside event records: read from state file at log time (couples logger to state), or join post-hoc on timestamps (looser, but interleaved specs ambiguity)?
5. Does code-review round logging live in the code-review gate (deterministic, sees JSON artifacts) or the skill instructions (sees more, but agent-mediated — likely no)?
6. Capture-level taxonomy: is `off`/`standard`/`full` sufficient, or does `standard` need splitting (e.g. failures-only vs. failures+subagent-results)? Where does the setting live — per-project marker file, or a key in Firebreak's existing config surface (`fbk config`)? What retention/rotation policy for `events.jsonl` at each level?

## Acceptance sketch

After one SDL cycle on any feature: `fbk report <spec>` produces a table with ≥ these populated rows — per-stage duration, gate attempts/first-pass, parks (with reasons), tasks completed/reworked, scope violations, detection rounds with sighting→finding counts, tokens per stage. Retrospective file contains the table, injected without agent involvement.
