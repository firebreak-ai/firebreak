# Design Overview — Deterministic Metrics Plane (Hook Harvesting)

## What this feature builds

Firebreak gains a measurement plane that records pipeline facts from code, aggregates them into a table, and funnels that table into the retrospective deterministically — so the agent interprets numbers it no longer has to construct from memory. The work spans three capture sources, a post-hoc token reader, a report, and a per-stage injection into the retrospective.

## Component boundaries

The feature decomposes into three capability slices, each its own design page:

- **Capture sources** (`capture-sources.md`) — where events come from: the globally-installed hook router, the per-project capture gate, the dispatch chokepoint recorder, the verification hook's now-persisted results, code-review round logging, and the shared event envelope with its versioned vocabulary and drift check.
- **Reporting and injection** (`reporting-and-injection.md`) — what consumes the events: the report command, the post-hoc token harvester, subagent-identity filtering, the state-derived parks/rework rows, and the deterministic per-stage retrospective injection.
- **Configuration and lifecycle** (`configuration-and-lifecycle.md`) — how the plane is governed: the three capture levels and their storage in `capture.cfg`, the retention cap with operator-lockable baselines, the duplicate-registration migration, the installer changes, and the source of the known-agent list.

Contracts that cross a process or trust boundary are recorded in `contracts.md`.

## The three hard seams

Most module boundaries here are clean. Three are not, and the design turns on them:

1. **The chokepoint stdout capture.** Gates print a single JSON result to stdout and then exit with a code that callers depend on. The recorder must copy that result into an event without disturbing the stdout-and-exit contract. The mechanism is an in-process stdout redirect that re-emits captured bytes before the process exits.

2. **Code-review round data.** The deterministic code-review gate checks artifacts on disk; it never sees the detection/challenge rounds, which the code-review skill orchestrates. The rounds reach a deterministic logger only through a file the skill writes (`.code-review-rounds.json`) and the gate reads at check time.

3. **Token stage attribution.** A session transcript is a flat list of API turns with no record of stage transitions. The harvester attributes tokens to stages by a hard split on the state engine's transition timestamps.

## Entry points

- `python3 fbk.py report <spec>` — the standalone report command, runnable at any pipeline point (ad-hoc spot check).
- The globally-registered `hook_router.py` — fired by Claude's hook runtime on tool use, lifecycle, and subagent events; gated to instrumented projects.
- The dispatch chokepoint inside `fbk.py` — wraps every gate/hook/state command and records it.
- The state engine's `transition_state()` — after writing the state file, deterministically appends the completed stage's metrics block to the retrospective.

## Dependency graph

```
fbk.py
  └─ chokepoint recorder
        ├─ capture gate (reads .claude/automation/ and .fbk-capture/capture.cfg)
        └─ event writer ─ schema/vocabulary ─ retention pruner

hook_router.py  [globally installed, one process per tool call]
  ├─ capture gate
  ├─ known-agent filter (SubagentStop)
  └─ event writer

task_completed hook (modified)        ─ event writer   [VERIFICATION_RESULT]
code-review gate (modified)           ─ event writer   [CODE_REVIEW_ROUNDS, reads .code-review-rounds.json]
spec gate + task-reviewer gate        ─ event writer   [replacing the old audit calls]

report command
  ├─ reads .fbk-capture/events.jsonl  (router + chokepoint + verification + rounds events)
  ├─ reads state engine               (stage durations, parks, rework, first-try/after-rework correlation)
  ├─ known-agent filter               (subagent counts)
  └─ token harvester                  (reads session + subagent transcripts; joins to stages by timestamp)

state engine transition_state() (modified)
  └─ retro injector ─ report.stage_summary() ─ retro.append_section()
```

The **join key throughout is `(spec, stage)`**. The report emits one row group per stage; the per-stage injection emits one block for the stage that just completed.

## Decomposition rationale

Vertical slices by capability boundary: each design page owns one capability a reader would reason about as a unit — where events originate, what consumes them, and how the plane is governed — rather than splitting by module or by data structure.
