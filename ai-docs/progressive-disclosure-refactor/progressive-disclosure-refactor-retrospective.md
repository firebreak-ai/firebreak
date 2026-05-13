# Progressive Disclosure Refactor — Retrospective

## Timeline

- 2026-05-01: Stage 1 (Spec) — in progress

## Key decisions

1. **Initial framing: feature-level scope with phased waves.** The refactor was first scoped as one cohesive initiative with sequenced phases. (Stage 1, superseded by decision 5)
2. **Phase boundary B: audit-driven + harness-driven.** Fix the eight specific audit-identified violations, then run the validation harness across the whole tree and fix anything else it surfaces. (Stage 1)
3. **Wave 0 reframed: extend existing test infrastructure rather than build a parallel harness.** Initial design proposed a new Python `validate_assets.py` with six detectors. Audit of `tests/sdl-workflow/` revealed orphan detection, per-asset reference checks, and migration-path validation already exist as TAP-format shell tests wired into CI. Revised approach: extend `test-reference-integrity.sh`, add new shell tests for the genuinely new detectors (cross-route, duplication, in-asset conditional), introduce a small `asset_graph.py` Python helper called from shell. No new top-level fbk command. (Stage 1, after user pushback)
4. **Tree-shaped routing, not centralized routers.** Initial Wave 1 design proposed a thin SKILL with a 70-line router carrying members table, tier-selection heuristics, Phase 0 entry check, and routing instructions. User pushback corrected this: the rules in `fbk-context-assets.md` say "Centralized indexes are not required and often counterproductive. Each routing decision happens at its own scope, narrowing as the agent's task narrows." Correct shape: thin SKILL trigger (~15 lines, tier routing only) → tier leaves act as routers for their own scope → leaves load downstream concerns on demand. (Stage 1, after user pushback)
5. **Asset-type taxonomy as architectural principle.** Agents own persona; leaves own instructions; skills are triggers + routing. Persona never lives in a leaf or inline in a skill; per-checkpoint instructions are leaves under `fbk-docs/`, not directories under `agents/`. (Stage 1)
6. **Parent spec restructured for per-finding child specs.** The single feature-spec became too complex as verification surfaced significant issues in every wave (W1 leaf undercount, W2 conditional-load infeasibility, W3 spawn-site nonexistence and convention conflict, W4 misidentified pairs and orphan file). Decision: overwrite the spec with a parent coordination document containing the eight audit findings and progressive-disclosure principles; each finding becomes its own dedicated child spec authored, reviewed, and implemented in isolation. (Stage 1, late)

## Scope changes

- **Validation harness → test-suite extension.** Wave 0 changed from "build new validation harness" to "extend existing test suite + add small Python routing-graph helper." Reduced new code substantially; preserved CI integration; aligned with established convention (shell tests for asset-tree validation, Python in `fbk-scripts/fbk/` for logic modules).
- **Single feature spec → parent spec + 8 child specs.** Refactor decomposed from 5 sequenced waves in one spec to 8 isolated child specs coordinated by a parent. Each child spec is authored, reviewed, and implemented separately. Parent spec contains shared principles, findings, dependency map, and cross-cutting concerns; no work happens against the parent directly.
- **Test-reviewer scope expanded and pinned separately.** The original Wave 3 plan was to split CP1–CP5 into per-checkpoint leaves. Verification revealed CP3–CP5 have no spawn sites and `/test-review` skill doesn't exist. User pinned a dedicated `test-reviewer-overhaul` child spec to handle the agent in total — not just refactor existing CP1/CP2, but decide whether to implement CP3–CP5 spawn sites and the `/test-review` skill, scoped as its own design discussion.

## Stage 1: Spec

### Clarifying questions that revealed ambiguity

- **Scope boundary (audit-driven / audit + harness / full sweep)** — user chose B; this clarification prevented the spec from being either too narrow (would leave un-audited corners untouched) or too broad (would pull on threads beyond the current evidence base).
- **Feature-level vs project-level vs parent-spec coordination** — initial framing was feature-level with phased waves. After verification surfaced significant issues across every wave, the framing shifted to a parent spec (coordination document) plus eight isolated child specs. Per-finding decomposition matches the project's own separation-of-concerns principle applied at the spec level.
- **Wave 0 architecture** — "build new harness" vs "extend existing tests"; resolved as extend.
- **Wave 1 routing shape** — "thin router with tier+heuristics+members+entry-check" vs "tree-shaped, stage-local routing"; resolved as tree-shaped.
- **Wave 3 leaf placement** — `agents/<name>/cp<N>.md` vs `fbk-docs/.../cp<N>.md`; resolved as the latter via the asset-type taxonomy principle.
- **CP3–CP5 in W3** — drop or implement; pinned to the dedicated test-reviewer-overhaul child spec.

### Scope inclusions / exclusions

- **Included**: parent spec captures the 8 audit findings, progressive-disclosure principles, child-spec map, dependencies, cross-cutting concerns, and decisions made during scoping. Each child spec covers exactly one finding.
- **Excluded** (parent-spec Non-goals): no agent persona / workflow stage / output format / SDL pipeline ordering changes; no new rule authoring in `fbk-context-assets.md`; no stylistic refactors of compliant assets; no fix for soft violations explicitly flagged as defensible; no retroactive rewrite of in-flight specs; no generalization of validation tooling outside this repo.

### Open questions deferred to later stages

Project-level open questions are captured in the parent spec under "Project-level Open Questions." Each child spec has its own open-questions section for finding-specific deferrals.

### Process observation — codebase-context check skipped before drafting

**What happened.** The initial Wave 0 design proposed a new Python validation harness (`validate_assets.py` with six detectors and ~12 unit tests) without first auditing the existing test/validation infrastructure. The user challenged with "is this the correct approach? we have existing tests" and that surfaced `tests/sdl-workflow/` — 60+ shell-based asset-tree tests already wired into `.github/workflows/ci.yml`, including `test-reference-integrity.sh` (orphan detection — directly duplicates the proposed `orphans` detector), `test-no-old-path-patterns.sh` (path validation), `test-council-skill-references.sh` (asset-specific reference checks), and `test-instruction-hygiene-*` (5 structural-content tests). The proposed harness would have built parallel infrastructure to existing CI-wired functionality.

**Root cause.** I did not audit the existing test/validation infrastructure before drafting the technical approach. The brownfield spec guide (`fbk-brownfield-spec.md`) explicitly directs *"Search the codebase for existing code that overlaps with the proposed feature before writing the technical approach"* and *"If the feature duplicates functionality that already exists, stop and reconsider the approach."* Both directives were skipped. Specifically:

- `tests/` (top-level) was not enumerated; only `assets/fbk-scripts/tests/` was checked.
- `.github/workflows/ci.yml` was not read to understand what is gated.
- The conventional split (shell tests for asset-tree validation, Python in `fbk-scripts/fbk/` for logic modules) was not derived from the existing structure before proposing a new module.

**Course correction in Stage 1.** Wave 0 was rewritten to extend `test-reference-integrity.sh` where applicable, add three new shell tests for the genuinely new detectors (cross-route, duplication, in-asset conditional), introduce a small `asset_graph.py` Python helper for multi-hop chain traversal called from shell tests, and treat migration-affected per-asset tests (`test-council-skill-references.sh`, `test-test-reviewer-*.sh`, `test-code-review-*.sh`) as deliverables of their respective waves. No new top-level fbk command, no parallel harness.

**Process improvement candidates.**

- **Codebase-context discovery should be a hard precondition for the technical approach section in any brownfield spec.** Currently `fbk-brownfield-spec.md` describes the requirement in prose. Consider promoting it to a structural prerequisite checked by the spec gate, or to an explicit step in `feature-spec-guide.md`'s "before drafting Section 4" guidance.
- **The `/fbk-spec` skill could ask a clarifying question** before drafting the technical approach when the spec involves test infrastructure, validation, CI, or anything that might already exist: "What existing files in this codebase address related concerns? Have you enumerated them?" — phrased as a check the agent runs, not a question to the user.
- **Pre-authoring investigation discipline.** The recently-added `pre-authoring-investigation.md` design guideline addresses related ground for code authoring; consider whether an analogous "pre-spec investigation" step should be loaded by the `/fbk-spec` skill or `fbk-spec-author` agent for brownfield work specifically.
- **Spec gate could grow a heuristic check** that flags new top-level scripts/commands/test files in the technical approach without a corresponding "I checked these existing files first" justification — though this is hard to enforce mechanically and may belong as an agent prompt rather than a gate.

**Lesson.** A spec author working in a brownfield codebase must default to *enumerating* existing infrastructure relevant to the proposed change before designing a solution. The cost of the enumeration is low; the cost of designing parallel infrastructure that has to be discarded is high.

### Process observation — verification before downstream design

**What happened.** After the W0 correction, I drafted W1–W4 designs without verifying current-state claims against the actual files. User asked for "the same scrutiny" applied to each wave; four parallel verification agents reading the target files surfaced significant issues in every wave: W1 undercounted leaves and conflated Phase 0 check with recovery protocol; W2's conditional-load model was infeasible at skill-load time (preset is resolved at `pipeline run`, not skill load); W3's CP3–CP5 spawn sites do not exist and the `agents/<name>/cp<N>.md` directory pattern violates the documented agent-file convention; W4 misidentified the duplications in 3 of 5 pairs and missed three additional cross-skill duplications.

**Root cause.** I treated the original audit's bullet-list of "doing poorly" findings as a sufficient design substrate. A bullet noting "council file has 947 lines and conflates X concerns" is a *symptom*, not a *design*. Designing the fix requires reading every line of the target file, mapping content to proposed leaves, identifying load conditions per leaf, and verifying the surrounding code (Python coupling, test assertions, cross-doc references, hooks) actually accommodates the proposed structure.

**Course correction.** Each child spec must perform full target-file verification during its Stage 1, not just cite the original audit. The parent spec provides the *what* (the eight findings); each child spec provides the *how* and earns its design through reading, not assumption.

**Process improvement candidates.**

- **`pre-authoring-investigation.md` analogue for spec authoring.** The recently-added design guideline addresses pre-coding investigation. The spec-authoring path needs an equivalent: enumerate existing assets, tests, hooks, and cross-references touching the target before drafting Section 4. Make this a structural prerequisite, not just prose guidance.
- **Verification-before-design at each spec stage.** Spec-review (Stage 2) currently focuses on the spec content. Consider whether spec-review should also validate that the spec's current-state claims match the codebase — a "ground-truth audit" pass alongside the spec quality review.
- **Use of parallel verification agents.** Spawning per-area verification agents during spec authoring (one agent per major target file or area) caught issues a single linear read missed. This pattern could be promoted to a standard step in `feature-spec-guide.md` for brownfield specs touching multiple files.

**Lesson.** Don't design downstream of an unverified premise. The original audit was correct in spirit but generated bullet points that read as design directives. They are not designs — they are findings. Each finding becomes a design only after the target is read line-by-line in its current context.

### Process observation — overrouting toward centralized indexes

**What happened.** When verification surfaced that Wave 1's six leaves didn't cover all SKILL.md content (members table, heuristics, observability section, etc.), my correction was to add those concerns to the SKILL.md router — a 70-line "thin router" with tier-selection + members + heuristics + Phase 0 entry-check + trigger phrases + routing instructions. User pushback: that's the centralized-index anti-pattern the rules explicitly counsel against.

**Root cause.** I read "tree-shaped, stage-local routing" and applied it incompletely. I correctly understood that leaves should split by condition. I incorrectly retained the assumption that the SKILL is the place where every routing decision is made. The actual rule: each leaf at each stage is a router for its own scope. The SKILL routes only on its immediate decision (tier); tier leaves route on their next decision; mode leaves route on theirs.

**Course correction.** Tree-shaped routing means *recursive* routing, not "one big tree-shaped router at the top." Each child spec applies stage-local routing per the principle in the parent spec.

**Process improvement candidate.** The principle in `fbk-context-assets.md`'s "Routing is tree-shaped" subsection is correct but easily misread. Consider strengthening with an explicit anti-pattern callout: "A skill router that lists every condition the skill might encounter is a centralized index. The skill routes only on its immediate decision; downstream conditions live in downstream leaves' routers."

**Lesson.** Apply the rule recursively. Each layer makes its own routing decision; layers don't pre-fetch downstream decisions.
