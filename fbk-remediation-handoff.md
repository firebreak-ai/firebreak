# Hook-harvesting remediation — session handoff

**Temporary doc.** Delete once the remaining work is scheduled or done. Written 2026-06-11 after a full code review of the `fbk/hook-harvesting` branch.

## Where things stand

- **Full review:** `fbk-code-review-2026-06-10-1530.md` (repo root) — 36 verified findings, grouped by theme, each with file:line and a fix direction. Read its **Headline** and **Theme A** sections first.
- **Branch:** `fbk/hook-harvesting-trivial-fixes` (branched off `fbk/hook-harvesting`). One commit so far: `5dbd3ac` — the 7 trivial mechanical fixes, 339 tests pass, ruff clean.
- **Already fixed in that commit (don't redo):** parked-stage stamping in the chokepoint (F-10), `PostToolUseFailure` → `TOOL_USE` map entry (F-09), bool rejection in round-log validation (F-17), unused imports (F-35), unreachable pruner branch (F-36), and two dead-code cleanups.
- **Remaining:** everything below. ~10–12 real work items (the 29 remaining findings cluster hard).

## The one thing to understand first

The capture **write** path is sound. The report **read** path is broken: it queries the event stream for keys, values, and stage fields that **no producer actually writes**. The whole test suite is green because every report fixture is hand-built in the report's *expected* shape, not the producers' *actual* shape — so the tests encode the same wrong assumption on both sides and never catch the drift.

**The single highest-value fix is one integration test:** run a real gate and a real task-completion through `event_writer`, then run `report` over the resulting `events.jsonl`, and assert the rows are non-zero. That test fails today and would catch the entire Theme-A cluster. Write it first; let it drive the contract fixes.

## Work items, in order

### Tier 1 — Release-blocking: the report renders zeros (do these together)

All four are producer/consumer envelope-contract mismatches. Fix the contract, then fix the fixtures that hid it. (Findings F-01–F-07.)

1. **Gate pass rates always 0** — `report.classify_gate_attempts` (report.py:47-51) filters `VERIFICATION_RESULT` by `stage`, but `task_completed.py:173-181` writes `stage=None`. Either stamp the real stage in the producer (preferred — reuse the chokepoint's `_resolve_spec_stage` pattern) or match by timestamp window.
2. **Kill rate always 0** — report reads `raised`/`confirmed` (report.py:393-399); producer writes `total_raised`/`total_survived` (code_review.py:155-165). Also `rounds` is read as a count but written as a list — use `len(rounds)`.
3. **Scope violations always 0** — report queries `PIPELINE_COMMAND` `data["command"]=="scope_violation"` (report.py:456-460); real data is in `VERIFICATION_RESULT` `out_of_scope_files` (task_completed.py:162-167).
4. **Tasks completed/reworked always 0** — report reads `data["command"]=="task_completed"` (report.py:439-448); chokepoint writes `command_name=="task-completed"` (hyphen). No `task-reworked` event exists — derive rework from `error_history`.
5. **Then fix the masking fixtures** so they use real producer shapes: `test_report_rendering.py` `_build_full_events` (F-05) and its kill-rate fixture (F-06); `test_report_arithmetic.py` / `test_report_rendering.py` gate-rate fixtures (F-07). After the integration test above exists, these become straightforward.

### Tier 2 — Capture correctness and safety (behavioral)

6. **Subagent completions double-counted** (F-08) — `hook_router.py:62` maps `SubagentStart` to `SUBAGENT_STOP`; should be `LIFECYCLE`. Add a router test feeding a `SubagentStart` payload.
7. **Router stamps terminal states on events** (F-11) — `hook_router._read_active_stage` (hook_router.py:84-105) has no terminal-state filter at all. Mirror the chokepoint's now-fixed logic; consider extracting a shared helper so the two never drift again. (Note: the chokepoint half, F-10, is already fixed on the branch.)
8. **Round detail leaks at standard level** (F-12) — `schema.py:37` `FREETEXT_KEYS` lists phantom `round_detail`; producer emits `rounds`. Add `rounds` to the set (and drop `round_detail`).
9. **Broken capture install crashes the verification hook** (F-13) — `task_completed.py:95` imports capture modules outside `try/except`; an ImportError exits code 1, not fail-silent. Move the import inside the existing guarded block.
10. **Pruner drops events under concurrent writes** (F-14) — `retention.py:60-137` does an unlocked read-modify-write; the router fires per tool call. Add an `fcntl.flock` across the sequence.
11. **First-write capture can escape via a symlinked root** (F-15) — `event_writer.py:79-88` skips the confinement check in the dir-creation branch (computes `real_root`, never uses it). Apply the same realpath check the existing-dir branch uses.
12. **Task-reviewer gate writes no event on failure** (F-16) — `task_reviewer.py:340-359` only writes on pass; the spec gate writes on both. Add a fail-path write. (Pairs with the missing fail-path test, F-23.)
13. **Failing/lint counts are binary 0/1, not counts** (F-25) — `task_completed.py:111-132` sets the value to `1` on any failure. Parse the runner/linter summary for the real number. (Pairs with the non-enforcing assertion F-24.)

### Tier 3 — Inert guarantees and missing outputs

14. **The drift check never fires** (F-18, F-19) — `schema.check_drift` regex (schema.py:87-90) doesn't match `event_writer.write("TYPE", ...)` call sites, and the only drift test scans just `fbk/capture/`. Add a pattern for the `write()` first arg; widen the test scan to the whole `fbk/` package.
15. **Unavailable-vs-zero broken in mixed-transcript cycles** (F-20) — `token_harvester.py:268-270` marks every stage available when any transcript is readable. Mark a stage available only when a turn is attributed to it from a readable transcript. The dead `readable_counts` dict (F-34, token_harvester.py:243) is the intended scaffold — implement it rather than deleting it.
16. **Boundary-adjacent turns and coarse-indicator label never rendered** (F-21) — harvester computes them (token_harvester.py:311); report never prints them. Render both; then add the label to `_REQUIRED_ROW_LABELS` (F-22).

### Tier 4 — Test-integrity and minor (mostly dissolve with the above)

- F-23 (task-reviewer fail-path test), F-24 (failing-count assertion), F-26 (chokepoint normal-return path untested — drive `report`, not `state transition`), F-27 (empty-identity assertion accepts None), F-28 (subagent-count test uses ambient `FBK_AGENTS_DIR`), F-29 (phantom pipe-split guard).
- F-30 (redundant migration test — minor), F-31 (dispatcher test counts `session-state` only by number — pre-existing minor).
- F-32 (STALE_FALLBACK warning read before the scan that sets it — report.py:346/491), F-33 (`UserPromptSubmit`/`Notification` lack explicit map entries; `PrePrompt`/`PostPrompt` are dead map entries).

## Confirmed correct — do not "fix"

- The **retrospective-injection predicate** (state.py / retro_injector.py, AC-18) — examined closely, correct.
- The **token-harvester hard-split attribution and boundary window** (AC-06 arithmetic) — correct. (The *availability* logic around it is the bug, item 15 — not the arithmetic.)

## How to run things

From `assets/fbk-scripts/`:
- Tests: `python3 -m pytest tests/ -q`
- Lint: `ruff check fbk/`

Source of truth for behavior is the spec: `ai-docs/hook-harvesting/hook-harvesting-spec.md` (27 acceptance criteria, the `IF-D-*` interface contracts). Each finding in the review report cites the AC it traces to.
