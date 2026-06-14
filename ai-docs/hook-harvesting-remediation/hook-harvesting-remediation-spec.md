# Spec: Hook-Harvesting Remediation (independent-review fixes)

Feature directory: `ai-docs/hook-harvesting-remediation/`
Source of truth for the defects: `ai-docs/hook-harvesting/fbk-cr-hook-harvesting-remediation.md` (the independent code review of the Stage-7 remediation diff). Each acceptance criterion below cites the review finding it closes.

This is a defect-remediation spec for the deterministic metrics plane shipped on `fbk/hook-harvesting`. The feature's write path is sound, but an independent review found that the remediation's own new code reproduces the producer/consumer envelope-drift failure class the feature exists to measure, plus a release-blocking install gap. All 25 verified findings are in scope, organised in three tiers so implementation can stop at a tier boundary.

---

## Problem

The hook-harvesting feature passes 359 tests and a 36-finding self-review, yet three of its core promises do not hold against real data: after a normal install it captures nothing (the gate's marker file is never created), the per-stage metrics it injects into every retrospective are an empty shell (the injector calls a stub that emits no measurements), and its subagent count is always zero (the report reads the writer name instead of the agent identity). Twelve further defects make the report's rates and token totals wrong under ordinary conditions, and a cluster of tests pass while encoding the same wrong assumption on both sides of a contract, so the suite cannot see any of it. The metrics plane therefore reports confidently incorrect numbers — worse than no metrics, because they look authoritative.

## Goals / Non-goals

**Goals**

- Make capture actually arm after an install, so a Firebreak-managed project records events with no manual step.
- Make the injected retrospective metrics block contain the real per-stage metrics, not a label-only stub.
- Make every report row read the same envelope field its producer writes, so rates, counts, token totals, and the subagent count reflect reality.
- Close the capture-gate's hot-path config read so a crafted repository cannot stall every tool call.
- Rewrite the tests that pass without verifying their claim, and add end-to-end guards across the two seams that broke silently (the injection seam and the install→gate→capture seam), so a future regression turns the suite red instead of staying green.
- Fold in the structural and type-checker cleanups surfaced by the review.

**Non-goals**

- No new metrics, rows, capture levels, or event types beyond what the original spec already defines. This is a correctness pass, not a feature extension.
- No change to the fail-silent guarantee, the privacy/redaction model, or the globally-armed/per-project-gated capture design. Fixes must preserve them.
- No rewrite of the capture subsystem's architecture. Each fix is local to the module that owns the defect, with one shared constant extracted where two modules must agree.
- No re-litigation of resolved design decisions (size-only retention, flat module homes, the out-of-tree `full` signal). Those stand.

## User-facing behavior

The operator is a Firebreak developer running the SDL; the surface is the `fbk.py report` command and the capture files on disk.

- **Capture arms on its own after install.** After running the installer in a Firebreak project, the operator runs a tool call and a `.fbk-capture/events.jsonl` appears with events in it — no hand-written `capture.cfg` required. *(closes F-03)*
- **The injected metrics block contains numbers.** When a working stage completes, the `## <STAGE> — metrics` block written into the retrospective shows that stage's gate rates, parks, and rework — not just a `stage:`/`spec:` label pair. *(closes F-04)*
- **The subagent count is real.** A cycle that ran known Firebreak agents shows a non-zero known-subagent count in the report. *(closes F-02)*
- **Events after a finished cycle are not misfiled.** Tool calls made after a cycle reaches its terminal state carry no stage and do not appear under a phantom `COMPLETED` row; events during inter-stage handoffs are correctly stamped as no-stage rather than misfiled under a checkpoint-named row (they appear in no per-stage row — the report renders working stages only). *(closes F-01, F-05)*
- **Gate rates cover every gate.** First-try and after-rework pass rates reflect the spec, task-reviewer, and code-review gates — not only the task-completion gate. A stage whose spec gate failed twice before passing shows a first-try rate below 1.0. *(closes F-06)*
- **Rates and tokens are correct under rework.** A stage that parked and resumed more than once classifies its attempts correctly, and per-stage token totals are not understated by turns siphoned into non-rendered states. *(closes F-07, F-10)*
- **Per-round review detail survives at the default level.** Running the report at `standard` shows one row per detection round, not a single collapsed total. *(closes F-09)*
- **A baseline lock is honored even under concurrent writes.** A lock dropped while capture is active protects its spec's lines. *(closes F-08)*
- **A hostile config cannot stall the session.** Opening a repository whose `capture.cfg` is a giant single line does not hang every tool call. *(closes F-11)*

## Technical approach

The feature is brownfield: all fixes land in the installed `fbk-scripts` package and the installer, against the modules the original feature already created. The review report names the exact file and line of every defect; this section gives the shape of each fix and the conventions that must stay consistent across module boundaries.

### The two roots

Most findings are independent, but two roots each spawn several findings and drive the design:

- **The active-stage attribution root.** `fbk/capture/active_stage.py` hardcodes `TERMINAL_STATES = ("DONE", "FAILED", "PARKED")` — two names that do not exist in the state machine, and missing `COMPLETED`, the real terminal state. `fbk/report.py:374` independently hardcodes a *different*, correct list of non-running states. The fix defines one authoritative "states that are not an active working stage" set in `fbk/state.py` itself, beside the `WORKING_STAGES` it derives from (the non-active set is every other state plus the terminal/idle ones); both `active_stage.py` and `report.py:374` import it, so the two can never drift again. Ownership sits in `state.py` deliberately: `state.py` already imports the capture package at the top level (`from fbk.capture import retro_injector`), so a constant homed in the capture package and imported back by the reporting chain would close an import cycle (state → retro_injector → report → active_stage → state); defining it beside `WORKING_STAGES` keeps every import edge one-directional. This single change closes the resolver's terminal-state bug and its checkpoint-state bug. *(F-01, F-05)*

- **The envelope-field root.** Several report rows read a key, value, or stage the producer does not write under that name. The fix traces each row to its producer and aligns the field: the subagent count reads `data["agent_type"]` (or the precomputed `data["is_known_agent"]`) instead of `source`; the gate-rate classifier reads `PIPELINE_COMMAND` outcomes for non-verification gates; the per-round detail is kept out of the redaction strip-list. *(F-02, F-06, F-09)*

### Integration seams

- [ ] `active_stage.py` ↔ `report.py`: the non-active-state set. `fbk/state.py` owns the constant (defined beside `WORKING_STAGES`); both modules import it — ownership sits in `state.py` to avoid the import cycle a capture-package home would create. Both the resolver's "return no stage" decision and the report's "exclude from ran_stages" decision read the same set. *(F-01, F-05)*
- [ ] hook_router → report: subagent identity. The router writes the agent identity into `data["agent_type"]` and a `data["is_known_agent"]` boolean; the report reads one of those, never the envelope `source` (which is always the writer name `"hook_router"`). *(F-02)*
- [ ] chokepoint → report: gate outcomes. Spec/task-reviewer/code-review gate pass-fail reaches the rate classifier as the chokepoint's `PIPELINE_COMMAND` events with `data["outcome"]` and a `data["command_name"]` the classifier matches against the known gate command names — the chokepoint is the single writer of gate-outcome events (the gates' own duplicate writes are removed; see Decisions). The design assumes a gate dispatch happens while its owning working stage is active: a gate dispatched at a checkpoint boundary resolves to no stage and exits the rates, so the seam tests pin this assumption. *(F-06, F-16)*
- [ ] state.py → report: the rework boundary. The after-rework boundary is derived from the first park recorded in the append-only `error_history` (the re-entry follows the park; `error_history` records parks, not re-entries, so the contract is stated against what the structure actually holds), not the last-write-wins `stage_timestamps["READY"]`. *(F-07)*
- [ ] event_writer ↔ retention: the locked-spec set is read inside the prune's lock scope, so a lock created during an active write is honored. *(F-08)*
- [ ] installer → gate_check: the installer writes the `.claude/automation/.fbk-managed` sentinel the gate keys on. The sentinel name is the single shared token (`gate_check.FBK_MARKER_SENTINEL`). *(F-03)*

### Module touch policy

- [ ] `fbk/capture/active_stage.py`: refactor-then-extend — replace the hardcoded `TERMINAL_STATES` tuple with the shared non-active-state set imported from `fbk/state.py`. *(F-01, F-05)*
- [ ] `fbk/report.py`: refactor-then-extend — import the shared non-active-state set (replacing the parallel literal at line 374); fix the subagent identity read (line 198); extend the gate-rate classifier to include `PIPELINE_COMMAND` outcomes (lines 46-50); derive the after-rework boundary from the first park in `error_history` (line 63); restrict the token-boundary list to working stages (lines 556-572); implement `stage_summary` to load events+state and render real per-stage metrics (lines 209-227); render one row per detection round and remove the dead `round_count` field (lines 419-423, 495-496). *(F-02, F-04, F-06, F-07, F-09, F-10, F-19)*
- [ ] `fbk/capture/event_writer.py`: refactor-then-extend — read the locked-spec set inside the prune lock scope; check `source` against `schema.SOURCES` and, when unregistered, write the event unchanged and emit a stderr warning (warn-but-write — mirrors the existing event-type warning path but never discards data, because after the subagent fix `source` is provenance, not load-bearing). *(F-08, F-21)*
- [ ] `fbk/capture/schema.py`: extend — keep the per-round numeric fields out of `FREETEXT_KEYS`, and make `redact` recurse into nested per-round structures so a free-text string inside a round entry is stripped at `standard` while the numeric counts and enum severity tag survive; the denylist recursion is defense-in-depth behind the code-review gate's allowlist projection, which is the control at the trust boundary; `SOURCES` stays the registry the writer's warn-but-write check reads. *(F-09, F-21)*
- [ ] `fbk/capture/gate_check.py`: extend — bound both hot-path reads (`f.readline(256)` in the cfg-level read and the `_full_corroborated` reads). *(F-11)*
- [ ] `fbk/capture/chokepoint.py`: extend — normalise the not-instrumented and redirect-fail fast paths to return `0` for `None`; produce a non-free-text gate-result summary (or drop the misleading "summarized" contract language). *(F-17, F-18)*
- [ ] `fbk/gates/spec.py`, `fbk/gates/task_reviewer.py`: refactor — remove the gates' own `PIPELINE_COMMAND` writes entirely. The chokepoint's event is the single record per dispatch: it already stamps `data["outcome"]`, the resolved stage, and the gate's full JSON stdout in its `output` field, so the richer gate payload survives unparsed and can be promoted to its own event type if a consumer ever appears. One dispatch yields exactly one `PIPELINE_COMMAND` event. *(F-16)*
- [ ] `fbk/gates/code_review.py`: extend — compute and write `rounds_to_quiet` (the IF-D-06 contract metric), or remove it from the contract; allowlist-project each round entry at the untrusted round-log boundary before writing — keep exactly `raised`, `survived`, and `severity` validated against the fixed severity enum, drop every other key — so the round-log file (untrusted input per the project threat model) cannot carry free text into the event payload under a key the redaction denylist has never met. *(F-09, F-20)*
- [ ] `fbk/capture/retention.py`: extend — annotate the optional-`fcntl` fallback so the type-checker is clean; behavior unchanged. *(F-25)*
- [ ] `installer/install.sh`: extend — create `.claude/automation/.fbk-managed` during install; write `settings.json` via a temp file created in the same directory as the target, then an atomic rename — same-directory placement is load-bearing, because a rename from another filesystem (e.g., a `/tmp` temp file) silently degrades to a non-atomic copy. *(F-03, F-22)*
- [ ] `fbk/state.py`: extend — define the shared non-active-state set beside `WORKING_STAGES` (a pure constant; no behavioral change). It owns the constant so the capture and reporting modules can both import it without creating a cycle.

### Test corrections (these are part of the change, not just verification)

The review found four tests that pass while not verifying their claim, and these are corrected as load-bearing work: the subagent-count test rebuilt with the production envelope shape — `source` pinned to the literal `"hook_router"`, identity in `data["agent_type"]` — so it can only pass when the report reads the identity field; the injection test extended to assert real metric content; the bounded-read test rebuilt around a divergence fixture (invalid bytes filling the first 256, a parseable level token beyond the cap in the same line) so the bounded and unbounded reads provably return different values and the test fails on the unbounded read by correctness, not timing; the central-redaction test rebuilt to enumerate `schema.SOURCES` dynamically.

Two existing seam tests already carry the same heading-only weakness and are folded into this work rather than left as weakened twins: `test_capture_e2e_seam.py::test_two_source_cycle_joins_in_one_report` and `test_capture_report_integration.py::test_real_producers_drive_nonzero_report_rows` are strengthened to assert exact metric values.

**Demonstration procedure.** The pre-fix reference is the feature-branch commit the remediation builds on — record its hash at implementation start (`40ec021` on `fbk/hook-harvesting` at spec time). It is *not* the review's merge-base `4437a6c`: that tree predates the capture package entirely, so tests run there fail on imports, not on the defects. Each corrected or new behavioral test is written and run **before** its fix lands, and its failing output is captured in the owning slice's completion notes; the post-fix passing run is captured alongside. One shared discipline for every slice: the red run executes from a second git worktree checked out at the recorded pre-fix commit with the new or corrected test file copied in — no per-slice improvisation with stashes. The red run uses the **rebuilt or net-new test versions only**: the original versions of the corrected tests are the masked guards this spec exists to fix and stay green at the pre-fix commit by construction, so an original-version run demonstrates nothing. *(F-12, F-13, F-14, F-15, F-23, F-24)*

## Testing strategy

The package has an established `pytest` suite under `fbk-scripts/tests/`. The discipline for this remediation: every behavioral fix gets a test that fails on the current (buggy) code and passes after the fix, so the test demonstrably guards the regression.

### New tests needed

- Unit (new file `tests/test_capture_active_stage.py` — the resolver currently has zero test coverage anywhere in the suite): `resolve_active_stage` returns `(None, None)` for a state file in `COMPLETED`, and for each checkpoint/idle state (`QUEUED`, `READY`, `VALIDATED`, `REVIEWED`, `BROKEN_DOWN`, `TASKS_READY`, `TESTS_WRITTEN`, `TESTS_READY`, `IMPLEMENTED`); returns the stage for a true working stage — covers AC-01.
- Unit: `active_stage` and `report` consume the one constant by identity — the test asserts each module's set is the same object (`is`) as the constant defined in `state.py`, and that the old local tuple is gone (accessing `active_stage.TERMINAL_STATES` raises `AttributeError`). Value-equality alone is not sufficient: it passes against two drifting copies, which is the failure mode this criterion exists to prevent — covers AC-02.
- Integration: `count_known_subagents` over `SUBAGENT_STOP` events written in the **production** shape — `source` pinned to the literal `"hook_router"`, identity in `data["agent_type"]` — returns the exact fixture count: two known-agent events plus one unknown yield exactly 2. Red-run mechanics, stated so the pre-fix failure is not in doubt: the pre-fix read takes the truthy envelope `source` first (always `"hook_router"`, never a known agent — its `or` fallback to the identity field never fires on a production envelope), so the pre-fix count is exactly 0 and the test fails red as 0 ≠ 2 — covers AC-03.
- Integration (real producer → real consumer): drive a real gate and a real task-completion through the writer, then run `stage_summary` for that stage and assert the injected block contains the exact gate-rate and parks values the fixture's events compute to (e.g., one fail-then-pass gate and one park → first-try rate exactly 1/2, parks exactly 1), not just the marker — covers AC-04 and the injection guard seam (AC-15).
- Integration: a stage whose spec gate emitted `PIPELINE_COMMAND` fail-then-pass alongside one first-try-passing gate yields a first-try rate of exactly 1/2 — covers AC-05.
- Unit: with `error_history` recording two parks, the after-rework boundary is the **first** park's timestamp; every attempt after the first park (i.e., after the stage re-entered) classifies as after-rework, including those between the re-entry and the second park — covers AC-06.
- Unit (concurrency): a lock file created between the append and the prune protects its spec's lines (drive the prune with a `protect_specs` read taken inside the lock) — covers AC-07.
- Integration: the report at `standard` renders one row per detection round with per-round raised/survived; the fixture's round log carries one entry with an unknown free-text key (asserted dropped by the gate's allowlist projection) and one out-of-enum severity (asserted rejected or normalised) alongside the well-formed rounds — covers AC-08.
- Unit: per-stage token totals attribute a turn during a checkpoint period to the adjacent working stage, not to a dropped checkpoint bucket; the totals equal the exact per-stage sums of the fixture's token counts, with every fixture turn accounted for — covers AC-09.
- Unit (bounded read): `resolve_capture_level` over the divergence fixture — a first line of 256 filler bytes containing no `=` or level token (e.g. `x` repeated 256 times), followed on the same line by `capture_level=full`. The out-of-bounds token must be a **non-default** level (`full`): the bounded read finds no token in its byte window and returns the safe default `standard`, while the pre-fix unbounded read resolves `full` — the test asserts `standard` and fails pre-fix on correctness alone. (A `standard` token beyond the cap would make both reads agree and the test would pass trivially on both implementations.) A companion non-gating wall-clock check over a 5 MB single-line config may accompany it but is not the guard — covers AC-10.
- Integration (install → capture seam): after the install routine runs in a `tmp_path` project, `project_is_instrumented` is true and a router event is recorded — covers AC-11 and the install guard seam (AC-16).
- Integration (installer atomic write): the install routine writes `settings.json` via a temp file created in the same directory as the target and renames it into place; the test asserts the merged result lands intact and no temp residue remains beside it — covers AC-20.
- Integration: one real gate dispatch through the chokepoint yields exactly one `PIPELINE_COMMAND` event for that command (the gates' own duplicate writes are gone); an event with an unregistered `source` is still written to the events file **and** a stderr warning is emitted (warn-but-write); every producer's test pins its exact `source` string literal — the only check that catches a wrong-but-registered label — covers AC-12, AC-13.
- Unit: the central-redaction test enumerates `schema.SOURCES` and asserts no `standard` record from any registered producer carries a free-text payload — covers AC-14.

### Existing tests impacted

- `tests/test_report_arithmetic.py::test_subagent_count_excludes_unknown_identity` — currently builds `source=<agent-name>`: rebuild with the production envelope shape (`source="hook_router"`, identity in `data["agent_type"]`); must fail on current code. `test_attempt_after_ready_reentry_classifies_after_rework` and `test_rework_derived_from_repeated_stage_entry` — encode the `stage_timestamps["READY"]` read: rebuild against the first-park boundary. `test_first_try_pass_rate_is_exact_fraction`, `test_kill_rate_is_exact_value`, `test_stale_fallback_warning_fires_with_zero_subagent_events`: confirm still green after the gate-rate extension.
- `tests/test_capture_retro_injector.py::test_injects_block_under_metrics_heading` — the heading-only injection assertion: extend to assert exact metric values computed from its fixture's events — the block must contain the stage's first-try rate with the exact fraction (e.g. exactly 0.5 for one fail-then-pass gate beside one first-try pass) and the exact parks count. The stub emits only `stage:`/`spec:` labels, so the pinned-value assertion fails against it by construction; a loose "contains metric content" assertion would not, and is insufficient.
- `tests/test_capture_e2e_seam.py::test_two_source_cycle_joins_in_one_report` — the existing real-producer seam test asserts only the `## VALIDATING — metrics` heading and the provenance-marker prefix, never a metric value — the same weakness the injection guard exists to kill: strengthen to assert the exact metric values its fixture computes to; must fail against the stub. Its choreography must also be corrected: today it transitions the run to `VALIDATED` (a checkpoint state) and then fires the router event — under the fixed resolver that event carries no stage and exits the asserted table for a reason unrelated to the stub. The router event must fire while the stage is actively `VALIDATING`, before the checkpoint transition.
- `tests/test_capture_report_integration.py::test_real_producers_drive_nonzero_report_rows` — asserts non-zero rather than exact values: strengthen to pin the exact row values its fixture computes to.
- `tests/test_capture_gate_check.py::test_level_reads_only_one_line` — the bounded-read test (payload on the second line, so it never exercises the unbounded path): rebuild on the divergence fixture (out-of-bounds token `full`, asserting the safe default `standard`); must fail against the unbounded `readline()`.
- `tests/test_capture_event_writer.py::test_standard_level_strips_freetext_payload` and `test_full_level_preserves_payload` — replace the single hand-built payload with a `schema.SOURCES`-driven enumeration; the standard-level fixture carries a free-text severity string nested inside a per-round entry and asserts it is stripped while the round's numeric fields survive. Ownership for the red-then-green runs: the nested-round fixture belongs to the per-round-detail slice; the `SOURCES`-driven enumeration belongs to the redaction-coverage slice — each rebuild's failing run is captured in its owning slice's completion notes.
- `tests/test_capture_gate_check_hardening.py::test_symlinked_config_refused` — add the missing `project_is_instrumented is False` assertion.
- `tests/test_install_migration.py` — `test_merge_alone_is_idempotent` already drives the merge-only path: confirm green. `test_second_run_is_idempotent` and `test_unrelated_hook_left_byte_intact` call the non-production `remove_hook_command` helper today: rewrite each to drive the production `merge_settings`-only path — two consecutive merges asserting the settings file is byte-identical after the second, and a merge over a file carrying an unrelated hook asserting that hook's entry survives byte-intact — with no `remove_hook_command` call. They stay distinct from the merge-alone test by pinning the second-run and unrelated-hook properties specifically. The file-level skip guard that skips the whole module when `remove_hook_command` is absent is removed as part of the rewrite — the rewritten tests no longer touch that helper, so the guard would silently skip production-path coverage.
- `tests/test_capture_hook_router.py` — the parked-run and no-state-file tests (lines 270, 303) assert the resolver's null-stage output through the real router: the only indirect resolver coverage in the suite, and it covers exactly the one terminal state the buggy hardcoded tuple gets right (which is why the suite stayed green). Confirm still green under the shared constant; owned by the stage-attribution slice.
- `tests/test_gates_spec.py` (the envelope-write assertions at 352-405) and `tests/test_gates_task_reviewer.py` (393-496) — assert the gates' own `PIPELINE_COMMAND` writes by invoking each gate's entry point directly: rebuilt under the single-writer resolution to assert the gate writes **no** envelope of its own (the chokepoint's single event per dispatch is asserted by the integration fixture); owned by the source-attribution slice.
- `tests/test_capture_chokepoint.py`, `tests/test_capture_chokepoint_integration.py`, `tests/test_capture_token_harvester.py`, `tests/test_report_rendering.py` — run to confirm the chokepoint, token, and render changes do not regress existing assertions; update any fixture that encoded the old (buggy) stage attribution. (The resolver has no direct coverage anywhere in the suite — its direct tests are net-new, listed above; the only indirect coverage is the two router tests named here.)

### Test infrastructure changes

- A real-producer-to-report integration fixture: drives an actual gate + task-completion through the writer into a `tmp_path` events file, then runs the report and the injector over it. Reused by the injection-seam and gate-rate tests.
- An install-seam fixture: invokes the installer's sentinel-creation and settings-merge against a `tmp_path` project, then runs the router. Reused by the install-guard test.

**Mocking justifications:** none. Every collaborator is code we own or the real filesystem via `tmp_path`. The clock is not mocked (tests assert marker shape and metric values, not timestamps). The bounded-read guard asserts a return value, not timing; only its optional companion wall-clock check is non-gating on flake, matching the existing overhead-budget test's convention.

### User verification steps

- UV-1: Run the installer in a Firebreak project, then make one tool call → `.fbk-capture/events.jsonl` exists and contains at least one event, with no hand-written `capture.cfg`. (covers AC-11)
- UV-2: Complete a working stage → the `## <STAGE> — metrics` block in the retrospective shows gate-rate and parks values, not only `stage:`/`spec:` lines. (covers AC-04)
- UV-3: Run a cycle with a known agent, then `fbk.py report <spec>` → the known-subagent count is non-zero. (covers AC-03)
- UV-4: On a stage whose spec gate failed once then passed, run the report → the first-try rate is below 1.0. (covers AC-05)
- UV-5: Run the report at `standard` after a multi-round code review → one row per round appears, not a single total. (covers AC-08)
- UV-6: Open a project whose `.fbk-capture/capture.cfg` is a single multi-megabyte line with no newline → tool calls remain responsive. (covers AC-10)

**UV-to-test mapping:** UV-1 → install-seam integration test; UV-2 → injection-seam integration test; UV-3 → subagent-count integration test; UV-4 → gate-rate integration test; UV-5 → per-round rendering integration test; UV-6 → bounded-read divergence unit test (plus its companion wall-clock check).

## Documentation impact

**Project documents to update**

- `docs/decisions-log.md` — append a remediation entry: the shared non-active-state constant, the install-time sentinel creation, and the gate-rate "all gate types" resolution (F-06).
- `ai-docs/hook-harvesting/hook-harvesting-retrospective.md` — add a Stage-8 (remediation-of-remediation) entry once the fixes land, recording that the independent pass found the predicted defect class recurring in the remediation's own code.
- `GLOSSARY.md` — no new terms; confirm "capture gate," "event envelope," and "chokepoint" entries still match the corrected behavior.
- `ai-docs/hook-harvesting/design/contracts.md` — correct the stage-summary contract's consumed-by line (the injector is its only caller; the report command never calls it), and record the resolved outcomes against the round-log and chokepoint contracts (`rounds_to_quiet` computed-or-removed; the gate-result "summarized at standard" wording corrected). The envelope contract's closed source enumeration stands unchanged — no new sources are registered now that the gates write no events of their own.

**New documentation to create**

- None. The capture/operator documentation the original spec deferred is tracked separately and is not part of this correctness pass.

## Acceptance criteria

- AC-01: `resolve_active_stage` returns no stage for the terminal state (`COMPLETED`) and for every checkpoint/idle state, and returns the stage only for a true working stage. *(F-01, F-05)*
- AC-02: The "not an active working stage" set is defined once (derived from `fbk/state.py`) and consumed by both `active_stage.py` and `report.py` by identity — both modules import the same object, the guard test asserts object identity (`is`), and no parallel literal or local copy remains. *(F-01, F-05)*
- AC-03: The report's known-subagent count reads the agent identity the router writes (`data["agent_type"]` / `data["is_known_agent"]`), and equals the exact number of known-agent events — the rebuilt guard test pins `source="hook_router"` and an exact expected count. *(F-02, F-13)*
- AC-04: The per-stage block produced by `stage_summary` and injected into the retrospective contains the stage's real gate-rate, parks, and rework values. *(F-04, F-12)*
- AC-05: First-try and after-rework pass rates include spec, task-reviewer, and code-review gate outcomes (read from `PIPELINE_COMMAND`), not only task-completion verification; the guard test pins an exact fraction (one fail-then-pass gate beside one first-try pass yields exactly 1/2). *(F-06)*
- AC-06: The after-rework boundary is derived from the first park recorded in the append-only `error_history` (the re-entry follows the park; the structure records parks, not re-entries), so a stage that parks and resumes more than once classifies its attempts correctly. *(F-07)*
- AC-07: A baseline lock created during an active write is honored — the locked-spec set is read inside the prune's lock scope, and a constructed concurrent test confirms the lines survive. *(F-08)*
- AC-08: At `standard` capture level the report renders per-round raised/survived/severity, not a single collapsed total. The code-review gate allowlist-projects each round entry to exactly `raised`, `survived`, and `severity` validated against the fixed enum — every other key dropped — before the event is written; the per-round numeric fields are not stripped by redaction, and redaction recurses into nested round entries as defense-in-depth. The guard fixture carries a nested free-text severity description (asserted stripped), a round entry bearing an unknown key with free text (asserted dropped by the projection), and an out-of-enum severity value (asserted rejected or normalised) — without the unknown-key case the guard cannot see the leak it exists to prevent. *(F-09)*
- AC-09: Per-stage token totals attribute turns during checkpoint/idle periods correctly; the guard test pins exact per-stage sums with every fixture turn accounted for, so no turn is dropped into a non-rendered bucket. *(F-10)*
- AC-10: The capture-gate config read is byte-bounded, so a `capture.cfg` that is one giant newline-less line cannot stall tool calls; both hot-path reads in `gate_check.py` are bounded, and the guard test proves the bound by divergence — the bounded read returns the safe default `standard` where the unbounded read resolves a non-default token (`full`) beyond the cap — not by timing. *(F-11, F-14)*
- AC-11: The installer creates the `.fbk-managed` sentinel, so a freshly-installed Firebreak project is instrumented and records events with no manual step. *(F-03)*
- AC-12: The spec and task-reviewer gates write no `PIPELINE_COMMAND` of their own — the chokepoint's event is the single record per dispatch, and the guard test asserts that one real dispatch through the chokepoint yields exactly one `PIPELINE_COMMAND` event for that command. *(F-16)*
- AC-13: `event_writer` checks `source` against `schema.SOURCES` and warn-but-writes: an unregistered source is written unchanged with a stderr warning — no event is ever dropped over a label, preserving the fail-silent guarantee — and every producer's tests pin its exact `source` string literal. *(F-21)*
- AC-14: The central-redaction test derives its producer list dynamically from `schema.SOURCES`, so a new producer that bypasses the writer is caught. *(F-15)*
- AC-15: An end-to-end test drives a real producer through the writer into the injector and asserts the injected block's metric content — guarding the injection seam against a silent regression. *(F-04, F-12)*
- AC-16: An end-to-end test runs the install routine then a router event and asserts capture armed — guarding the install→gate→capture seam. *(F-03)*
- AC-17: The chokepoint's not-instrumented and redirect-fail fast paths return an `int` (normalising `None` to `0`), and the type-checker is clean on `chokepoint.py` and `retention.py`. *(F-17, F-25)*
- AC-18: The dead `round_count` field is removed or rendered; the `rounds_to_quiet` contract metric is computed and written, or removed from IF-D-06; and the gate-result `output` field is either summarised at `standard` or the "summarized" contract wording is corrected. *(F-18, F-19, F-20)*
- AC-19: The two installer-migration tests exercise the production `merge_settings`-only path, and the symlinked-config test asserts `project_is_instrumented is False`. *(F-23, F-24)*
- AC-20: `settings.json` is written atomically — the temp file is created in the same directory as the target and renamed into place (a cross-filesystem temp location silently loses atomicity) — so an interrupted install cannot leave it truncated. *(F-22)*
- AC-21: The full suite passes with zero failures after all fixes, and every corrected test in AC-03/04/06/08/10/14/19 is demonstrated to fail against the pre-fix code — the feature-branch commit recorded at implementation start (`40ec021` at spec time; not the review's merge-base, which predates the capture package) — with the failing and passing runs captured in the owning slice's completion notes.

## Interface contracts

All entries are spec-originated (`IF-S`) — see `design/contracts.md` for why this remediation has no design-originated contracts. Signatures are summaries; the authoritative envelope shapes remain `IF-D-01`…`IF-D-10` in `ai-docs/hook-harvesting/design/contracts.md`, which this work does not change.

- id: IF-S-01
  name: Shared non-active-state set
  signature: A single constant (the states that are not an active working stage) defined in state.py beside WORKING_STAGES, imported by active_stage.py in place of its hardcoded tuple and by report.py in place of its parallel literal; state.py ownership keeps the import graph acyclic, because state.py already imports the capture package.
  invariants: resolve_active_stage returns no stage for any member (COMPLETED, PARKED, and every checkpoint/idle state) and a stage only for a true working stage; report.py excludes exactly the same set from ran_stages; the two never drift because there is one definition.
  covers: [AC-01, AC-02]
  design-ref: none
- id: IF-S-02
  name: Subagent identity field
  signature: report.count_known_subagents reads the agent identity from the SUBAGENT_STOP event's data.agent_type (or the precomputed data.is_known_agent), never the envelope source the hook_router stamps as the writer name.
  invariants: the count is non-zero exactly when known-agent SUBAGENT_STOP events are present; the envelope source ("hook_router") is never treated as an agent identity.
  covers: [AC-03]
  design-ref: none
- id: IF-S-03
  name: Stage-summary metric render
  signature: report.stage_summary(spec, stage) loads the events file and the state and renders the stage's real gate-rate, parks, and rework values beneath the provenance marker; retro_injector injects that block.
  invariants: the injected block contains metric values, not only the marker and stage/spec labels; the render reads the same producers the report command reads.
  covers: [AC-04, AC-15]
  design-ref: none
- id: IF-S-04
  name: Gate-rate classification across all gates
  signature: report.classify_gate_attempts reads pass/fail from VERIFICATION_RESULT and from PIPELINE_COMMAND outcomes whose command_name matches a known gate; the chokepoint is the single producer of those gate-outcome events, emitted through the writer to report.
  invariants: first-try/after-rework rates reflect spec, task-reviewer, and code-review gates, not only task-completion; a stage whose non-verification gate failed then passed shows a first-try rate below 1.0.
  covers: [AC-05]
  design-ref: none
- id: IF-S-05
  name: Rework boundary from history
  signature: report derives the after-rework boundary from the first park recorded in state.py's append-only error_history (the re-entry follows the park; the structure records parks, not re-entries), not the last-write-wins stage_timestamps READY key.
  invariants: a stage that parks and resumes more than once classifies attempts against the first park's boundary; the boundary is stable regardless of later transitions.
  covers: [AC-06]
  design-ref: none
- id: IF-S-06
  name: Retention locked-set under lock
  signature: event_writer reads the locked-spec set inside the prune's lock scope (or retention re-reads locked/ within its own locked section), so the protected set is current at prune time.
  invariants: a lock file created during an active write is honored; locked specs' lines are never pruned even under concurrent append+prune.
  covers: [AC-07]
  design-ref: none
- id: IF-S-07
  name: Per-round detail survives redaction
  signature: the code-review gate allowlist-projects each round entry at the untrusted round-log boundary (raised, survived, severity validated against the fixed enum; every other key dropped); schema keeps the per-round numeric fields out of FREETEXT_KEYS, and redact recurses into nested round entries as defense-in-depth; report renders one row per detection round at standard level.
  invariants: at standard capture level the per-round raised/survived/severity is present; no free-text payload leaks — free text under a known key is stripped by redaction, and free text under an unknown key never reaches the events file because the projection drops it.
  covers: [AC-08]
  design-ref: none
- id: IF-S-08
  name: Token boundary on working stages
  signature: report restricts the transition-boundary list handed to token_harvester to working stages, so turns during checkpoint/idle periods are not siphoned into non-rendered buckets.
  invariants: per-stage token totals are not understated; a turn during a checkpoint is attributed to the adjacent working stage.
  covers: [AC-09]
  design-ref: none
- id: IF-S-09
  name: Bounded hot-path config read
  signature: gate_check bounds both hot-path reads (the cfg-level read and the full-corroboration read) with an explicit byte cap on readline.
  invariants: a capture.cfg that is one giant newline-less line cannot stall a tool call; the safe default is returned on any read failure; the guard test proves the bound by divergence (safe default where the unbounded read resolves a token beyond the cap), not by timing.
  covers: [AC-10]
  design-ref: none
- id: IF-S-10
  name: Install-time capture marker
  signature: the installer creates the .fbk-managed sentinel (the single shared token gate_check keys on) under .claude/automation/ during install.
  invariants: a freshly-installed Firebreak project is instrumented with no manual step; the installer and gate_check agree on the sentinel name.
  covers: [AC-11, AC-16]
  design-ref: none
- id: IF-S-11
  name: Single-writer gate events and source validation
  signature: the spec and task_reviewer gates write no PIPELINE_COMMAND events of their own — the chokepoint is the single writer of gate-outcome events, stamping data.outcome, the resolved stage, and the gate's JSON stdout in the output field; event_writer checks source against schema.SOURCES and warn-but-writes — an unregistered source is written unchanged with a stderr warning; every producer's tests pin its exact source string.
  invariants: one dispatch yields exactly one PIPELINE_COMMAND event; each event's source identifies its true writer; an unregistered source is never silent (warning emitted) and never lost (event still written); a wrong-but-registered label is caught by the per-producer pinning tests, not the runtime check.
  covers: [AC-12, AC-13]
  design-ref: none
- id: IF-S-12
  name: Redaction coverage derived from the registry
  signature: the central-redaction test enumerates schema.SOURCES and asserts no standard-level record from any registered producer carries a free-text payload.
  invariants: a new producer that bypasses the central writer is caught by the test rather than silently invisible.
  covers: [AC-14]
  design-ref: none
- id: IF-S-13
  name: Structural and type cleanups
  signature: chokepoint fast paths return int (None normalised to 0); retention's optional-fcntl fallback is typed clean; rounds_to_quiet is computed-or-removed; the gate-result output field is summarised-or-its-contract-wording-corrected; the dead round_count is removed.
  invariants: the type-checker is clean on chokepoint.py and retention.py; no dead field or misleading contract wording remains.
  covers: [AC-17, AC-18]
  design-ref: none
- id: IF-S-14
  name: Installer test corrections and atomic write
  signature: the installer-migration tests exercise the production merge path; the symlinked-config test asserts not-instrumented; settings.json is written via a temp file created in the same directory as the target, then renamed into place.
  invariants: the migration tests guard the real installer path; an interrupted install cannot leave settings.json truncated.
  covers: [AC-19, AC-20]
  design-ref: none

## Uncovered acceptance criteria

- id: AC-21
  rationale: This is a global verification criterion (the whole suite passes and every corrected test is shown to fail against the pre-fix code), not a single interface contract. It is satisfied by the post-fix test run across all slices rather than by one contract, so it is recorded here rather than forced under an arbitrary contract's covers list.

## Open questions

None.

## Dependencies

- **The shipped feature branch** `fbk/hook-harvesting` — this spec remediates it in place; it must be the implementation base.
- **The independent review report** `ai-docs/hook-harvesting/fbk-cr-hook-harvesting-remediation.md` — the authoritative finding list (F-01…F-25) this spec closes.
- **`fbk/state.py`** — the home of the shared non-active-state constant; extended with that one pure constant beside `WORKING_STAGES`, no behavioral change.
- **The existing `fbk-scripts` pytest suite and venv** — no new third-party dependency; the hot-path reads stay dependency-free.

---

## Decisions resolved during scoping

- **Full tiered scope.** All 25 verified findings are in scope, tiered critical → major → minor so implementation can stop at a tier boundary. Rationale: the minors are cheap (mypy/dead-code/attribution cleanups) and several share a file with a major fix, so folding them in avoids a second touch of the same module.
- **Gate rates cover all gate types (F-06).** AC-05 resolves the review's intent question in favour of "all gate types" — the rate classifier reads `PIPELINE_COMMAND` outcomes for the spec, task-reviewer, and code-review gates, matching AC-07 of the original spec as written, rather than relabelling the metric as verification-only.
- **F-11 is in scope as a real gap.** The unbounded hot-path config read is treated as a genuine defect despite the review-stage Challenger's literal reading of "single-line read," because the feature's threat model names this exact denial-of-service and names a *bounded* single-line read as its mitigation.
- **Guard tests for both broken seams.** The remediation adds end-to-end tests for the injection seam and the install→gate→capture seam (AC-15, AC-16), implementing the standing pipeline control the retrospective recommended, because both seams broke while the suite stayed green.
- **Source validation is warn-but-write (F-21).** The writer checks `source` against `schema.SOURCES`; an unregistered source is written unchanged with a stderr warning. Rationale: after the subagent fix nothing reads `source` to compute any metric, so dropping a real event over a label mismatch would recreate the silent-data-loss failure class this remediation exists to kill, while the warning still surfaces typos and unregistered producers cheaply. The wrong-but-registered case — the actual mislabel the review found — is caught by the per-producer tests pinning each exact source string, not by any runtime check. Operator-confirmed at spec review (2026-06-12).
- **The gate-rate fix cannot be separated from stage attribution by a tier stop.** The rate classifier needs resolved stages on gate events, which needs the corrected resolver and the single-writer gate events (the chokepoint stamping resolved stages, the gates' duplicates removed); the `gate-rate-all-gates` slice therefore lands in the same tier as `stage-attribution-shared-constant` and `source-attribution-and-validation`, and no implementation stop boundary may fall between them.
- **The shared non-active-state constant lives in `fbk/state.py`.** `state.py` already imports the capture package at the top level, so homing the constant in the capture package and importing it back from the reporting chain would close an import cycle. Defining it beside `WORKING_STAGES` keeps every import edge one-directional.
- **The pre-fix demonstration reference is the feature-branch tip, not the review's merge-base.** The merge-base the review diffed against (`4437a6c`) predates the capture package entirely — tests run there fail on imports, demonstrating nothing. Corrected tests are demonstrated red-then-green against the branch commit recorded at implementation start (`40ec021` at spec time), with both runs captured in the owning slice's completion notes.
- **One gate dispatch writes one event (F-16; council-resolved, operator-confirmed at spec review 2026-06-12).** The spec and task-reviewer gates' own `PIPELINE_COMMAND` writes are removed; the chokepoint's event — which already carries the outcome, the resolved stage, and the gate's full JSON stdout in its `output` field — is the single record per dispatch. The previous "or document why both are needed" escape hatch was arithmetically incompatible with the exact-fraction gate-rate criterion (two events per dispatch double-count attempts, and the gate's own event carries no outcome field so it classifies as a fail). The alternative — gates as the classifier's source, chokepoint excluded by command name — would create a second two-module name agreement of exactly the parallel-literal kind the shared-constant fix eliminates. The gates' richer payload is retained unparsed in the chokepoint event's `output` field and can be promoted to its own event type if a consumer appears.
- **Round entries are allowlist-projected at the code-review gate (council-resolved, operator-confirmed at spec review 2026-06-12).** Redaction is a key denylist, and round entries arrive verbatim from the round-log file — untrusted input per the project threat model — so denylist recursion alone cannot satisfy the no-leak invariant: free text under an unknown key would pass through unseen, and a guard fixture using only known keys would stay green against the leak. The gate projects each entry to exactly `raised`, `survived`, and enum-validated `severity` before writing; the redaction recursion remains as defense-in-depth; the guard fixture covers the unknown-key and out-of-enum cases.

---

## Slices

```yaml
slices:
  - name: stage-attribution-shared-constant
    description: Define one non-active-state set in state.py beside WORKING_STAGES; active_stage and report import it (consumed by identity); resolver returns no stage for COMPLETED and checkpoint/idle states. Resolver tests are net-new in tests/test_capture_active_stage.py — resolve_active_stage has no direct coverage (the only indirect coverage is the two router tests asserting the null-stage cases the buggy tuple gets right; confirm them green), so there is no direct test to retire (the coverage absence is itself part of the defect)
    test-discipline: contract-evolving
    covers: [F-01, F-05]
  - name: subagent-identity-field
    description: Report reads agent identity from data.agent_type / data.is_known_agent, not the envelope source
    test-discipline: contract-evolving
    covers: [F-02, F-13]
    retired-tests:
      - tests/test_report_arithmetic.py::test_subagent_count_excludes_unknown_identity: built source=<agent-name>, a non-production envelope shape that masked the always-zero bug; rebuilt pinning source="hook_router"
  - name: installer-sentinel-and-atomic-write
    description: Installer creates .fbk-managed and writes settings.json via same-directory temp-then-rename
    test-discipline: new-contract
    covers: [F-03, F-22]
  - name: injection-render
    description: stage_summary loads events+state and renders real per-stage metrics into the injected block
    test-discipline: contract-evolving
    covers: [F-04, F-12]
    retired-tests:
      - tests/test_capture_retro_injector.py::test_injects_block_under_metrics_heading: heading-only assertion that passed against the metrics-less stub; extended to assert metric content
      - tests/test_capture_e2e_seam.py::test_two_source_cycle_joins_in_one_report: existing seam test asserting only the heading and provenance marker; strengthened in place to assert exact metric values rather than left as a weakened twin of the new guard, and re-choreographed so the router event fires while the stage is actively VALIDATING (after the resolver fix, an event fired post-transition carries no stage and would exit the asserted table for an unrelated reason)
  - name: gate-rate-all-gates
    description: classify_gate_attempts includes PIPELINE_COMMAND outcomes for spec/task-reviewer/code-review gates; depends on stage-attribution-shared-constant and source-attribution-and-validation (resolved stages on gate events) — lands in the same tier, no stop boundary between them
    test-discipline: contract-evolving
    covers: [F-06]
  - name: rework-boundary-from-history
    description: After-rework boundary derived from the first park in append-only error_history (the re-entry follows the park), not last-write-wins stage_timestamps
    test-discipline: contract-evolving
    covers: [F-07]
  - name: retention-locked-set-under-lock
    description: Locked-spec set read inside the prune lock scope so a concurrently-added lock is honored
    test-discipline: contract-preserving
    covers: [F-08]
  - name: per-round-detail-survives-redaction
    description: Code-review gate allowlist-projects round entries (raised/survived/enum-validated severity, unknown keys dropped) at the untrusted round-log boundary; per-round numeric fields kept out of FREETEXT_KEYS; redact recurses into nested round entries as defense-in-depth; report renders one row per round; dead round_count removed
    test-discipline: contract-evolving
    covers: [F-09, F-19]
    retired-tests:
      - tests/test_capture_event_writer.py::test_standard_level_strips_freetext_payload: single hand-built payload; rebuilt carrying the nested-round fixture (free text in a round stripped, numerics and enum tag survive, unknown-key entry dropped by the projection)
  - name: token-boundary-working-stages
    description: Token-boundary list restricted to working stages so checkpoint-period turns are not dropped
    test-discipline: contract-evolving
    covers: [F-10]
  - name: gate-config-read-bounded
    description: Both hot-path gate_check reads byte-bounded against a giant newline-less config
    test-discipline: contract-evolving
    covers: [F-11, F-14]
    retired-tests:
      - tests/test_capture_gate_check.py::test_level_reads_only_one_line: payload on the second line never exercised the unbounded path; rebuilt on the divergence fixture
  - name: source-attribution-and-validation
    description: Gates' own PIPELINE_COMMAND writes removed — the chokepoint is the single writer of gate-outcome events, asserted as exactly one event per real dispatch; writer warn-but-writes unregistered sources; per-producer tests pin exact source strings
    test-discipline: contract-evolving
    covers: [F-16, F-21]
    retired-tests:
      - tests/test_gates_spec.py (envelope-write assertions, 352-405): asserted the gate's own duplicate PIPELINE_COMMAND write; rebuilt to assert the gate writes no envelope of its own (the chokepoint's single event is the record)
      - tests/test_gates_task_reviewer.py (envelope-write assertions, 393-496): same rebuild as the spec-gate tests
  - name: redaction-coverage-from-sources
    description: Central-redaction test enumerates schema.SOURCES dynamically
    test-discipline: cross-cutting
    covers: [F-15]
    retired-tests:
      - tests/test_capture_event_writer.py::test_full_level_preserves_payload: single hand-built payload; rebuilt with the schema.SOURCES-driven enumeration alongside the new dynamic central-redaction test
  - name: structural-and-type-cleanups
    description: Chokepoint return-type normalisation, retention fcntl typing, rounds_to_quiet, output summary/contract wording
    test-discipline: contract-preserving
    covers: [F-17, F-18, F-20, F-25]
  - name: installer-test-corrections
    description: Idempotency/byte-intact tests use the production merge path; symlinked-config test asserts not-instrumented
    test-discipline: cross-cutting
    covers: [F-23, F-24]
  - name: seam-guards
    description: End-to-end guards for the injection seam and the install-to-capture seam
    test-discipline: cross-cutting
    covers: [F-04, F-03]
```
