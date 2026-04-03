# Firebreak/Dispatch vs GSD-2: Comparative Analysis

**Date**: 2026-03-18
**Sources**: [GSD-2 GitHub](https://github.com/gsd-build/gsd-2), [gsd.build](https://gsd.build), [Medium analysis](https://medium.com/@sajith_k/gsd-2-the-ai-coding-agent-that-actually-controls-its-own-context-window-fb04706b081e), [DEV Community guide](https://dev.to/alikazmidev/the-complete-beginners-guide-to-gsd-get-shit-done-framework-for-claude-code-24h0), [Substack analysis](https://neonnook.substack.com/p/the-rise-of-get-shit-done-ai-product)

## What GSD-2 is

GSD-2 is a standalone CLI built on the Pi SDK that orchestrates Claude Code sessions for autonomous project development. It evolved from a prompt framework (v1) into an agent application (v2) that programmatically controls agent sessions — managing context windows, file injection, git branches, cost tracking, and crash recovery. 26K+ GitHub stars. Built by Lex Christopherson.

The system operates as a state machine driven by files on disk (`.gsd/` directory). Each dispatch reads the current state, determines the next unit of work, spawns a fresh agent session with pre-inlined context, and writes results back to disk for the next iteration.

## Where they solve the same problem

Both frameworks address the core challenge: unstructured agentic coding produces code that degrades in quality over long sessions.

| Shared principle | GSD-2 | Firebreak/Dispatch |
|---|---|---|
| Spec-driven development | Milestones → slices → tasks, each with "truths" (observable behaviors) | Spec → review → breakdown → implement, each with ACs |
| Fresh context per task | Fresh 200K session per task, pre-inlined context | Agent team with independent task files, context isolation per teammate |
| Task decomposition | Automatic: slice → 1-7 tasks, each context-window-sized | Compiled: spec → sized tasks (1-2 files, <55 lines), wave-ordered |
| Verification gates | Verification commands per task + milestone validation | Per-wave test suite + final verification + test reviewer checkpoints |
| Git as checkpoint | Branch-per-slice, squash merge to main | Per-wave commits, revert points |
| State on disk | `.gsd/` directory with STATE.md, plans, summaries | `ai-docs/<feature>/tasks/task.json` with status tracking |

## Where they diverge fundamentally

### 1. Quality model: Tests vs verification commands

This is the biggest difference. GSD-2 uses verification commands — shell commands like `npm run lint`, `npm run test`, `curl localhost:3000/api returns 200`. These verify "does it run?" Firebreak uses test-first development with a dedicated test reviewer agent — tests are written before implementation, reviewed for behavioral completeness, and the test reviewer checks whether tests would actually fail if the behavior is broken (the "show your work" requirement).

GSD-2's verification is pass/fail on commands that already exist. Firebreak's verification includes *designing* the right tests as a first-class pipeline stage. The Space Invaders retrospective proved this matters: 124 tests passed, the app didn't work. The tests themselves were the problem — they tested the wrong things at the wrong level. GSD-2 doesn't have a mechanism to catch this.

### 2. Human involvement model

GSD-2 optimizes for autonomy — "walk away, come back to a built project." Auto mode runs research → plan → execute → verify → commit → advance without human intervention. The human reviews after the fact.

Firebreak optimizes for human-in-the-loop at design decisions — the human co-authors specs, reviews council findings, approves breakdown, and monitors implementation. The human is removed from mechanical execution but present for judgment calls. The Phase 1.5 retrospective validated this: "human spec review cannot be skipped — the pipeline optimizes for whatever the spec says."

GSD-2's approach is faster for greenfield prototyping. Firebreak's approach produces higher quality for production code where the spec's framing determines whether the output is correct.

### 3. Quality feedback loop

Firebreak has structured retrospectives that feed process improvements — the Phase 1.5 spec was entirely derived from retrospective findings. GSD-2 has task summaries and a decisions register but no formal mechanism for the pipeline to learn from its own failures across runs. GSD-2's DECISIONS.md is append-only within a milestone; Firebreak's retrospectives drive changes to the context assets that control future pipeline behavior.

### 4. Context management approach

GSD-2's primary innovation is programmatic context control — fresh sessions per task, pre-inlined files, aggressive context isolation managed by the CLI itself (not by prompts). This is technically more sophisticated than Firebreak's approach, which relies on Claude Code's native agent teams and context isolation.

Firebreak's context management is simpler: each teammate gets the task file as sole context. The tradeoff is that Firebreak doesn't have GSD-2's pre-inlining (injecting relevant files before execution) or its session forensics (recovering context from crashed sessions).

### 5. Parallelism model

GSD-2 supports multi-worker parallel milestone orchestration via file-based IPC — multiple GSD workers coordinating across milestones. Firebreak uses wave-based parallelism within a single feature — tasks in the same wave run concurrently, waves execute sequentially. Firebreak's model is simpler and prevents cross-task interference; GSD-2's is more flexible but has the multi-agent coordination risks flagged in industry analysis ("multi-agent systems don't reduce ambiguity — they multiply it").

## What GSD-2 does better

### Context management is a first-class engineering concern
Not a prompt-level hope. Fresh sessions per task, pre-inlined context, and cost/token tracking are programmatic, not advisory. Firebreak relies on Claude Code's native isolation, which is less controlled.

### Crash recovery and resilience
Lock files, session forensics, exponential backoff, model fallback chains, stuck detection. Firebreak has no crash recovery mechanism — an interrupted session requires manual resume from `task.json` status.

### Cost visibility
Per-unit token tracking, budget ceilings, cost projections. Firebreak has no cost instrumentation.

### Autonomous operation
For projects where the spec is clear and the human doesn't need to be in the loop for design decisions, GSD-2 can run unattended. Firebreak requires human participation at stage transitions.

### Git strategy
Branch-per-slice with worktree isolation and squash merge is cleaner than Firebreak's per-wave commits on the working branch.

## What Firebreak does better

### Test quality as a first-class concern
The test reviewer agent with 5 criteria, two-tier enforcement, and "show your work" has no equivalent in GSD-2. GSD-2 runs verification commands but doesn't evaluate whether those commands are adequate. The Space Invaders experience — 124 passing tests, non-functional app — would happen in GSD-2 just as easily if the verification commands were shallow.

### Spec review with adversarial perspectives
The council review (6 specialized agents evaluating the spec from different SDL concerns) catches design problems before implementation. GSD-2's planning phase decomposes work but doesn't adversarially review it. The council's findings on the Space Invaders specs (collision extensibility, renderer context access, flamethrower simplification) prevented expensive rework.

### Integration seam awareness
Firebreak explicitly declares and tests integration seams — the boundaries where modules interact. All 5 Space Invaders bugs were at these seams. GSD-2's task-level verification checks individual tasks but doesn't specifically target cross-task integration points.

### Structured self-improvement
Retrospectives → spec → implementation → retrospective is a closed loop. The pipeline's context assets are the process, and editing them changes the process. GSD-2's DECISIONS.md is within-project memory; Firebreak's retrospectives drive cross-project process improvements.

### Corrective workflow
Firebreak has a formalized diagnostic workflow (test-first → diagnose → fix → retest) with context-independent diagnosis agents. GSD-2's error handling retries and escalates but doesn't have a structured root-cause-analysis workflow.

### Brownfield awareness
Codebase-grounded compilation (breakdown agent reads actual code to verify conventions), pattern consistency review (council checks new code follows existing patterns), and readiness checks (implementation agent verifies prior-wave outputs). GSD-2's research phase scouts the codebase but the verification is less structured.

## The critical gap in each

### GSD-2: The oracle problem
Who watches the tests? GSD-2 runs `npm test` — but if the tests are smoke tests that pass on a non-functional app (our exact experience), GSD-2 will happily commit and advance. The framework has no mechanism to evaluate test adequacy, flag silent failures, or require e2e coverage for user-facing behavior. This is exactly the failure class that Phase 1.5 was designed to prevent.

### Firebreak: Operational resilience
Crash recovery, cost tracking, model fallback, stuck detection — these are real production concerns that Firebreak handles minimally. The permissions friction experienced during Phase 1.5 implementation (7/11 tasks requiring team lead intervention due to subagent permissions on `home/dot-claude/` paths) is the kind of operational issue GSD-2's infrastructure approach handles better.

## GSD-2 architectural details for reference

### Work decomposition hierarchy
- **Milestone**: A shippable version (4-10 slices)
- **Slice**: One demoable vertical capability (1-7 tasks)
- **Task**: One context-window-sized unit of work

### Workflow phases
Research → Plan → Execute (per task) → Complete → Reassess Roadmap → Next Slice

### Execution modes
- **Step mode**: Pauses between units with a wizard. Advance one step at a time.
- **Auto mode**: State machine runs research → plan → execute → verify → commit → advance without human intervention.
- **Headless mode**: No terminal UI, for CI pipelines. Automatic responses, completion detection, structured exit codes.

### Disk artifacts
| File | Purpose |
|------|---------|
| `STATE.md` | Dashboard — always read first |
| `PROJECT.md` | Living doc of project state |
| `DECISIONS.md` | Append-only architectural decisions register |
| `M001-ROADMAP.md` | Milestone plan with slice checkboxes, risk levels |
| `S01-PLAN.md` | Slice task decomposition with must-haves |
| `T01-PLAN.md` | Individual task plan with verification criteria |
| `T01-SUMMARY.md` | Execution results — YAML frontmatter + narrative |
| `S01-UAT.md` | Human test script derived from outcomes |

### Task plan structure
- **Truths**: Observable behaviors ("User can sign up with email")
- **Artifacts**: Files that must exist with real implementation, not stubs
- **Key Links**: Imports and wiring between artifacts

### Verification ladder
Static checks → Command execution → Behavioral testing → Human review

### Error handling
- Crash recovery via lock files + session forensics
- Provider error recovery (transient vs permanent)
- Stuck detection (same unit dispatched twice without expected output)
- Timeouts (soft → idle watchdog → hard)

### Known limitations (per community)
- 4:1 overhead ratio (4 tokens orchestration per 1 token coding)
- Slower than autonomous loops without the framework
- Requires Max plan ($100-200/mo) due to token consumption
- Overkill for simple tasks

## Synthesis: Complementary, not competitive

The ideal system would combine GSD-2's execution infrastructure (context management, crash recovery, cost tracking, parallel orchestration) with Firebreak's quality model (test reviewer, council review, integration seam coverage, corrective workflow, self-improvement loop). GSD-2 is a better engine; Firebreak is a better quality system. Neither alone produces the full picture.

### What Firebreak could learn from GSD-2
1. Programmatic context control instead of relying on Claude Code's native isolation
2. Crash recovery and session forensics
3. Cost/token tracking per task and per wave
4. Branch-per-feature with worktree isolation
5. Stuck detection and automatic retry with diagnostics
6. Pre-inlining relevant files into task context (beyond just the task file)

### What GSD-2 could learn from Firebreak
1. Test quality evaluation — not just "do tests pass?" but "are the tests good enough?"
2. Adversarial spec review with multiple specialized perspectives
3. Integration seam declaration and coverage verification
4. Structured retrospectives that drive process improvement
5. Corrective workflow with context-independent diagnosis
6. Two-tier enforcement with "show your work" requirements
