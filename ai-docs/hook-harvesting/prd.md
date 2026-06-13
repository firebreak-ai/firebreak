# PRD: Deterministic Metrics Plane (Hook Harvesting)

## Vision

Firebreak becomes self-measuring. After every structured development cycle, a machine-generated table of facts — stage durations, gate outcomes, rework counts, scope violations, code-review detection rates, and token spend — is available to anyone who runs a single command. That table lands automatically in the retrospective file, so the agent interprets data instead of constructing it from memory. Changes that claim to reduce rework can be evaluated against before-and-after numbers; harness improvements no longer require a full benchmark run to demonstrate effect.

## Problem statement

Firebreak's only performance record today is the retrospective markdown, which agents append by hand at the end of a development cycle. This record has three compounding defects.

First, it is anecdotal. Agents narrate outcomes rather than count them, so there are no rates, no denominators, and no way to aggregate across cycles. "Rework occurred" and "rework occurred in three of seven tasks" are not equivalent observations, and the current record produces only the former.

Second, it is unreliable. Appending the retrospective is an instruction, and instructions erode under context pressure. A session that runs long, encounters errors, or parks and resumes is more likely to produce a thin or absent retrospective than a short, clean one. The sessions where measurement matters most are the ones least likely to produce it.

Third, it is not queryable. A narrative paragraph cannot answer "what fraction of gate attempts passed on the first try in the last five cycles?" The question is unanswerable today even in principle.

The consequence is that the queue of features meant to reduce rework — interface contracts, the wave-commit model — cannot be evaluated before and after they ship. Without a measurement plane, improvement claims are stories, not evidence. The most expensive feedback loop available (a full benchmark run) remains the only way to detect whether a harness change made things better or worse.

## Goals and non-goals

**Goals**

- Capture pipeline events deterministically, from code, without relying on agents to record them.
- Record the outcomes of every gate attempt, every park, every verification run, every code-review detection round, and every subagent completion — with enough precision that a report command can compute rates and ratios, not just lists.
- Capture token spend per stage from session transcripts after the fact, joined to pipeline stages via existing state timestamps.
- Produce a report that an operator can run at any point in a cycle for a spot check, and that is automatically injected into the retrospective without agent involvement.
- Keep the capture invisible to normal pipeline operation: no stdout, no broken tool calls, no pipeline commands interrupted by a capture failure.
- Gate capture to projects that have opted in, so the globally-installed hook router does not silently record activity in unrelated projects.

**Non-goals**

- No live telemetry collector. There is no streaming pipeline, no OpenTelemetry integration, and no central server receiving events.
- No change to the agent's narrative role in the retrospective. The agent still writes interpretive prose; this feature adds the machine-recorded table the agent interprets. No agent-side recording instruction is added or removed.
- No cross-project aggregation write path. Joining data from multiple projects is a manual sweep run outside sandboxes; the feature does not write to any shared or central location.

## Use cases

**The retrospective consumer.** At the end of a Firebreak development cycle, the operator runs the retrospective phase. The metrics table is injected into the retrospective file automatically from code (B-009), drawing on the aggregated report (B-007). The agent reads the table and writes interpretive prose — explaining what the numbers mean, identifying patterns, proposing improvements. The agent does not produce the numbers; the table is already there when the retrospective runs.

**The mid-cycle spot check.** During a development cycle — after the spec gate, or partway through implementation — the operator wants to know how many verification runs have failed, how many tasks have been reworked, or how long the current stage has been running. The operator runs the report command directly (B-008); it aggregates what has been captured so far (B-007) and produces a partial table. No special mode is required; the same command works at any point.

**The before-and-after evaluation.** A new Firebreak feature claims to reduce rework. The operator captures a baseline cycle, ships the feature, and captures a comparison cycle. The report's gate first-pass rates, rework counts, and detection-round counts (B-007, B-005) before and after are comparable without running a full benchmark. This use case is only possible if the measurement plane is consistent and machine-generated; it is impossible with the current retrospective-only record.

**The debugging session.** A harness developer suspects a specific gate or hook is misbehaving. They switch the capture level to full (B-010), which records complete event payloads including tool-call detail, and run the report. The full-capture profile gives enough detail to trace what happened step by step. Outside this use case, full capture is not the default.

**The token-cost audit.** After a completed cycle, the operator wants to know how many tokens each stage consumed and whether any stage is disproportionately expensive. The post-hoc token harvester (B-006) reads the session and subagent transcripts, joins them to stages via the state engine's timestamps, and adds token counts by type and model to the report table.

## Functional requirements

### Capture sources

**The per-project capture gate (B-001).** The hook router is installed globally, meaning it activates in every Claude session regardless of which project is open. Its first action in every invocation is to check whether the current project is Firebreak-managed (detected by the presence of Firebreak's automation directory) or carries an explicit capture marker. If neither condition is met, the router exits immediately and records nothing. This check is the governing constraint for all privacy and overhead properties of the feature.

**The hook router event recorder (B-002).** When the per-project capture gate passes, the router records Claude-level harness events — tool use, lifecycle events, subagent completions, and prompt submissions — to a capture file that lives in the project's own directory, in a subdirectory that is gitignored. The capture level governs how much of each event is recorded: at standard, a tool-use event records that a tool ran and which one, with its payload stripped; the full argument detail and any prompt text are recorded only at full capture (see the capture-levels requirements). The router never writes to the global configuration directory, never emits to standard output, and never causes a tool call or pipeline command to fail. If the write fails for any reason, the failure is silent.

**The pipeline chokepoint recorder (B-003).** Every gate, hook, and state transition in Firebreak's pipeline already routes through a single dispatch point. Wrapping that dispatch point records, for each command: the command name, its arguments, the outcome (success or failure), and how long it took. This single wrapping instruments all gates, hooks, and state transitions without requiring changes to individual command modules.

**Verification result persistence (B-004).** The per-task verification hook already runs the test suite, the linter, and a check against the declared file scope after every task completion. Today it discards those results. This feature changes that behavior: the hook records test pass or fail plus the count of failing tests, the number of lint errors, and the list of any files touched outside the declared scope. Scope violations are currently warned and forgotten; they become a queryable data point.

**Code-review round logging (B-005).** The code-review gate records, for each detection round: the number of issues raised, the number that survived adversarial challenge, the severity breakdown across those survivors, and the total number of rounds before the review went quiet. The challenger kill rate is defined at the cycle level as the fraction of raised issues that the adversarial challenge killed — total issues raised across all rounds, minus the issues confirmed (those that survived to the final quiet round), over total issues raised. A high kill rate means the detector raised many issues that did not survive challenge, which points to a noisy detector rather than a healthy one; the rate is a calibration signal to watch over time, not a number with a single "good" direction. Per-round raised-and-survived counts are retained so the rate can be recomputed; the exact roll-up the report displays is a presentation detail for design.

**The post-hoc token harvester (B-006).** Token counts are not available to the pipeline's Python layer during a live session. After a session completes, the harvester reads the session transcript and subagent transcripts, extracts tokens by type (input, output, cache reads) and by model, counts tool calls and tool errors, and joins all of this to pipeline stages using the state engine's per-stage timestamps. The harvester runs at retrospective time and adds its output to the report. When a transcript is absent or unreadable, the harvester does not invent zeros: it marks the affected token rows as unavailable, distinct from a genuine count of zero, so a missing transcript never reads as "this stage spent no tokens."

**Subagent identity filtering (B-016).** When the report aggregates subagent-completion events, it counts only events whose agent identity matches a known Firebreak agent. Events with an empty or unrecognized agent identity — the harness's own internal helpers, such as title and suggestion generators — are still recorded in the capture file but are excluded from any aggregated subagent count or result, so phantom helpers never inflate the metrics.

**State-derived park and rework metrics (B-017).** Two of the report's rows do not come from a new capture stream — they are derived from data the state engine already keeps. Parks per stage and their reasons come from the state engine's existing park and error history. Rework is derived from stage re-entry: when a task or feature returns to a stage it already passed through, the repeated stage timestamp marks the rework, distinct from a first-pass failure corrected without re-entering the stage. The report reads these from the state engine; no new logging is added for them. This makes explicit which source produces the parks and rework rows the report and the success metrics require.

### Reporting

**The report command (B-007).** A single command aggregates all capture sources — hook router events, pipeline chokepoint events, verification results, code-review round logs, state engine timestamps, and token harvest output — into a metrics table. The join spans sources whose on-disk storage topology (one shared stream versus per-spec files plus a merge) is a design-deferred open question; the report's contract is that it presents one unified table regardless of how the underlying events are stored. The table includes at minimum: per-stage duration, gate attempts and first-pass rate for each gate, parks per stage with the recorded reason for each park (B-017), tasks completed and reworked (B-017), scope violations, code-review detection rounds with issue-raised-to-confirmed counts, and tokens per stage. The command produces the same table whether run mid-cycle or at the end; mid-cycle rows are partial.

**Ad-hoc invocation (B-008).** The report command is runnable at any point in the pipeline. No special flag, mode, or stage requirement is needed to invoke it outside the retrospective.

**Auto-injection at retrospective (B-009).** When the retrospective phase runs, the report command is called from code and its output is written into the retrospective file as part of the phase, independent of the agent — the agent does not trigger this step and does not author the numbers. The injected table carries a machine-generated provenance marker (a header tag or comment that the agent does not produce), so any reader or automated check can confirm the table was written by the report command rather than hand-authored. The agent's interpretive prose is added separately; the table's position within the file relative to that prose is a design detail, as long as the table itself is the machine-written, marked section.

### Capture levels

**Three capture levels (B-010).** The system supports exactly three capture levels. "Off" means the router exits immediately and nothing is recorded, regardless of project type. "Standard" means lifecycle events, failures, subagent results, and pipeline chokepoint events are recorded, but tool-call payloads and prompt text are not. "Full" means every event is recorded with complete payloads, including tool-call detail and prompt text. The levels are mutually exclusive and project-local.

**Shipped default for Firebreak-managed projects (B-011).** The default capture level inside a Firebreak-managed project is standard. An operator must take an explicit action to move to full; full is not enabled by default anywhere. Uninstrumented projects are always off regardless of any setting. The default-level *behavior* is settled here; the *mechanism* an operator uses to change the level is the same design-deferred question as where the capture setting lives (see Open questions).

### Shared event envelope

**Common event schema (B-012).** Events from the hook router and events from the pipeline chokepoint share a common envelope shape and a fixed event-type vocabulary. The report command can join events from both sources because the envelope fields are consistent between them. The event format is versioned, and a drift check guards the event-type vocabulary so that additions or changes are detected rather than silently tolerated.

**Stage stamping (B-013).** Each event record carries the pipeline stage that was active when the event was recorded. The stage is read from the state engine at the moment the event is written. If no pipeline stage is active — for example, if the hook fires outside an SDL run — the event carries no stage field and is still recorded normally.

### Retention

**Automatic size or age cap (B-014).** The capture file in each project self-prunes automatically when it reaches a size or age threshold, so the file does not grow unbounded without operator action. The exact threshold and pruning mechanism are a design-phase detail; the behavioral requirement is that the file stays bounded without requiring the operator to remember to clean it up.

### Migration

**Duplicate registration removal (B-015).** When the global hook router install ships, any project-level router registration left over from earlier capture experiments must be removed. If both a global and a project-level registration are present, the hook fires twice and events duplicate. The shipped install must not leave a state where duplication is possible in a previously-instrumented project.

## Non-functional requirements

**Fail-silent capture.** A capture write failure must never cause a tool call to return an error, never cause a pipeline command to fail, and never produce output to standard output. From the operator's and the pipeline's perspective, the capture layer does not exist unless they look for its output.

**Per-project confinement.** Capture data never leaves the project directory. The capture directory is gitignored. The global configuration directory is never written to by the capture layer, because per-project sandboxes may mount parts of that directory read-only.

**Payloads only at full capture, only in instrumented projects.** The privacy-sensitive content is not just prompt text but any free-form payload — prompt text and tool-call arguments alike can carry user-authored or sensitive values. Standard capture records that events occurred (which tool, which lifecycle event, which outcome) without their payloads; full capture records the payloads, including tool-call arguments and prompt text. Payloads are therefore recorded only when the operator has explicitly opted the project into full capture, and never in a project that has not passed the per-project capture gate.

**Consistent event schema across sources.** The event envelope and event-type vocabulary must be stable enough that the report command can join events from the hook router and from the pipeline chokepoint without special-casing. Schema drift is a defect, caught by the drift check.

**No ambient overhead in uninstrumented projects.** The globally-installed router must complete its per-project capture gate check in well under a second per tool call. The gate check is a deterministic file-system test; the overhead budget is the cost of that check plus interpreter startup, nothing more.

## Edge cases and failure modes

**The uninstrumented project.** The hook router fires in every Claude session. When the current project is not Firebreak-managed and does not carry a capture marker, the router must exit immediately and record nothing. This is not a degraded state; it is the designed behavior for the majority of projects on any operator's machine.

**Read-only global configuration directory.** Per-project sandboxes in Firebreak's own development environment mount parts of the global configuration directory as read-only. The capture layer must never attempt to write there. All writes go to the project-local capture directory. This is enforced by design, not by a runtime check.

**Harness-internal subagents without agent identity.** Claude's runtime generates subagent completion events for internal helpers — title generators, suggestion generators — that are not Firebreak agents. These events appear with an empty agent identity field. Subagent identity filtering (B-016) excludes events with an empty or unrecognized agent identity from aggregated counts; the filter is on the agent identity field, and events that fail the filter are still recorded but excluded from aggregated subagent counts and results.

**Verification hook absent for background tasks.** The per-task verification hook fires on SDL task completion, not on arbitrary background shell commands. When the report sees no verification events for a period, it must not treat that absence as a failure. The hook simply did not trigger because no SDL task completed. The report omits the verification row rather than reporting a zero or an error.

**Duplicate registration during global install migration.** An operator who ran the earlier capture experiment may have a project-level router registration in an existing project. When the global install ships, both registrations fire and events are written twice per tool call. The installer must detect and remove any project-level registration that would duplicate the global one. The operator should not have to find and remove these manually.

**Capture write failure.** The capture file may be unwritable due to permissions, a full disk, or a sandbox restriction not anticipated at design time. Any such failure must be caught, discarded, and not propagated. The pipeline command that triggered the hook continues normally.

**Capture outside an SDL run.** The hook router may fire when no SDL pipeline run is in progress — for example, when the operator runs a Firebreak utility command outside a feature cycle. In this case the state engine has no active stage. The event is still recorded; the stage field is simply absent. No error is raised and no synthetic stage value is invented.

**A cycle spanning multiple sessions.** A development cycle can park and resume across several separate Claude Code sessions over days — the very scenario the problem statement names as where measurement matters most. The token harvester must aggregate token and tool counts across every session and subagent transcript belonging to the cycle, not just a single transcript, and attribute each to the stage that was active when it ran. A cycle that ran across three sessions produces one set of per-stage token totals, not three disconnected ones.

## Dependencies

**State engine timestamps.** The report command and the post-hoc token harvester both depend on the state engine's per-stage timestamps to attribute events and tokens to stages. These timestamps already exist in the current state engine; no change to them is required.

**Existing retrospective append mechanism.** Auto-injection of the report table at retrospective time uses the existing function in the retrospective module that appends a section to the retrospective file. That mechanism already exists; the feature wires the report command's output to it.

**Session and subagent transcripts.** The post-hoc token harvester reads the session transcript and any subagent transcripts from the project's transcript store. These transcripts are produced by Claude Code's normal operation and are already present; the harvester reads them after the session rather than during it.

**Global hook registration.** The hook router requires a hooks entry in the Claude configuration. This entry must be placed by the installer. The installer already manages the global configuration; adding the router to that managed set is within scope. The human operator must apply any configuration update that Claude Code's self-modification gate prevents Claude from applying autonomously.

**Capture-experiment prototype.** A working prototype of the hook router, the transcript harvester, and the report aggregation logic exists from a prior exploration session. The design phase should treat these as the baseline to port and harden, not as a design to reproduce from scratch.

## Success metrics

After one complete SDL cycle on any feature, the following must all be true:

The report command, run without arguments beyond the spec name, produces a table with at least these rows populated: per-stage duration for each stage that ran; gate attempts and first-pass rate for each gate that was exercised; parks per stage with a recorded reason for each park; tasks completed and tasks reworked; scope violations from verification runs; and code-review detection rounds with issue-raised-to-confirmed counts. The tokens-per-stage row is populated whenever the session and subagent transcripts for that cycle are present; when a transcript is missing, that row reads "unavailable" rather than zero. (Where no event of a kind occurred at all — for example, no parks — the row is legitimately empty; the criterion is that the row exists and reflects the true count.)

The retrospective file for that cycle contains the metrics table, and the table carries the machine-generated provenance marker, confirming it was written by the report command rather than hand-authored by the agent.

The capture file in the project directory is present, is gitignored, stays within its configured size or age bound, and contains events from both the hook router and the pipeline chokepoint with consistent envelope fields.

A session run in a project that is not Firebreak-managed and carries no capture marker produces no entries in any capture file and no output from the router.

## Open questions

The following items are design-deferred. The product behavior is settled; the mechanism is a design choice.

**Single event store versus per-spec files with a merge step.** The existing audit log writes one file per spec under the automation logs directory. The hook router capture writes one file per project. The report command must join both. The design-phase lean is toward a single shared event stream with the spec as a field, but the migration path for the existing per-spec files, and whether the existing audit log is retired or preserved alongside the new stream, has not been decided.

**Gate result envelope shape.** Gate commands produce JSON result payloads that can include long finding lists. Recording these verbatim would make the capture file large and the schema unstable as finding formats evolve. The design-phase lean is toward a summarized envelope — recording counts and verdicts rather than full finding text — but the exact fields of that envelope have not been decided.

**Where the capture setting lives, and how the explicit capture marker is defined.** The capture level for a project (off, standard, or full) must be stored somewhere project-local and sandbox-writable. The candidates are a standalone marker file in the capture directory, or a key in Firebreak's existing project configuration surface. The tradeoffs between these — discoverability, the existing config surface's read path, and how an operator changes the level — have not been decided. The same open question covers the explicit capture marker that lets a non-Firebreak project opt into capture: its name, location, and format are undefined. Resolving where the setting lives should also define this marker.

**Exact retention threshold, and its interaction with cross-cycle comparison.** The feature requires that the capture file self-prune to stay bounded. The pruning mechanism (size cap, age cap, or both), the specific threshold values, and what happens to pruned events (deleted, archived, summarized) are design-phase details. There is a real tension to resolve here: the before-and-after evaluation use case needs two full cycles' events retained for comparison, but a size or age cap could prune the older baseline cycle before the comparison runs. Design must reconcile the retention cap with cross-cycle comparison so that pruning never silently destroys a baseline an operator still needs.

**The known-Firebreak-agent list for subagent filtering.** Subagent identity filtering counts only events whose agent identity matches a known Firebreak agent. How that list of known agents is sourced and kept current is undecided. A list that goes stale when a new agent is added would silently undercount that agent's work with no error. Design must decide where the list comes from (for example, derived from the installed agent set rather than hand-maintained) so the filter does not rot.

All other product decisions from the intent grilling are settled and treated as requirements above.
