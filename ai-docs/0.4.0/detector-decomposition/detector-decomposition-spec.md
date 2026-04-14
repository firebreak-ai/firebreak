# detector-decomposition — Feature Spec

## Problem

Post-hygiene (v0.3.5), each Detector receives ~30 discrete instructions — still 1.5x the ~20 reliable compliance threshold identified by IFScale research. The v0.3.5 evaluation against Project B confirmed the impact: 78% of missed issues (14/18) were execution gaps where the checklist already covered the pattern but Detectors didn't apply it consistently. The root cause is attention competition — once a Detector finds 1-3 instances of a pattern, it moves on rather than systematically applying every checklist item to every file.

Two additional problems compound the execution gap:

1. **No cross-instance search.** When a Detector identifies a pattern instance, no instruction directs it to search the full codebase for other instances of the same pattern. The divergence analysis found this single gap accounts for 5-6 of the 14 execution-gap misses (#22, #10, #19, #32, #11, #8).

2. **Specialized detection tasks compete with structural detection.** Intent-based path tracing and test quality review are handled by generic Detectors alongside 30+ other detection targets. The v0.3.5 evaluation showed these tasks have high yield (29% of findings intent-sourced, both criticals intent-sourced, "tests protecting bugs" uniquely enabled by intent) but share the same attention budget as structural items.

Additionally, 4 methodology gaps identified in the divergence analysis have no detection targets in the current checklist: unbounded data structure growth, migration idempotency, batch transaction atomicity, and intra-function logical redundancy.

## Goals

- Decompose detection from 3 generic Detectors to 7 Tier 1 groups with 3-5 items each, targeting ~20 total instructions per agent (including overhead) as a guideline for reliable compliance — not a hard gate
- Create per-group agent definitions so each Tier 1 Detector is self-contained with its assigned detection targets
- Add an Intent Path Tracer agent that traces main execution paths against the intent register
- Add a Test Reviewer agent dedicated to test quality, test-intent alignment, and tests protecting bugs
- Add 4 new detection targets from methodology gaps to quality-detection.md
- Add a two-phase detection structure: per-file enumeration pass first, cross-instance search second
- Randomize detection target ordering within each group across runs to avoid position-dependent attention bias
- Add cross-agent sighting deduplication with explicit merge policy before Challenger verification
- Add Challenger batching to handle increased sighting volume (1 Challenger per 5 sightings, grouped by detection category)
- Scope the Mermaid diagram to Intent Path Tracer only, saving ~900 tokens per Tier 1 Detector spawn
- Add detection preset system with per-group toggles so users can select which detection categories to run, with preset-sequential execution for full runs

**Non-goals:**
- Tier 2 cross-module detection using AST skeletons or behavioral summaries (that's `tiered-detection`, v0.4.1)
- New finding types, severity levels, or sighting format fields
- Changes to the intent extraction phase (v0.3.5, already complete)
- Changes to the retrospective format (beyond per-group performance metrics)
- Changes to the checkpoint-based Test Reviewer (`fbk-test-reviewer.md`) used by `/fbk-spec-review` and `/fbk-breakdown`

## User-facing behavior

No change to invocation syntax. The `/fbk-code-review` skill, sighting format, finding format, and review report structure are unchanged.

Observable effects:
- Higher detection coverage per round — more checklist items applied per file, fewer missed instances of patterns the methodology already covers
- Intent-specific findings from a dedicated path tracer (detection source: `intent`)
- Test-specific findings from a dedicated reviewer (detection source: `checklist` or `intent`)
- Detection presets allow users to select which categories to run (e.g., `behavioral-only`, `test-only`, `full`). Default preset is `behavioral-only`. Agent spawns scale with the selected preset rather than always spawning the full complement.
- Retrospective includes per-group performance metrics: enumeration compliance, sighting volume, sighting survival rate, and phase attribution

## Technical approach

### Tier 1 group definitions

Decompose the current detection targets into 7 groups based on detection similarity — items in the same group use the same reasoning pattern (scanning for the same class of code structure). Test-related items are removed to the dedicated Test Reviewer.

Each group gets its own agent definition file containing the group's detection targets, behavioral comparison methodology, sighting format, and scope discipline. The orchestrator spawns each group's agent by name — no dynamic prompt assembly required.

**Group 1: value-abstraction** (3 items)
- Bare literals (ai-failure-modes #1)
- Hardcoded coupling (ai-failure-modes #2)
- String-based type discrimination (quality-detection / ai-failure-modes #11)

Detection pattern: "Is a concrete value used where an abstraction should be?" Scan for literals in conditionals, direct references where interfaces/config should be, string matching for type dispatch.

**Group 2: dead-code** (5 items)
- Dead infrastructure (quality-detection / ai-failure-modes #7)
- Middleware or layers never connected (ai-failure-modes #3)
- Dead code after field or function removal (quality-detection)
- Dead conditional guards (ai-failure-modes #14)
- Intra-function logical redundancy (NEW — quality-detection)

Detection pattern: "Is this code/condition live and reachable?" Trace whether constructs are invoked, conditions can be true, and removed fields leave orphaned guards. All items require reachability/liveness reasoning.

**Group 3: signal-loss** (3 items)
- Zero-value sentinel ambiguity (ai-failure-modes #9)
- Context discard (quality-detection / ai-failure-modes #10)
- Silent error discard (quality-detection)

Detection pattern: "Is information being lost or misinterpreted?" Trace how special values, contexts, and errors flow through call sites. All items involve a value that should be preserved or distinguished but isn't.

**Group 4: behavioral-drift** (3 items)
- Comment-code drift (ai-failure-modes #8)
- Semantic drift (quality-detection)
- Dual-path verification (quality-detection)

Detection pattern: "Does X claim one thing while reality is different?" Compare names/docs/paths against actual behavior. Dual-path verification fits because it detects state divergence between two paths that should agree.

**Group 5: function-boundaries** (3 items)
- Mixed logic and side effects (quality-detection)
- Ambient state access (quality-detection)
- Non-importable behaviors (quality-detection)

Detection pattern: "Is this function doing too much or depending on hidden state?" Analyze function boundaries for entangled computation/effects, undeclared dependencies, and untestable embedded logic.

**Group 6: cross-boundary-structure** (4 items)
- Caller re-implementation (quality-detection)
- Parallel collection coupling (quality-detection)
- Multi-responsibility modules (quality-detection)
- Composition opacity (quality-detection)

Detection pattern: "Is behavior duplicated, coupled, or untested across module boundaries?" Compare across call sites and modules for re-implemented logic, index-coupled collections, scope violations, and unverified composition.

**Group 7: missing-safeguards** (4 items)
- Surface-level fixes (ai-failure-modes #5)
- Unbounded data structure growth (NEW — quality-detection)
- Migration/DDL idempotency (NEW — quality-detection)
- Batch transaction atomicity (NEW — quality-detection)

Detection pattern: "Is the implementation missing a safety mechanism?" Look for fixes that bypass root cause, data structures with no lifecycle management, migrations without re-execution guards, and multi-write loops without transaction wrappers.

**Item count summary:** 25 Tier 1 items across 7 groups (range: 3-5 per group).

### Overhead instruction inventory

Each per-group agent definition includes detection targets plus overhead instructions. The overhead inventory provides design-time estimates for future optimization, not a pass/fail threshold. The ~20 instruction target is a guideline backed by IFScale research — compliance degrades linearly, so every reduction helps, but there is no cliff edge. Runtime instruction traces (AC-02) will provide actual instruction counts per agent; the estimates below will be validated against runtime data after the first evaluation runs.

**Active instructions (imperatives the Detector must follow):**
1. Describe what the code does, then compare against the source of truth — behavioral comparison methodology
2. Record each observation as a sighting using the provided format — sighting output
3. Assign a sequential sighting ID with group prefix (e.g., G1-S-01, G1-S-02) — sighting output
4. Assign a type to each sighting — sighting output
5. Assign an initial severity estimate — sighting output
6. Assign a cross-cutting pattern label when applicable — sighting output
7. Describe what you observed in behavioral terms — sighting output
8. Tag each sighting with its detection source — sighting output
9. Tag each sighting with its detection phase (`enumeration` or `cross-instance`) — sighting output
10. Analyze only the code the orchestrator directs you to — scope discipline
11. Do not write files — scope discipline
12. Exclude nits from sightings — scope discipline
13. Per-file enumeration: report files with issues individually, summarize clean files in one line — enumeration
14. Cross-instance search (phase 2): after completing the detection pass, search for other instances of each identified pattern — cross-instance
15-17(+). Group-specific detection targets (3-5 items)

**Reference material (lookup tables, not action directives):**
- Sighting format template (field definitions)
- Type classification definitions (relevant subset per group)
- Severity classification definitions (4 levels)
- Type disambiguation rule

**Totals per group:**
| Group | Detection targets | Active overhead | Total active | Reference items |
|-------|------------------|-----------------|--------------|-----------------|
| G1 value-abstraction | 3 | 14 | 17 | ~6 |
| G2 dead-code | 5 | 14 | 19 | ~6 |
| G3 signal-loss | 3 | 14 | 17 | ~6 |
| G4 behavioral-drift | 3 | 14 | 17 | ~6 |
| G5 function-boundaries | 3 | 14 | 17 | ~6 |
| G6 cross-boundary-structure | 4 | 14 | 18 | ~6 |
| G7 missing-safeguards | 4 | 14 | 18 | ~6 |

All groups fall within the 17-19 range for active instructions. Group 2 is highest at 19. If evaluation shows Group 2 underperforming, splitting it (see Open Question #1) brings both sub-groups to 16-17.

### Per-group agent definitions

Create 7 Tier 1 agent definition files, each self-contained:

| Agent definition file | Group |
|-----------------------|-------|
| `fbk-t1-value-abstraction-detector.md` | Group 1 |
| `fbk-t1-dead-code-detector.md` | Group 2 |
| `fbk-t1-signal-loss-detector.md` | Group 3 |
| `fbk-t1-behavioral-drift-detector.md` | Group 4 |
| `fbk-t1-function-boundaries-detector.md` | Group 5 |
| `fbk-t1-cross-boundary-structure-detector.md` | Group 6 |
| `fbk-t1-missing-safeguards-detector.md` | Group 7 |

Each agent definition contains:
- Frontmatter: name, description, tools (Read, Grep, Glob), model (sonnet)
- Behavioral comparison methodology instruction
- Sighting output instructions (format, group-prefixed ID, type, severity, pattern label, detection source tagging)
- Scope discipline (analyze only directed code, read-only, exclude nits)
- Per-file enumeration instruction
- Two-phase cross-instance search instruction
- The group's specific detection targets with full definitions (copied from quality-detection.md / ai-failure-modes.md)
- Reference material: sighting format template, relevant type definitions, severity definitions

**Sighting ID prefixes:** Each agent assigns sighting IDs with a unique group prefix for global uniqueness across agents:

| Agent | Prefix | Example |
|-------|--------|---------|
| Group 1 (value-abstraction) | G1 | G1-S-01 |
| Group 2 (dead-code) | G2 | G2-S-01 |
| Group 3 (signal-loss) | G3 | G3-S-01 |
| Group 4 (behavioral-drift) | G4 | G4-S-01 |
| Group 5 (function-boundaries) | G5 | G5-S-01 |
| Group 6 (cross-boundary-structure) | G6 | G6-S-01 |
| Group 7 (missing-safeguards) | G7 | G7-S-01 |
| Intent Path Tracer | IPT | IPT-S-01 |
| Test Reviewer | TR | TR-S-01 |

The prefix is embedded in each agent definition. Downstream consumers (Deduplicator, Challengers, retrospective) reference sightings by prefixed ID, which carries originating agent provenance without additional tracking.

The orchestrator spawns each agent by name. No dynamic prompt assembly — the orchestrator's job reduces to "spawn named agents with code files and intent claims, then spawn the Deduplicator, then spawn Challengers."

The canonical detection target definitions remain in quality-detection.md and ai-failure-modes.md. Per-group agent definitions contain operational copies. When a detection target is modified in its canonical source, the corresponding agent definition must be updated. This duplication is the tradeoff for simpler orchestration.

### Intent Path Tracer agent

A specialized agent that traces main execution paths against the intent register. Unlike Tier 1 Detectors that apply per-file checklist items, the Intent Path Tracer follows call chains across files.

**Input:**
- Intent register: behavioral claims (up to 30) + Mermaid diagram
- Project entry points with associated intent claims (identified by the orchestrator)
- Tool-based file access: the Intent Path Tracer reads files on demand via Read/Grep/Glob as it follows execution paths, rather than receiving all code files pre-loaded. This keeps its initial prompt small (~2,500 tokens) and its context focused on the path being traced, avoiding ~12,000+ tokens of pre-loaded code that may be irrelevant to traced paths.

**Mandate:**
- Trace 5-8 main execution paths from entry points through the call chain
- For each path, compare the actual execution flow against the relevant intent claims
- Detection targets:
  - Architectural mismatches: documented behavior with no entry point or code path
  - Module-level intent drift: code path exists but diverges from documented intent
  - Unreachable documented features: intent claims with no reachable implementation
  - Workflow completeness: does an operation's inverse undo all effects (e.g., unsubscribe not removing all subscription artifacts)
- For each traced path, state the intent claim compared and the conclusion

**Output:** Sightings in standard format with detection source `intent`.

**Agent definition:** New file `assets/agents/fbk-intent-path-tracer.md`. Tools: Read, Grep, Glob. Model: inherits parent (sonnet).

### Test Reviewer agent

A dedicated agent for test quality, removing test-related items from Tier 1 groups and giving test review its own optimized context shape.

**Input:**
- Test files in the review scope (pre-loaded in spawn prompt)
- Production source files that test files import (pre-loaded in spawn prompt)
- Intent register (behavioral claims only, no Mermaid diagram)

**Mandate:**
- Test-intent alignment: do tests cover the behavioral paths documented in the intent register?
- Tests protecting bugs: tests that validate broken behavior against documented intent (finding type uniquely enabled by intent extraction — v0.3.5 evaluation: F-11 prefilter tests assert all articles go to AI, which is correct per code but wrong per intent)
- Agentic test failure modes:
  - Name-assertion mismatch (ai-failure-modes #4)
  - Non-enforcing test variants (ai-failure-modes #6)
  - Semantically incoherent fixtures (ai-failure-modes #12)
  - Mock permissiveness masking constraints (ai-failure-modes #13)
  - Test-production string alignment (quality-detection)
- For each test file reviewed, state which checks were applied and whether issues were found

**Output:** Sightings in standard format with detection source `checklist`, `structural-target`, or `intent` depending on the triggering comparison target.

**Agent definition:** New file `assets/agents/fbk-cr-test-reviewer.md`. Tools: Read, Grep, Glob. Model: inherits parent (sonnet).

**Item count:** 7 detection targets. With ~13 overhead instructions, total ~20. All targets are within a coherent domain (test quality). The test failure mode items have concrete "Check for..." heuristics that support reliable application. Monitor for selective application during evaluation (see Open Question #2).

### New detection targets

Add 4 new structural detection targets to `quality-detection.md`, following the established format (imperative + "Detect this when..." heuristic):

**Unbounded data structure growth:**
"Flag long-lived data structures (Maps, Sets, arrays on module-scoped or class-scoped variables) and persistent tables that grow monotonically with no eviction, rotation, TTL, or size cap. Detect this when a collection or table receives insertions (add, set, push, INSERT) without any corresponding deletion, eviction, or size-limiting mechanism in the same module or a scheduled job."

Note: This is a hybrid Tier 1/Tier 2 target. The per-file heuristic above goes in Tier 1 Group 7. The cross-module enhancement (trace resource lifecycle across modules — writes without corresponding cleanup jobs) is deferred to `tiered-detection` (v0.4.1).

**Migration/DDL idempotency:**
"Flag schema migrations and one-time initialization code that lacks guards against re-execution. Detect this when a migration file contains ALTER TABLE, CREATE TABLE, ADD COLUMN, or equivalent DDL statements without IF NOT EXISTS, IF EXISTS, or equivalent idempotency guards."

**Batch transaction atomicity:**
"Flag loops performing multiple independent write operations where partial completion leaves inconsistent state. Detect this when a loop body contains two or more write calls (database writes, file writes, API calls with side effects) without a surrounding transaction, batch construct, or rollback mechanism."

**Intra-function logical redundancy:**
"Flag conditional checks within a single execution path that are fully subsumed by earlier checks in the same path. Detect this when a guard or branch condition tests a property that was already guaranteed by a preceding check, early return, or assignment in the same function."

### Orchestrator spawn logic

Replace the current single-Detector spawn in SKILL.md's Detection-Verification Loop with a multi-agent spawn:

**Current (SKILL.md step 1):**
> Spawn Detector with: target code file contents first, then linter output (if available), then intent register (from Intent Extraction), then source of truth + behavioral comparison instructions + structural detection targets from quality-detection.md last.

**New (SKILL.md step 1):**
The orchestrator resolves the selected detection preset to a list of agent groups, then spawns the agents for that preset in parallel:
1. **Tier 1 Detectors** — spawn each selected per-group agent by name. Inject into each spawn prompt: target code file contents first, then linter output (if available), then intent register claims last. Groups 2 (dead-code) and 6 (cross-boundary-structure) also receive the Mermaid diagram; other Tier 1 groups receive claims only. Construct all Tier 1 spawn prompts with identical code payloads in identical order to maximize prompt cache hits across agents. The orchestrator randomizes the order of detection targets within each agent definition's group payload.
2. **Intent Path Tracer** (if included in preset) — spawn `fbk-intent-path-tracer`. Inject: intent register (claims + Mermaid diagram) and entry point list with associated intent claims. The Path Tracer reads code files on demand via tools.
3. **Test Reviewer** (if included in preset) — spawn `fbk-cr-test-reviewer`. Inject: test files in scope + their production imports first, then intent register claims (no Mermaid diagram) last.

All agents in a preset wave spawn as a team. Each agent produces sightings independently with no shared state. The orchestrator collects all sightings before proceeding to deduplication (new step 1a) and Challenger verification (step 2). For `full` runs, this cycle repeats per preset wave.

**Per-agent respawn gating:** In iterative detection rounds, the orchestrator only respawns an agent if its previous instance produced at least one verified sighting above info level. If an agent's sightings all failed Challenger verification or were info-level only, that agent is not spawned in the next round. Maximum 5 repetitions per agent regardless of output. This applies independently to each Tier 1 group, the Intent Path Tracer, and the Test Reviewer. When a merged sighting survives Challenger verification, all originating agents (per the Deduplicator's merge log) are credited for respawn eligibility. In practice, preset-sequential execution means most merges occur within a wave where agents have distinct mandates, making cross-agent merges rare.

**Entry point identification for Intent Path Tracer:** The orchestrator identifies entry points from three sources:
1. **Intent register**: behavioral claims that describe user-facing actions or triggers (e.g., "users can subscribe to feeds," "the scheduler runs every 6 hours")
2. **Conventional entry points**: main files, route/command handlers, event listeners, exported CLI commands, cron/scheduler callbacks
3. **Package configuration**: scripts in package.json, entry fields, CI workflow triggers

Provide the Intent Path Tracer with up to 10 entry point file paths and the intent claim each relates to, prioritized by coverage of intent claims (entry points mapping to more claims rank higher). The Path Tracer decides which paths to trace from these starting points.

**Code access strategy:** Tier 1 Detectors receive all code files pre-loaded in the spawn prompt for exhaustive per-file scanning. The Intent Path Tracer starts with the intent register and entry points, then reads files on demand via tools as it follows execution paths — pre-loading the full codebase would waste context on files outside traced paths. The Test Reviewer receives pre-loaded test files and their production imports only.

**Broad-scope handling:** For broad-scope reviews with multiple reviewable units, spawn the selected preset's agent complement per unit. The current per-unit Detector spawn (SKILL.md line 100-101) becomes per-unit preset-driven multi-agent spawn. Cross-unit pattern deduplication (SKILL.md line 102) operates after per-unit deduplication.

### Two-phase detection: enumeration then cross-instance search

Each Tier 1 Detector operates in two phases within a single invocation:

**Phase 1 — Detection pass (per-file enumeration):**
"Apply all assigned detection targets to every file in scope. Report files where issues were found individually with full sighting detail. List all clean files in a single summary line with count and filenames. Do not skip files."

This prevents satisficing — the Detector cannot report on file A and silently skip file B — while keeping output concise. Clean files are accounted for (enabling enumeration compliance computation) without consuming output tokens on repetitive per-file "no issues" reports.

**Phase 2 — Cross-instance search:**
"After completing the detection pass for all files, review your sightings and search the full project for other instances of each identified pattern using Grep and Glob. Produce a separate sighting for each new instance found, including files not provided in your initial code payload."

This makes cross-instance search a discrete second phase, not a per-sighting interrupt. The Detector finishes its primary job (exhaustive per-file application of all assigned targets) before spending context on cross-instance expansion. This prevents a common pattern like "bare literals" from derailing the detection pass — Group 1 applies all 3 targets to all 15 files first, then searches for additional bare literal instances it may have missed.

The Intent Path Tracer already searches across files by design (path tracing). The Test Reviewer receives an analogous two-phase instruction scoped to test files.

### Randomized ordering

The orchestrator randomizes the order of detection targets within each group's agent definition payload before injection. This prevents position-dependent attention bias — research shows items at the beginning and end of an instruction list receive more attention than items in the middle (U-shaped attention curve).

Randomization is per-run, not per-round within a run. All Tier 1 Detectors within a single review run receive a consistent (but randomized) ordering for their group.

Implementation: The orchestrator shuffles the list of detection target definitions for each group before constructing the spawn prompt. The agent definition files contain the targets in a canonical order; the orchestrator reorders at spawn time.

### Cross-agent sighting deduplication

New step 1a in the Detection-Verification Loop, after all agents in a preset wave complete and before Challenger spawn:

When a preset wave contains multiple agents, the orchestrator spawns a Sighting Deduplicator agent (`fbk-sighting-deduplicator`) with the full sighting list from the wave. The Deduplicator compares sightings for same-file, overlapping-line-range overlaps, merges duplicates, and returns the deduplicated list plus a merge log. When a preset wave contains a single agent (e.g., `test-only`), skip the Deduplicator — sightings pass directly to Challengers.

**Pattern-label dedup:** When sightings from different Detectors share the same pattern label, keep all instances — these are cross-cutting pattern instances, which is the desired behavior. Deduplication applies only to same-location overlaps.

This dedup step runs before Challenger verification to avoid wasting Challenger attention on duplicate sightings.

**Cross-preset finding dedup (`full` runs only):** After all preset waves complete, the orchestrator performs an inline location-based check on verified findings across waves. If two findings from different presets reference the same file and overlapping line ranges, keep the higher-severity finding and note both detection sources. This is orchestrator-inline (no Deduplicator spawn) because the input is a small set of verified findings and cross-preset overlap is rare given the distinct mandates of each preset.

### Sighting Deduplicator agent

A lightweight agent that performs sighting deduplication as an isolated step. Keeps merge logic out of the orchestrator's context.

**Input:** Raw sighting list from the preset wave (passed in spawn prompt).

**Mandate:**
- Identify sightings referencing the same file and overlapping line ranges
- Compare observations to determine if they describe the same underlying issue
- Merge duplicates: retain the higher severity, the more specific type, list all detection sources, keep the observation text from the higher-severity sighting
- When sightings at the same location describe different issues, keep both
- Preserve all sightings with different pattern labels (cross-cutting instances, not duplicates)

**Output:** Deduplicated sighting list + merge log (number of merges, merged sighting ID pairs).

**Agent definition:** New file `assets/agents/fbk-sighting-deduplicator.md`. Tools: none (operates on text data in the spawn prompt). Model: sonnet.

### Challenger batching

Spawn 1 Challenger per 5 sightings, grouped by the originating detection category (matching the Tier 1 group that produced them, or Intent Path Tracer / Test Reviewer as their own categories). Spawn all Challengers in parallel.

**Example:** A preset wave produces 18 deduplicated sightings:
- Group 1 (value-abstraction): 4 sightings → 1 Challenger
- Group 2 (dead-code): 6 sightings → 2 Challengers (5 + 1)
- Group 3 (signal-loss): 3 sightings → 1 Challenger
- Intent Path Tracer: 5 sightings → 1 Challenger
- Total: 5 Challengers, all parallel

Merged sightings (from deduplication) go to whichever originating group's batch has room, since the merge already resolved their metadata.

The Challenger agent definition and verification protocol are unchanged. This is purely orchestrator-level batching — how many sightings each Challenger instance receives. Challengers run per preset wave, scoped to that wave's sightings.

### Detection presets and per-group filters

The orchestrator accepts a detection preset that determines which agent groups to spawn. Users select a preset via the `/fbk-code-review` invocation. Per-group toggles allow overriding any preset.

**Presets:**

| Preset | Agents spawned | Use case |
|--------|---------------|----------|
| `behavioral-only` (default) | Groups 1-4 (value-abstraction, dead-code, signal-loss, behavioral-drift) + Intent Path Tracer | Highest signal-to-noise for most reviews. Benchmark data: projected F1=46.4% vs 31.6% all-types. |
| `structural` | Groups 5-7 (function-boundaries, cross-boundary-structure, missing-safeguards) | Architecture and design pattern analysis. |
| `test-only` | Test Reviewer | Dedicated test quality pass. |
| `full` | All 9 agents | Complete analysis. Runs each preset group sequentially: `behavioral-only` → `structural` → `test-only`, each with its own dedup and Challenger pass. |

**Per-group toggles:** Users can enable or disable individual groups by name, overriding the preset. For example, `behavioral-only` + `test-reviewer` runs Groups 1-4 + Intent Path Tracer + Test Reviewer.

**Default:** `behavioral-only`. This reflects the benchmark finding that 56% of FPs are non-behavioral finding types the benchmark's golden set structurally cannot reward. For users focused on correctness bugs, this is the highest-value configuration. Users who want structural or test analysis opt in explicitly.

**Sequential preset execution for `full` runs:** Rather than spawning all 9 agents simultaneously, `full` runs each preset as a self-contained wave: spawn agents → collect sightings → dedup → Challenger verification → next preset. This keeps each wave's sighting volume manageable, allows per-wave retrospective metrics, and makes each preset independently testable. Cross-preset dedup runs after all presets complete, before final report assembly.

**Extensibility:** New detection categories (e.g., security-focused, performance-focused) are added as new agent groups and registered in new or existing presets. The orchestrator's spawn logic is preset-driven — adding a preset requires no orchestrator changes beyond the preset-to-group mapping.

### Mermaid diagram scoping

The intent register has two components: behavioral claims (text list) and the Mermaid diagram (module relationships, data flow, contracts). Currently, both are injected into every Detector's spawn prompt.

**Change:** The Mermaid diagram is provided to agents whose mandates require understanding module relationships:
- **Intent Path Tracer** — traces execution paths across modules; the diagram is its navigation map
- **Group 2 (dead-code)** — "dead infrastructure" and "middleware never connected" require knowing the intended architectural wiring to identify disconnected components
- **Group 6 (cross-boundary-structure)** — all 4 targets (caller re-implementation, parallel collection coupling, multi-responsibility modules, composition opacity) reason about module boundaries, which is what the diagram describes

All other Tier 1 groups (1, 3, 4, 5, 7) and the Test Reviewer receive only the behavioral claims list. These agents apply per-file detection patterns that don't benefit from structural relationship information.

**Token savings:** ~900 tokens saved per non-diagram agent. 5 Tier 1 groups × 900 + Test Reviewer × 900 = ~5,400 tokens saved per full round vs injecting the diagram everywhere.

### Changes to existing files

**SKILL.md** — Major changes:
- Detection-Verification Loop step 1: replace single-Detector spawn with preset-driven multi-agent spawn
- Add detection preset definitions and per-group toggle interface
- Add entry point identification heuristic for Intent Path Tracer
- Add new step 1a: spawn Sighting Deduplicator agent with wave sightings
- Add Challenger batching (1 per 5 sightings, grouped by detection category, all parallel)
- Agent Team section: update from 2 agent types to 5 (Tier 1 Detectors, Sighting Deduplicator, Challenger, Intent Path Tracer, Test Reviewer)
- Broad-Scope Reviews: update per-unit spawn to preset-driven multi-agent complement

**code-review-guide.md** — Moderate changes:
- Orchestration Protocol: update step 1 to reflect multi-agent spawn, add step 1a (Sighting Deduplicator spawn), add Challenger batching guidance
- Retrospective Fields: add per-group performance metrics (enumeration compliance, sighting volume, sighting survival rate, phase attribution)

**quality-detection.md** — Add 4 new detection targets (unbounded growth, migration idempotency, batch transaction atomicity, intra-function logical redundancy) following existing format.

**ai-failure-modes.md** — No changes. Test-related items (#4, #6, #12, #13) remain in the document; the orchestrator routes them to the Test Reviewer via its dedicated agent definition. The document remains a complete checklist for reference.

**fbk-code-review-detector.md** — Removed. Replaced by 7 per-group Tier 1 agent definitions. No external references depend on this file; all test references are updated as part of B-4 test impact changes.

**fbk-code-review-challenger.md** — No changes to the agent definition or verification protocol. Challenger batching is orchestrator-level.

**existing-code-review.md** — No changes. The conversational flow is orchestrator-directed; the orchestrator handles multi-agent spawn transparently.

**post-impl-review.md** — Minor change: step 2 ("Spawn Detector with modified files + feature spec ACs") updates to multi-agent spawn using named per-group agents.

**fbk-improve skill** — Minor change: improvement analysis agents should be aware of per-group retrospective metrics (enumeration compliance, sighting survival rate, phase attribution) to surface group-specific improvement proposals (e.g., "Group 2 underperforming — consider splitting").

### Integration seam declaration

- [ ] SKILL.md step 1 ↔ per-group agent definitions: orchestrator spawns each Tier 1 agent by name, injecting code payload and intent claims into the spawn prompt
- [ ] Per-group agent definitions ↔ quality-detection.md / ai-failure-modes.md: agent definitions contain operational copies of detection targets; canonical definitions in source documents are authoritative
- [ ] SKILL.md step 1 ↔ Intent Path Tracer: orchestrator provides intent register (claims + Mermaid diagram) + entry points with associated claims; agent reads code via tools and returns sightings in standard format
- [ ] SKILL.md step 1 ↔ Test Reviewer: orchestrator provides test files + production imports + intent claims; agent returns sightings in standard format
- [ ] SKILL.md step 1a (dedup) ↔ Sighting Deduplicator agent: orchestrator spawns Deduplicator with raw sighting list; receives deduplicated list + merge log
- [ ] Sighting Deduplicator ↔ step 2 (Challenger): deduplicated sighting set feeds into Challenger batching
- [ ] SKILL.md step 2 (Challenger batching) ↔ Challenger agent definition: Challengers receive batches of up to 5 sightings grouped by detection category; Challenger protocol is unchanged
- [ ] quality-detection.md new targets ↔ per-group agent definitions: each new target is assigned to exactly one group and copied to its agent definition
- [ ] ai-failure-modes.md test items ↔ Test Reviewer: items #4, #6, #12, #13 are included in the Test Reviewer agent definition, not removed from ai-failure-modes.md
- [ ] quality-detection.md test item ↔ Test Reviewer: test-production string alignment is included in the Test Reviewer agent definition

## Testing strategy

### New tests needed

Shell tests verify structural shape and group completeness. Detection accuracy is verified via evaluation (UV-8).

- Shell test: Verify all 7 per-group Tier 1 agent definition files exist at `assets/agents/fbk-t1-*.md` with required frontmatter (name, tools: Read/Grep/Glob, model: sonnet).
- Shell test: Verify each per-group agent definition contains its assigned detection target names (cross-reference against the group definitions in this spec).
- Shell test: Verify Intent Path Tracer agent definition exists at `assets/agents/fbk-intent-path-tracer.md` and contains required fields (name, tools: Read/Grep/Glob, path-tracing mandate).
- Shell test: Verify Test Reviewer agent definition exists at `assets/agents/fbk-cr-test-reviewer.md` and contains required fields (name, tools: Read/Grep/Glob, test review mandate).
- Shell test: Verify `quality-detection.md` contains all 4 new detection target section headings: "Unbounded data structure growth", "Migration/DDL idempotency" (or "Migration idempotency"), "Batch transaction atomicity", "Intra-function logical redundancy". Each section contains "Detect this when".
- Shell test: Verify SKILL.md Detection-Verification Loop references all 7 Tier 1 group agent names.
- Shell test: Verify SKILL.md Agent Team section references Tier 1 Detectors, Sighting Deduplicator, Challenger, Intent Path Tracer, and Test Reviewer.
- Shell test: Verify SKILL.md step 1a references Sighting Deduplicator agent spawn (grep for "deduplicator" or "dedup").
- Shell test: Verify Sighting Deduplicator agent definition exists at `assets/agents/fbk-sighting-deduplicator.md` with no tools and merge mandate.
- Shell test: Verify SKILL.md contains Challenger batching guidance (grep for "per 5 sightings" or "wave" or "batch").
- Shell test: Verify no detection target name from ai-failure-modes.md or quality-detection.md was lost — every existing target name appears in at least one agent-facing document post-change. (Extends the AC-10 test from instruction-hygiene.)
- Shell test: Verify SKILL.md contains "randomize" or "shuffle" instruction for detection target ordering.
- Shell test: Verify code-review-guide.md references preset-driven spawn (grep for "preset" or "Tier 1") and Sighting Deduplicator (grep for "Deduplicator" or "dedup").
- Shell test: Verify Mermaid diagram scoping — `fbk-intent-path-tracer.md`, `fbk-t1-dead-code-detector.md`, and `fbk-t1-cross-boundary-structure-detector.md` reference "Mermaid" or "diagram"; all other `fbk-t1-*.md` and `fbk-cr-test-reviewer.md` do NOT.
- Shell test: Verify post-impl-review.md step 2 references multi-agent spawn (not single Detector).
- Shell test: Verify each per-group agent definition contains per-file enumeration instruction ("clean files" or "summary line" or "issues were found") and two-phase cross-instance search instruction ("after completing the detection pass" or "search the full project").
- Shell test: Verify SKILL.md contains entry point identification heuristic (grep for "entry point" and "intent register" and "conventional").
- Shell test: Verify code-review-guide.md retrospective fields reference "enumeration compliance", "sighting survival" or "survival rate", and "phase attribution".
- Shell test: Verify SKILL.md specifies identical code payload ordering for Tier 1 spawn prompts (grep for "identical" and "payload" and "order").
- Shell test: Verify `fbk-cr-test-reviewer.md` contains all 5 specific agentic failure mode names: "Name-assertion mismatch", "Non-enforcing test", "Semantically incoherent fixtures", "Mock permissiveness", "Test-production string alignment".
- Shell test: Verify SKILL.md contains per-agent respawn gating (grep for "respawn" and "verified" and "info").

### Existing tests impacted

**Tests referencing `fbk-code-review-detector.md`** — The generic Detector is replaced by 7 per-group definitions. These tests need updating to reference per-group agent files or verify the generic fallback differently:
- `tests/sdl-workflow/test-code-review-integration.sh` — References generic Detector; update to verify per-group agent definitions
- `tests/sdl-workflow/test-code-review-structural.sh` — References generic Detector; update assertions to per-group agents. ai-failure-modes.md item count (>= 14) assertions remain valid.
- `tests/sdl-workflow/test-classification-system.sh` — References generic Detector; update to per-group agents
- `tests/sdl-workflow/test-category-migration.sh` — References generic Detector; update to per-group agents
- `tests/sdl-workflow/test-instruction-hygiene-agents.sh` — References generic Detector; update to per-group agents
- `tests/sdl-workflow/test-instruction-hygiene-coverage.sh` — References generic Detector and quality-detection.md; update Detector references, quality-detection count assertions need updating (>= 11 → >= 15 with 4 new targets)

**Tests referencing SKILL.md orchestration** — Decomposition changes how quality-detection is referenced in SKILL.md:
- `tests/sdl-workflow/test-instruction-hygiene-orchestration.sh` (test 4) — Greps SKILL.md for `quality-detection`; update if decomposition changes how quality-detection is referenced
- `tests/sdl-workflow/test-orchestration-extensions.sh` (test 8) — Asserts SKILL.md Detector spawn references quality-detection.md; update to reflect preset-driven spawn

**Tests referencing quality-detection.md** — No targets removed, only added. Existing assertions should pass, but count thresholds need updating:
- `tests/sdl-workflow/test-detection-scope.sh` — Detection target count assertion (>= 11) needs updating to >= 15
- `tests/sdl-workflow/test-instruction-hygiene-heuristics.sh` — "Detect this when" count assertion (>= 11) needs updating to >= 15
- `tests/sdl-workflow/test-instruction-hygiene-scope.sh` — No changes needed (tests individual target presence, not counts)
- `tests/sdl-workflow/test-code-review-guide-extensions.sh` — No changes needed (tests quality-detection reference presence)

**Installer tests** — Must verify install/uninstall of new agent files (10 new agents vs 1 generic):
- `tests/installer/test-install.sh` — References `fbk-code-review-detector.md`; update to verify per-group agent files + Deduplicator
- `tests/installer/test-upgrade-uninstall.sh` — References `fbk-code-review-detector.md` for uninstall verification; update to cover new agent files
- `tests/installer/test-e2e-lifecycle.sh` — References `fbk-code-review-detector.md`; update to cover new agent files

### Test infrastructure changes

None — existing shell test infrastructure is sufficient.

### User verification steps

UV-1: Open SKILL.md → Detection-Verification Loop step 1 spawns 7 named Tier 1 per-group agents, Intent Path Tracer, and Test Reviewer in parallel. Each Tier 1 agent name matches its agent definition file.

UV-2: Open SKILL.md → step 1a spawns Sighting Deduplicator agent with wave sightings. Open `assets/agents/fbk-sighting-deduplicator.md` → contains location-based merge logic, merge rules, pattern-label preservation, and merge log output.

UV-3: Open SKILL.md → step 2 describes Challenger batching (1 per 5 sightings, grouped by detection category, all parallel per wave).

UV-4: Open each `assets/agents/fbk-t1-*.md` file → contains its group's detection targets, behavioral comparison methodology, sighting output instructions, scope discipline, per-file enumeration, and two-phase cross-instance search. Count total active instructions and verify against the overhead inventory.

UV-5: Open `assets/agents/fbk-intent-path-tracer.md` → contains path-tracing mandate, 4 detection targets, entry-point-based tracing, tool-based file access, standard sighting output format.

UV-6: Open `assets/agents/fbk-cr-test-reviewer.md` → contains test-intent alignment, tests protecting bugs, 5 agentic test failure mode targets, standard sighting output format.

UV-7: Open `quality-detection.md` → contains 4 new sections (unbounded growth, migration idempotency, batch transaction atomicity, intra-function logical redundancy) in standard format with "Detect this when..." heuristics.

UV-8a: (Human-triggered, post-release) **Methodology expansion.** Run code review on Project B or a comparable repo (minimum criteria: 5-50 source files, >=15 filed issues from an independent source). Of the 4 methodology-gap issues from the divergence analysis (#4, #25, #3, #12), how many do the new detection targets catch? Binary per-target: fires or doesn't.

UV-8b: (Human-triggered, post-release) **Execution improvement.** Same run as UV-8a. Of the 14 execution-gap issues from the divergence analysis, how many does the decomposed pipeline catch vs v0.3.5's 0/14? This is the decomposition's own scorecard. Require 2 runs for both success and regression conclusions.

UV-8c: (Human-triggered, post-release) **Martian benchmark re-run.** Run full 50-PR benchmark with `behavioral-only` preset. Compare against v0.3.5 consensus baseline (F1=31.6% all-types, projected F1=46.4% behavioral-only). Validates whether the behavioral-only projection holds as an actual (not projected) score. Require 2 runs with consensus judge protocol for both success and regression conclusions.

UV-9: Verify all 25 Tier 1 detection targets are assigned to exactly one of the 7 groups, with no target missing and no target in multiple groups. Cross-reference against the pre-change target list.

UV-10: Verify the Mermaid diagram is provided to Intent Path Tracer, Group 2 (dead-code), and Group 6 (cross-boundary-structure). Verify all other Tier 1 groups and the Test Reviewer receive intent claims only, NOT the diagram.

UV-11: Verify all 7 Tier 1 Detector spawn prompts contain identical code payloads in identical order (prompt cache optimization).

UV-12: Open code-review-guide.md Orchestration Protocol section → reflects preset-driven multi-agent spawn, Sighting Deduplicator step, and Challenger batching per preset wave.

## Documentation impact

### Project documents to update
- `CHANGELOG.md` — add entry under v0.4.0 for detector decomposition
- `README.md` — check whether detection methodology or agent topology is referenced; update if the multi-agent architecture changes any user-facing claims
- `ai-docs/detection-accuracy/detection-accuracy-overview.md` — update feature map paths from `ai-docs/detection-accuracy/detector-decomposition/` to `ai-docs/0.4.0/detector-decomposition/`. Update status from "Not started" to current status. Update tiered-detection version from v0.4.0 to v0.4.1.

### New documentation to create
- `assets/agents/fbk-t1-value-abstraction-detector.md` — Group 1 agent definition
- `assets/agents/fbk-t1-dead-code-detector.md` — Group 2 agent definition
- `assets/agents/fbk-t1-signal-loss-detector.md` — Group 3 agent definition
- `assets/agents/fbk-t1-behavioral-drift-detector.md` — Group 4 agent definition
- `assets/agents/fbk-t1-function-boundaries-detector.md` — Group 5 agent definition
- `assets/agents/fbk-t1-cross-boundary-structure-detector.md` — Group 6 agent definition
- `assets/agents/fbk-t1-missing-safeguards-detector.md` — Group 7 agent definition
- `assets/agents/fbk-intent-path-tracer.md` — Intent Path Tracer agent definition
- `assets/agents/fbk-cr-test-reviewer.md` — Test Reviewer agent definition
- `assets/agents/fbk-sighting-deduplicator.md` — Sighting Deduplicator agent definition

## Acceptance criteria

- AC-01: 7 per-group Tier 1 agent definition files exist, each self-contained with its assigned detection targets, behavioral comparison methodology, sighting output, scope discipline, per-file enumeration, and two-phase cross-instance search instructions.
- AC-02: The retrospective includes per-agent instruction trace: instruction files loaded at runtime and total prompt composition (instruction tokens vs payload tokens). Implementation validates hook-based Read attribution (PreToolUse hook logging `{agent_id, file_path}` for instruction file reads); falls back to structured agent output if agent identity context is unavailable in hooks. The overhead instruction inventory is documented in this spec. The ~20 active instruction target is a guideline — every reduction improves compliance, but exceeding it does not block release.
- AC-03: SKILL.md Detection-Verification Loop step 1 resolves the selected detection preset to agent groups and spawns them in parallel. Tier 1 spawn prompts contain identical code payloads for prompt cache optimization.
- AC-04: Intent Path Tracer agent definition exists with path-tracing mandate, 4 detection targets (architectural mismatch, intent drift, unreachable features, workflow completeness), tool-based file access, and standard sighting output.
- AC-05: Test Reviewer agent definition exists with test-intent alignment, tests-protecting-bugs, and 5 agentic test failure mode targets. Test items (#4, #6, #12, #13 from ai-failure-modes.md, test-production string alignment from quality-detection.md) are included in the Test Reviewer agent definition.
- AC-06: quality-detection.md contains 4 new detection targets (unbounded growth, migration idempotency, batch transaction atomicity, intra-function logical redundancy) in standard format with "Detect this when..." heuristics.
- AC-07: Every detection target that existed pre-change exists in at least one agent-facing document post-change. No detection capability lost during decomposition.
- AC-08: SKILL.md step 1a spawns a Sighting Deduplicator agent with the wave's sighting list. Sighting Deduplicator agent definition exists at `assets/agents/fbk-sighting-deduplicator.md` with merge mandate, no tools, and merge log output. Retrospective includes merge count and merged pairs from dedup logs.
- AC-09: SKILL.md contains Challenger batching guidance: 1 Challenger per 5 sightings, grouped by originating detection category, all spawned in parallel. Challengers run per preset wave.
- AC-10: The orchestrator randomizes detection target ordering within each group's spawn payload per run.
- AC-11: The Mermaid diagram is provided to the Intent Path Tracer, Group 2 (dead-code), and Group 6 (cross-boundary-structure). All other Tier 1 groups and the Test Reviewer receive intent claims only.
- AC-12: SKILL.md contains an entry point identification heuristic for the Intent Path Tracer (intent register claims, conventional entry points, package configuration).
- AC-13: post-impl-review.md reflects multi-agent spawn using named per-group agents.
- AC-14: code-review-guide.md Orchestration Protocol section reflects multi-agent spawn, deduplication step with merge policy, and Challenger batching.
- AC-15: Retrospective fields include per-group performance metrics: enumeration compliance (files_reported / files_in_scope), sighting volume, sighting survival rate (sightings promoted to findings / total sightings), and phase attribution (Phase 1 vs Phase 2 sighting counts). All metrics are computable by the orchestrator from existing detection and verification output.
- AC-16: SKILL.md defines detection presets (`behavioral-only`, `structural`, `test-only`, `full`) with preset-to-group mappings. Default preset is `behavioral-only`.
- AC-17: SKILL.md supports per-group toggle overrides on any preset.
- AC-18: The `full` preset runs each component preset sequentially (behavioral-only → structural → test-only). Within each preset wave, all groups run in parallel. Each wave has its own Sighting Deduplicator and Challenger pass. After all preset waves complete, cross-preset finding dedup runs inline (orchestrator-level, no agent spawn).
- AC-19: A shell test verifies each detection target name from quality-detection.md and ai-failure-modes.md appears in exactly one per-group agent definition or the Test Reviewer. Catches missing targets, cross-group duplication, and duplication drift.
- AC-20: SKILL.md contains per-agent respawn gating: agents are only respawned in iterative rounds if their previous instance produced at least one verified sighting above info level. Maximum 5 repetitions per agent.

## Open questions

1. **Group 2 size.** *(Resolved: keep as-is.)* Group 2 (dead-code) has 5 items at 18 total active instructions. All 5 use reachability/liveness reasoning — the 2-instruction delta from smaller groups is marginal given IFScale's linear degradation model, and splitting would produce a 2-item group where 87% of instruction budget is overhead. Per-group enumeration compliance rate (AC-15) provides the evaluation signal: if Group 2's enumeration coverage is consistently lower than 3-item groups, split into `dead-infrastructure` (3) and `dead-logic` (2).

2. **Test Reviewer instruction count.** *(Resolved: keep as-is.)* The Test Reviewer has 7 detection targets (~20 total instructions) in two coherent clusters: intent comparison (test-intent alignment, tests-protecting-bugs) and enforcement validation (5 agentic failure modes). Splitting would destroy the cross-cluster signal — the most valuable findings come from the intersection (e.g., a name-assertion mismatch that's actually a test protecting a bug). The Test Reviewer also has a natural context advantage: it receives only test files + production imports, not the full codebase. Per-group enumeration compliance rate (AC-15) applies to the Test Reviewer. If enumeration coverage is consistently below Tier 1 group averages, split into test-intent (test-intent alignment, tests-protecting-bugs) and test-failure-modes (5 agentic failure modes).

3. **Broad-scope cost.** *(Resolved: addressed by detection presets.)* The 72-spawn scenario assumed full-complement runs. With detection presets (default: `behavioral-only`), most real scans spawn 4-5 agents per unit, not 9. The `full` preset runs presets sequentially, keeping each wave manageable. Users who select `full` on a broad-scope review opt into the cost knowingly. No orchestrator-level pruning heuristic needed.

4. **Deduplication false merges.** *(Resolved: simplified merge policy, keep pre-Challenger.)* Preset-sequential execution reduces cross-group overlap — agents within a preset wave have distinct mandates. Merge policy simplified to: retain higher severity, more specific type, list all detection sources, keep higher-severity observation text. Retrospective logs merge count and merged pairs for auditability. If false merge rates are high, the data will be visible in retrospective logs.

5. **Detection target duplication maintenance.** *(Resolved: shell test enforcement.)* Per-group agent definitions contain operational copies of detection targets. A shell test verifies that each detection target name from quality-detection.md and ai-failure-modes.md appears in exactly one per-group agent definition or the Test Reviewer — catching both missing targets and cross-group duplication. See AC-19.

6. **Output verbosity as a cost lever.** *(Resolved: deferred to v0.4.1.)* Orthogonal to detection quality — purely output format and cost optimization. Full diagnostic output (intent register, retrospective with AC-15 metrics) is required during 0.4.0 evaluation to validate decomposition. Verbosity modes should be designed after multiple runs establish which retrospective fields are load-bearing for ongoing evaluation vs one-time validation. Added to v0.4.1 scope.

7. **Per-finding-type detection filters.** *(Resolved: promoted to spec scope.)* Detection presets and per-group toggles are now a first-class feature. See "Detection presets and per-group filters" in Technical approach. Default preset is `behavioral-only`. Benchmark data validates: behavioral-only projected F1=46.4% vs 31.6% all-types.

## Dependencies

- **Depends on:** `instruction-hygiene` (v0.3.5, complete) — assumes cleaned-up instruction set, deduplicated definitions, resolved scope contradiction, promoted heuristics, and content-first prompt ordering.
- **Depends on:** `intent-extraction` (v0.3.5, complete) — assumes existing intent register format (claims + Mermaid diagram) and user checkpoint flow.
- **Depended on by:** `tiered-detection` (v0.4.1) — assumes decomposed orchestrator spawn logic, per-group agent definitions, cross-agent deduplication infrastructure, Challenger batching, and per-group detection attribution.
- **Depended on by:** `output-verbosity` (v0.4.1) — findings-only production mode, ~60-70% output reduction. Requires 0.4.0 retrospective data to determine which diagnostic fields are safe to strip.
