# Remediation Flow — Project Overview

A new pipeline branch in Firebreak for remediating **AI-slop-contaminated codebases** — codebases where existing source has been AI-generated under weak processes, and where Firebreak's current spec-driven pipeline fails because every downstream agent pattern-matches on the contamination and replicates it.

This document is the **parent spec**. It defines the project's vision, system-level architecture, technology choices, feature decomposition, and cross-cutting concerns. Each feature listed in §4 will receive its own child spec in `ai-docs/remediation-flow/<feature-name>/<feature-name>-spec.md`. The project is **hypothesis-gated**: every feature past Feature 1 (the validation experiment) is conditional on the firebreak hypothesis surviving falsification.

Source material this consolidates:
- `~/llm-wiki/wiki/syntheses/firebreak-remediation-flow-architecture.md` — v0.2 architecture
- `~/llm-wiki/wiki/syntheses/firebreak-remediation-flow-plan.md` — phased delivery plan
- `~/llm-wiki/sources/firebreak-remediation-flow-brainstorm.md` — source brainstorm (four sessions)

---

## Vision

Firebreak's current spec-driven pipeline works for greenfield and reaches POC-level success on clean-brownfield. It fails on **AI-slop-contaminated codebases** because agents pattern-match on the codebase as their dominant grounding signal: prose context cannot override 500 files of contrary structural signal. Every downstream Firebreak agent reading a slop codebase becomes a slop-producer.

The remediation flow inserts a pre-amble of three new stages — pre-flight assessment, intent extraction, module rearchitecture — and then installs a **read-isolation firebreak** by materializing each rewrite inside a git worktree whose sparse-checkout reveals only the in-scope paths, so the slop codebase is physically absent from the working tree downstream agents see. Tool-dispatch denial backs this as a floor against absolute-path escapes. Under the firebreak, the existing per-module Firebreak pipeline runs unchanged on each new module — spec → spec-review → breakdown → implement → code-review — followed by a per-module caller-update step that reconfigures the sparse-checkout to include that module's callers at call-expression granularity. Each completed module (rewrite + callers) commits atomically to an operator-managed remediation branch before the loop advances to the next module in wave order.

The bet is structural: the firebreak produces a clean substrate per module; the existing Firebreak machinery — which already works on greenfield — handles each rewrite as greenfield-with-contract. The bet is also unvalidated. The first feature in this project is a one-weekend validation experiment that falsifies or confirms the load-bearing assumption that **isolation from the slop codebase produces structurally cleaner code than spec-driven-on-existing-code**. Nothing past that feature is committed.

Strategic context: this work targets a market hypothesis — that teams who shipped fast with AI in 2024–2026 will need AI-built codebase remediation in 2–3 years. The early signal is [[realmind]]; the operator has observed the same shape in professional production codebases. Firebreak is structurally positioned to serve that market if the remediation flow works in practice.

---

## Architecture

### Cycle and wave order

A **cycle** is one operator-chosen scope of remediation work that runs the full pipeline once: pre-flight → intent → rearchitecture → per-module pipeline × N (each iteration ending with that module's caller-update step and an atomic commit to the remediation branch) → cycle retrospective. The scope is variable. A cycle may target a single module (as in Feature 1), a merge pair (Feature 1.5), an operator-selected subsystem (Feature 8), or the whole codebase. Pre-flight, intent extraction, rearchitecture, and the cycle retrospective each run exactly once per cycle; the per-module loop runs N times within the cycle for the modules the rearchitecture's move-list produces.

Each cycle is identified by a `<cycle-id>` of the form `NNN-<slug>` — a zero-padded sequence prefix plus an operator-chosen kebab-case label, e.g., `042-realmind-persona-merge`. The sequence prefix gives stable sort order; the slug gives at-a-glance recognition without consulting a registry.

**Wave order** within the per-module loop is computed by rearchitecture as a topological sort of the module dependency graph: foundations — modules with no dependencies on other not-yet-rewritten modules in the cycle — run first. The operator reviews the generated `wave-order.yaml` at the move-list approval gate and may override by editing the file; an override requires a comment line stating the rationale. Default-then-override matches Firebreak's general "algorithmic default + operator authority" pattern and keeps wave-order approval inside the existing move-list gate rather than introducing a new one.

### Pipeline shape

```
(dirty codebase + operator-created remediation branch)
     │
     ▼
Pre-flight assessment        ◄── NEW. External evidence only. Assesses tier-fit; may refuse work.
     │
     ▼
Intent extraction            ◄── NEW. Operator-first. Architectural-intent +
     │                            external-boundary contract + decomposition-agnostic
     │                            behavior inventory (two-tier schema).
     ▼
Module rearchitecture        ◄── NEW. Designs per-module contracts. Outputs move-list +
     │                            module graph + prose + typed interface contracts.
     │                            Highest-stakes stage.
     ▼
┌── per module, in foundation-first wave order — loop body ────────────────┐
│                                                                          │
│   ═════ FIREBREAK ENGAGES (spec-authoring inclusion manifest) ═════      │
│        │   Worktree materialized off the remediation branch; sparse-     │
│        │   checkout reveals rearchitecture artifacts + the module-id     │
│        │   placeholder directory + per-cycle CLAUDE.md. Slop source      │
│        │   physically absent from this point onward in the loop body.    │
│        ▼                                                                  │
│   Per-module spec              ◄── REUSED /fbk-spec; authored INSIDE     │
│        │                          worktree against rearchitecture        │
│        │                          artifacts (typed contracts, dep map,   │
│        │                          behavior inventory agent-facing block).│
│        ▼                                                                  │
│   Per-module spec review       ◄── REUSED /fbk-spec-review; INSIDE       │
│        │                          worktree.                               │
│        │                                                                  │
│        ▼                                                                  │
│   ═════ FIREBREAK RECONFIGURES (scaffold inclusion manifest) ═════       │
│        ▼                                                                  │
│   Prep stage                   ◄── NEW. Generates stubs/mocks from typed │
│        │                          contracts; scaffolds module skeleton.  │
│        │                          Gate: scaffold compiles + typechecks    │
│        │                          → breakdown.                            │
│        ▼                                                                  │
│   Per-module breakdown         ◄── REUSED /fbk-breakdown; inside worktree.│
│        ▼                                                                  │
│   Per-module implement         ◄── REUSED /fbk-implement; /goal drives    │
│        │                          the per-wave loop autonomously.         │
│        ▼                                                                  │
│   Per-module code review       ◄── REUSED /fbk-code-review; inside        │
│        │                          worktree.                               │
│        │                                                                  │
│        ▼                                                                  │
│   ═════ FIREBREAK RECONFIGURES (caller-update inclusion manifest) ═════  │
│        │   Sparse-checkout reconfigured to include this module's callers │
│        │   at call-expression granularity; operator-gated batches inside.│
│        ▼                                                                  │
│   Per-module caller-update     ◄── REUSED + tighter scope. Updates this  │
│        │                          module's callers only. Diff-pattern    │
│        │                          check rejects scope widening.          │
│        ▼                                                                  │
│   Commit to remediation branch ◄── Module rewrite + its callers land     │
│        │                          atomically. Loop advances to next      │
│        │                          module, or exits when wave order is    │
│        │                          exhausted.                              │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
     │
     ▼
Cycle retrospective          ◄── REUSED, extended with architecture-decision fields.
     │
     ▼
(Operator squash-merges the remediation branch into their target — main, a version
 branch, or wherever their branching practice dictates — at operator discretion,
 outside the firebreak's scope.)
```

### Reuse-vs-new boundary

Most pipeline stages reuse existing Firebreak machinery. The new pieces are pre-flight, intent extraction, behavior inventory (two-tier schema), rearchitecture (now producing typed contracts), the prep stage, worktree-based isolation infrastructure, and `/goal` composition at implement; the move-list approval gate adapts the existing council pattern. Everything else is an existing skill running with adjusted scope or in a different working directory (the worktree).

| Stage | Status | Existing Firebreak module |
|---|---|---|
| Pre-flight assessment | NEW | — |
| Intent extraction | NEW | — |
| Behavior inventory (decomposition-agnostic, two-tier schema) | NEW | — |
| Rearchitecture (move-list + module graph + typed contracts) | NEW | — |
| Move-list approval gate | NEW (style on existing infra) | `/fbk-spec-review` council |
| Per-module spec / spec review | REUSED, scoped to rearchitecture artifacts | `/fbk-spec`, `/fbk-spec-review` |
| Worktree-based isolation (the firebreak) | NEW | `git sparse-checkout`; tool-dispatch denial as floor |
| Prep stage (worktree creation + stub generation + scaffold) | NEW | — |
| Per-module breakdown → code review | REUSED, run inside worktree | `/fbk-breakdown`, `/fbk-implement`, `/fbk-code-review` |
| Per-module caller-update step | REUSED + tighter scope | Interface-change-split + caller-migration in `task-compilation.md` |
| Cycle retrospective | REUSED + extended | `retrospective-guide.md` |
| `/goal` integration at implement | NEW composition | `/goal` (Claude Code) + `/fbk-implement` wave loop |

### Integration seams

Each seam below must hold consistent conventions across both sides. Validated at feature-level spec time.

- [ ] Intent extraction → Module rearchitecture: behavior-inventory ID format (stable `B-NNN` identifiers; decomposition-agnostic; two-tier schema with agent-facing/operator-facing separation; referenced by `rearchitecture/move-list.yaml`)
- [ ] Module rearchitecture → Per-module spec: move-list move record (fields per §2 schema; consumed as raw material for `/fbk-spec` Problem/Goals/Technical Approach/AC sections); typed interface contracts paired with prose contracts
- [ ] Per-module spec → Prep stage: spec carries full service contracts and dependency map needed to construct the worktree and generate stubs/mocks
- [ ] Prep stage → Worktree: inclusion manifest declared per module (sparse-checkout patterns + stub-target list + per-stage CLAUDE.md path); rearchitecture artifact directory always included
- [ ] Prep stage → Per-module breakdown: scaffold-green gate (compile + typecheck of generated stubs and module skeleton) must pass before breakdown starts
- [ ] Worktree → All downstream skills: filesystem absence is the primary firebreak; skills read whatever the sparse-checkout reveals; tool-dispatch denial provides the floor against absolute-path escapes
- [ ] Reused skills → Per-module artifact root: each reused skill (`/fbk-spec`, `/fbk-spec-review`, `/fbk-breakdown`, `/fbk-implement`, `/fbk-code-review`) resolves its `ai-docs/$FEATURE/` references under `.firebreak/remediation/<cycle-id>/modules/<module-id>/` when invoked within a remediation cycle context; the cycle-and-module context mechanism (env var, CLI args, or cycle context file) is Feature 3's skills inventory audit deliverable
- [ ] Worktree → Gate scripts: `$HOME/.claude/fbk-scripts/fbk.py` invocations from within the worktree are exempt from tool-dispatch denial — gate scripts read fixed paths under the user's Claude home, not the slop codebase
- [ ] Worktree → CLAUDE.md per-stage selection: which CLAUDE.md applies at which stage (above-firebreak stages — pre-flight, intent, rearchitecture — each have a named structural defense; in-worktree stages — per-module spec onward — reference rearchitecture artifacts and the new module only)
- [ ] /fbk-implement → /goal: /goal completion condition phrasing maps to existing per-wave + final-verification gate artifacts (`task.json status=complete`, per-wave verification exit 0, baseline regression exit 0, final verification exit 0, no parked tasks)
- [ ] Caller-update tasks → Worktree: at the per-module caller-update step the worktree's sparse-checkout reconfigures to include this module's caller files at call-expression granularity; diff-pattern check at verification gate rejects edits widening beyond signature mapping; reconfiguration happens once per module, not once per cycle
- [ ] Cycle retrospective → Next cycle: architecture-decision fields persist as input to next cycle's structural-analysis priors (firebreak-leak counts, move-list accuracy, caller-update bleed rate)

### Runtime value precision

The following conventions cross module boundaries and must be authored once and used consistently in child specs:

- Inclusion manifest file: `.firebreak/remediation/<cycle-id>/inclusion-manifests/<module-id>.yaml` (default per module; `<module-id>-caller-update.yaml` variant for the per-module caller-update step). Fields: `included-paths` (sparse-checkout patterns), `stub-targets` (modules to scaffold from typed contracts), `claude-md` (path to per-stage CLAUDE.md). The included paths always include `.firebreak/remediation/<cycle-id>/rearchitecture/**` implicitly. Per-task write-scope manifests remain unchanged from existing Firebreak.
- Worktree root: `.firebreak/remediation/<cycle-id>/worktree/` (a `git worktree add` checkout off the operator-created remediation branch; sparse-checkout configured per `inclusion-manifests/<module-id>.yaml`).
- Rearchitecture artifact root: `.firebreak/remediation/<cycle-id>/rearchitecture/`. Subpaths: `module-graph.yaml`, `move-list.yaml`, `interface-contracts/<module-id>.md` (prose), `interface-contracts/<module-id>.<lang-ext>` (typed; one per target language), `out-of-scope.md`, `wave-order.yaml`, `decomposition-rationale.md`.
- Intent artifact root: `.firebreak/remediation/<cycle-id>/intent/`. Subpaths: `architectural-intent.md`, `external-boundary-contract.md`, `behavior-inventory.yaml`.
- Per-module artifact root: `.firebreak/remediation/<cycle-id>/modules/<module-id>/`. Contains the per-module reused-skill artifacts: `<module-id>-spec.md` (from `/fbk-spec`), `<module-id>-review.md` (from `/fbk-spec-review`), `<module-id>-tasks/` (from `/fbk-breakdown`), `<module-id>-retrospective.md` (extended per-stage by `/fbk-spec`, `/fbk-spec-review`, `/fbk-breakdown`, `/fbk-implement`, `/fbk-code-review`). The reused skills are modified (Feature 3's skills inventory audit deliverable) to resolve their default `ai-docs/$FEATURE/` paths under this root when invoked within a cycle context.
- Cycle retrospective: `.firebreak/remediation/<cycle-id>/retrospective.md`. A cycle-level artifact distinct from per-module retrospectives, capturing the four cross-cutting fields (architectural-decision, firebreak-leak, move-list accuracy, caller-update bleed) and aggregating per-module retrospective signals.
- Behavior inventory schema: each entry has `id` (`B-NNN`), `type` (`external-interaction` | `system-invariant` | `scheduled-routine`), `short-handle` (audit-checked domain-language slug), an `agent-facing` block (`triggering-event`, `actor`, `observable-outcome`, `invariants`, `related-domain-concepts`), and an `operator-facing` block (`current-impl-trace`, `notes`). Downstream skills render the agent-facing block only.
- Cycle IDs: `NNN-<slug>` (zero-padded sequence + operator-chosen kebab-case label, e.g., `042-realmind-persona-merge`). The full ID is used wherever `<cycle-id>` appears in the path conventions above. Cycle IDs are not reused across cycles on the same codebase.
- Behavior IDs: `B-<NNN>` (stable within a single cycle, deliberately not stable across cycles — see Decisions resolved during scoping).
- Move IDs: `M-<NNN>` (stable within a move-list version).
- Move record fields: each entry in `move-list.yaml` carries `id` (`M-NNN`), `type` (from the move-types enum), `sources` (list of slop module IDs the move acts on; empty for `create-new`), `target` (new module ID the move produces; empty for `delete`), `stakes` (from the stakes enum), `behaviors-touched` (list of `B-NNN` IDs whose realization the move affects), `prerequisite-moves` (list of `M-NNN` IDs that must complete first; feeds wave-order computation), `rationale` (free-text). Feature 4's child spec extends this minimum with per-move-type semantic detail, decomposition-rationale linkage, approval-record fields, and the typed-contract interface-relationship field (deferred per Decisions resolved during scoping).
- Move-list ID: `ML-<cycle-id>` (e.g., `ML-042-realmind-persona-merge`).
- Module IDs: cycle-local; the `<cycle-id>` prefix in the artifact path supplies global uniqueness. The same module name (e.g., `unified-ingestion`) may appear in independent cycles without collision.
- Tier values: `0` | `1` | `2` | `3` (tier model defined in Feature 5 — Pre-flight Assessment).
- Move types: `merge` | `split` | `replace` | `delete` | `re-parent` | `promote` | `demote` | `extract-shared-core` | `re-shape-interface` | `create-new`.
- Stakes values (attach to move records; consumed by Feature 4's stakes-tiered operator recognition UX): `low` | `medium` | `high`.

---

## Technology decisions

### Build on Claude Code + Firebreak SDL (no new runtime)

The remediation flow operates entirely inside the existing Firebreak SDL surface — skills, agents, scripts, hooks. No new runtime, no external services. Rationale: every existing Firebreak quality mechanism (council deliberation, SHA-256 test locking, per-wave verification, Detector/Challenger code review) needs to apply to per-module rewrites; reusing the existing SDL gets all of it for free. Building outside Firebreak would require re-deriving these mechanisms.

### Worktree-based isolation via `git sparse-checkout`

The firebreak is implemented as a git worktree with sparse-checkout configured to reveal only the in-scope paths for the current module's stage. The slop codebase is not physically present in the worktree — it isn't denied, it isn't there. Skills reading "the codebase" find what's in the worktree, which is greenfield-flavored. Rationale: physical absence is structurally stronger than prompt-level discipline or runtime denial; uses git's actual primitives rather than inventing a parallel enforcement model; sparse-checkout is reconfigurable per stage so the worktree's contents grow across the cycle in foundation-first wave order; reads that fail return "file not found," which is more natural for agents to recover from than tool refusals.

### Filesystem absence is the firebreak; tool-dispatch denial is the floor

The primary enforcement is filesystem absence (sparse-checkout omits paths). Tool-dispatch denial is retained as a floor — it catches absolute-path escapes, remembered import paths, and any read attempt that bypasses the worktree's relative-path view. Rationale: prompt-based read-discipline is exactly the mechanism CLAUDE.md uses to lose against 500 files of contrary signal, so it cannot be the primary defense; physical absence removes the temptation entirely; tool-dispatch denial closes the residual gap. See "Firebreak coverage" below for the enumerated escape paths and tool-dispatch scope.

### Firebreak coverage: escape paths and tool-dispatch scope

"Filesystem absence" blocks slop reads via the worktree's relative paths, but several other access paths to slop content remain on the same machine and require explicit mitigation. The parent spec pins the enumeration and default mitigation per path; Feature 3's child spec refines the specific implementation mechanisms (hook implementation surface, exact denial patterns, validation rules).

**Escape paths and default mitigations:**

- **Symlinks pointing outside the worktree.** Inclusion-manifest validation rule rejects symlink entries in `included-paths`; sparse-checkout does not follow symlinks added to the working tree after checkout. Symlinks already present in committed files are flagged at scaffold-green gate.
- **Git history access** (`git show <sha>:slop-path`, `git log -p slop-path`, `git blame slop-path` on the remediation branch — the git object database still contains slop content even when sparse-checkout hides the working-tree copy). Bash denial blocks `git` commands that target slop paths or unbound SHAs; allowed `git` operations are limited to worktree-scoped commands (`git status`, `git diff` on worktree paths, `git commit` for per-module commits, `git log` on worktree paths only).
- **Bash path traversal** (`cat /home/user/realmind/slop.py`, `find / -name '*.py'`, `cat ../../slop.py`). Bash denial blocks absolute paths outside the worktree and `../` traversal patterns; permitted `Bash` commands operate within the worktree only.
- **Build configs with external absolute paths** (e.g., `pyproject.toml` `include = ["/path/to/slop"]`, `tsconfig.json` `paths` mappings to outside locations). Inclusion-manifest validation excludes build configs that reference external absolute paths; scaffold-green gate audits for any such references in included build configs.
- **Agent transcript memory** (slop content read in an earlier turn of the same session carries forward into later turns). In-worktree skill invocations start fresh Claude sessions; no transcript carryover from above-firebreak stages (intent extraction, rearchitecture). Session boundaries are enforced at skill-invocation level — when control crosses the firebreak boundary, a new session begins.
- **Sparse-checkout misconfigurations** (overly-broad patterns like `*` or `**` accidentally include everything). Inclusion-manifest validation rejects patterns that would defeat sparse-checkout: specific path patterns required, bare wildcards disallowed, validation runs before worktree creation and at every sparse-checkout reconfiguration.

**Tool-dispatch scope inside the firebreak:**

- **Allowlist by default for in-worktree stages.** Only the tools enumerated below may run inside the worktree; any other tool invocation is denied.
- **Read / Grep / Glob**: permitted within worktree only. Absolute paths outside worktree blocked; symlink resolution to outside paths blocked.
- **Edit / Write**: permitted per the per-task write-scope manifest (existing Firebreak convention; unchanged for in-worktree skills).
- **Bash**: permitted with the restrictions enumerated under "Bash path traversal" and "Git history access" above — no absolute paths outside worktree, no `../` traversal, no `git` commands targeting slop paths or unbound SHAs, no commands that read or list files outside the worktree.
- **Task** (subagent launches): subagents inherit the firebreak permissions of the parent context; cannot escalate.
- **Out of scope for this firebreak**: `WebFetch`, `WebSearch`. These address a different threat (external network exfiltration / external content injection) not within the slop-contamination model.

Feature 3's child spec refines: hook implementation surface (a permission hook over `Bash`, a path-validator hook over `Read`/`Grep`/`Glob`, or a combined hook), exact denial patterns per tool, inclusion-manifest validation rules, session-boundary enforcement mechanism, and any tools not covered above that surface as needing explicit decisions.

### /goal composes only downstream of the firebreak

`/goal` (Claude Code's session-loop primitive — see `~/llm-wiki/wiki/entities/goal-command.md`) drives the per-module implement stage's wave loop autonomously. The /goal evaluator only sees what the worker surfaced in conversation, so worker reads of slop pollute the transcript and the evaluator can confirm false positives. /goal is therefore restricted to under-the-firebreak stages (per-module spec, implement, code review, caller-update within batches). The composability map is load-bearing — child specs must enforce it.

### Structural analysis runs as meta-analysis, not semantic reading

The rearchitecture stage's structural-analysis tooling (function-signature similarity, control-flow shape, cohesion/coupling, parallel-hierarchy detection) operates *about* the codebase, not by reading its content semantically. Meta-analysis is not poisoned the way agentic reading is. Specific tool selection TBD per Open Questions §6; investigate Pocock's `improve-codebase-architecture` skill before building from scratch.

### Hypothesis-gating discipline

No tooling investment beyond Feature 1 (the validation experiment) until results land. The project commits to running the experiment cheaply and then deciding. Every child spec for Features 2–8 is conditional on Feature 1's outcome and may be redirected per the fallback paths declared in §4. Rationale: the architecture is unvalidated at its load-bearing assumption; committing to design ahead of evidence is exactly the failure mode the brainstorm's status banner warns against.

To prevent the hypothesis-gating discipline from being rhetorical — i.e., committing "no investment beyond Feature 1" while simultaneously pinning many design decisions — the parent spec includes a "Decisions revisitable after Feature 1" section that explicitly enumerates which resolved-during-scoping decisions are open to reconsideration based on Feature 1's outcome versus which are fixed regardless. See that section after "Decisions resolved during scoping."

### Terminology hygiene and project glossary

Every term used in remediation-flow artifacts shapes downstream agent behavior — a misleading or value-laden term steers the model in directions the operator did not intend. Terms must be intuitive to a context-empty agent reading them for the first time and value-neutral unless value-loading is itself part of the intended signal.

This project adopts a repo-wide `GLOSSARY.md` at the firebreak repo root as the canonical source of agreed terminology and definitions. The repo's `.claude/CLAUDE.md` references the glossary so every agent inherits the shared vocabulary. The glossary applies to all firebreak work, not only remediation flow — it is a first-class artifact across the project. Child specs that introduce a new term add the corresponding glossary entry, and spec-review gains a "new terms have glossary entries with hygiene rationale" check. Entries accrete at the point of use; pre-drafting risks defining terms before their use sharpens them.

---

## Feature map

Eight features, sized for operator + Firebreak SDL as the implementer. Each feature has an explicit **progress gate**: a prototype-validation condition that must be met before the next feature is approved to start. Features past Feature 1 are **hypothesis-gated** — conditional on Feature 1's outcome with named fallback paths.

### Feature 1 — Validation Experiment *(Phase 0 in the wiki plan)*

**Scope.** Run a single-module remediation manually, end-to-end, with operator-enforced read-isolation (no new tooling — the operator acts as the substitute for not-yet-designed mechanisms). Compare blinded `/fbk-code-review` outputs of original realmind module vs rewrite. Falsify or confirm the firebreak hypothesis. Methodology learnings from the operator's manual workflow feed the design of Features 2–7.

**Dependencies.** None.

**Gate framing.** The gate is **operator judgment informed by per-capita measurement**, not a mechanical metric. The pre-experiment commitment doc functions as a forcing function — articulate criteria *before* seeing data — not a binding contract. Two signal axes:
- **Volume:** sightings normalized per deterministic codebase characteristic (LOC, function count, or similar) — the "per-capita" comparison vs a best-guess fresh-module floor. Absolute sighting count alone is insufficient because a fresh module has its own sighting floor unrelated to slop.
- **Distribution:** category-density shift — fewer sightings in classifications specifically tied to agentic-code-failure modes, even if total volume is similar.

The rubric is **pinned for Feature 1's gate decision** in the pre-experiment commitment doc and does not change once data starts arriving. Iteration on the rubric happens between cycles (Features 1.5, 8) using Feature 1's learnings; mid-experiment tweaks are out of bounds.

**Required commitment doc fields.** The pre-experiment commitment doc must specify each of the following before intent extraction begins; missing fields fail the Feature 1 progress gate. The doc is committed to git before intent extraction begins; git history serves as the pre-registration record.

1. **Module selected** for the experiment (single realmind module identified by path).
2. **Per-capita denominator** = function count from a named tool. For Python: radon's function count (or equivalent named tool). For TypeScript: ts-morph's function count (or equivalent named tool). Fixed once and reused identically in Features 1.5 and 8 — cross-cycle comparison requires a consistent denominator. LOC and cyclomatic-weighted-LOC are not acceptable denominators (sensitive to formatting and tooling versions).
3. **Fresh-module floor methodology**: mean sightings/function across at least 3 fresh modules generated from realmind typed-contract stubs by `/fbk-implement`. The fresh-module fixture composition is recorded (which typed-contract stubs were used; operator-authored stubs from the rearchitecture artifacts are acceptable for Feature 1 since Feature 4's tooling does not yet exist). Model version and temperature are recorded. Floor is recomputed per major model upgrade and re-recorded; cross-cycle floor comparisons require the floor methodology be reproducible from the commitment doc alone.
4. **Meaningful-volume-drop threshold for different-bad-pathology**: an operator-pinned numeric value (e.g., "≥40% reduction in per-capita sighting count" or "operator-pinned absolute number with stated rationale"), with rationale tied to the measured fresh-module floor. The threshold is determined after the floor is measured but before the experiment's rewrite is reviewed — so the floor's actual values inform the threshold without the rewrite's outcome contaminating it.
5. **Signal-axis rubric pinned**: per-capita normalization defined per item 2; category-density shift methodology pinned (which finding categories count, how distribution-shift is measured).
6. **Bias controls documented**: blinding protocol for the `/fbk-code-review` comparison; classification decision-tree from measurement to outcome class (so post-experiment classification becomes mechanical given the measurements).
7. **Retrospective skeleton drafted**: the cycle retrospective fields (architectural-decision, firebreak-leak, move-list accuracy, caller-update bleed) and their measurement sources are pre-noted.
8. **Acknowledged limitations recorded**: operator mental-model contamination explicitly named; any other known threats to validity.

**Outcome class definitions.** The five outcome classes referenced in the progress gate below are distinguished by which signal-axis pattern they show:
- **rewrite-wins-structurally**: clear improvement on both volume and distribution axes — firebreak demonstrably produces cleaner code.
- **wins-but-misses-behavior**: structural improvement holds but the rewrite misses behaviors the slop covered. Proceeds with Feature 2 scope expanded.
- **similar-findings**: rewrite shows the same distribution and volume of findings as the slop. The firebreak didn't change anything. Stops the project.
- **different-bad-pathology**: rewrite has a different distribution of AI-failure-mode findings than the slop. Evaluated on the volume axis: a meaningful drop in quantity/severity of slop-sightings is a **positive signal** (firebreak demonstrably improves code quality even though it didn't eliminate the AI-failure-mode shape) and proceeds; the same distribution shift with no meaningful volume drop indicates the firebreak only shifted badness sideways, and stops the project. Elimination of AI-failure-mode findings is aspirational — even human-written code has findings; meaningful improvement is the operational success criterion.
- **can't-tell**: signals too noisy or inconsistent to classify. Iterate experiment design (sharper metrics, broader module sample) before drawing conclusions.

**Acknowledged limitation (recorded in commitment doc).** Operator mental-model contamination is an unmitigated threat to validity: the operator has been working in the slop codebase, and their mental model of "what this should do" may have internalized slop-shaped abstractions. The Feature 1 retrospective explicitly evaluates whether this threat played out. No structural protection is available at this stage; Feature 2's child spec considers whether intent extraction needs structural defenses against operator-articulated slop becoming ground truth.

**Read-isolation mechanism.** Once intent extraction and the manual rearchitecture artifacts are complete, the operator opens the rewrite session in a fresh working directory that contains only the rearchitecture artifacts, the typed-contract stubs, and the new module skeleton — the slop source is not present on the filesystem of the rewrite session. This is the manual analogue of the worktree firebreak Feature 3 will eventually automate; validating it at Feature 1 scale also produces evidence about whether the "physical absence beats discipline" principle holds in practice. The retrospective records "physical separation maintained" as a binary check, with any breach (slop module re-introduced into the rewrite directory) explicitly noted.

**Progress gate (prototype validation):**
- Pre-experiment commitment doc written and committed to git BEFORE intent extraction begins; all eight required fields populated per "Required commitment doc fields" above
- Blinded `/fbk-code-review` comparison run; finding-distribution analysis complete; volume and distribution signals evaluated against the pinned rubric and threshold
- Retrospective classifies outcome into one of the five success/failure modes (rewrite-wins-structurally / wins-but-misses-behavior / similar-findings / different-bad-pathology / can't-tell) using the classification decision-tree from the commitment doc applied to the measurements

**Approval to proceed:** Feature 2 starts only if outcome is **rewrite-wins-structurally**, **wins-but-misses-behavior** (requires Feature 2 scope expanded with stronger intent capture), or **different-bad-pathology with meaningful volume drop** (requires Feature 2 scope adjusted to address why the new pathology emerged). Any other outcome **stops the project** for investigation per the fallback paths.

**Fallback paths:**
- Outcome = similar-findings, OR different-bad-pathology with no meaningful volume drop: stop, investigate why Firebreak's pipeline itself produces slop-shaped output before scaling tooling. Possible pivots: deeper Firebreak per-stage quality work (orthogonal); or concede that AI-slop remediation at this automation level is currently intractable.
- Outcome = can't-tell: iterate experiment design (sharper metrics, broader module sample) before drawing conclusions.

### Feature 1.5 — Merge-Case Validation *(Phase 0.5 in the wiki plan)*

**Scope.** Same shape as Feature 1, applied to a merge candidate pair (persona/world from the brainstorm, or equivalent). Tests the architectural-decomposition hypothesis — that many-to-many module remapping (specifically the merge move) produces better code than preserving original boundaries.

**Dependencies.** Feature 1 complete and gate passed.

**Progress gate (prototype validation):**
- Pre-experiment commitment doc for merge case
- Blinded `/fbk-code-review` comparison; explicit analysis of whether the merge produced design improvements beyond what either source module alone would have

**Approval to proceed:** Feature 2 starts only if merge produces strictly better cohesion / less duplication than separate rewrites would.

**Fallback paths:**
- Merge produces no improvement: rearchitecture's architectural-move authority is unsupported. Reduce Feature 4 scope to within-module rewrites only. Significant design change to Feature 4's child spec.

### Feature 2 — Intent Extraction & Behavior Inventory Skill *(Phase 1)*

**Scope.** Build the operator-first intent extraction stage. New skill (working name `/fbk-remediation-intent`). Three artifacts: architectural-intent doc, external-boundary contract, decomposition-agnostic behavior inventory. Recognition-over-recall UX. Parallel wiki update to `[[rewrite-vs-refactor]]` adding the never-authored-design debt category.

**Behavior inventory schema (two-tier).** Each behavior is an `id` (`B-NNN`, mechanical, zero semantic weight), a `type` discriminator (`external-interaction` | `system-invariant` | `scheduled-routine`), a `short-handle` (audit-checked domain-language slug), an `agent-facing` block (`triggering-event`, `actor` from a controlled vocabulary, `observable-outcome` in domain terms, `invariants`, `related-domain-concepts`), and an `operator-facing` block (`current-impl-trace` with slop module names allowed, free-form `notes`). Downstream skills (move-list authoring, per-module spec, breakdown, implement) render *only* the agent-facing block — operator-facing fields are physically excluded from downstream agent contexts. This tier separation is the contamination firewall at the inventory layer; the audit gate operates on the agent-facing view.

**Intent extraction read-permission contract.** Intent extraction is the only above-firebreak stage where the agent may read slop directly. Feature 2's child spec must define an explicit read-permission contract: which slop artifacts the agent is permitted to read while the operator-first authoring is in progress (typical scope: module names, function signatures, top-level docstrings, public type definitions; not function bodies). The contract is enforced at the skill-prompt level with hook-level reinforcement where feasible. The two-tier behavior inventory schema above is the structural follow-on defense: even when the agent has read slop during hypothesis generation, only the agent-facing block survives into downstream stages.

**Progress gate (prototype validation):**
- Skill produces all three artifacts for a representative realmind subsystem in <4 hours operator time
- Behavior inventory audit on agent-facing fields: no current module names; `short-handle` matches a domain-language pattern (no CamelCase, no slop-style function names); `actor` uses controlled vocabulary; description slots populated
- Architectural-intent hypotheses are recognizable to operator (>80% confirm/correct rate; <20% wholesale rejection)

**Fallback paths:**
- Recognition rate too low: redesign with stronger evidence-richness scoring; agent's hypotheses are too uninformed by external evidence.
- Operator time exceeds budget: this codebase needed a higher tier than expected; revisit Feature 5 (pre-flight assessment).
- Agent-facing audit fails repeatedly: tighten the controlled vocabularies and audit heuristics; consider whether the operator needs adversarial-hypothesis prompts to surface slop-shaped articulations.

### Feature 3 — Worktree Firebreak Infrastructure + Prep Stage *(Phase 2)*

**Scope.** Worktree-based isolation as the primary firebreak mechanism. Specifically:
- **Worktree management:** `git worktree add` + `git sparse-checkout` primitives wired into a cycle-branch workflow. One worktree per cycle, sparse-checkout reconfigured per module as the foundation-first wave order advances.
- **Inclusion manifest format:** YAML schema for `inclusion-manifests/<module-id>.yaml` (sparse-checkout patterns, stub-target list, per-stage CLAUDE.md). Plus a `<module-id>-caller-update.yaml` variant for the per-module caller-update step.
- **Prep stage skill** (working name `/fbk-remediation-prep`): consumes the per-module spec + typed contracts + dep map; creates/reconfigures the worktree, runs deterministic stub-and-mock generation from typed contracts, scaffolds the new module skeleton, and verifies the scaffold compiles + typechecks. Verification gate: scaffold green → breakdown starts; scaffold red → breakdown blocked.
- **Skills inventory audit:** classify each existing Firebreak skill by partial-codebase tolerance (works as-is / needs minor adjustment / needs significant rework). Per-stage CLAUDE.md selection mechanism for the worktree.
- **Tool-dispatch denial as floor:** lightweight enforcement against absolute-path escapes and remembered-import patterns that bypass the sparse-checkout view. Not the primary mechanism; the residual gap closer.

**Dependencies.** Feature 2 complete and gate passed (intent extraction outputs feed rearchitecture which feeds prep). Feature 4 must produce typed contracts before Feature 3's prep stage can deterministically scaffold; the worktree-management portion of Feature 3 may parallelize with Feature 4, but the prep stage's end-to-end test fixture requires Feature 4's typed-contract output.

**Progress gate (prototype validation):**
- Worktree creation + sparse-checkout reconfiguration runs cleanly on a realmind cycle-branch; reads of out-of-scope paths fail with "file not found"
- Tool-dispatch scope enforced per the parent spec's "Firebreak coverage" subsection: `Read`/`Grep`/`Glob` blocked against paths outside the worktree, `Bash` blocked against absolute paths outside worktree and `../` traversal and `git` commands targeting slop paths/SHAs, inclusion-manifest validation rejects symlink entries and overly-broad sparse-checkout patterns, in-worktree skill invocations begin fresh Claude sessions — each tested in the harness
- Prep stage runs end-to-end on a sample per-module spec + typed contracts: generates stubs/mocks, scaffolds the module skeleton, scaffold compiles and typechecks, gate passes
- Skills inventory audit complete; any skill flagged as "needs significant rework" has a remediation path or is excluded from the in-worktree pipeline
- Inclusion-manifest format documented and exercised across at least two stages (prep, breakdown) and one caller-update variant

**Fallback paths:**
- `git sparse-checkout` proves too coarse or buggy for the realmind layout: fall back to a `worktree add` with manual file curation; accept higher setup cost per module.
- Deterministic stub generation from typed contracts is incomplete for the target language: prep stage emits partial stubs and surfaces gaps for operator review; scaffold-green gate temporarily downgraded to "compiles with stubbed bodies."
- Existing skill needs unscoped reads to function under the worktree: tighten the inclusion manifest to include the needed paths explicitly, or modify the skill once (not branching by mode) so it operates against the worktree's visible filesystem rather than reaching outside.

### Feature 4 — Rearchitecture Stage Skill + Structural Analysis *(Phase 3)*

**Scope.** New skill (working name `/fbk-rearchitect`). Structural-analysis tooling integration (function-signature similarity, data-shape, control-flow, cohesion/coupling, import graph, dead-code, parallel-hierarchy). Council-driven move-list authoring. Operator recognition UX by stakes tier (high one-by-one, medium batched, low bulk-confirm). Optional adversarial decomposition pass. Inversion test mechanic. Move-list schema implementation. Full `rearchitecture/` directory output, including **typed interface contracts paired with prose contracts** (one typed-contract file per module per target language; the typed form drives Feature 3's deterministic stub generation while the prose form carries the human-review semantics). Each typed contract declares the new module's relationship to the slop module's effective external interface (preservation vs deliberate change); the exact field name and value set are part of Feature 4's typed-contract authoring design, subject to `GLOSSARY.md` terminology-hygiene review before they enter circulation.

**Dependencies.** Feature 2 complete (provides inputs). Features 3 and 4 may partially parallelize, but Feature 3's prep stage end-to-end test depends on Feature 4 producing typed contracts.

**Progress gate (prototype validation):**
- Skill produces complete rearchitecture artifact for a realmind subsystem in <2 days operator time at Tier 1
- Council deliberation surfaces at least one move the operator did not propose
- Inversion test (if implemented) catches at least one contamination-preserving rearchitecture in test fixtures
- Operator recognition UX completes review within expected stakes-tier time budgets
- Typed interface contracts compile/typecheck in isolation against the target language's tooling (no runtime, just type-level validation); prep stage can deterministically transform them into scaffold stubs

**Fallback paths:**
- Structural-analysis tooling produces too much noise: scope to top-3-most-confident moves per category.
- Council deliberation produces lower-quality output than operator-driven authoring: simplify to operator-with-AI-proposals; preserve council for the move-list approval gate only.
- Inversion test cannot be made falsifiable: drop as a hard gate; use as informational signal in retrospectives.
- Typed-contract authoring UX is too costly for the operator/council: degrade to prose-contract-only and accept that prep stage emits skeletal stubs that the operator hand-edits before scaffold-green gate; documents a known scaling limitation.

### Feature 5 — Pre-flight Assessment + Tier Model *(Phase 4)*

**Scope.** New skill (working name `/fbk-remediation-preflight`). Evidence-richness scoring rubric. Tier decision rule (0/1/2/3). Tier-fit deliverable for operator. **Refusal protocol** — Firebreak declines to run remediation at a lower tier than the codebase warrants (the inverse of "just fix it" products).

**External evidence principle.** "External evidence" means anything *about* the slop code rather than the slop code itself — documentation, commit metadata, discussion artifacts, external interface specs. Pre-flight does not read slop source files as part of its assessment, because reading them contaminates the assessment exactly the way reading slop contaminates downstream stages. Feature 5's child spec enumerates which specific categories the evidence-richness rubric scores against, with weights calibrated from Intent Extraction's, Worktree Firebreak's, and Rearchitecture's experience.

**Dependencies.** Features 2–4 complete; their experience shapes the pre-flight heuristics.

**Progress gate (prototype validation):**
- Pre-flight produces a tier recommendation in <30 minutes operator time
- Tier recommendations match operator's post-hoc assessment on >75% of a fixture codebase set
- Refusal protocol is structurally enforced (operator cannot bypass without explicit override)

**Fallback paths:**
- Evidence-richness scoring proves unreliable: drop automated tier recommendation; require operator to state tier; pre-flight becomes documentation step rather than a gate.

### Feature 6 — /goal Integration at Implement Stage *(Phase 5)*

**Scope.** Compose `/goal` with existing per-wave + final-verification gates so per-module implementation runs autonomously under the firebreak. /goal condition phrasing keyed to existing structural artifacts. Optional belt-and-suspenders deterministic verification script. Retrospective fields for /goal evaluator turn count, false-positive rate, false-negative rate.

**Dependencies.** Feature 3 (firebreak MUST exist before /goal runs under it — upstream-of-firebreak /goal is unsafe per the composability map).

**Progress gate (prototype validation):**
- /goal-driven per-module implementation runs to completion without operator intervention in >75% of trial cases
- No /goal false positives (evaluator confirms completion when verification gates have not actually passed)
- Operator-facing turn count and token cost match expected /goal economics

**Fallback paths:**
- /goal evaluator unreliable on Firebreak's transcript shape: keep /goal off; use existing operator-driven per-wave checkpoints unchanged. **Acceptable — architecture works without /goal**; /goal is a composition gain, not a requirement.

### Feature 7 — Per-Module Caller-Update Tightening *(Phase 6)*

**Scope.** Extend the existing interface-change-split + caller-migration pattern (`task-compilation.md`) with remediation-specific tightening, applied per-module rather than as a cycle-wide wave: diff-pattern enforcement (only call-site changes accepted), worktree sparse-checkout reconfigured per-module to include this module's caller files at call-expression granularity (the caller-update inclusion-manifest variant), operator-gated batches inside the module's caller-update step, optional adversarial Challenger pass against the interface contract.

**Dependencies.** Feature 3 (inclusion-manifest format must support the caller-update variant and call-expression-granular path inclusion).

**Progress gate (prototype validation):**
- Caller-update tasks measurably tighter in scope (median diff size, files touched) than current `/fbk-implement` caller-migration tasks
- No caller-update task widens scope to caller logic
- firebreak-leak retrospective metric shows <5% out-of-scope-read attempts
- Per-module commit cleanly groups rewrite + its callers as an atomic unit on the remediation branch

**Fallback paths:**
- Diff-pattern enforcement too brittle: drop hard restriction; rely on per-task scope check + adversarial Challenger pass + retrospective audit. Increases contamination surface but does not compromise the firebreak structurally.

### Feature 8 — End-to-End Remediation Cycle on Realmind *(Phase 7)*

**Scope.** Run the full pipeline end-to-end on a realmind subsystem. Pre-flight → intent → rearchitecture → per-module pipeline × N modules (each iteration ending with that module's caller-update and atomic commit to the remediation branch) → cycle retrospective. Compare result quality against Feature 1 baseline.

**Dependencies.** Features 1–7 all complete and gates passed.

**Progress gate (prototype validation — these are the load-bearing criteria for whether the architecture works):**
- Rewrite findings distribution shows substantial improvement on structural / convention / pattern axes vs original
- Behavioral parity holds (no missed AC; no caller behavior regressions at integration)
- Pipeline executes within operator-time budget consistent with declared tier
- firebreak-leak rate <5%
- Move-list accuracy: <20% of behaviors discovered during implementation that the inventory missed
- Caller-update bleed: 0 tasks widened scope beyond signature-mapping

**Approval to proceed (out of this project):** Feature 8 completion gates any decision about external use. External use is a separate decision after Feature 8 retrospective.

**Fallback paths:**
- Pipeline runs but produces inferior code: identify which stage(s) introduced the regression; redirect to refining those stages rather than scaling.
- Operator-time budget exceeded: tier model is wrong, or codebase needed a higher tier than pre-flight recommended. Revisit Feature 5.
- Firebreak leaks: Feature 3 enforcement is incomplete; revisit.

### Dependency graph

```
Feature 1 (validation experiment)
    │
    ▼
Feature 1.5 (merge-case validation)
    │
    ▼
Feature 2 (intent extraction)
    │
    ├──────────────┐
    ▼              ▼
Feature 3      Feature 4
(firebreak)    (rearchitecture)
```

After Features 3 and 4 complete (with Feature 4's typed contracts available for Feature 3's prep-stage end-to-end test), three downstream features become eligible to start:

- **Feature 5 (Pre-flight Assessment)** depends on Features 2, 3, AND 4 — pre-flight's evidence-richness heuristics calibrate from intent-extraction's, firebreak's, and rearchitecture's actual experience.
- **Feature 6 (/goal integration)** depends on Feature 3 — /goal can only run safely under the firebreak.
- **Feature 7 (per-module caller-update tightening)** depends on Feature 3 — the caller-update inclusion-manifest variant must support call-expression-granular path inclusion.

All three converge into Feature 8:

```
Feature 5 (pre-flight) ──┐
Feature 6 (/goal) ───────┼──► Feature 8 (end-to-end realmind cycle)
Feature 7 (caller-update)┘
```

Features 3 and 4 may partially parallelize (with the constraint that Feature 3's prep-stage end-to-end test requires Feature 4's typed-contract output). Everything else is serial by hypothesis-gate dependency.

---

## Cross-cutting concerns

### The firebreak is itself a cross-cutting infrastructure

Read-isolation is not a per-feature concern. Once Feature 3 ships, every downstream feature operates inside the cycle's worktree by default. Each downstream child spec must include an Inclusion Manifest section enumerating which paths the feature's stage requires in the worktree.

### Inclusion manifest format

Single canonical format used across all downstream features. Defined in Feature 3 and referenced by every later child spec. Fields: `included-paths` (list of repo-relative globs as sparse-checkout patterns), `stub-targets` (modules to scaffold from typed contracts in the prep stage), `claude-md` (path to per-stage CLAUDE.md). The rearchitecture artifact directory is always implicitly included.

### Per-stage CLAUDE.md selection

The CLAUDE.md hierarchy that applies during a remediation cycle is stage-dependent:
- **Pre-flight / intent / rearchitecture stages** (above the firebreak): the three stages that operate before per-module work begins. Each has a structural defense against contamination — pre-flight reads "external evidence only" (the External Evidence Principle in Feature 5); rearchitecture runs "structural analysis as meta-analysis, not semantic reading" (Tech decisions); intent extraction is operator-first with the agent-facing/operator-facing tier separation (Feature 2's two-tier behavior inventory schema). Use a remediation-stage CLAUDE.md that includes guidance on slop-pattern recognition and reinforces each stage's read-permission contract. Intent extraction's specific agent read-permission contract (which slop artifacts the agent may read while the operator-first authoring is in progress) is owned by Feature 2's child spec.
- **In-worktree stages (per-module spec onward)**: see only the new architecture. Use a per-cycle CLAUDE.md present inside the worktree that references the rearchitecture artifacts and the new module's directory only. Per-module spec and spec review are inside the firebreak (firebreak engages at the start of the per-module loop body, before per-module spec) so they author against rearchitecture artifacts only — not against slop source.

Child specs must declare which CLAUDE.md applies to their tasks.

### Two-tier behavior inventory as cross-cutting

The behavior inventory's agent-facing / operator-facing tier separation (defined in Feature 2) governs every downstream skill that consumes behaviors. Move-list authoring, per-module spec generation, breakdown, implement, code review — all of these must render only the agent-facing block. Operator-facing fields exist for traceability during rearchitecture and Feature 1-style retrospective work, but never reach downstream agent contexts. Child specs that consume behaviors must declare they honor the tier separation.

### Typed interface contracts as cross-cutting

Typed contracts (defined in Feature 4) are used by the prep stage (Feature 3) for deterministic stub generation, by per-module spec for grounding the new module's surface, by `/fbk-code-review` for verifying the new module respects its boundary, and by the per-module caller-update step for signature mapping. Child specs that produce or consume contracts must use the paired prose-plus-typed form; prose-only contracts are insufficient because they cannot drive scaffold generation.

### Defenses against contamination, and supporting controls

The firebreak's primary threat is AI-slop contamination propagating from the existing codebase into the rewrite. Two structural defenses target this threat directly. Several other Firebreak mechanisms support cycle quality but do not by themselves defeat contamination — naming them as defenses would inflate the apparent depth of coverage and obscure where the real protection lives.

**Defenses against contamination:**
- **Physical**: worktree absence of slop source. Feature 3's worktree + sparse-checkout configuration; the slop codebase isn't denied, it isn't present in the working tree downstream agents see. Defeats contamination via codebase reads at every in-worktree stage.
- **Lexical/structural**: agent-facing-field audit gates — controlled vocabularies, no current module names, domain-language patterns. Defeats terminology-level contamination even when an above-the-firebreak agent has read slop, because operator-facing fields preserve traceability but are physically excluded from downstream agent contexts.

**Supporting controls (valuable for cycle quality; not contamination defenses by themselves):**
- **Tool-dispatch denial floor**: catches absolute-path escapes and remembered-import patterns that bypass the worktree's relative-path view. Not the primary defense; the slop is physically absent, not denied. Floor closes the residual gap when the physical layer's coverage has known escape paths (e.g., `Bash`, git history, symlinks — see Feature 3's enumeration).
- **Council deliberation** at intent, rearchitecture, and spec review: provides process quality, authority distribution, and operator-judgment scrutiny at high-stakes design moments. Not a contamination defense per se — council members above the firebreak have themselves read slop and carry the same priors. Useful for surfacing design issues, not for catching slop survival.
- **Correctness gates**: scaffold-green, per-wave verification, baseline regression, final verification. Defend behavioral regression and integration breakage, not contamination. A perfectly-typechecking, fully-test-passing module can still encode slop-shaped abstractions, control-flow shapes, and naming patterns — per the project's own premise, contamination is structural, not behavioral.
- **Retrospective fields** (firebreak-leak, move-list accuracy, caller-update bleed, architectural-decision retrospective): forensic detection of contamination that did pass through during the cycle; feedback signal for the next cycle's design, not per-cycle prevention.

Child specs identify which of the two real defenses apply to their stage and document the specific failure mode each catches. Supporting controls document their scope and limitations but no child spec needs to claim them as defense-in-depth coverage. The principle is structural: every transformation (intent → behavior inventory → move-list → spec → scaffold → code) has at least one of the two real defenses against slop passing through, and the supporting controls catch correctness/process failures alongside.

### Behavior inventory ID stability

Behavior IDs (`B-NNN`) are stable within a single remediation cycle and deliberately not stable across cycles. If cross-cycle behavior continuity becomes useful once the project has actually run more than one cycle on the same codebase, add an optional cross-cycle mapping artifact at the codebase level rather than baking continuity into the ID. See Decisions resolved during scoping.

### Retrospective field extensions

Remediation cycles produce a distinct **cycle retrospective** artifact at `.firebreak/remediation/<cycle-id>/retrospective.md`, separate from the per-module retrospectives that follow the existing `retrospective-guide.md` structure under `.firebreak/remediation/<cycle-id>/modules/<module-id>/<module-id>-retrospective.md`. The cycle retrospective captures four new fields specific to remediation cycles and aggregates signals from each per-module retrospective:
- **Architectural-decision retrospective**: per move, was the move the right call?
- **firebreak-leak retrospective**: how many out-of-scope reads were attempted? How many denied?
- **Move-list accuracy**: behaviors missed by inventory; behaviors discovered to be obsolete.
- **Caller-update slop signal**: caller-update tasks that widened scope.

### Hypothesis-gating discipline

Every child spec for Features 2–8 includes a "Conditional on Feature 1 outcome" clause and links to its fallback paths. No child spec graduates from review without explicit acknowledgment that its work is contingent. This is cultural infrastructure: the project's commitment is to run the experiment first and decide after, not to commit to the architecture ahead of evidence.

### Wiki cross-references

The wiki at `~/llm-wiki/` holds the architecture v0.2 document, the phased plan, and the source brainstorm. Each child spec references these in §1 Problem and §4 Technical Approach rather than duplicating content. The parent spec (this document) is the firebreak-repo entry point; the wiki is the deep reference.

### No new runtime; no new external dependencies

Every new piece extends existing Firebreak SDL surfaces (skills, agents, scripts, hooks) and uses existing Claude Code primitives (skills, slash commands, `/goal`). No new build tools, no new languages, no new external services. Maintains the "build on Claude Code + Firebreak SDL" technology decision from §3.

---

## Open questions

These must be resolved before the corresponding feature enters Stage 2 review.

### Feature 3 (worktree firebreak + prep stage)

- **Sparse-checkout reconfiguration trigger**: parent spec commits to one worktree per cycle with sparse-checkout reconfigured as the wave order advances; the open question is what triggers each reconfiguration — automatic on entry into a new module's prep stage, an explicit operator step, or some other mechanism? Affects whether reconfiguration is observable in the audit trail. **Resolve in Feature 3 child spec.**
- **Stub generation mechanics**: which language-specific transform implements typed-contract → stub? Existing AST tools per target (Python, TypeScript) — investigate per language. **Resolve in Feature 3 child spec.**
- **CLAUDE.md per-stage selection mechanism**: parent spec decides the rule (one CLAUDE.md for above-firebreak stages, a per-cycle CLAUDE.md at the worktree root for in-worktree stages); how is the stage-appropriate one actually loaded — hook on session start, skill instruction, manifest field consumed by an existing loader, or worktree-root placement that the harness picks up naturally? **Resolve in Feature 3 child spec.**
- **Skills inventory audit method**: by what test do we classify a skill as worktree-tolerant vs needing rework? Functional run against a partial codebase fixture? Static read of skill prompts for unscoped-grep instructions? **Resolve in Feature 3 child spec.**

### Feature 4 (rearchitecture)

- **Typed contract authoring UX**: how does the operator/council author typed contracts during rearchitecture? Inline with prose contract authoring? Generated draft then human-refined? Type-check feedback during authoring? **Resolve in Feature 4 child spec.**
- **Structural-analysis tooling selection**: which existing static-analysis tools integrate, in which languages? Investigate Pocock's `improve-codebase-architecture` skill first. **Resolve in Feature 4 child spec.**
- **Operator recognition UX shape**: CLI? web? batched markdown review files? **Resolve in Feature 4 child spec.**
- **Inversion test falsifiability bar**: what counts as "predicts old code too closely"? Quantitative threshold or qualitative review? **Resolve in Feature 4 child spec.**

### Feature 5 (pre-flight)

- **Evidence-richness scoring rubric**: which evidence categories count and at what weights? **Resolve in Feature 5 child spec.**
- **Tier decision rule**: external-evidence score + operator preference → recommendation. Specific decision function? **Resolve in Feature 5 child spec.**
- **Refusal protocol UX**: how does Firebreak communicate refusal? What override mechanism exists, if any? **Resolve in Feature 5 child spec.**

### Feature 6 (/goal)

- **/goal condition exact phrasing**: which transcript artifacts does the evaluator pattern-match against? The condition needs to reference existing per-wave and final-verification artifacts in a form Haiku can recognize. **Resolve in Feature 6 child spec.**
- **Belt-and-suspenders verification script**: required or optional? **Resolve in Feature 6 child spec.**

### Feature 7 (caller-update)

- **Diff-pattern enforcement mechanism**: how is "only call-site changes" structurally verified? AST-based check at verification gate? Regex on diff? **Resolve in Feature 7 child spec.**

### Deferred — explicitly out of project scope

- **Market launch / external customer use**: when does Firebreak offer remediation externally? Out of scope for this project; decided separately after Feature 8 retrospective lands.
- **AI-built codebase remediation as a product offering**: should this become a productized service? Strategic question deferred indefinitely; out of scope here.
- **Cross-language structural analysis**: which languages does Feature 4's structural-analysis tooling cover at v1? Scoped to a single language family (Python and TypeScript, matching realmind and Firebreak's current operating range); multi-language is a follow-on project, deferred from this overview.

---

## Decisions resolved during scoping

These were originally open at parent-spec drafting and have since been closed. Rationale is preserved here so child specs inherit the decision without re-litigating it.

- **Firebreak shape (was: tool-dispatch denial mechanism).** **Resolved:** worktree-based isolation via `git sparse-checkout` is the primary mechanism; tool-dispatch denial is demoted to a floor against absolute-path escapes. Rationale: physical absence is structurally stronger than prompt-level discipline; uses git's native primitives; reads-as-file-not-found are more natural for agents to recover from than tool refusals; sparse-checkout reconfiguration supports foundation-first wave order naturally.
- **Per-module compile/test feedback (was: how do new modules typecheck against absent slop dependencies).** **Resolved:** rearchitecture produces typed interface contracts paired with prose contracts; the prep stage deterministically transforms typed contracts into stubs/mocks inside the worktree. Rationale: keeps "greenfield-with-contract" claim honest by giving the new module a real compile/typecheck feedback loop; leverages the target codebase's existing language ecosystem rather than inventing a custom schema.
- **Prep stage as a pipeline stage.** **Resolved:** added between per-module spec review and per-module breakdown. Inputs: spec + typed contracts + dep map. Output: worktree-with-scaffold ready for breakdown. Verification gate: scaffold compiles + typechecks. Rationale: separates deterministic transform (contract → scaffold) from creative work (rewrite); the firebreak is physically engaged by prep, not declared by prose.
- **Behavior inventory schema (was: how do you describe behaviors without referencing current module names).** **Resolved:** two-tier schema with mechanical IDs (`B-NNN`), audit-checked `short-handle`, agent-facing block (rendered to downstream skills) and operator-facing block (traceability, never rendered). Audit gates on agent-facing fields enforce no module names, controlled vocabularies, domain-language patterns. Rationale: structural contamination firewall at the inventory layer; preserves operator's ability to cross-reference back to slop during authoring.
- **Feature 1 gate framing (was: operational definition of the five outcomes).** **Resolved:** gate is operator judgment informed by per-capita measurement, not a mechanical metric. Pre-experiment commitment doc pins the rubric (per-capita normalization, signal axes, fresh-module floor) before data lands; iteration happens between cycles. Mental-model contamination acknowledged as unmitigated limitation. Rationale: single-dev project cannot sustain a fully mechanical rubric; the discipline that matters is articulating criteria before seeing data and not tweaking mid-experiment.
- **Cycle ID format.** **Resolved:** `NNN-<slug>` — zero-padded sequence prefix + operator-chosen kebab-case label (e.g., `042-realmind-persona-merge`). Rationale: sequence preserves machine sort order; slug gives at-a-glance recognition without consulting a registry; matches Firebreak's existing pattern of pairing a mechanical ID with a domain label.
- **Behavior ID cross-cycle stability.** **Resolved:** behavior IDs are cycle-local only; no per-codebase registry, no cross-cycle binding at the ID layer. If cross-cycle continuity becomes useful later, add an optional separate mapping artifact rather than baking it into the ID. Rationale: rebuilding the inventory per cycle from intent keeps the contamination firewall simple; cross-cycle ID stability is exactly the speculative infrastructure the hypothesis-gating discipline warns against committing ahead of evidence.
- **Module ID namespacing.** **Resolved:** module IDs are cycle-local; the `<cycle-id>` prefix in the artifact path supplies global uniqueness. Rationale: consistent with the cycle-local behavior ID decision — one architectural philosophy applied at both the inventory and rearchitecture layers; module IDs stay short and domain-meaningful.
- **Cycle scope.** **Resolved:** a cycle is one operator-chosen scope of remediation work, variable from a single module to a whole codebase. Pre-flight, intent, rearchitecture, and the cycle retrospective run once per cycle; the per-module loop runs N times within the cycle. Rationale: matches what Features 1, 1.5, and 8 already imply at different scopes; keeps operator authority over scope-shaping rather than pre-judging cycle size before evidence.
- **Wave order determination and authority.** **Resolved:** rearchitecture computes `wave-order.yaml` as a topological sort of the module dependency graph (foundations first); the operator reviews and may override at the move-list approval gate, with override requiring a comment line stating rationale. Rationale: algorithmic default minimizes operator labor on the common case; explicit override preserves operator authority on irregular cases; ties wave-order approval to the existing move-list gate rather than introducing a new gate.
- **Feature 1 read-isolation enforcement mechanism.** **Resolved:** physical separation — the rewrite session runs in a fresh working directory containing only the rearchitecture artifacts, typed-contract stubs, and new module skeleton, with no slop source present on the filesystem. The retrospective records "physical separation maintained" as a binary check. Rationale: this is the manual analogue of the worktree firebreak Feature 3 will automate; validating it at Feature 1 scale is itself evidence for whether Feature 3 is worth building, and the manual mechanism matches the parent spec's "physical absence beats discipline" principle.
- **Caller-update timing.** **Resolved:** per-module incremental — each module's caller-update runs as the final step of that module's loop body, before advancing to the next module in wave order. The pipeline runs (per-module-loop including caller-update) × N rather than (per-module-loop × N) → single caller-update wave. Rationale: keeps the codebase out of long-lived "many modules in flight" states; each module's rewrite + its callers forms an atomic unit of complete work; matches the operator-managed remediation branch model where each completed module commits cleanly.
- **Remediation branch model.** **Resolved:** the operator creates a remediation branch before the cycle begins; the firebreak's worktree is added off that branch. Each completed module (rewrite + its callers) commits to the remediation branch as a self-contained unit. The operator squash-merges the remediation branch into their target (main, a version branch, or wherever their branching practice dictates) at their discretion after the cycle retrospective lands — merge-back is *outside* the firebreak's responsibility. Rationale: matches realistic team branching practice (no one runs remediation directly against main); cleanly decouples Firebreak's per-module commit cadence from the operator's release/merge cadence; the retrospective informs but does not gate merge-back.
- **Interface stance dropped from parent runtime-precision.** **Resolved:** the `faithful | corrected` value pair was removed from the runtime-precision block. The underlying concept (the new module's declared relationship to the slop module's effective external interface) remains real but is now scoped to Feature 4's typed-contract authoring design, where it can be named with terminology-hygiene review against `GLOSSARY.md` before entering circulation. Rationale: the original terms carried unintended LLM priors ("faithful" loads virtue/loyalty; "corrected" implies the original was wrong) that could steer downstream agents; better to defer naming until the concept's use sharpens and the glossary review can apply.
- **Project glossary as repo-wide infrastructure.** **Resolved:** `GLOSSARY.md` lives at the firebreak repo root as a first-class artifact covering all firebreak terminology, not only remediation flow. `.claude/CLAUDE.md` references it as the canonical source. Entries accrete at the point of use — each spec or context asset that introduces a new term adds an entry, with hygiene review applied at spec-review or asset-authoring time. Rationale: terms shape LLM behavior; misleading terminology causes unintended results; a single canonical source prevents the same concept from being named differently across artifacts, which is itself a contamination vector for agents reading across the repo.
- **Move-record minimum schema in parent.** **Resolved:** parent runtime-precision block carries an eight-field minimum move-record schema (`id`, `type`, `sources`, `target`, `stakes`, `behaviors-touched`, `prerequisite-moves`, `rationale`). Feature 4's child spec extends this minimum with per-move-type semantic detail, decomposition-rationale linkage, approval-record fields, and the typed-contract interface-relationship field. Rationale: all eight fields are inferable from terms the parent already commits to (move types, behavior IDs, stakes, wave-order computation), so pinning them costs nothing the parent doesn't already imply; the integration seam reference becomes valid; Feature 4 inherits a foundation rather than navigating a blank slate.
- **External evidence principle for pre-flight.** **Resolved:** pre-flight reads anything *about* the slop code (documentation, commit metadata, discussion artifacts, external interface specs) but does not read slop source files. Feature 5's child spec enumerates the specific evidence categories the rubric scores against, with weights calibrated from prior features' experience. Rationale: the principle is the firebreak-discipline analogue at the assessment layer — reading slop contaminates the assessment exactly the way reading slop contaminates downstream stages; category enumeration is calibration work that Feature 5 should own with concrete experience from Features 2–4.
- **Different-bad-pathology outcome interpretation.** **Resolved:** the five Feature 1 outcome classes are evaluated against both signal axes (volume, distribution). A different-bad-pathology outcome — rewrite shows different AI-failure-mode finding distribution than the slop — is a **positive signal** when accompanied by a meaningful drop in quantity/severity of slop-sightings (firebreak demonstrably improves code quality even though it didn't eliminate the AI-failure-mode shape). Different-bad-pathology with no meaningful volume drop stops the project. Rationale: elimination of AI-failure-mode findings is aspirational — even human-written code has findings; meaningful quantity/severity improvement is the operational success criterion for whether the firebreak is worth building.
- **Pre-flight feature dependency set.** **Resolved:** Feature 5 (Pre-flight Assessment) depends on Features 2 (Intent Extraction), 3 (Worktree Firebreak Infrastructure), AND 4 (Rearchitecture). The dependency graph is updated to reflect this; the prose dependency claim was correct and the prior diagram was incomplete. Rationale: pre-flight's evidence-richness heuristics calibrate from intent-extraction's experience (what kinds of evidence richer codebases have), firebreak's experience (which skills survive partial-codebase reads, itself a tier-fit input), and rearchitecture's experience (which structural patterns rearchitecture can handle).
- **Wave terminology — generic concept, no rename.** **Resolved:** "wave" is a generic term defined in `GLOSSARY.md` as "a unit of parallel tasks within a structured workflow." Both `/fbk-implement`'s per-wave verification and the remediation flow's foundation-first wave order are valid instances of the same underlying concept; surrounding text disambiguates which wave instance is being discussed. No rename. Rationale: the apparent collision dissolves once the term is defined as generic; renaming would force one of the two existing uses to take a less natural name without corresponding clarity gain.
- **Per-module artifact paths under a remediation cycle.** **Resolved:** all per-module reused-skill artifacts live under `.firebreak/remediation/<cycle-id>/modules/<module-id>/` (paths: `<module-id>-spec.md`, `<module-id>-review.md`, `<module-id>-tasks/`, `<module-id>-retrospective.md`). The cycle-level retrospective is a separate artifact at `.firebreak/remediation/<cycle-id>/retrospective.md`. Reused skills are modified (Feature 3 skills inventory audit deliverable) to resolve their default `ai-docs/$FEATURE/` paths under this root when invoked within a cycle context. Gate-script invocations (`$HOME/.claude/fbk-scripts/fbk.py`) are exempt from tool-dispatch denial. Rationale: co-locates all cycle artifacts (machine-state + operator-facing) under a single root, simplifying worktree inclusion-manifest scope, audit-trail reasoning, and cleanup; keeps `ai-docs/` reserved for non-remediation feature work (including this parent overview and the eight features that build the remediation flow itself).
- **Defense-in-depth taxonomy collapsed to real defenses + supporting controls.** **Resolved:** the prior six-layer claim (Lexical/structural, Physical, Boundary, Semantic, Functional, Post-hoc) restructured into two real contamination defenses (Physical worktree absence, Lexical/structural audit gates on agent-facing fields) plus a Supporting Controls list (tool-dispatch denial floor, council deliberation as process quality, correctness gates against behavioral regression, retrospective fields as forensic detection). Rationale: three of the original six layers did not actually defend against contamination — Semantic (council deliberation above the firebreak is itself contaminated and has no articulated defeat mechanism), Functional (correctness gates defend behavioral regression, not contamination — contamination is structural per the project's own premise), Post-hoc (retrospective fields are forensics, not prevention — they record leaks that already occurred). Honest taxonomy clarifies where real protection lives, removes a cross-cutting child-spec obligation ("identify which of six layers apply" becomes "identify which of two real defenses apply"), and matches convergent reviewer findings across Builder and Security perspectives.
- **Feature 1 commitment-doc structure pinned in the parent.** **Resolved:** the parent spec specifies eight required commitment-doc fields, with methodology choices fixed at the parent level for fields whose consistency propagates across cycles (denominator = function count from a named tool; floor methodology = mean sightings/function across ≥3 fresh modules with recorded model version + temperature; reproducible across Features 1.5 and 8). Per-cycle operator judgment is preserved for the meaningful-volume-drop threshold (set after the floor is measured but before the rewrite is reviewed) and for the classification decision-tree. Commitment doc committed to git before intent extraction; git history is the pre-registration record. Rationale: methodology consistency across cycles enables iteration on the rubric to be operationalized (Features 1.5 and 8 reuse Feature 1's denominator and floor methodology, making cross-cycle comparison meaningful); per-cycle threshold flexibility lets operator judgment incorporate fixture-floor evidence without contaminating it with rewrite-outcome evidence; pre-registration via git history is structural counter-pressure against motivated reasoning at classification time.
- **Firebreak coverage pinned: escape paths enumerated + tool-dispatch scope specified.** **Resolved:** parent spec adds a "Firebreak coverage: escape paths and tool-dispatch scope" subsection in Technology decisions, enumerating six escape paths (symlinks, git history access, Bash path traversal, build configs with external absolute paths, agent transcript memory, sparse-checkout misconfigurations) with default mitigation per path, plus an allowlist-by-default tool-dispatch scope for in-worktree stages (Read/Grep/Glob within worktree, Edit/Write per write-scope, Bash with restrictions, Task inheriting parent firebreak; WebFetch/WebSearch out of scope as different-threat). Feature 3's child spec refines hook implementation surface, exact denial patterns, validation rules, and session-boundary enforcement. Rationale: pins what "filesystem absence" actually covers vs what needs additional mitigation; gives Feature 3 child spec a foundation rather than asking it to invent the threat model; makes Feature 3's progress gate measurable against an enumerated coverage spec rather than vague "tool-dispatch denial floor."
- **Above-firebreak set shrunk; per-module spec and spec-review moved inside the firebreak.** **Resolved:** the firebreak engages at the start of the per-module loop body (with a spec-authoring inclusion manifest revealing rearchitecture artifacts + module-id placeholder + per-cycle CLAUDE.md), then reconfigures after spec review (with a scaffold inclusion manifest that adds the prep stage's generated stubs). Above-firebreak stages reduce to three: pre-flight (structurally defended by the External Evidence Principle), intent extraction (operator-first + two-tier inventory tier separation; agent read-permission contract owned by Feature 2 child spec), rearchitecture (structural-analysis-as-meta-analysis). Per-module spec and spec-review now author against rearchitecture artifacts only — true to the spec's claim that the new module rewrite is "greenfield-flavored Firebreak with an interface contract." Rationale: the prior "with care" phrasing for above-firebreak stages was the same prompt-level discipline the spec elsewhere argues cannot be the primary defense; shrinking the surface to the three stages where structural defenses genuinely exist is internally consistent. Pipeline diagram, cross-cutting per-stage CLAUDE.md selection, and integration seams updated; new "spec-authoring inclusion manifest" variant joins the existing "scaffold" and "caller-update" variants.

---

## Decisions revisitable after Feature 1

The hypothesis-gating discipline (see Technology decisions) commits the project to "no tooling investment beyond Feature 1 until results land." This section makes explicit which of the resolved-during-scoping decisions are open to reconsideration based on Feature 1's outcome and operator experience, versus which are fixed regardless. The categorization splits along whether Feature 1 can produce evidence about the decision: schema/ceremony decisions get tested by the operator's one-weekend manual experiment; naming conventions, cross-cycle decisions, and the hypothesis itself cannot.

### Status after Feature 1 (2026-05-21)

Feature 1 completed with outcome `rewrite-wins-structurally`. The retrospective (`ai-docs/remediation-flow/validation-experiment/retrospective.md`) records evidence on each revisitable decision and new findings the parent spec did not account for. The decisions below are updated to reflect post-experiment status. The original framings are preserved with status annotations.

**Revisitable based on Feature 1 evidence:**

- Two-tier behavior inventory schema — **Validated, refined.** Field set worked. Audit rules need strengthening: capability-not-shape needs front-loading (not just an audit step); descriptions over identifiers in human-facing communication.
- Typed-contract requirement — **Validated as viable.** Hand-authoring tractable when designed from intent (inside firebreak). Driver of architecturally-rooted categorical eliminations.
- Move-record minimum schema 8 fields — **Not exercised at scale.** Defer to Feature 1.5.
- Per-module incremental caller-update timing — **Not exercised** (single-module experiment). Defer.
- Triple-council deliberation count — **Council not used; experiment succeeded without it.** Operator review + agent dialogue (architectural review meeting pattern) was sufficient at this scope. Council should be opt-in at high-stakes design moments, not default ceremony per stage.
- Stakes-tier UX commitment — **Not exercised.** Defer.
- Defense-in-depth Path A restructure — **Validated.** Two real defenses + supporting controls held up. Categorization clean.
- Above-firebreak set composition — **Revised during experiment.** Rearchitecture moved *inside* the firebreak (was above). Intent stays above. Pre-flight stays above. Above-firebreak set shrank further than parent expected. Parent-spec change: update §Cross-cutting / Per-stage CLAUDE.md selection and §Pipeline shape to reflect rearchitecture-inside.
- Firebreak coverage enumeration — **Held up.** Sandbox isolation worked; no escape paths surfaced.
- Feature 1 commitment-doc structure — **Not formally followed.** Operator chose prototype mode; classification was driven by qualitative pattern-class analysis rather than pre-pinned numerical thresholds. Qualitative result was decisive without thresholds, but Feature 1.5 should run with formal commitment-doc to validate quantitative-qualitative correlation.

### New findings from Feature 1 not yet in this parent spec

Feature 1's retrospective surfaced parent-spec additions that should land before Feature 2 begins:

1. **Wave order as contamination control (not just engineering convenience).** Elevate from §Tech decisions to load-bearing architectural commitment. The lowest-layer slop sets the upper bound on cleanliness for everything above it; violating wave order contaminates via interface shape.

2. **Interface-shape contamination as a separate vector** from body-pattern contamination. The firebreak isolates against bodies; interfaces imported from unrewritten slop neighbors carry slop shape inward. Mitigation: design dep stubs from intent (capability-driven) rather than transcribing from slop (shape-driven) when the codebase is past the remediation-feasibility threshold. Add to §Firebreak coverage.

3. **Curse-of-knowledge gaps as a named failure mode at intent extraction.** Mitigation pattern: grill-me framing (front-end) + intent-alignment review by context-clear subagent (back-end). Feature 2 codification.

4. **Intent-alignment-review pattern** (sibling to spec-review). Feature 2 codification target as `/fbk-intent-review`.

5. **Architectural review meeting pattern** as real-time co-author-and-defend mode for design phases. Feature 4 codification target.

6. **Spec-redundancy finding.** Intent + rearchitecture artifacts cover ~80–90% of `/fbk-spec`'s output. `/fbk-spec` becomes redundant synthesis in the remediation pipeline. Possible restructure: intent + rearchitecture outputs become spec-format directly. Feature 2/4/parent codification.

7. **Fix-pass regression (FPR) as a measurable failure mode.** 40% rate in Feature 1's iteration. Feature 7 (caller-update tightening) should design to drive this rate down.

8. **Mock permissiveness (MPM) as a measurable failure mode** in scopes that include test-infrastructure. Add to cycle retrospective fields.

9. **Pattern-class breadth as a measurable instrument.** Categorical-elimination rate is a sharper signal than density alone. Feature 8's progress gate should include this alongside per-capita density.

10. **Detection-source mix as a spec-quality indicator.** High `spec-ac` percentage signals sound spec; high `intent`/`checklist` percentage signals under-specified spec.

These additions are commitments for the parent spec rev that precedes Feature 2's child spec, not for Feature 1's retrospective alone.

**Fixed regardless of Feature 1 outcome** — either Feature 1 cannot produce evidence about these, or they are load-bearing for Feature 1's interpretability:

- Cycle ID format `NNN-<slug>` (pure naming convention; no Feature-1 evidence relevant)
- Behavior ID cross-cycle stability cycle-local (Feature 1 is a single cycle; cannot inform cross-cycle decisions)
- Module ID namespacing cycle-local (same: Feature 1 is single-cycle)
- Cycle scope = operator-chosen (Feature 1 confirms this with its single-module scope; no contrary evidence possible)
- Wave order ownership = algorithmic default + operator override (Feature 1 has one module; wave-order doesn't apply at scale)
- Feature 1 read-isolation = physical separation (this IS the hypothesis under test; if it fails, the project stops per the fallback paths, not revisits)
- Remediation branch model = operator-managed with per-module commits (pure workflow convention)
- Project glossary as repo-wide infrastructure (meta-level commitment, not a Feature-1 learning)
- Per-module artifact paths under `.firebreak/remediation/<cycle-id>/modules/<module-id>/` (pure naming convention)
- Pre-flight feature dependency set on Features 2, 3, AND 4 (depends on Features 2–4 having actually run; not informed by Feature 1)
- Wave terminology — generic concept, no rename (validated by operator framing during spec review; orthogonal to Feature 1)

If Feature 1's retrospective surfaces a need to revisit any of the Revisitable decisions, the parent spec is updated before the affected child spec(s) begin. If Feature 1 surfaces a need to revisit a Fixed decision, that is itself a signal that something has gone unexpectedly wrong with the experiment design and warrants stopping for investigation per the hypothesis-gating discipline's fallback paths — the fallback is "stop and investigate," not "edit the parent and continue."
