# Observability Substrate — Feature Spec (Thin First Slice)

Release target: 0.5.2. Brownfield: this feature extends the existing hook-capture
measurement plane in `assets/fbk-scripts/fbk/`. Revised after Stage-3 review.

## Problem

Firebreak captures a continuous stream of harness events but the stream is
semantically blind: a live probe of 219 events showed every one with null stage
and no shape information. The richer per-agent context exists in the Claude Code
workflow journal, but that journal is scattered in a machine-local directory
outside the project and is never joined to the event stream. As a result the
retrospective an operator reads is narrated by an agent from memory rather than
assembled from involuntary signals. There is no durable, attributed, queryable
record of what actually happened in a workflow run.

## Goals / Non-goals

Goals:
- Add a closed five-shape work-capability vocabulary and resolve each unit to one shape.
- Stamp each unit's shape, topology, and asset-bundle identity through channels the harness records below the agent — never agent narration.
- Consolidate the harness event stream, the workflow journal, and the per-agent transcripts into one durable per-run record at workflow close.
- Finalize per run, robustly across many-runs-per-session and crash/restart, using already-wired hooks.
- Keep the durable record under the same capture-level redaction policy as the event stream.
- Deliver exactly one reader: a single-run retrospective view that queries the record.
- Prove the spine end to end with a purpose-built minimal workflow.

Non-goals (deferred, not dropped):
- Cross-run evaluation scorer, self-improvement reader, failure-attribution reader.
- The rich asset-bundle fields (instructions + decision-tree): structurally reserved in the record but populated only once the dynamic assembler exists to stamp them truthfully.
- Retrofitting the on-rails SDL ceremony onto the substrate.
- Background-workflow finalization via a dedicated completion hook; per-tool-call attribution; additional hook event types.
- Composition-feedback / dynamic assembly.

## User-facing behavior

The operator runs a code-defined Firebreak workflow. When it closes, a record
appears under `.fbk-capture/runs/<run-id>.json` with no command typed. Running
`fbk.py run-retro <run-id>` prints a per-unit table — kind of work (shape),
how it was organized (cardinality and stance), which persona was loaded,
duration, tokens, and gate outcome — assembled from the record, never narrated by
an agent. Null fields render as an em dash. A run that crashed mid-flight renders
with a partial-record warning rather than a misleading "complete" picture; a run
with no record prints an explicit "no harvest record" line. Reading the same
record twice prints identical output. Free-text content in the record honors the
project's capture level, exactly as the event stream does.

## Technical approach

The feature adds five new modules and extends three existing ones, following the
established capture-plane conventions (a single write chokepoint, fail-silent
hooks, available-vs-zero token semantics, per-project capture gating, and
realpath confinement of the capture directory). The harvest concern is split
across three focused single-responsibility modules (parse, engine, trigger) so
each compiles as a small, independently testable unit — see decision D-14;
the function signatures and behaviors are unchanged, only their file homes.

**New modules.**
- `fbk/shapes.py` — `SHAPE_VOCABULARY` (frozenset: `distill`, `implement`, `review`, `synthesize`, `gate`) and `resolve_shape(raw)`; a persona/value that maps to nothing returns `None` (never an invented shape).
- `fbk/attribution.py` — `parse_attribution(first_message_text)`: extracts the launch-prompt descriptor from the first transcript message (regex `<!--fbk-attr (\{.*?\})-->`, `re.DOTALL`, first match only) and returns cardinality/stance (+ asset_bundle when present) with `attribution_absent` true on a missing or malformed block; never raises.
- `fbk/harvest.py` — `harvest(run_id, project_cwd)`. Resolves the run directory (projects root from `FBK_PROJECTS_ROOT`), reads the `workflow journal` (`journal.jsonl`) as the authoritative agent roster, filters `events.jsonl` to those `agent_id`s, joins the `agent transcript` files (using `attribution.parse_attribution` and the token accessor) for the descriptor and token usage, redacts free-text at the resolved capture level, and writes the `run record` through the confined capture path.
- `fbk/finalize.py` — the hook-invoked `finalize_runs(hook_event_name, cwd, payload=None)` trigger, a thin wrapper that locates closed-unfinalized runs and calls `harvest`.
- `fbk/run_retro.py` — the only reader. Exposes `main()` (reads `sys.argv` for the run id, `os.getcwd()` for the project) delegating to `run_retro(run_id, project_cwd)`; registered in `COMMAND_MAP` as `run-retro`.

**Attribution channel (minimal descriptor).** The workflow glue prepends a
`<!--fbk-attr {json}-->` block to each agent prompt carrying the two
deployment-level facts the harness cannot otherwise expose: `cardinality`
(`single`/`fan-out`) and `stance` (`collaborative`/`adversarial`). `shape` is
derived from the persona name (`agent_type`, recorded on `SubagentStop`) via
`resolve_shape`. The record's `asset_bundle.persona` is set from the persona
name; `asset_bundle.instructions` and `asset_bundle.decision_tree` are present in
the schema but null in this slice — reserved for the dynamic assembler that will
stamp them truthfully later (forward-compatible, no migration).

**Run identification (verified).** The `Workflow` tool result text contains
`Transcript dir: …/subagents/workflows/<run-id>`. The router passes the hook
payload it already read to `finalize_runs` as a third argument, and
`finalize_runs` parses the run id from the `Workflow` response inside that
payload. On `PostToolUse(Workflow)` the trigger finalizes ONLY that parsed run —
the run the Workflow tool just returned, which is therefore closed — and does not
sweep. On `SessionStart` no payload run id is present, so the trigger sweeps the
newest closed-unfinalized run on disk. On any other event the trigger no-ops.
The trigger, not `harvest`, is the closure authority: `harvest` takes no closure
parameter and assumes its caller has already established the run is closed (see
decision D-16). Run-id parsing lives in `harvest.py`, not the router; the router
only forwards the payload.

**Run-directory resolver (net-new).** No existing code resolves the nested run
directory (`token_harvester` receives pre-resolved paths; `report.py` uses a
different flat layout). `harvest` locates the run directory by globbing
`<projects-root>/*/*/subagents/workflows/<run-id>/` and matching the run id —
avoiding any dependency on the undocumented project-hash algorithm. The
projects-root is read from the `FBK_PROJECTS_ROOT` environment variable,
defaulting to `~/.claude/projects` when unset — the injectable test seam that
points resolution at a `tmp_path` root rather than the real home directory
(mirrors the existing `CLAUDE_CONFIG_DIR` override in `gate_check`).

**Finalization (two already-wired triggers).** `hook_router` calls
`finalize_runs` on `PostToolUse` (the `Workflow` tool) and on `SessionStart`,
inside the existing `project_is_instrumented` gate. `PostToolUse(Workflow)` is
the normal-close path: it finalizes ONLY the run whose id it parses from the
`Workflow` tool response — the just-returned, hence closed, run — and does NOT
sweep, because a mid-session sweep could finalize a still-live concurrent
workflow for which there is no closure proof. `SessionStart` is the recovery
sweep: a run id is never reopened, so at any session start every run directory on
disk is closed-forever (nothing live can extend it) — this is the one event where
the closed-forever invariant holds for every on-disk run — including runs orphaned
by a prior crashed session, which the single-session-per-project sandbox
constraint makes safe to sweep; the `SessionStart` sweep finalizes the newest
closed-unfinalized run. On any other hook event `finalize_runs` returns
immediately (no-op). `SessionEnd` and `TaskCompleted` are not used: `SessionEnd`
is subsumed by the next `SessionStart`, and `TaskCompleted` is wired to the SDL
gate, not the router. Background runs finalize on the next `SessionStart`
(accepted latency). To stay within the 15-second fail-silent hook budget, the
`SessionStart` sweep finalizes at most the newest closed-unfinalized run per
trigger; the next trigger catches the rest. The no-op check for an
already-finalized run reads only the `finalized` flag and file existence, never a
full re-parse. `finalize_runs` never raises into the router, which stays exit 0.

**Finalization correctness.** A record is finalized only for a closed run (its
`Workflow` call returned, or a restart proves nothing live can extend it) —
never on mid-run journal balance, which cannot tell "done" from "done so far."
Because the trigger only ever calls `harvest` on a run it has already established
is closed, every `harvest` ALWAYS writes `finalized=true`; the function carries no
closure parameter and never decides closure itself. `harvest` is idempotent: a
re-harvest of an existing finalized record reads only the `finalized` flag and
file existence and no-ops, preserving `harvested_at` by value. `harvested_at` is
set on the first harvest and preserved across re-harvests so attributed content is
reproducible. The timestamp is read through a module-level `_utcnow()` helper in
`harvest.py` (returning a tz-aware UTC datetime) so tests can monkeypatch it to a
fixed value — the injected-clock seam the idempotency and determinism tests need.
The write is atomic: a unique per-writer temp name (pid/uuid) then `os.replace`,
resolved through `gate_check._real_capture_dir` so a symlinked `.fbk-capture/`
cannot redirect it. Confinement extends to the `runs/` subdir itself: after
resolving the real capture dir, `harvest` refuses the write (returns an error,
writes nothing) when `runs/` is a symlink or its realpath escapes the confined
capture dir — closing the `runs/`-only redirect that `_real_capture_dir`, which
checks `.fbk-capture/` alone, does not cover. Completeness is `clean-complete` (every `started`
has a `result`, transcripts readable) or `truncated` (gaps recorded as absent,
never invented or dropped).

**Privacy (capture-level parity).** The record is a durable free-text sink and
must honor the same policy as `events.jsonl`. `harvest` reads
`resolve_capture_level(cwd)`: at `off` it writes no free-text record; otherwise
it routes the record's free-text fields (`journal_result` and any
descriptor-derived strings) through `schema.redact()` at the resolved level
before the atomic write. The two sinks share one redaction policy.

**Runtime value precision.**
- Hook event names used as triggers: `PostToolUse` (tool `Workflow`) and `SessionStart`. Join-relevant events: `SubagentStop`, `SubagentStart`.
- Run dir: `~/.claude/projects/<project-hash>/<session-uuid>/subagents/workflows/<run-id>/`, located by glob-and-match on `<run-id>`.
- Journal lines: `{"type":"started"|"result","agentId":"…","result":{…}}`. Join key: event `data.agent_id` == journal `agentId`.
- Token usage fields (summed across an agent's turns): `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`.
- Descriptor sentinel: `<!--fbk-attr {json}-->`, parsed from the transcript's first (launch) message with regex `<!--fbk-attr (\{.*?\})-->` compiled `re.DOTALL`, first match only.
- Record path: `<cwd>/.fbk-capture/runs/<run-id>.json`.
- Projects-root env seam: `FBK_PROJECTS_ROOT` (default `~/.claude/projects`).
- Harvest clock seam: module-level `_utcnow()` in `harvest.py`.
- Reader output literals (fixed so test and reader agree): an absent record
  prints a line containing the exact substring `no harvest record`; a malformed
  (unparseable JSON) record prints a line containing the exact substring
  `malformed record`; an unfinalized or `truncated` record prints a warning line
  containing the exact substring `partial record`. The malformed and absent
  literals are distinct so the reader tells a corrupt record from a missing one.

**Integration seams.**
- [ ] hook_router → harvest: finalize-trigger invocation passes the hook event name, cwd, and the hook payload, inside the instrumentation gate; harvest must never raise into the router (router stays exit 0).
- [ ] harvest → workflow journal: `journal.jsonl` is the agent roster; the run directory is located by glob-and-match on the run id.
- [ ] harvest → events.jsonl: filter `SubagentStop`/`SubagentStart` by roster `agent_id`.
- [ ] harvest → agent transcript: first-message descriptor parse plus token usage fields summed across turns.
- [ ] harvest → run record: the per-run JSON schema, free-text redacted at the resolved capture level, written through the confined path.
- [ ] run_retro → run record: the reader reads the record and renders deterministically.

**Module touch policy.**
- [ ] fbk/capture/hook_router.py: extend (call finalize_runs after the existing write, inside the project_is_instrumented gate, forwarding the already-read hook payload as the third argument; the router does not itself parse the Workflow tool-response run id — that parsing lives in harvest.py; no change to existing event-write behavior).
- [ ] fbk/__init__.py COMMAND_MAP: extend (register `run-retro`; co-land with the importable reader module).
- [ ] fbk/capture/token_harvester.py: extend (add a public per-transcript token accessor that aggregates across turns, reusing `_parse_transcript`).
- [ ] fbk/capture/schema.py: leave alone (reuse `redact()`; no new event type).
- [ ] fbk/capture/gate_check.py: leave alone (reuse `project_is_instrumented`, `resolve_capture_level`, `_real_capture_dir`).
- [ ] fbk/report.py: leave alone (the new reader is separate).

## Testing strategy

**New tests needed.**
- Unit: `resolve_shape` maps a known persona to a vocabulary member and an unknown value to `None` (no invented shape) — covers AC-01.
- Unit: descriptor parse — a valid first-message sentinel yields cardinality and stance; a forged `<!--fbk-attr-->` block in *agent output* (a later message) does not override the launch descriptor; a missing or malformed block yields all-null attribution with `attribution_absent=true` — covers AC-02.
- Integration: `harvest` uses the journal roster to filter `events.jsonl`, emits one unit per roster agent, and two fixture runs with separate journals produce non-overlapping records — covers AC-03.
- Integration (round-trip join key): drive the real `hook_router` with a `SubagentStop` payload carrying `agent_id`, read the written `events.jsonl`, and run `harvest` against that live file — confirms the `data.agent_id`/`agentId` join survives the full round-trip — covers AC-03.
- Unit: `harvest` completeness — all started→result yields `clean-complete`; a started lacking a result yields `truncated` with that unit's `journal_result_present=false` and `journal_result` null, while its attribution reflects its transcript's descriptor parse and is not forced absent by the missing result — covers AC-04.
- Unit: `harvest` atomic + idempotent — write goes through a unique temp name then replace; a second harvest *after a mutation to the run directory* (e.g. an appended journal line) leaves attributed content unchanged and `harvested_at` equal by value to the first — proving the finalized no-op runs, not just fixture determinism — covers AC-05.
- Integration: `finalize_runs` parses and finalizes the run id from a fixture `Workflow` tool response on `PostToolUse` (finalizing only that run, no sweep), sweeps the newest closed run on `SessionStart`, no-ops on any other event, and never raises (router still exits 0) — covers AC-06.
- Integration (crash recovery): a run directory left with started-but-no-result by a prior session is finalized as `truncated` on the next `SessionStart` sweep — covers AC-07.
- Unit: `run_retro` renders per-unit fields with em-dash for null; output is identical when read at two different mocked clock values, and unit ordering is stable and content-derived; a missing file prints the "no harvest record" line and a truncated/unfinalized record prints a partial-record warning — covers AC-08.
- Unit: `COMMAND_MAP` contains `run-retro` resolving to `fbk.run_retro`, and `fbk.run_retro` exposes an importable `main()` invocable through the dispatcher — covers AC-09.
- Unit: the record carries `schema_version` and `run_retro` tolerates an added unknown top-level key without error — covers AC-10.
- Unit: the token accessor sums the four usage fields across an agent transcript's turns and marks `tokens_available=false` for an unreadable transcript (asserting the accessor's own flag, not the underlying parser) — covers AC-12.
- Unit: at capture level `off` `harvest` writes no free-text record; at `standard` the record's `journal_result` and descriptor-derived free-text are redacted via `schema.redact()` — covers AC-13.
- Unit: the harvest write resolves through `gate_check._real_capture_dir`; a symlinked `runs/` target is refused, and concurrent harvests use distinct temp names — covers AC-14.
- E2e: run the conformance workflow, then `run-retro` — all three units show non-null shape, cardinality (one single, two fan-out), and stance (one adversarial), with `asset_bundle.persona` populated; the record present after a normal close with no operator command; readable after the project directory is moved — covers AC-11, UV-1, UV-2, UV-3, UV-5.

**Existing tests impacted.**
- `tests/test_dispatcher.py::test_command_map_contains_all_19_commands` — registering `run-retro` raises the count to 20; update the count and the `expected_commands` set. This is the contract-evolving change in the `run-retro-reader` slice.
- `tests/test_dispatcher.py::test_each_command_resolves_to_importable_module` — iterates `COMMAND_MAP` and imports each value; needs no edit but requires `fbk.run_retro` to be importable, so command registration must co-land with the reader module.
- `tests/test_capture_hook_router.py` — the router gains a `finalize_runs` call; existing event-write assertions must stay green, and a new test must confirm the router exits 0 when finalize raises internally and when invoked against a run directory containing an unreadable transcript (reuse `write_unreadable_transcript`).
- `tests/test_capture_e2e_seam.py` and `tests/test_install_seam.py` — both drive `hook_router` end-to-end via subprocess and assert on written events; they must stay green after the `finalize_runs` call is added.
- `tests/test_capture_token_harvester.py` — adding the public accessor must leave existing token tests green.

**Test infrastructure changes.**
- A fixture builder that constructs a fake workflow run directory (`journal.jsonl` with started/result lines, `agent-<id>.jsonl` with a first-message launch prompt carrying the descriptor plus usage fields, `agent-<id>.meta.json`) under a `tmp_path` projects root, extending `tests/capture_fixtures.py`.
- An `events.jsonl` fixture with `SubagentStart`/`SubagentStop` events carrying `agent_id`, reusing existing capture fixtures.
- The projects-root path is injected via parameter/env so tests point resolution at `tmp_path` rather than the real home directory.

**Mocking justifications.**
- Clock: `harvested_at` reads wall-clock time — non-deterministic and OS-owned; a stand-in clock (injected or monkeypatched timestamp) is justified for the idempotency and determinism assertions.
- Filesystem and the session-runtime journal/transcripts: not mocked. Real `tmp_path` files stand in for the externally-written run directory, so the join and the round-trip join-key test exercise real file I/O. No mock for code we own.

**User verification steps.**
- UV-1: Run the conformance workflow → it completes and a run directory with a journal and per-agent transcripts exists.
- UV-2: Look in `.fbk-capture/runs/` after the run closes → a `<run-id>.json` record is present, with no command typed.
- UV-3: Run `fbk.py run-retro <run-id>` → the table shows three units with non-null shape, one `single` and two `fan-out` cardinalities, one `adversarial` stance, and a persona each.
- UV-4: Run `fbk.py run-retro <run-id>` again → byte-identical output.
- UV-5: Move the project directory and run `fbk.py run-retro <run-id>` → the same record renders with no reconstruction.

UV-1/UV-2/UV-3/UV-5 map to the conformance e2e test (AC-11); UV-4 maps to the determinism test (AC-08).

## Documentation impact

**Project documents to update.**
- `docs/architecture-overview.md` — update the "Measurement (in progress)" section to describe the substrate: the shape/topology vocabulary, harvest-at-close, the per-run record, the capture-level parity, and the `run-retro` reader. Durable-doc change to review with the operator before applying.
- `GLOSSARY.md` — add entries for shape, topology, asset bundle, and workflow journal.
- `CHANGELOG.md` — add the substrate under Added for 0.5.2.
- `README.md` — check whether the command list needs the `run-retro` reader.

**New documentation to create.** The conformance workflow under `ai-docs/observability-substrate/conformance/` is net-new work, not a pre-existing artifact: a runnable three-agent code-defined workflow whose glue emits the minimal descriptor. It is the only artifact that exercises the spine end to end and must be authored as part of the slice. Its verification is the manual operator procedure (UV-1/2/3/5) — running the real workflow against the live harness is the one thing a fixture-based test cannot do, so there is no automated pytest e2e for it; automated regression for the harvest and reader logic comes from the fixture-driven integration tests. The conformance task therefore delivers the workflow script, its descriptor-emitting glue, and the documented manual procedure.

Note: `.fbk-capture/` carries its own `.gitignore` that ignores all contents, so `runs/` records are untracked by inheritance — no `.gitignore` change is required. This is what "portable" means for the record: self-contained on disk and surviving a directory move (the move-the-project verification), NOT git-tracked. The gitignored state is intended; records travel when the folder is copied or moved, not via git.

## Acceptance criteria

- AC-01: `fbk/shapes.py` exposes a closed five-member shape set; `resolve_shape` returns a member for a known persona/value and `None` for an unknown one, never an invented shape.
- AC-02: a first-message `<!--fbk-attr {…}-->` sentinel yields parsed cardinality and stance; a forged block in agent output does not override it; a missing or malformed block yields all-null attribution with `attribution_absent=true`.
- AC-03: `harvest` reads the run's workflow journal as the agent roster, filters `events.jsonl` to those `agent_id`s, and emits one unit per roster agent; the join key survives a real-router round trip; two concurrent runs produce non-overlapping records.
- AC-04: a closed run is `clean-complete` only when every `started` agent has both a `result` and a readable transcript; any gap makes the run `truncated`. A `started` lacking a `result` is recorded with `journal_result_present=false` and its `journal_result` null; a `started` whose transcript cannot be read is recorded with `tokens_available=false`; either gap downgrades the run to `truncated` so the operator sees a partial record rather than a false "complete." A gapped unit's attribution is still whatever the descriptor parse of its (existing) transcript yielded — attribution is NOT forced absent by a missing result (the two facts are independent; see decision D-17).
- AC-05: `harvest` writes the record via a unique temp name then `os.replace`; a re-harvest after a run-directory mutation preserves `harvested_at` by value and leaves attributed content unchanged.
- AC-06: `finalize_runs` is invoked from `hook_router` on `PostToolUse`(Workflow) and `SessionStart`; on `PostToolUse` it parses and finalizes the run id from the `Workflow` response (and does not sweep), on `SessionStart` it sweeps the newest closed run, on any other event it no-ops, and it never raises into the router.
- AC-07: a run is finalized only when closed (the closed-forever invariant: `PostToolUse` fires after the run returns; `SessionStart` sees only dead run directories); finalization never occurs on a mid-run balance.
- AC-08: `run_retro` renders per-unit shape, topology, persona, duration, tokens, and gate outcome from the record; output is byte-identical across repeated reads — a pure function of the record, independent of wall-clock time (the reader holds no clock of its own) — with stable content-derived ordering and no agent invocation; a missing file prints the "no harvest record" line and a truncated/unfinalized record prints a partial-record warning.
- AC-09: `run-retro` is registered in `COMMAND_MAP` and `fbk.run_retro` exposes an importable `main()` invocable as `fbk.py run-retro <run-id>`.
- AC-10: the run record carries `schema_version` and the reader tolerates an added top-level key without error.
- AC-11: running the purpose-built conformance workflow then `run-retro` shows non-null shape, topology, and persona for all three units, with at least one `single` and one `fan-out` cardinality, the record present under `.fbk-capture/runs/` after a normal close with no operator command, and readable after the project directory is moved.
- AC-12: the token accessor sums the four usage fields across an agent transcript's turns; an unreadable transcript marks `tokens_available=false` rather than recording zero.
- AC-13: at capture level `off` `harvest` writes no free-text record; otherwise the record's `journal_result` and descriptor-derived free-text are passed through `schema.redact()` at the resolved level before the write.
- AC-14: the harvest write resolves through `gate_check._real_capture_dir` (refusing a symlinked target) and uses unique per-writer temp names so concurrent harvests cannot clobber each other.

## Interface contracts

- id: IF-D-01
  name: Launch-prompt attribution descriptor
  signature: workflow glue prepends `<!--fbk-attr {json}-->` to each agent prompt carrying cardinality and stance (and optionally asset_bundle.persona); harvest extracts it from the first message of the agent transcript via `<!--fbk-attr (\{.*?\})-->` (re.DOTALL, first match) and json-parses it. shape is derived from the recorded persona name; asset_bundle.instructions and asset_bundle.decision_tree are reserved null in this slice.
  invariants: pre — the block, when present, is valid JSON in the launch (first) message, never read from agent output; post — first sentinel block wins, unknown keys ignored; error — missing/malformed block yields all-null attribution with attribution_absent=true, never a raise or invented value.
  covers: [AC-02]
  design-ref: design/contracts.md#if-d-01
- id: IF-D-02
  name: Shape vocabulary and resolver
  signature: `SHAPE_VOCABULARY` frozenset {distill, implement, review, synthesize, gate} and `resolve_shape(raw: str | None) -> str | None` mapping a persona name to a member in fbk/shapes.py.
  invariants: pre — raw may be any string or None; post — return is always a member or None; error — an unmapped non-null raw returns None with a stderr warning, never a string outside the set.
  covers: [AC-01]
  design-ref: design/contracts.md#if-d-02
- id: IF-D-03
  name: Harvest join
  signature: `harvest(run_id: str, project_cwd: str) -> HarvestResult` where HarvestResult carries record_path, unit_count, units_with_full_attribution, completeness, finalized, error; locates the run directory by glob-match, reads the workflow journal as roster, filters events.jsonl to those agent_id, joins the agent transcript per agent, redacts free-text at the resolved capture level, and writes the run record through the confined path. It takes no closure parameter — the caller (the trigger) is the closure authority — so it ALWAYS writes finalized=true.
  invariants: pre — project_cwd absolute and instrumented, run_id non-empty, the caller has established the run is closed; post — on success the record exists with finalized=true, valid JSON, written atomically via unique-temp-then-replace under gate_check._real_capture_dir, with free-text redacted at the resolved level (no free-text record at level off); a re-harvest of an existing finalized record reads only the finalized flag and file existence and no-ops, preserving harvested_at by value; error — a missing journal yields a truncated record (no fabricated units), an unreadable events.jsonl returns error and writes nothing.
  covers: [AC-03, AC-04, AC-05, AC-13, AC-14]
  design-ref: design/contracts.md#if-d-03
- id: IF-D-04
  name: Finalization trigger
  signature: `finalize_runs(hook_event_name: str, cwd: str, payload: dict | None = None) -> None`, invoked from hook_router on PostToolUse(Workflow) and SessionStart inside the instrumentation gate, with the router forwarding the hook payload it already read. On PostToolUse(Workflow) it parses the run id from the Workflow response and finalizes ONLY that just-returned (hence closed) run — it does not sweep, since a mid-session sweep has no closure proof for a concurrent live workflow. On SessionStart it sweeps the newest closed-unfinalized run, the closed-forever invariant holding for every on-disk run at session start. On any other event it returns immediately. The trigger is the sole closure authority and calls harvest only on a run it has established is closed.
  invariants: pre — router confirmed the project is instrumented; post — on PostToolUse the parsed run is finalized and no other run is swept, on SessionStart the newest closed-unfinalized run is finalized, on any other event nothing happens; an already-finalized run is a cheap no-op (finalized-flag/existence check only); finalization occurs only for closed runs; error — a per-run failure is isolated and the trigger never raises into hook_router (which stays exit 0).
  covers: [AC-06, AC-07]
  design-ref: design/contracts.md#if-d-04
- id: IF-D-05
  name: Durable run record store
  signature: on-disk `.fbk-capture/runs/<run-id>.json` — one JSON object with schema_version, run_id, finalized, completeness, units[], phases[], ceremony_metrics — produced by harvest, consumed by run_retro and future readers.
  invariants: pre — file name is the harness run_id, write resolved through gate_check._real_capture_dir; post — the run record is self-contained and portable (no absolute or session-local paths) — "portable" meaning self-contained on disk and surviving a directory move (the move-the-project verification), NOT git-tracked — and new top-level keys may be added without changing existing keys; error — a malformed or missing file is reported explicitly by the reader with two distinct fixed literals — an absent record prints `no harvest record`, a malformed (unparseable JSON) record prints `malformed record` — not treated as an empty run.
  covers: [AC-05, AC-10, AC-14]
  design-ref: design/contracts.md#if-d-05
- id: IF-D-06
  name: Retrospective reader query
  signature: `run_retro(run_id: str, project_cwd: str) -> None` plus an importable `main()` reading sys.argv and os.getcwd(), exposed as `fbk.py run-retro <run-id>`, rendering the run record to stdout (null fields as em dash).
  invariants: pre — run_id non-empty, project_cwd absolute, no instrumentation required to read; post — output is deterministic (identical at two clock values, stable content-derived ordering) with no agent invocation and no re-derivation from events.jsonl; error — a missing file prints the no-record line and a truncated/unfinalized record prints a warning, neither raises.
  covers: [AC-08, AC-09]
  design-ref: design/contracts.md#if-d-06
- id: IF-S-01
  name: Per-transcript token accessor
  signature: a public function in token_harvester returning the four usage fields (input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens) summed across one agent transcript's turns, plus an availability flag, reusing `_parse_transcript`.
  invariants: pre — the path may be unreadable or absent; post — a readable transcript returns the four summed counts with available true; error — an unreadable transcript returns available false rather than zero counts.
  covers: [AC-12]
  design-ref: none

## Uncovered acceptance criteria

- id: AC-11
  rationale: this is an end-to-end behavior that spans every contract (descriptor → harvest → record → reader) rather than a single seam; it is validated by the cross-cutting conformance slice's e2e test, not by one contract's covers list.

## Open questions

None.

## Dependencies

- The existing capture spine (`hook_router`, `event_writer`, `schema.redact`, `gate_check.project_is_instrumented`/`resolve_capture_level`/`_real_capture_dir`, `active_stage`) — inherited; all capture guarantees remain in force.
- The `agent_id`/`agentId` join key (added in PR #10) — already satisfied; a regression removing it from `SubagentStop` would break the harvest.
- The Claude Code session runtime's workflow journal and transcript layout — external and undocumented; the glob-and-match resolver avoids depending on the project-hash algorithm, but the directory layout itself remains a stability assumption.
- `token_harvester._parse_transcript` — reused via the new accessor.
- Python 3 standard library only (json, re, os, pathlib, glob) — no new third-party dependency.

## Slices

```yaml
slices:
  - name: shape-vocabulary
    description: closed five-shape set and resolver in fbk/shapes.py
    test-discipline: new-contract
    covers: [B-001]
  - name: attribution-descriptor
    description: minimal launch-prompt descriptor (cardinality, stance) parse plus persona-derived shape; rich bundle fields reserved
    test-discipline: new-contract
    covers: [B-002, B-003]
  - name: harvest-join
    description: glob-match run-dir resolve, journal-roster join, capture-level redaction, confined idempotent atomic write into the durable record
    test-discipline: new-contract
    covers: [B-006]
  - name: finalization-trigger
    description: hook-invoked finalize_runs on PostToolUse(Workflow) and SessionStart with bounded sweep and closed-forever finalization
    test-discipline: new-contract
    covers: [B-005]
  - name: conformance-and-stamping
    description: purpose-built three-agent workflow that emits the descriptor and proves the spine end to end
    test-discipline: cross-cutting
    covers: [B-004]
  - name: run-retro-reader
    description: single-run retrospective reader with a main() entry registered in COMMAND_MAP
    test-discipline: contract-evolving
    covers: [B-007]
    retired-tests:
      - test_command_map_contains_all_19_commands: the exact-19-commands contract no longer holds once run-retro is registered; replaced by a count of 20 and an updated expected set
  - name: record-extensibility
    description: record schema_version and reader tolerance of added top-level keys for future readers
    test-discipline: cross-cutting
    covers: [B-008]
```

---

## Decisions resolved during scoping and review

- **Two triggers, not four.** Finalization fires on `PostToolUse(Workflow)` and `SessionStart`. `TaskCompleted` is wired to the SDL gate (not the router) and `SessionEnd` is subsumed by the next `SessionStart`; both dropped. Background runs finalize on the next `SessionStart`.
- **Quiescence guard dropped.** It defended against concurrent same-project sessions (prevented by the sandbox) and required durable cross-process state; the closed-forever invariant covers the slice. Re-add in one function if the single-session constraint is ever relaxed.
- **Minimal descriptor.** The descriptor carries cardinality and stance; shape derives from the recorded persona; `asset_bundle.persona` is set and the rich fields (instructions, decision-tree) are reserved null until the dynamic assembler can stamp them truthfully — chosen over hand-declaring throwaway richness now.
- **Capture-level parity.** The record honors the project's capture level: no free-text record at `off`, `schema.redact()` at the resolved level otherwise — closing the redaction-bypass the Security review found.
- **Run id is recoverable; resolver is net-new.** The `Workflow` tool result carries the transcript dir (run id); the run directory is located by glob-and-match, not by reversing the undocumented project-hash.
- **Launch prompt and token fields verified on disk.** The launch prompt is the transcript's first message; the four usage fields are present and summed across turns.
