# Progressive Disclosure Refactor — Parent Spec

This is a parent coordination document. It captures the progressive-disclosure principles being applied, the eight specific violations identified by the bootstrap audit, and the child-spec map for fixing each violation as isolated work. Each child spec is authored, reviewed, and implemented on its own; no work happens against this parent spec directly.

---

## Progressive Disclosure Principles

The Firebreak context-asset tree was authored before its own progressive-disclosure rules in `assets/fbk-docs/fbk-context-assets.md` were finalized. This refactor brings the tree into compliance with those rules, applied aggressively. The principles below govern every child spec.

### Aggressive progressive disclosure

Every instruction in a loaded asset must apply every time the asset loads. Not 90%, not "the primary use case" — every load. An instruction that applies only sometimes belongs in a separately-routed asset gated by its sub-condition.

### Tree-shaped, stage-local routing

Routing is tree-shaped. Each routing decision happens at its own scope, narrowing as the agent's task narrows. Centralized indexes — single tables that enumerate every condition the system might encounter — are an anti-pattern. We are explicitly not creating gigantic single routing tables; we are dismantling them.

The skill (or top-level asset) makes only its immediate routing decision. The leaf it routes to makes its own next decision. Each leaf at each stage is a router for its own scope, not a holder of every downstream concern.

### Per-load-path Necessity Test

Given other assets already loaded on the same path, every instruction must add new behavior. An instruction that another loaded asset along the same chain already covers fails this test and must be removed from at least one location.

### Cross-route validity

Reference assets reachable from multiple parent routes must contain only instructions valid under *every* parent route. Condition-specific content extracts to deeper sub-leaves.

### Asset-type taxonomy

Use the right asset type for each role:

- **Agents** (`assets/agents/<name>.md`) own persona content — role, voice, values, anti-defaults, quality bars. Persona always lives in an agent file. Skills and leaves may spawn agents that read leaves as task instructions, but persona never moves into a leaf or inline into a skill.
- **Leaves** (`assets/fbk-docs/**/*.md`) own task instructions, schemas, methodologies, checkpoints, references. The leaf is *what* to do; the agent is *who* is doing it.
- **Skills** (`assets/skills/<name>/SKILL.md`) are triggers (slash command, semantic invocation) plus instructions. Instructions may be actual instructions, a routing table for a condition tree, or a combination. Skills don't own persona. Skills can read leaves and spawn agents.

### Necessity Test (per-instruction)

For every instruction, ask: *"If removed, is the agent more likely to make a mistake?"* If the answer is no, the instruction does not earn its place. Every sentence in every context asset must prevent a concrete mistake.

---

## Bootstrap Audit Findings

The initial audit identified eight specific progressive-disclosure violations in the asset tree. Each is in scope for the refactor; each becomes its own dedicated child spec.

### Finding 1: `skills/fbk-council/SKILL.md` — single-file conflation

**Location:** `assets/skills/fbk-council/SKILL.md` (947 lines).
**Problem:** Quick Council, Full Council, Ralph Wiggum loop, compaction recovery, self-evaluation, decision protocol, members table, orchestration guidelines, and observability all coexist in one file. Every council invocation loads instructions for modes that aren't active.
**Principles violated:** strict relevance, per-load-path Necessity Test, asset-type discipline (skill body holds content that should be tree-shaped routing).
**Child spec:** `council-decomposition`.
**State:** IMPLEMENTED 5/3/2026

### Finding 2: `skills/fbk-code-review/SKILL.md:10` — five-doc unconditional load

**Location:** `assets/skills/fbk-code-review/SKILL.md:10`.
**Problem:** Skill loads `code-review-guide.md`, `ai-failure-modes.md`, `security-patterns.md`, `detection-audits.md`, and `quality-detection.md` unconditionally. `security-patterns.md` is only relevant for code touching auth/network/persistence; `quality-detection.md` is only relevant when preset includes structural targets (default preset excludes them); `detection-audits.md` is diff-specific.
**Principles violated:** strict relevance.
**Child spec:** `code-review-conditional-loads`.
**State:** DEFERRED - requires more careful and dedicated code-review revision

### Finding 3: Code-review orchestration loop duplicated in skill and guide

**Locations:** `assets/skills/fbk-code-review/SKILL.md:79-93` (Detection-Verification Loop) and `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md:99-113` (Orchestration Protocol).
**Problem:** The same 10-step orchestration protocol is described in both files in near-identical wording. Same for source-of-truth handling at `SKILL.md:20-22` vs `guide:121-131`.
**Principles violated:** per-load-path Necessity Test.
**Child spec:** `code-review-orchestration-dedup`.
**State:** DEFERRED - requires more careful and dedicated code-review revision


### Finding 4: `skills/fbk-spec` Verification Gate duplicated with guide

**Locations:** `assets/skills/fbk-spec/SKILL.md:34-42` (Gate section) and `assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md:124-156` (Verification Gate + Transition).
**Problem:** Skill and guide both describe the gate decision flow and transition prose. Verification confirmed the *transition flow* is the actual duplication (skill 40-42 ≈ guide 147-153), not the structural-prerequisites prose. Same pattern applies to `fbk-spec-review` ↔ `review-perspectives.md` (threat-model determination + transition) and `fbk-implement` ↔ `implementation-guide.md` (wave loop, escalation, final verification, team setup, team shutdown).
**Principles violated:** per-load-path Necessity Test.
**Child spec:** `sdl-skill-guide-dedup`. Scope spans the SDL skill/guide pairs that exhibit this pattern. Verification refined which pairs have true duplication: `fbk-implement` (largest), `fbk-spec` (transition only), `fbk-spec-review` (threat-model + transition). `fbk-breakdown` does NOT exhibit duplication — schema description in skill is operational mapping, not duplication of the guide's schema definition.
**State:** IMPLEMENTED 2026-05-04

### Finding 5: `fbk-design-guidelines/quality-detection.md` — cross-route with conditional validity

**Location:** `assets/fbk-docs/fbk-design-guidelines/quality-detection.md`.
**Problem:** Reachable from two parent routes with different validity conditions. `/fbk-code-review` loads it as "structural detection targets applicable to all code reviews," but the default preset (`behavioral-only`) excludes structural findings — so most loads waste the file. `fbk-design-guidelines.md` routes to it for "reviewing code for structural quality," where it applies. Same pattern applies to `security-patterns.md` (cross-route from `fbk-spec-author`, `/fbk-code-review`, possibly others).
**Principles violated:** cross-route validity (content does not hold under every parent route — specifically the unconditional load from code-review default preset).
**Child spec:** `shared-leaf-cross-route-resolution`. Scope: validate content holds under each parent route; split or conditionalize where it doesn't.

### Finding 6: `code-review-guide.md` — mixed audiences

**Location:** `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md` (143 lines).
**Problem:** File mixes detector/challenger reference content (sighting format, finding format, classification — lines 16-97) with orchestrator-only instructions (orchestration protocol, source-of-truth handling, retrospective fields — lines 99-143). The two audiences load via different paths; carrying both in one leaf forces every reader to load the other audience's content. Behavioral Comparison Methodology (lines 3-14) is a third concern not cleanly belonging to either.
**Principles violated:** strict relevance, separation of concerns.
**Child spec:** `code-review-guide-split`. Splits into `code-review-guide/sighting-schema.md` (detector/challenger reference) and `code-review-guide/orchestration.md` (skill orchestrator). Methodology placement decided in the spec.

### Finding 7: `agents/fbk-test-reviewer.md` — multiple compounding issues

**Location:** `assets/agents/fbk-test-reviewer.md` (181 lines).

**Problems** (compounding):

1. **Five checkpoints in one body.** CP1–CP5 coexist in a single agent file (`Checkpoint 1` at line 85 through `Checkpoint 5` at line 155). Any given invocation operates at exactly one checkpoint, so each invocation loads four checkpoints' worth of irrelevant instructions. *Principles violated: strict relevance.*

2. **Persona/instruction conflation.** Persona content (role at lines 8–10, quality bars at lines 12–18, context isolation at lines 20–22, override mechanism at 63–73) is intermixed with checkpoint-specific instructions (lines 85–169). Per the asset-type taxonomy, persona belongs in the agent file; per-checkpoint instructions are leaves under `fbk-docs/`, loaded on demand. *Principle violated: asset-type discipline.*

3. **No direct user-invocable trigger.** Agent frontmatter (line 3) claims `Invocable on-demand via /test-review`, but no `/test-review` skill exists in `assets/skills/`. The advertised user-invocation path is broken. Only real triggers are spawn sites at `assets/skills/fbk-spec-review/SKILL.md:49` (CP1) and `assets/skills/fbk-breakdown/SKILL.md:77` (CP2) via Agent Teams teammate spawn. *Principle violated: asset-type discipline (skills are triggers; an agent that documents a non-existent skill trigger is broken).*

4. **CP3, CP4, CP5 have no spawn sites.** `/fbk-implement` does not spawn the agent at any wave step (the "checkpoint" references in `/fbk-implement` are wave checkpoints, a different concept). The on-demand invocation that CP5 would use depends on the missing `/test-review` skill. CP3–CP5 are aspirational dead documentation in `assets/`. *Principle violated: Necessity Test (instructions for invocations that never happen don't earn their place).*

5. **Frontmatter `name` field inconsistent with filename.** Frontmatter declares `name: test-reviewer` (line 2), but the file is `fbk-test-reviewer.md`. Every other agent in `assets/agents/` declares `name: fbk-<role>` matching its filename (`fbk-improvement-analyst`, `fbk-spec-author`, `fbk-task-compiler`, etc.). The missing `fbk-` prefix breaks naming convention and may interfere with agent-resolution if loaders match filename to frontmatter name. *Principle violated: convention consistency.*

**Principles violated overall:** strict relevance, asset-type discipline, Necessity Test, naming-convention consistency.

**Child spec:** `test-reviewer-overhaul`. User-pinned as a dedicated larger spec scoping the agent in total. Scope includes:

- Persona-only agent file (~30 lines: role, quality bars, anti-defaults, override mechanism, output format, brownfield modifier).
- Per-checkpoint leaf docs at `assets/fbk-docs/fbk-sdl-workflow/test-reviewer-checkpoints/cp<N>.md` for the checkpoints that have spawn sites.
- Frontmatter `name` field corrected to `fbk-test-reviewer`.
- Frontmatter description corrected — remove the dangling `/test-review` reference if the skill is not authored as part of this spec.
- Decision on `/test-review` skill creation: implement as a real user-invocable skill (with appropriate routing for CP3/CP4/CP5 invocation modes), or remove the claim from frontmatter and treat test-reviewer as solely an agent-team spawnable.
- Decision on CP3, CP4, CP5: implement spawn sites in `/fbk-implement` (CP3 after test code is written, CP4 pre-merge), implement an on-demand invocation path for CP5 mutation testing, OR drop them and capture in a future spec.
- Cross-doc reference updates: `feature-spec-guide.md:28,49` and `corrective-workflow.md:50` hardcode the parent-file path and criterion numbers; both need updating to point at the new structure.
- Test-suite updates: rewrite `test-test-reviewer-agent.sh`, `test-test-reviewer-extensions.sh`, `test-test-reviewer-persona.sh` against the new persona-only + per-CP-leaf structure.

### Finding 8: `fbk-sdl-workflow.md` — mixed index and content; orphan file

**Location:** `assets/fbk-docs/fbk-sdl-workflow.md`.
**Problem:** File mixes pipeline principles (lines 1-22) with a routing table (lines 24-46). Verification additionally confirmed the file is an orphan — no skill, agent, or `assets/CLAUDE.md` references it; it's not loaded anywhere. Pipeline principles repeat content in the leaves it claims to index.
**Principles violated:** separation of concerns; the orphan status raises a meta-question about whether the file should exist at all.
**Child spec:** `fbk-sdl-workflow-cleanup`. Scope: decide keep or remove; if keep, separate principles from routing; if remove, redistribute the iteration-cap table to its load-bearing destination (likely `implementation-guide.md`).

---

## Child Spec Map

Each finding has one dedicated child spec. Child specs live at `ai-docs/progressive-disclosure-refactor/<child-name>/<child-name>-spec.md` per the project-level convention in `feature-spec-guide.md:118`.

| # | Child spec | Touches | Notes |
|---|------------|---------|-------|
| 1 | `council-decomposition` | `skills/fbk-council/`, council session-state Python (read-only) | Tree-shaped: thin SKILL trigger + tier leaves as their own routers + condition leaves on demand |
| 2 | `code-review-conditional-loads` | `skills/fbk-code-review/SKILL.md` | Move conditional loads into orchestration spawn-prompt construction (preset is resolved at pipeline run, not skill load) |
| 3 | `code-review-orchestration-dedup` | `skills/fbk-code-review/SKILL.md`, `code-review-guide/orchestration.md` | Skill defers to guide; guide owns the loop. Depends on Finding 6 splitting the guide first. |
| 4 | `sdl-skill-guide-dedup` | `skills/fbk-spec/`, `fbk-spec-review/`, `fbk-implement/` and corresponding guides | Skill keeps gate-script invocations; guide owns workflow content. `fbk-implement` ↔ `implementation-guide.md` is the largest pair. `fbk-breakdown` is excluded — no real duplication. |
| 5 | `shared-leaf-cross-route-resolution` | `quality-detection.md`, `security-patterns.md` | Validate content holds under each parent route; split or conditionalize where it doesn't |
| 6 | `code-review-guide-split` | `code-review-guide.md` → `code-review-guide/sighting-schema.md` + `code-review-guide/orchestration.md` | Detector/challenger spawn-prompt construction in skill updated to point at sighting-schema |
| 7 | `test-reviewer-overhaul` | `agents/fbk-test-reviewer.md`, per-CP leaves, frontmatter corrections, `/test-review` skill (if in scope), cross-doc reference updates, test-suite updates | User-pinned larger spec covering five compounding issues: 5-CP conflation, persona/instruction conflation, broken `/test-review` claim, missing CP3–CP5 spawn sites, frontmatter name convention violation |
| 8 | `fbk-sdl-workflow-cleanup` | `fbk-sdl-workflow.md` | Orphan-or-keep decision; if keep, separate routing from principles |

### Dependencies

- Finding 6 (`code-review-guide-split`) before Finding 3 (`code-review-orchestration-dedup`): can't dedup if the guide hasn't been split yet.
- All child specs benefit from validation tooling (see Cross-cutting Concerns below); the foundational test-suite extensions are authored alongside the first child spec that needs them, or as a small dedicated spec preceding the others.
- No other inter-finding dependencies. Findings 1, 2, 4, 5, 7, 8 are independent.

---

## Cross-cutting Concerns

These apply to every child spec and are not duplicated in each one.

- **Tree-shaped routing.** No child spec creates a centralized routing table. Each child spec applies stage-local routing per the principles above.
- **Asset-type taxonomy.** Persona stays in agents, instructions in leaves, triggers + routing in skills.
- **Test-suite extensions.** Asset-tree validation lives in `tests/sdl-workflow/` (TAP-format shell tests, auto-discovered by `.github/workflows/ci.yml`). New detectors needed for the refactor (broken-paths, cross-route-leaves, load-path-duplication, in-asset-conditional smell) are added to that suite — not as a parallel Python harness. A small `fbk asset-graph` Python helper supports multi-hop chain traversal where shell is impractical. Existing tests under `tests/sdl-workflow/` that hard-code current asset structure (`test-council-skill-references.sh`, `test-test-reviewer-*.sh`, `test-code-review-*.sh`) are updated within the child spec that touches their target asset, OR deleted when their assertions belong to a refactor that is already complete and the general structural detectors below subsume their purpose.
- **Adaptive structural detectors over path-pinning.** Tests should encode the invariants we care about (no orphans; every `read <path>` reference resolves under both source-tree and install-tree path conventions) rather than pin specific file paths or content strings. Path-pinning tests are brittle artifacts of past refactors and break on every structural change. Two general detectors capture the real invariants: an **orphan detector** that walks all triggers (skills, agents with spawn sites, CLAUDE.md, paths-scoped rules, hooks), follows every `read <path>` reference recursively, and asserts every file under `assets/fbk-docs/`, `assets/agents/`, `assets/skills/` is reached; and a **link-resolution detector** that resolves every reference under both `assets/...` and `~/.claude/...` path conventions. These adapt to any structure change automatically — no per-refactor test maintenance required. Authored as a preceding `asset-graph-detectors` spec; every subsequent child spec relies on these for verification rather than authoring its own path-pinning tests.
- **Existing-codebase audit before drafting.** Every child spec must enumerate the existing tests, scripts, and references touching its target before proposing changes. The bootstrap audit's process miss (proposing parallel infrastructure without checking what already exists) is documented in the retrospective.
- **CI integration.** New tests are auto-discovered by the existing CI glob `for test in tests/sdl-workflow/test-*.sh`. No CI workflow changes required.
- **Documentation discipline.** Each child spec's release entry updates `CHANGELOG.md` per `keepachangelog.com` format. `README.md` is reviewed for path-reference impact when files move; required edits discussed with the user before applying.
- **Behavioral preservation.** Every refactor preserves observable agent output. The refactor moves instructions; it does not change what the agents produce. Smoke tests at child-spec gate verify equivalence.

---

## Non-goals

- No changes to agent personas, workflow stages, output formats, or SDL pipeline ordering. Routing/structure changes only.
- No expansion of the rule set in `fbk-context-assets.md` or its sub-leaves. We apply existing rules; we don't author new ones.
- No refactor of assets that already pass the rules for stylistic uniformity.
- No fix for the soft violations the audit explicitly flagged as defensible (centralized frontmatter tables in `fbk-context-assets/skills.md` and `agents.md`).
- No retroactive rewrite of in-flight specs in `ai-docs/`.
- No generalization of validation tooling for use outside this repo.

---

## Future work (recognized, not in scope)

These insights surfaced during child-spec authoring and are recognized as worth pursuing later, but are not in scope for any of the eight findings:

- **Logging hookification.** Several `session-logger` invocations the council orchestrator currently runs explicitly (`contribution`, `tool-use`, potentially `phase-start`/`phase-end` checkpoints, `session-state checkpoint`) would be better satisfied deterministically by hooks rather than orchestrator-invoked commands. The pattern is already partially established: `permission-request` is auto-logged by a permissions hook today. Future hookification would: (a) reduce orchestrator-loadable context (the SKILL no longer needs to list these commands inline), (b) eliminate the failure mode where the orchestrator forgets to log a contribution, (c) enable richer logging (full content via stdin) without spec churn. Out of scope for progressive-disclosure-refactor because hookification touches `assets/fbk-scripts/fbk/council/*.py`, new hook scripts, and `.claude/settings.json` — different work surface from asset-tree restructuring. Surfaced during DECISION-D in `council-decomposition` child spec (2026-05-02).

---

## Project-level Open Questions

These are project-wide questions deferred to or shaped by individual child specs.

- **Q1: Order of child-spec authoring.** Finding 1 (council) is the largest single token-load reduction. Finding 7 (test-reviewer) is user-pinned as a dedicated larger spec. Findings 6 → 3 must sequence in that order. Other findings are independent. Default order: 1, 6, 3, 2, 4, 5, 8, 7. Reorder per priority as decisions land.
- **Q2: Test-suite extensions — preceded as a separate small spec or authored alongside the first child spec that needs them?** Each child spec needs at least the broken-paths detector to verify its own changes. Recommendation: small dedicated spec preceding the others, since every subsequent spec depends on it. **Resolved during council-decomposition spec authoring (2026-05-02): a preceding `asset-graph-detectors` spec authors the `fbk asset-graph` helper plus the orphan and link-resolution shell tests. Detectors are general structural invariants that adapt to any structure change automatically, replacing path-pinning tests rather than augmenting them.**
- **Q3: `fbk-sdl-workflow.md` keep or remove?** Verification confirmed it is an orphan with zero callers. Decision belongs in Finding 8's spec; the parent spec does not pre-decide.
- **Q4: CP3–CP5 in `test-reviewer-overhaul` — implement or drop?** User-noted: test-reviewer is supposed to perform real work and `/test-review` was intended as a skill. The dedicated test-reviewer spec scopes whether to implement CP3–CP5 spawn sites and the `/test-review` skill, or refactor only CP1/CP2 and capture the rest as a future feature.

---

## Decisions made during parent-spec scoping

The following decisions were made during this parent spec's authoring and apply to all child specs unless explicitly overridden in a child spec.

1. **Boundary B — audit-driven + harness-driven.** Each child spec fixes its specific finding and runs the test-suite extensions to surface anything else its area touches.
2. **Test-suite extensions, not parallel harness.** Asset-tree validation extends `tests/sdl-workflow/`; no new top-level `fbk` command for asset validation.
3. **Tree-shaped routing, no centralized indexes.** Confirmed as the design principle for every child spec, not just the council one.
4. **Asset-type taxonomy.** Persona/leaf/skill role discipline applies to every child spec.
5. **Cross-route shared leaves are accepted via `cross-route-accepted.txt`** when content holds under every parent route. Splits happen only when content fails the cross-route test under at least one route.
6. **CP3–CP5 in test-reviewer are deferred to that child spec.** Parent spec does not predetermine the answer.
7. **Adaptive structural detectors precede all child specs.** A small `asset-graph-detectors` spec is authored before any of the eight findings' child specs. It delivers the `fbk asset-graph` Python helper plus shell tests for orphan-detection and link-resolution. Each subsequent child spec relies on these general detectors for verification rather than authoring path-pinning tests for its own scope. Existing path-pinning tests whose target refactor is already complete are deleted in the child spec that touches their area.
8. **Council-decomposition direction (Finding 1).** Tier prescription (Quick/Full protocols, tier-selection heuristics, auto-escalation) is replaced by judgment-based council sizing — a single instruction: "size the council appropriately for the current task, selecting the members relevant to the discussion." Orchestrator persona remains as the user's main Claude (not extracted to a subagent), preserving Phase 2 user-clarification capability. Always-relevant content (phases, members table, default logging) stays inline in `SKILL.md` per the "topmost where always relevant" placement principle. Conditionally-relevant content (decision protocol, conflict resolution, compaction recovery, Ralph integration, advanced observability) extracts to leaves under `assets/fbk-docs/fbk-council/`.
