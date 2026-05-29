# Refactored SDL — Specification

> **Scope note.** This is one consolidated feature spec covering the full refactoring, by operator choice. It is large because it touches roughly two dozen assets. It does **not** restate the upstream planning package — it maps the "how" onto it. Read these first; this spec links to them rather than repeating them:
> - `ai-docs/refactored-sdl/prd.md` — the "what" and "why"
> - `ai-docs/refactored-sdl/behavior-inventory.yaml` — the 24 behaviors (B-001…B-024)
> - `ai-docs/refactored-sdl/adr-spine.md` — the 15 decisions and their rationale
> - `ai-docs/refactored-sdl/design/` — the per-capability design pages
> - `ai-docs/refactored-sdl/design-manifest.md` — index of the design pages
>
> **Dogfooding.** This project designs a new SDL and is itself built through the *current* shipped SDL. The document keeps the current `feature-spec-guide.md` 9-section structure (so the current `spec-gate` passes), **and additionally dogfoods the new slice-declaration format**: §Slices populates the `## Slices` block this project designs, carving the work into twelve vertical slices with declared `test-discipline` modes and dependency edges. The current `spec-gate` ignores that extra section; the current breakdown reads it as decomposition guidance, so the breakdown is decomposed and parallel rather than re-derived off a flat AC list. See the resolved decision at the end.
>
> **Revision note (post spec-review).** This revision addresses the Stage 2 review's 13 blocking findings. Acceptance criteria were renumbered and split for measurability, so AC numbers here do not match the prior review document (a point-in-time snapshot). The substantive changes: gate "extend" claims that were really rewrites are reclassified; the breakdown/test-hash/code-review gate plans are now shape-aware and backward-compatible; the `review-gate` caller list is complete; the phantom "installer manifest registration" is removed; injection-detection parity is added for the new gates; and the durable-doc path class is defined.

## Problem

The shipped Firebreak SDL starts at the spec, which forces one document to answer "what," "why," and "how" at once; it carves work in a single breakdown step that degrades as work grows; and it leaves the always-on authoring disciplines that produced clean remediation code uncodified. The refactoring adds a front-of-pipeline intent phase and a separate design phase, narrows the spec to "how," reshapes breakdown into vertical slices with per-slice test discipline, extends code-review with a quality scan and a final test-review, extracts four reusable technique skills, codifies the always-on disciplines, and establishes a lightweight durable-artifact discipline so intent and decisions survive past a feature. The `prd.md` Problem statement carries the full motivation; this spec defines how to build it against the existing asset base.

## Goals / Non-goals

### Goals

- Build two new phase skills (`fbk-intent`, `fbk-design`) with their gates, agents, and durable-doc integration.
- Extract four technique skills (`fbk-grilling`, `fbk-fresh-eyes`, `fbk-quality-scan`, `fbk-test-review`) that phase skills compose and operators invoke directly.
- Narrow `fbk-spec` to "how," teach it to declare per-slice test discipline, and re-point its grilling at a composed technique skill.
- Reshape `fbk-breakdown` into slice-identification then per-slice work-unit authoring, with four slice shapes loaded by progressive disclosure and a bounce-back-to-spec mechanism.
- Extend `fbk-code-review` with a top-five quality scan and a final test-review pass, both additive to the preserved bug-finding loop.
- Implement the new and changed gates as `fbk.py` subcommands following one hybrid pattern (mechanical anchor + semantic anchor on a technique-skill artifact), with new mechanical checks gated behind slice metadata so in-flight specs are unaffected.
- Codify the always-on disciplines in CLAUDE.md and the asset-authoring rules, and establish the durable-artifact discipline (glossary already exists; add a decisions log and an architecture/intent overview, plus the governing conventions).
- Write the concept/pattern docs the skills route to at runtime. (New assets install automatically — the installer auto-discovers files under `assets/`; the only registration is `COMMAND_MAP` for new gate subcommands.)

### Non-goals

Carried from `prd.md` "Non-goals" — not restated in full. The load-bearing ones for build scope: **no** complexity-classification eval or tier tag; **no** hooks, state-machine, config, or audit-log changes (the orchestration project owns those — known downstream dependency: the two new phases will need state-machine entries later); **no** AST schema-extraction tooling; **no** project-memory system beyond plain markdown; **no** council-agent migration; **no** mutation sampling. Additionally for this spec: **no** rewrite of the current spec/breakdown/code-review gate *behavior* for work that carries no slice metadata, and **no** retroactive application of the new format to specs already in flight. The full four-way slice-shape-to-work-unit match is **not** gate-enforced this cycle (it is breakdown-leaf authoring guidance — see the resolved decision).

## User-facing behavior

The operator is a technical lead who makes product and architecture calls and relies on the agents to translate to implementation. After this ships, the operator sees:

- **A new entry point.** `/fbk-intent <name> <terse description>` opens an interview, draws out what the work is and why, and writes a PRD + behavior inventory in plain language. For an established project it reads the architecture/intent overview first and asks only about the delta.
- **A new design step.** `/fbk-design <name>` proposes a module shape, contracts, and a decomposition rationale, surfacing each real choice one at a time with a recommendation and tradeoff. It writes design pages + a manifest into the feature directory and appends enduring decisions to the durable decisions log.
- **A narrower spec.** `/fbk-spec <name>` now consumes intent + design and records only "how" — tech choices, file organization, integration, testing strategy, module-touch policy, slice declarations. It grills only on "how," and bounces back to design if the design under-specifies.
- **Slice-shaped breakdown.** Breakdown carves the spec into vertical slices and, per each slice's declared test discipline, produces the matching work-unit shape. If it can't write a work unit a less-familiar agent could execute, it names the gap and bounces back to spec instead of pushing forward.
- **A heavier code review.** After the existing bug-finding pass, code review surfaces a ranked top-five quality list (surface-only, the operator decides what to do) and a final test-review that flags any test that drifted out of relevance.
- **Capability-entry.** Nothing forces the full chain. A bugfix can start at spec or stay conversational. Invoking a phase whose inputs are missing produces "here's what's missing, want me to run the upstream phase?" — never a hard block.
- **Four standalone tools.** `/fbk-grilling`, `/fbk-fresh-eyes`, `/fbk-quality-scan`, `/fbk-test-review` are invocable outside any ceremony on an arbitrary topic, document, diff, or test set.
- **Consistent plain-language register.** Every artifact and every question reads as if written for a smart non-engineer; conversation refers to items by description, not identifier.

Error and edge behavior the operator encounters is enumerated in `prd.md` "Edge cases and failure modes" (non-convergent interview surfaces rev count; design-can't-honor-intent surfaces the tension; spec-finds-design-thin offers to re-run design; missing-prerequisite reports specifically and offers the upstream phase; breakdown-can't-write-units names the gap; hash drift fails the code-review gate; a drifted locked test surfaces as a finding; a stale overview shows up in the PR diff). Those are the acceptance targets for the failure-mode ACs below.

## Technical approach

The system is Claude Code context assets (skills, agents, referenced docs) plus Python gate scripts. Source lives under `assets/` and installs to `~/.claude/` via `installer/install.sh`, which **auto-discovers** every file under the source tree — there is no per-asset manifest to register into; new files install automatically once they exist under `assets/`.

**Three path classes** (a finding from review — the installed-path constraint applies to only the first):
1. **Installed firebreak assets** — skills, agents, docs, gate scripts. Any path *referenced inside one of these* must use the installed form (`~/.claude/fbk-scripts/...`, `.claude/fbk-docs/...`), never the source `assets/...` form.
2. **Feature artifacts** — everything under `ai-docs/<feature>/`. Project-relative; referenced as-is.
3. **Operator-project durable docs** — `docs/decisions-log.md`, `docs/architecture-overview.md`. These live in whatever repo the operator runs the SDL in, never install to `~/.claude/`, and are referenced by the intent/design skills as project-relative paths. They are *not* firebreak-shipped assets, so the installed-path constraint does not apply to them.

This spec uses source `assets/...` paths to say what to build; the assets themselves must use installed paths per class 1.

Established patterns this work must follow (from the asset-authoring rules and existing assets):
- **Asset-type split** (`fbk-context-assets.md`): skills are triggers + routing; agents own persona; referenced docs (leaves) own instructions; technique skills are the capability layer. Progressive disclosure and the necessity test apply to every asset — a referenced doc earns its place only if a skill routes to it at runtime.
- **Skill shape** (existing `fbk-*/SKILL.md`): frontmatter `description` + `argument-hint`, a thin body that routes to `.claude/fbk-docs/...` leaves and runs the gate via `python3 "$HOME"/.claude/fbk-scripts/fbk.py <gate>`.
- **Gate shape** (existing `fbk/gates/*.py`): a module with `main()` and an argparse front, pure check functions returning failure lists, JSON to stdout, exit 0/2, registered in `fbk/__init__.py` `COMMAND_MAP`, unit-tested in `assets/fbk-scripts/tests/test_gates_*.py` (pytest, `testpaths = ["tests"]`). Each gate validates its path args with `is_file()`/`is_dir()` + `sys.exit(2)` before opening, and reads with `errors="replace"` (the pattern in `breakdown.py`, `spec.py`, `test_hash.py`).
- **Stage transition** (`fbk-sdl-workflow.md`): write artifacts → append retrospective → summarize → compact → invoke next; mid-pipeline entry validates the prior gate before proceeding.

### New vs. modified — the full asset surface

**New skills** (`assets/skills/<name>/SKILL.md`):
- `fbk-intent` — intent phase. Routes to a new `fbk-sdl-workflow/intent-guide.md`. Composes `fbk-grilling` and `fbk-fresh-eyes`. Delegates PRD drafting to the new product-author agent. Reads/updates the architecture/intent overview (project-relative path). Runs `fbk.py intent-gate`.
- `fbk-design` — design phase. Routes to a new `fbk-sdl-workflow/design-guide.md`. Composes `fbk-grilling` and `fbk-fresh-eyes`. Delegates to the new architect agent. Writes design pages + manifest; appends to the decisions log (project-relative). Runs `fbk.py design-gate`.
- `fbk-grilling` — grilling technique. Body encodes the one-question-at-a-time + recommendation + reflect-back-to-confirm loop; soft cap ~10 questions; writes a decision log to `ai-docs/<feature>/grilling-log-<phase>.md` when invoked in-ceremony. The log records, per decision, the question, the recommendation, the operator's answer, **and a reflect-back confirmation line** — so "reflected back before recording" is an observable property of the log, not an unverifiable behavior. (See resolved decision on why this is a new firebreak asset rather than a change to the external `/grill-me`.) **Its frontmatter must credit Matt Pocock with the source link** (`https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md`), matching the `Source: adapted from [link]` line the external grill-me carries.
- `fbk-fresh-eyes` — cold-comprehension technique. Spawns an isolated cold-reviewer agent; returns a severity-categorized observation report; no-fix. Writes `ai-docs/<feature>/fresh-eyes-<artifact>.md`.
- `fbk-quality-scan` — top-five quality scan. Spawns the adapted detector; returns ≤5 ranked severity-tagged findings; scan-only. Writes `ai-docs/<feature>/quality-scan.md`.
- `fbk-test-review` — formalizes the existing test-reviewer agent as a callable technique with a widened invocation contract (pre-lock and final-pass modes; reviews the full set of tests covering the changed module, including the pre-existing tests a contract-preserving slice locks). Writes `ai-docs/<feature>/test-review-<checkpoint>.md` with a verdict line.

**New agents** (`assets/agents/<name>.md`):
- `fbk-product-author` — requirements/product author persona: plain-language, capability-framed, interview-grounded. Tools: Read, Grep, Glob (no Write — the skill owns artifact writes, matching `fbk-spec-author`). Model: sonnet.
- `fbk-architect` — senior architect persona for `fbk-design` authoring mode. Scope this cycle: author designs in isolation. Tools: Read, Grep, Glob. Model: sonnet. (The future council-architect collapse is recorded in the decisions log, not built here — see resolved decision.)
- `fbk-fresh-eyes-reviewer` — thin cold reviewer; no specialist lens; its value is being uncontaminated. Tools: Read, Grep, Glob. Model: sonnet.

All three new agents and the reused test/quality reviewers carry **no Write or Edit tool** — they observe/scan only and cannot auto-fix (AC-15).

**Modified agents:**
- `fbk-test-reviewer.md` — **refactor-then-extend** (not a description tweak): the agent is built around a fixed CP1/CP2/CP3 checkpoint model; this rewires its criteria-to-checkpoint mapping to pre-lock and final-pass modes, widens its review scope to all tests covering the changed module(s) (including pre-existing tests being locked), and adds contract-evolving retirement-list awareness. Persona and the four core checks preserved; current tools (Read, Grep, Glob, Bash — no Write/Edit) preserved through the rewire (AC-15).
- `fbk-code-review-detector.md` — refactor-then-extend: gains a mode-neutral persona framing so the quality-scan technique can reuse it in a quality-opportunity mode via the spawn prompt (not a sibling note). Bug-detection behavior unchanged; current tools (Read, Grep, Glob — no Write/Edit) preserved, and `test-code-review-structural.sh` (which asserts this) must stay green.

**Modified skills:**
- `fbk-spec/SKILL.md` — refactor-then-extend: inputs become PRD + behavior inventory + design pages + manifest; body re-points "Closing ambiguity" to compose `fbk-grilling` narrowed to "how" questions; adds slice-declaration authoring. Routes to the (modified) `feature-spec-guide.md`.
- `fbk-breakdown/SKILL.md` — refactor-then-extend: split into slice-identification then per-slice work-unit authoring; route to four new shape leaves under `fbk-sdl-workflow/slice-shapes/` (progressive disclosure); invoke `fbk-test-review` pre-lock with verdict gating lock application; implement bounce-back-to-spec. Routes to the (modified) `task-compilation.md`. Note it invokes `review-gate` today as its prior-stage check — that call is preserved.
- `fbk-code-review/SKILL.md` — extend: after the existing bug-finding pass, invoke `fbk-quality-scan` then `fbk-test-review` (final), then run the new `code-review-gate`. Bug-finding loop untouched.
- `fbk-spec-review/SKILL.md` — leave alone behaviorally; doc-only reframing as the spec gate's semantic-anchor producer.
- `fbk-implement/SKILL.md` — leave alone behaviorally; reframed as phase five in docs only.

**New/modified gate scripts** (`assets/fbk-scripts/fbk/gates/` + `COMMAND_MAP` in `fbk/__init__.py`):
- `fbk/injection.py` (**new shared module**) — `detect_injections()` is promoted out of `spec.py` into this module so the spec, intent, and design gates import one copy and the pattern list can't drift across three gates. `spec.py` imports it (refactor-then-extend of `spec.py`). Its only current consumers are `spec.py` internals and `test_gates_spec.py`, so the move has no hidden caller.
- `intent.py` (new, `intent-gate`) — mechanical: PRD present with the required sections (Vision, Problem statement, Goals and non-goals, Use cases, Functional requirements, Non-functional requirements, Edge cases and failure modes, Dependencies, Success metrics, Open questions); behavior-inventory present with consistent IDs and bidirectional PRD↔inventory reference consistency; grilling log present. Runs the shared injection scan on its inputs (PRD, inventory, grilling log), emitting an `injection_warnings` count. Semantic anchor: a fresh-eyes report file present with no open critical observations after dedup.
- `design.py` (new, `design-gate`) — mechanical: design manifest present; bidirectional check (every manifest page entry resolves to a file under `ai-docs/<feature>/design/`, every such file appears in the manifest); decomposition rationale present; the manifest's "Decisions recorded" count line present and non-zero. Runs the shared injection scan on the design pages + manifest. Semantic anchor: a fresh-eyes report file present with no open critical observations.
- `spec.py` (refactor-then-extend, `spec-gate`) — add, **activated only when the spec declares a `## Slices` block** (backward-compatible): each slice carries a `test-discipline` from the four-shape taxonomy; every behavior in the linked inventory is covered by ≥1 slice; design pages referenced by the spec exist. The existing `_check_testing_strategy_traceability` (testing-strategy section must reference ≥1 `AC-NN`) is **kept unchanged for both legacy and slices-bearing specs** — slice declarations supplement AC traceability, they do not replace it. The slices-block detector must not fire on a legacy spec that merely contains the token `test-discipline` in prose or a code fence. Also promote `detect_injections` to the shared module.
- `breakdown.py` (refactor-then-extend, `breakdown-gate`) — the new checks fire **only when tasks carry slice metadata** (the same backward-compat hinge the spec gate uses; legacy breakdowns are unaffected). The existing per-AC test+impl coverage check becomes **slice-shape-aware**: a `cross-cutting` slice's AC may be covered by a test-only task (no impl), and a `contract-preserving` slice's AC may be covered by an impl task over locked existing tests (no new test task) — so the current checks #1 and #8 are *modified*, not merely extended. Gate-enforced shape rules this cycle are the two cheap, high-value invariants only: **cross-cutting ⇒ no impl task**, and **contract-evolving ⇒ a retired-tests list with rationale is present**. The full four-way shape-to-work-unit match is breakdown-leaf authoring guidance, not gate-enforced (resolved decision). Also: no unresolved bounce-back markers; pre-lock test-review verdict was `accepted` (verified by manifest presence). Existing DAG/wave checks preserved.
- `test_hash.py` (**refactor-then-extend**, `test-hash-gate`) — the shipped manifest is a flat auto-discovered `{"files": {path: hash}}` map; this restructures the per-file value to an object `{sha256, slice, test-discipline}` (a schema change that rewrites the `verify_manifest` comparison loop and updates every `test_gates_test_hash.py` assertion). Adds a **list-driven lock mode** so contract-preserving slices can lock *named pre-existing* project test files (not only feature-dir rglob discovery). The runtime file stays `test-hashes.json` (preserving the path and any hook wiring); "test-lock manifest" is its conceptual name. `verify_manifest`'s existing UNEXPECTED-file detection becomes the **shadow-test** mechanism: a test file present in a locked slice's scope but absent from the manifest is a shadow test. In list-driven mode "scope" is the locked set's directories, not a repo-wide scan, so unrelated project tests are never flagged. `verify_manifest` is given a **structured return** (a list of typed discrepancies — `modified` vs `unexpected` — not a `pass`-or-blob string) so `code_review.py` branches on the discrepancy kind rather than parsing a substring.
- `code_review.py` (**new module**, `code-review-gate`) — resolved: the code-review close-out checks land in a *new* module, not in `review.py` (which gates the spec-review council artifact, a different phase). Checks: a quality-scan artifact present with the severity field populated; a final test-review verdict artifact present; the hash + shadow-test check performed by **calling `test_hash.verify_manifest`** (not a second hash-comparison path) and branching on its structured discrepancy kinds. Severity does not block — even critical findings surface for operator triage; only a hash mismatch (`modified`) or a shadow test (`unexpected`) fails the gate.

**New referenced docs** (leaves the skills route to at runtime, under `assets/fbk-docs/`):
- `fbk-sdl-workflow/intent-guide.md`, `fbk-sdl-workflow/design-guide.md` — phase guides (routed by the two new skills) mirroring the existing `feature-spec-guide.md` shape.
- `fbk-sdl-workflow/slice-shapes.md` (index, routed by breakdown) + `fbk-sdl-workflow/slice-shapes/{new-contract,contract-preserving,contract-evolving,cross-cutting}.md` (four leaves, loaded one at a time).
- `fbk-sdl-workflow/capability-entry.md` — routed by the phase skills' mid-pipeline-entry step.
- Concept docs with **no runtime skill route** (hybrid-gate-pattern, technique-skills, design-manifest, durable-artifact-discipline) are **folded into the architecture/intent overview** rather than shipped as standalone leaves nothing loads (necessity test). The richer rationale already lives in the design pages and the decision spine.

**Modified docs:**
- `fbk-sdl-workflow.md` (index) — add the two new phases to the pipeline description and route to the new leaves.
- `fbk-sdl-workflow/feature-spec-guide.md` — add the `## Slices` declaration format and narrow the grilling guidance to "how." (Prose-anchored; see existing-tests-impacted.)
- `fbk-sdl-workflow/task-compilation.md` — replace single-pass breakdown guidance with slice-identification-then-pairing and the four shapes (routing to the leaves).
- `fbk-sdl-workflow/code-review-guide.md` — add the quality-scan and final test-review passes after the bug-finding pass.
- `fbk-sdl-workflow/retrospective-guide.md` — add stage sections for intent and design.
- `fbk-context-assets.md` and/or a new routed `fbk-context-assets/always-on-disciplines.md` — absorb the five always-on disciplines.
- `.claude/CLAUDE.md` (project) — surface the five always-on disciplines at session start (one-liners + route to the rule).
- `GLOSSARY.md` — add: capability-entry, durable-artifact discipline, architecture/intent overview, decisions log, slice shape (+ the four), technique skill (confirm present), fresh-eyes, quality scan; remove cut terms if present: project-memory, capture gate, mutation sampling.
- `CHANGELOG.md` / `README.md` — see Documentation impact.

**New durable docs** (path class 3 — project-relative, never installed):
- A **decisions log** at `docs/decisions-log.md` — append-only, chronological, status-bearing entries.
- An **architecture/intent overview** at `docs/architecture-overview.md` — living, onboarding-length. For *this* repo, seed it from the current SDL's shape (and fold in the unrouted concept material above) so future intent phases have something to inherit.

### Slice declaration format (the spec→breakdown handoff)

Resolved (was an open question): the handoff is a `## Slices` block in the spec, one entry per slice, per the `slice-shapes` design page:

```yaml
slices:
  - name: <slice-name>
    description: <one-line>
    test-discipline: new-contract | contract-preserving | contract-evolving | cross-cutting
    contract: <pointer to the spec/design section defining the contract>
    retired-tests: []   # contract-evolving only; each with a one-line rationale
```

Each parallel breakdown sub-step receives one slice entry plus the spec/design sections it points to. Finer details of the per-step payload are pinned in `task-compilation.md` during implementation, but the entry shape above is fixed now because both the spec gate and breakdown gate validate against it. **This spec's own slices are declared in §Slices below** (dogfooding the format).

### Integration seam declaration

Each entry: two components, the shared state/interface, the convention both sides must honor.

- [ ] `fbk-intent` skill → `fbk-product-author` agent: spawn-prompt contract — the skill passes interview notes + the architecture/intent overview path; the agent returns PRD prose; the skill owns the file write.
- [ ] `fbk-intent` / `fbk-design` skills → `fbk-grilling` skill: invocation contract — caller passes topic + context + open-questions; grilling writes `ai-docs/<feature>/grilling-log-<phase>.md` in decision-log shape, **with a reflect-back confirmation line per decision**, which the caller later reads for dedup.
- [ ] `fbk-intent` / `fbk-design` / `fbk-spec` gates → `fbk/injection.py`: shared-scan contract — all three gates import `detect_injections` from the one module and run it on their text inputs; the pattern list lives in exactly one place.
- [ ] `fbk-intent` / `fbk-design` gates → `fbk-fresh-eyes` skill: artifact contract — fresh-eyes writes `ai-docs/<feature>/fresh-eyes-<artifact>.md` with `## Critical/## Substantive/## Minor` sections; the gate reads it and the phase skill's dedup step reduces it before the gate's "no open critical" check.
- [ ] `fbk-design` skill → decisions log: append contract — the design skill appends status-bearing entries to `docs/decisions-log.md`; the manifest's "Decisions recorded" line carries a count the design gate checks is non-zero, and points to the durable log (never duplicates it).
- [ ] `fbk-design` → `design-gate`: manifest contract — manifest lists `design/<slug>.md` entries; gate runs the bidirectional check against `ai-docs/<feature>/design/`.
- [ ] `fbk-spec` → `spec-gate`: slices contract — the `## Slices` block uses `test-discipline:` values from `{new-contract, contract-preserving, contract-evolving, cross-cutting}`; the gate enforces presence, taxonomy membership, and inventory coverage; the slices-block detector ignores the bare token in prose/code fences.
- [ ] `fbk-spec` → `fbk-breakdown`: slice handoff — breakdown reads each `## Slices` entry + its contract pointer (format fixed above).
- [ ] `fbk-breakdown` → `fbk-test-review` (pre-lock) → `test-hash-gate`: lock-application contract — breakdown invokes test-review pre-lock over the full set of tests covering the changed module (incl. pre-existing tests being locked); only an `accepted` verdict triggers `test-hash-gate` manifest population; manifest entries carry `sha256` + `slice` + `test-discipline`.
- [ ] `fbk-breakdown` shape leaves → breakdown agent: progressive-disclosure contract — once a slice's `test-discipline` is read, the agent loads only that one shape leaf.
- [ ] `fbk-code-review` → `fbk-quality-scan` + `fbk-test-review` (final) → `code-review-gate`: artifact contract — both write their feature-directory artifacts; the gate checks presence + structure and calls `test_hash.verify_manifest` for the hash + shadow-test check; the existing bug-finding loop runs ahead of both, unchanged.
- [ ] all new/reshaped phase skills → `retrospective-guide.md`: append contract — each appends its stage section, reading before writing so prior stages survive.
- [ ] all phase skills → `capability-entry.md` / mid-pipeline-entry: prerequisite contract — a directly-invoked phase checks the prior gate is satisfiable; if not, it names the specific missing artifact and the upstream phase to run, and offers it rather than blocking.

### Module-touch policy

- [ ] `fbk-spec/SKILL.md`: refactor-then-extend (re-point grilling to composed technique; add slice authoring; change inputs).
- [ ] `fbk-breakdown/SKILL.md`: refactor-then-extend (split into two steps; four-shape routing + bounce-back + pre-lock test-review).
- [ ] `fbk-code-review/SKILL.md`: extend (append two technique invocations + the new gate call).
- [ ] `fbk-spec-review/SKILL.md`: leave alone (doc-only reframe).
- [ ] `fbk-implement/SKILL.md`: leave alone (doc-only reframe).
- [ ] `fbk-test-reviewer.md`: **refactor-then-extend** (checkpoint-model rewire, widened scope, retirement awareness).
- [ ] `fbk-code-review-detector.md`: refactor-then-extend (mode-neutral persona framing).
- [ ] `fbk/gates/spec.py`: refactor-then-extend (slice/coverage checks behind the slices-block hinge; import shared injection module).
- [ ] `fbk/gates/breakdown.py`: refactor-then-extend (modify checks #1/#8 to be slice-shape-aware behind the slice-metadata hinge; add the two cheap shape invariants + bounce-back-marker check; preserve DAG/wave checks).
- [ ] `fbk/gates/test_hash.py`: refactor-then-extend (per-entry manifest schema; list-driven lock mode; shadow-test detection).
- [ ] `fbk/gates/code_review.py`: create (new module; reuses `test_hash.verify_manifest`).
- [ ] `fbk/injection.py`: create (shared `detect_injections`).
- [ ] `fbk/__init__.py`: extend (`COMMAND_MAP` += `intent-gate`, `design-gate`, `code-review-gate`).
- [ ] `fbk-sdl-workflow.md`, `feature-spec-guide.md`, `task-compilation.md`, `code-review-guide.md`, `retrospective-guide.md`: refactor-then-extend.
- [ ] `fbk-context-assets.md`: extend (route to always-on-disciplines leaf).
- [ ] `.claude/CLAUDE.md`: extend (five always-on one-liners + route).
- [ ] `GLOSSARY.md`: extend (add terms; remove cut terms).
- [ ] `CHANGELOG.md`, `README.md`: extend.
- [ ] `installer/install.sh`, the installer manifest, the state machine, config layer, audit log, hooks: leave alone (the installer auto-discovers new assets; the rest are standing non-goals).

### Runtime values that must be exact

- Gate subcommand names: `intent-gate`, `design-gate`, `code-review-gate` (new); existing `spec-gate`, `breakdown-gate`, `review-gate`, `test-hash-gate`, `task-reviewer-gate`.
- Slice `test-discipline` values: `new-contract`, `contract-preserving`, `contract-evolving`, `cross-cutting` — defined once as a shared constant the spec, breakdown, and test-hash gates import, so adding a shape later is a one-file change, not three.
- Fresh-eyes / quality-scan severities: `critical`, `substantive`, `minor`.
- Test-review verdict line: `accepted` | `needs-revision`.
- Test-lock manifest file: `test-hashes.json`; per-file value object: `{sha256, slice, test-discipline}`.
- Shared injection module: `fbk/injection.py`, function `detect_injections`.
- Gate exit codes: `0` pass, `2` fail; JSON result to stdout with `{"gate": <name>, "result": "pass"|"fail", ...}`.
- Gate invocation form inside skills: `python3 "$HOME"/.claude/fbk-scripts/fbk.py <gate-name> <args>`.

### Interface contracts (pinned so parallel slices don't diverge)

These are the cross-slice code interfaces. They are fixed here so independent implementation agents code against them rather than each deciding — the precondition that lets the slices run in parallel. Names of skills, agents, gate commands, artifact files, and artifact section structures are already pinned above; this section pins the remaining six.

1. **`COMMAND_MAP` entries** (`fbk/__init__.py`), exact: `"intent-gate": "fbk.gates.intent"`, `"design-gate": "fbk.gates.design"`, `"code-review-gate": "fbk.gates.code_review"`. Note the hyphenated command maps to an underscore module path.
2. **Shared slice-discipline constant** — module `fbk/slices.py`, constant `TEST_DISCIPLINES = ("new-contract", "contract-preserving", "contract-evolving", "cross-cutting")`. Imported by `fbk/gates/spec.py`, `fbk/gates/breakdown.py`, and `fbk/gates/test_hash.py`. No gate hard-codes the strings.
3. **`fbk/injection.py`** — `def detect_injections(path_or_text: str) -> int` returns the warning count and prints `WARNING: [injection] ...` lines to stderr (the current `spec.py` behavior, moved verbatim). Imported by `fbk/gates/{spec,intent,design}.py`.
4. **`test_hash.verify_manifest(feature_dir, manifest_path=None) -> list[dict]`** — keeps the existing optional `manifest_path` second argument; the refactor changes only the return type to a list of discrepancy dicts, each `{"kind": "modified" | "unexpected" | "missing", "path": "<relpath>"}`; an empty list means clean. (`modified` = hash mismatch; `unexpected` = a test file present in scope but not in the manifest, i.e. a shadow test; `missing` = a manifest entry whose file is gone.) `code_review.py` fails the gate on any `modified` or `unexpected`; `missing` surfaces as a finding, not a failure.
5. **`test-hashes.json` shape** — `{"computed_at": "<iso8601>", "files": {"<relpath>": {"sha256": "<hex>", "slice": "<slice-name>", "test-discipline": "<mode>"}}}`. The per-file value is an object, not a bare hash string. `breakdown-gate` reads this file directly against this schema (it does not import `test_hash`), so it parallelizes with the manifest-restructure slice.
6. **Grilling-log entry shape** (`ai-docs/<feature>/grilling-log-<phase>.md`) — markdown, one `### <decision-slug>` block per decision, each with the lines `- Question:`, `- Recommendation:`, `- Answer:`, `- Confirmed:` (the reflect-back line). The intent/design gates check the file is present; the grilling-log seam test checks at least one well-formed block; the phase-skill dedup step reads the `Answer`/`Confirmed` lines.

Two consumers of fresh-eyes/quality-scan/test-review outputs (the gates that read them) and the technique-skill agents that write them share the structures already pinned above and in the cited design pages: the fresh-eyes gate bar is "the `## Critical` section has no observation entries after dedup"; the quality-scan artifact carries a `Severity:` field and at most five ranked entries; the test-review artifact carries an `accepted | needs-revision` verdict line.

## Slices

This spec **dogfoods** the slice-declaration format it designs (reversing the earlier "format built, not used here" stance — see the resolved decision). The block below carves the ~22-asset change into twelve vertical slices so breakdown carves along declared seams instead of re-deriving them off the AC list, and so the build-order edges the review flagged as hidden are explicit. The current `spec-gate` ignores this extra section; the current breakdown reads it as decomposition guidance. Each slice names its `test-discipline` (per the four-shape taxonomy), the ACs it delivers, and its `depends-on` edges. **`depends-on` lists only build-order predecessors** — a slice whose Python symbols this slice imports, so this slice's tests cannot go green until the predecessor exists. Pure contract references (a skill that names a gate command, a gate that reads an artifact by its pinned schema) are **not** dependencies, because §Interface contracts pins them — those slices run in parallel. A few slices carry only a *soft runtime dep* (noted inline): their code and tests are self-contained, but the assembled system works only once the referenced asset exists, which the final e2e slice catches. `contract-preserving` does not appear — no slice changes an implementation while leaving its contract and tests intact; that is an honest property of this work, not an omission.

For prompt-asset slices (skills, agents, docs) the "test" is a shell integration test, but the discipline is still `new-contract`: the shell assertion (e.g., "this skill produces its named output," "this frontmatter carries the attribution") fails before the asset exists and passes after — a real red→green.

```yaml
slices:
  - name: foundation-disciplines-durable-docs
    description: Always-on disciplines into CLAUDE.md + authoring rules; the two durable docs seeded; GLOSSARY updates.
    test-discipline: new-contract
    contract: §Technical approach "Modified docs" + "New durable docs"; AC-17, AC-18, AC-19
    covers: [AC-17, AC-18, AC-19]
    depends-on: []
    retired-tests: []
  - name: shared-gate-infrastructure
    description: fbk/injection.py (detect_injections promoted from spec.py) + the shared slice-discipline constant.
    test-discipline: new-contract
    contract: §Technical approach "fbk/injection.py" + "Runtime values"; AC-23
    covers: [AC-23]
    depends-on: []
    retired-tests: []
  - name: test-lock-manifest-restructure
    description: test_hash.py flat map → per-entry objects; list-driven lock of pre-existing tests; shadow-test detection; structured verify_manifest return.
    test-discipline: contract-evolving
    contract: §Technical approach "test_hash.py"; AC-07
    covers: [AC-07]
    depends-on: [shared-gate-infrastructure]
    retired-tests: ["test_gates_test_hash.py flat-map assertions (len==64 on the file value; direct hash-string comparison) — replaced by per-entry-object assertions"]
  - name: intent-gate
    description: intent.py + intent-guide.md + the capability-entry prerequisite probe; injection scan on inputs.
    test-discipline: new-contract
    contract: §Technical approach "intent.py"; AC-01, AC-02, AC-24
    covers: [AC-01, AC-02, AC-24]
    depends-on: [shared-gate-infrastructure]
    retired-tests: []
  - name: design-gate
    description: design.py + design-guide.md; bidirectional manifest check, decisions-log count, injection scan.
    test-discipline: new-contract
    contract: §Technical approach "design.py"; AC-03, AC-24
    covers: [AC-03, AC-24]
    depends-on: [shared-gate-infrastructure]
    retired-tests: []
  - name: technique-skills-and-agents
    description: fbk-grilling / fbk-fresh-eyes / fbk-quality-scan / fbk-test-review skills; fbk-product-author / fbk-architect / fbk-fresh-eyes-reviewer agents; test-reviewer + detector reframes. Shell tests (standalone-invocation, grilling-log seam, attribution, tool-lists) written first.
    test-discipline: new-contract
    contract: §Technical approach "New skills"/"New agents"/"Modified agents"; AC-10, AC-13, AC-14, AC-15, AC-16
    covers: [AC-10, AC-13, AC-14, AC-15, AC-16]
    depends-on: []
    retired-tests: []
  - name: spec-gate-slice-awareness
    description: spec.py slice/coverage checks behind the slices-block hinge; full-path regression + adversarial-prose tests; import shared injection module.
    test-discipline: contract-evolving
    contract: §Technical approach "spec.py"; AC-04, AC-21
    covers: [AC-04, AC-21]
    depends-on: [shared-gate-infrastructure]
    retired-tests: ["the inline detect_injections coverage in test_gates_spec.py — moves to test_injection.py in the shared-infrastructure slice"]
  - name: breakdown-gate-slice-awareness
    description: breakdown.py checks #1/#8 made slice-shape-aware behind the slice-metadata hinge; cheap invariants (cross-cutting⇒no-impl, contract-evolving⇒retired-list); bounce-back marker check.
    test-discipline: contract-evolving
    contract: §Technical approach "breakdown.py"; AC-05, AC-06
    covers: [AC-05, AC-06]
    depends-on: [shared-gate-infrastructure]   # reads the test-lock manifest by its pinned schema (§Interface contracts #5), does not import test_hash — so it parallels the manifest-restructure slice
    retired-tests: ["no test files retired — existing breakdown fixtures keep passing because they carry no slice metadata; new shape cases are added"]
  - name: code-review-gate
    description: code_review.py (new module) calling test_hash.verify_manifest; quality-scan + final-test-review artifact checks; ordering sentinel; critical/drift non-blocking.
    test-discipline: new-contract
    contract: §Technical approach "code_review.py"; AC-08, AC-09, AC-11, AC-24
    covers: [AC-08, AC-09, AC-11, AC-24]
    depends-on: [test-lock-manifest-restructure]
    retired-tests: []
  - name: dispatcher-registration
    description: COMMAND_MAP += intent-gate/design-gate/code-review-gate; positive-presence assertions (not subset); count/name update.
    test-discipline: contract-evolving
    contract: §Technical approach "fbk/__init__.py" + §Interface contracts #1; supports AC-01/AC-03 routing
    covers: []
    depends-on: []   # COMMAND_MAP entries are pinned strings (§Interface contracts #1) and the presence test is self-contained; soft runtime dep on the three gate modules existing
    retired-tests: ["test_dispatcher.py 'all_14_commands' literal/subset assertion — renamed and replaced with positive-presence checks for the three new commands"]
  - name: phase-skill-modifications
    description: fbk-spec / fbk-breakdown / fbk-code-review SKILL.md changes; feature-spec-guide / task-compilation / code-review-guide / retrospective-guide; slice-shapes leaves; capability-entry.md; re-sentinel the prose-anchored tests.
    test-discipline: contract-evolving
    contract: §Technical approach "Modified skills"/"Modified docs"; AC-12, AC-20
    covers: [AC-12, AC-20]
    depends-on: []   # the skills reference gate commands and technique-skill names that are pinned (§Interface contracts + the names above); the prose-sentinel tests are self-contained; soft runtime dep on the gates + technique skills existing
    retired-tests: ["no test files retired — test-skill-guide-dedup.sh and the test-code-review-*.sh sentinels are updated in place, not removed"]
  - name: cross-cutting-verification-and-dogfood-e2e
    description: Full-chain dogfood UV on a throwaway sample feature; installer e2e for new assets + auto-discovery + adversarial no-assets/-path grep; two-phase retrospective preservation; reference-integrity extension. Test-only — the implementation exists across the other slices.
    test-discipline: cross-cutting
    contract: §Testing strategy "User verification steps" + shell/installer tests; AC-22
    covers: [AC-22]
    depends-on: [foundation-disciplines-durable-docs, shared-gate-infrastructure, test-lock-manifest-restructure, intent-gate, design-gate, technique-skills-and-agents, spec-gate-slice-awareness, breakdown-gate-slice-awareness, code-review-gate, dispatcher-registration, phase-skill-modifications]
    retired-tests: []
```

**Wave ordering** (derived from build-order `depends-on` only). With the interface contracts pinned, ten of the twelve slices run as independent parallel subagents across two wide waves; only the test-integrity tail and the final integration pass impose order:

- **Wave 1** (5, parallel — no build-order predecessors): `foundation-disciplines-durable-docs`, `shared-gate-infrastructure`, `technique-skills-and-agents`, `dispatcher-registration`, `phase-skill-modifications`.
- **Wave 2** (5, parallel — each imports only the wave-1 shared infrastructure): `test-lock-manifest-restructure`, `intent-gate`, `design-gate`, `spec-gate-slice-awareness`, `breakdown-gate-slice-awareness`.
- **Wave 3** (1): `code-review-gate` — the only slice that calls the restructured `verify_manifest`, and since the test strategy uses real collaborators (no mocks) its tests need that function to exist.
- **Wave 4** (1): `cross-cutting-verification-and-dogfood-e2e` — runs the assembled chain end-to-end; verification, not a build slice competing for parallelism.

Why this is flat rather than the earlier six-wave chain: the apparent dependencies between slices are almost all *contract* references that §Interface contracts now pins, so they no longer force ordering. The only true build-order edges are imports of the wave-1 shared symbols (the injection module, the `TEST_DISCIPLINES` constant) and the one `verify_manifest` call in wave 3. Within any wave, the per-slice work-unit authoring (breakdown's second step) is fully independent and parallelizable.

## Testing strategy

This is a context-asset project. Two kinds of artifact need different verification:

1. **Python gate scripts** are ordinary code with testable return values (JSON + exit code) — unit-tested with pytest under `assets/fbk-scripts/tests/`.
2. **Prompt assets** (skills, agents, docs, CLAUDE.md, rules) have no unit-test surface. Their observable outcomes are (a) the artifacts they produce and the gate verdicts over those artifacts — covered by the gate unit tests and the shell integration tests under `tests/sdl-workflow/`; and (b) end-to-end behavior — covered by the manual UV steps against a throwaway sample feature. The independent checkpoint-1 reviewer confirmed this is a legitimate limitation, not test-avoidance; where a property *can* be checked mechanically (frontmatter, routing resolution, discipline presence, the grilling-log reflect-back line, the agents' tool lists) the strategy now does so rather than deferring to a manual step.

### New tests needed

Unit tests (`assets/fbk-scripts/tests/`):
- `test_injection.py` (new): the shared `detect_injections` catches each pattern class and is importable from `fbk/injection.py` — covers AC-23.
- `test_gates_intent.py` (new): `intent-gate` passes a well-formed PRD + inventory + grilling log + clean fresh-eyes report — covers AC-01. Fails on each missing PRD section, on a PRD↔inventory reference mismatch (behavior referenced but absent; inventory item never referenced), on missing grilling log, and on a fresh-eyes report with an open critical — covers AC-02. A poisoned input raises the `injection_warnings` count — covers AC-02/AC-23.
- `test_gates_design.py` (new): `design-gate` passes a manifest whose entries all resolve and whose directory has no unlisted pages; fails on manifest→file drift, on file→manifest drift, and on a simultaneous both-directions case (reports both); fails on missing decomposition rationale; fails on a zero/absent "Decisions recorded" count; fails on open-critical fresh-eyes — covers AC-03.
- `test_gates_spec.py` (refactor-then-extend): full feature-path run — a no-slices spec passes identically, and an adversarial legacy spec carrying the bare token `test-discipline` only in prose/a code fence fires no slice check — covers AC-21. With a `## Slices` block: fails a slice missing `test-discipline`, fails an out-of-taxonomy value, fails an inventory behavior covered by no slice — covers AC-04. A slices-bearing spec still requires an `AC-NN` reference in its testing-strategy section (the existing check is retained) — covers AC-04/AC-21.
- `test_gates_breakdown.py` (refactor-then-extend): with slice metadata — a cross-cutting slice with a test-only task **passes** (the case the old check #1 rejected); a contract-preserving slice with impl-but-no-new-test **passes** (the case old check #8 rejected); a contract-evolving slice missing its retired-tests list **fails**; an unresolved bounce-back marker **fails**. Without slice metadata, the existing DAG/wave/AC behavior is unchanged — covers AC-05, AC-06.
- `test_gates_test_hash.py` (refactor-then-extend): per-entry manifest round-trips `sha256` + `slice` + `test-discipline`; the list-driven mode locks a named pre-existing test file and verifies it; tamper detection still trips; an unlisted test file in a locked slice's scope is flagged as a shadow test; **and an unlisted test file outside any locked slice's scope is NOT flagged** (the negative case — list-driven shadow detection is scoped to the locked set's directories, not a repo-wide rglob, so it must not flag the whole project test suite) — covers AC-07.
- `test_gates_code_review.py` (new): `code-review-gate` fails when the quality-scan artifact is absent or missing its severity field, when the final test-review verdict artifact is absent, on a hash mismatch, or on a shadow test; passes when all present and hashes intact; a critical-severity quality finding and a drifted-but-unmodified locked test do **not** fail it; the hash check is performed via `test_hash.verify_manifest` — covers AC-08, AC-09, AC-10, AC-11.
- Capability-entry prerequisite unit test (in the gate/helper test): for each of the four upstream-missing cases (intent-missing-at-design, design-missing-at-spec, spec-missing-at-breakdown, impl-missing-at-code-review) the prerequisite probe returns a structured result naming the missing artifact and the upstream phase, without a hard-failure exit — covers AC-12.
- `test_dispatcher.py` (extend): positive assertions that `intent-gate`, `design-gate`, and `code-review-gate` are each present in `COMMAND_MAP` (not a subset check that passes on omission); update the count literal and test name — covers AC-01/AC-03 routing.
- Path-arg guard tests for the three new gates: a missing path exits 2; a binary/garbage artifact degrades to a structural failure rather than a traceback — covers AC-24.

Shell integration tests (`tests/sdl-workflow/`, matching the existing `test-*.sh` style):
- Reference-integrity extended to the new skills/agents/docs (routed paths resolve) **plus an adversarial grep**: no installed firebreak-asset body contains the literal `assets/` path prefix — covers AC-22.
- Instruction-hygiene, enumerating each item by name (the existing per-target pattern): all five always-on disciplines appear in `.claude/CLAUDE.md` and in the authoring rules — covers AC-17, AC-18; the `fbk-grilling` frontmatter contains the Pocock attribution and source link — covers AC-16; the three observe/scan agents declare no Write/Edit tool — covers AC-15.
- Standalone technique-invocation test: invoking each technique skill with minimal input produces its named output artifact (`fresh-eyes-*.md`, `quality-scan.md`, `test-review-*.md`, `grilling-log-*.md`) — covers AC-13, AC-14.
- Grilling-log seam test: a correct-shape log (with a reflect-back confirmation line per decision) lets the intent gate pass; a wrong-shape log makes it fail — covers AC-13.
- Durable-doc test: `docs/decisions-log.md` and `docs/architecture-overview.md` exist, the overview is non-empty, and the authoring docs state the governing conventions — covers AC-19.
- Two-phase retrospective preservation test: after two phases run in sequence, both stage sections are present in the retrospective — covers AC-20.
- Capability-entry test: invoking a phase with missing upstream artifacts prints the missing-artifact name and the upstream-phase name and does not hard-fail — covers AC-12.
- Code-review ordering sentinel test: greps `fbk-code-review/SKILL.md` to assert the existing bug-finding pass precedes the `fbk-quality-scan` and `fbk-test-review` (final) invocations and the `code-review-gate` call, in that order (the sentinel pattern `test-skill-guide-dedup.sh` uses) — covers AC-08. (AC-08's ordering is a sequencing contract in one skill file; the sentinel test catches a silent reorder that a live UV run would not.)

Installer test (`tests/installer/`):
- Extend the e2e install/upgrade test to assert the new skill/agent/doc files are present under `~/.claude/` after install and gone after uninstall, and that `fbk.py` exposes `intent-gate`/`design-gate`/`code-review-gate` after install. The gate subcommands live inside the installed `fbk-scripts/` tree (removed wholesale at uninstall), so the uninstall assertion checks the tree is gone, not a per-subcommand artifact — covers AC-22.

### Existing tests impacted

- `test_gates_test_hash.py` — **manifest shape changes** from `{path: hash}` to per-entry objects; the `len==64` and direct hash-string comparisons must be rewritten. Reclassify the touch as refactor-then-extend; enumerate the changed assertions during implementation. Affected path: `fbk/gates/test_hash.py`.
- `test_gates_breakdown.py` — checks #1/#8 become slice-shape-aware; existing fixtures pass only because they carry no slice metadata (the backward-compat hinge). Add the passing cross-cutting and contract-preserving cases. Affected path: `fbk/gates/breakdown.py`.
- `test_gates_spec.py` — gains the full-path regression and adversarial-prose cases; existing pure-function tests preserved. Affected path: `fbk/gates/spec.py`.
- `test_gates_review.py` — **unaffected**: the code-review checks land in the new `code_review.py`, so `review.py` and `validate_review` are not moved. Confirmed below in caller enumeration.
- `test_dispatcher.py` — the `all_14_commands` count literal and name change; add positive presence assertions for the three new gates. Affected path: `fbk/__init__.py`.
- Prose-anchored shell tests that grep exact strings in files this work rewrites: `tests/sdl-workflow/test-skill-guide-dedup.sh` (greps `fbk-spec/SKILL.md` and `feature-spec-guide.md`), and the code-review path tests `test-code-review-skill.sh`, `test-code-review-guide-extensions.sh`, `test-code-review-integration.sh`, and `test-code-review-structural.sh` (the last asserts the detector agent's tool list and description, which the mode-neutral persona reframe edits). Update their sentinels. Also any `tests/sdl-workflow/*` test enumerating the skill/agent/phase set needs the two new phases added — search for hard-coded asset lists before editing.

**Caller enumeration for the `review-gate` symbol** (review finding — the code-review gate is a *new* module, so `review.py` is **not** moved and nothing below breaks; enumerated to prove it): runtime callers of `review-gate` are `fbk-spec-review/SKILL.md` (semantic anchor) and `fbk-breakdown/SKILL.md` (prior-stage check); the import caller is `test_gates_review.py` (`validate_review`); shell references are `test-gate-output-review-python.sh`, `test-review-integration.sh`, `test-skill-guide-dedup.sh`. All keep working because `review.py`/`validate_review`/`review-gate` are untouched.

### Test infrastructure changes

- New pytest fixtures in `conftest.py`: a valid intent artifact set (PRD + inventory + grilling log + fresh-eyes report), a valid design manifest + `design/` tree, a spec with a valid `## Slices` block, an adversarial legacy spec with the bare `test-discipline` token in prose, per-shape breakdown task sets (cross-cutting test-only, contract-preserving impl-only, contract-evolving with/without retired-list), and a per-entry test-lock manifest. Build from the existing `valid_spec_text` pattern.
- A throwaway **sample feature** for end-to-end dogfooding — used by the UV steps, not committed.
- **No mocks.** All collaborators are the real filesystem and real gate code; fresh-eyes/quality-scan/test-review *outputs* are fixture files (we test the gate's reading of the artifact, not the LLM that produced it). There is no network, clock, or paid service, so nothing meets the mock-justification bar — real collaborators throughout.

### User verification steps

Run against a throwaway sample feature in a scratch branch. Each step maps to a test except where marked intentionally-manual.

- UV-1 (→ `test_gates_intent.py`): Run `/fbk-intent sample "add a trivial flag"` → an interview opens, then `prd.md` + `behavior-inventory.yaml` + `grilling-log-intent.md` appear in `ai-docs/sample/`, in plain language — AC-01.
- UV-2 (→ `test_gates_intent.py`): At intent close the fresh-eyes report is produced and `intent-gate` prints `result: pass` only after critical observations are resolved — AC-02.
- UV-3 (→ `test_gates_design.py`): Run `/fbk-design sample` → design pages + `design-manifest.md` appear under `ai-docs/sample/design/`, an entry is appended to `docs/decisions-log.md`, and `design-gate` passes; deleting one design page without updating the manifest makes the gate fail — AC-03.
- UV-4 (→ `test_gates_spec.py`): Run `/fbk-spec sample` → the spec declares ≥1 slice with a `test-discipline`, links every inventory behavior to a slice, and `spec-gate` passes; removing a slice's `test-discipline` makes it fail — AC-04, AC-21.
- UV-5 (→ `test_gates_breakdown.py`, `test_gates_test_hash.py`): Run `/fbk-breakdown sample` → each slice yields work units matching its shape; pre-lock `/fbk-test-review` runs and only an `accepted` verdict populates the manifest with `slice` + `test-discipline`; forcing an under-specified slice triggers a named bounce-back — AC-05, AC-06, AC-07.
- UV-6 (→ `test_gates_code_review.py`): Run `/fbk-code-review` → the existing bug-finding pass runs first, then a ranked ≤5 quality list and a final test-review; tampering with a locked test fails the gate; a drifted-but-unmodified test surfaces as a finding; a shadow test fails the gate — AC-08, AC-09, AC-10, AC-11.
- UV-7 (→ standalone technique-invocation test): `/fbk-grilling`, `/fbk-fresh-eyes`, `/fbk-quality-scan`, `/fbk-test-review` each run standalone and produce their named output artifact — AC-13, AC-14.
- UV-8 (→ capability-entry test): Run `/fbk-design sample` in a fresh repo with no intent artifacts → it names what's missing and offers to run `/fbk-intent`, without blocking — AC-12.
- UV-9 (→ instruction-hygiene test for the mechanical half): Open a fresh session and read `.claude/CLAUDE.md` → the five always-on disciplines are surfaced and route to the rule — AC-17. *Intentionally manual, no test:* spot-check that a phase artifact and a grilling question read in plain language and describe items rather than cite identifiers — this is an LLM-behavioral quality that cannot be mechanized (documented per the guide's allowance).
- UV-10 (→ two-phase retrospective preservation test): After two phases run, both stage sections are present in `ai-docs/sample/sample-retrospective.md` — AC-20.

## Documentation impact

### Project documents to update

- `GLOSSARY.md` — add capability-entry, durable-artifact discipline, architecture/intent overview, decisions log, slice shape + the four shape names, fresh-eyes, quality scan (confirm technique skill present); remove project-memory, capture gate, mutation sampling if present.
- `CHANGELOG.md` — next release: Added (intent/design phases, four technique skills, durable-artifact discipline, intent/design/code-review gates, shared injection module), Changed (spec/breakdown/code-review phases, test-lock manifest schema, test-reviewer agent, CLAUDE.md, asset-authoring rules). Per project rule, review `README.md` after and discuss proposed README changes with the operator before applying.
- `README.md` — update the SDL phase list to six phases; mention the technique skills and durable docs (operator-approved changes only).
- `fbk-sdl-workflow.md` and the four modified leaves — as listed in the technical approach.
- `.claude/CLAUDE.md` and the asset-authoring rules — absorb the five always-on disciplines.

### New documentation to create

- Routed concept docs under `fbk-sdl-workflow/`: `intent-guide.md`, `design-guide.md`, `capability-entry.md`, `slice-shapes.md` + the four shape leaves. (Unrouted concept material — hybrid-gate-pattern, technique-skills, design-manifest, durable-artifact-discipline — folds into the architecture overview rather than shipping as standalone leaves.)
- The two durable docs: `docs/decisions-log.md` and `docs/architecture-overview.md` (seeded for this repo).
- This feature's retrospective gains intent and design stage sections (mechanism, not a standing doc).

## Acceptance criteria

- AC-01: `fbk-intent` exists and produces `prd.md`, `behavior-inventory.yaml`, and `grilling-log-intent.md` in `ai-docs/<feature>/`; `intent-gate` is registered in `COMMAND_MAP` and passes a well-formed artifact set.
- AC-02: `intent-gate` fails on any missing required PRD section, on PRD↔inventory reference inconsistency, on a missing grilling log, or on a fresh-eyes report with an unresolved critical observation; and it runs the shared injection scan on its inputs, emitting an `injection_warnings` count.
- AC-03: `fbk-design` exists and produces `design/` pages + `design-manifest.md` and appends ≥1 status-bearing entry to `docs/decisions-log.md`; `design-gate` enforces the bidirectional manifest↔directory check (failing on drift in either direction), requires a decomposition rationale, requires the manifest's "Decisions recorded" count to be present and non-zero, requires a clean fresh-eyes report, and runs the injection scan on the design pages and manifest.
- AC-04: `fbk-spec` consumes intent + design, declares ≥1 slice in a `## Slices` block with a `test-discipline` from the four-shape taxonomy, links every inventory behavior to ≥1 slice, and passes the modified `spec-gate` (which retains the existing testing-strategy AC-traceability check).
- AC-05: When tasks carry slice metadata, `breakdown-gate` enforces the cheap shape invariants (cross-cutting ⇒ no impl task; contract-evolving ⇒ a retired-tests list with rationale) and its AC-coverage check is slice-shape-aware so a cross-cutting (test-only) slice and a contract-preserving (impl-without-new-test) slice both pass; the full four-way shape match is breakdown-leaf guidance, not gate-enforced this cycle.
- AC-06: `breakdown-gate` fails on an unresolved bounce-back marker; the breakdown skill emits a named bounce-back identifying the specific spec gap rather than producing oversized work units. (Whether a warranted bounce-back actually fired is a manual/UV judgment the gate cannot detect — a breakdown that should have bounced but didn't passes the gate silently. This is a documented residual limitation, not a gate failure.)
- AC-07: The test-lock manifest (`test-hashes.json`, restructured to per-entry objects) records `sha256`, `slice`, and `test-discipline` per file; a list-driven lock mode locks named pre-existing project test files for contract-preserving slices; `test-hash-gate` verifies hashes, detects tampering, and flags an unlisted test file in a locked slice's scope as a shadow test.
- AC-08: `fbk-code-review` runs the existing bug-finding pass unchanged, then invokes `fbk-quality-scan` and then `fbk-test-review` (final pass).
- AC-09: The new `code-review-gate` requires a quality-scan artifact with the severity field populated and a final test-review verdict artifact, and performs the hash + shadow-test check by calling `test_hash.verify_manifest` rather than a second hash path.
- AC-10: `fbk-quality-scan` returns at most five ranked, severity-tagged findings and is scan-only (no auto-fix).
- AC-11: At the code-review gate, a critical-severity quality finding or a drifted-but-unmodified locked test surfaces for operator triage; only a hash mismatch or a shadow test fails the gate.
- AC-12: A phase invoked without its upstream artifacts names the specific missing artifact and the upstream phase to run, and does not hard-block, for each of the four upstream-missing cases.
- AC-13: `fbk-grilling` asks one question at a time with a recommendation, records a reflect-back confirmation line per decision in its grilling log (making reflect-back observable), and is invocable out-of-ceremony.
- AC-14: `fbk-fresh-eyes`, `fbk-quality-scan`, and `fbk-test-review` each exist as callable technique skills with a stable input/output contract (a named output artifact, plus a verdict or severity field where applicable) and are invocable out-of-ceremony.
- AC-15: The observe/scan technique agents (`fbk-fresh-eyes-reviewer`, the quality-scan detector, `fbk-test-reviewer`) carry no Write or Edit tool in their definitions, so they cannot auto-fix.
- AC-16: The `fbk-grilling` frontmatter credits Matt Pocock and links the source grill-me skill (`https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md`).
- AC-17: `.claude/CLAUDE.md` surfaces all five named always-on disciplines (simple language, descriptions over identifiers, capability framing, interview before drafting, structural-principles awareness) and routes to the rule that carries them.
- AC-18: The asset-authoring rules contain all five always-on disciplines as instructions.
- AC-19: The durable-artifact discipline is established — `docs/decisions-log.md` and `docs/architecture-overview.md` exist, the overview is seeded for this repo and non-empty, and the authoring docs state the governing conventions (plain markdown, bounded length, in-branch updates that merge with the change).
- AC-20: Each new and reshaped phase skill appends its stage section to the feature retrospective, and after two phases run both stage sections are present (the append preserves prior stages).
- AC-21: The modified `spec-gate` is backward compatible — a spec with no `## Slices` block passes identically over the full feature path, including an adversarial case where the bare token `test-discipline` appears only in prose or a code fence and fires no slice check.
- AC-22: Every new skill, agent, and doc installs under `~/.claude/` via the installer's auto-discovery (no manifest-registration step); every firebreak-asset reference uses the installed path form (an adversarial grep finds no `assets/` prefix in installed asset bodies); durable docs and feature artifacts are project-relative, a path class distinct from installed assets.
- AC-23: `detect_injections` lives in the shared `fbk/injection.py` module and is imported by the spec, intent, and design gates, verified by a unit test importing it from that location.
- AC-24: The new gate scripts validate each path argument before opening (exit 2 on a missing path) and read with `errors="replace"`, so a binary or garbage artifact degrades to a structural failure rather than crashing.

## Open questions

None. (The two prior open questions are resolved below: the slice→breakdown handoff format is fixed in §"Slice declaration format," and the code-review gate lands in a new `code_review.py` module.)

## Dependencies

- The existing Firebreak SDL asset base: the eight `fbk-*` skills, the agent roster, the `fbk-scripts` gate/hook/state/dispatcher modules, the `fbk-docs` doc tree, the installer (auto-discovery), and the pytest + shell test suites.
- The existing code-review machinery (intent extraction + detector/challenger loop) and the test-integrity hash-lock mechanism — both preserved and built upon.
- The existing `fbk-spec-review` council, threat-model pathway, and structural review gate — preserved; reframed only in docs. `review.py`/`review-gate`/`validate_review` are untouched (the code-review gate is a new module).
- The existing retrospective pattern and the `fbk-improve` self-improvement loop — consumed by the retrospective-append requirement.
- `GLOSSARY.md` and the project's CLAUDE.md and asset-authoring rules — modified by this work.
- The external `/grill-me` skill — prior art the grilling technique adapts (see resolved decision); not a runtime dependency of the shipped firebreak assets.
- Python 3.11+, pytest. No new third-party libraries.
- Near-term follow-on this work is shaped to consume but does not build: AST-based schema extraction; the orchestration project's state-machine entries for the two new phases.

---

## Decisions resolved during scoping

- **One consolidated spec.** The operator chose a single feature spec over a project overview + per-feature specs. Slice declarations inside this spec are where breakdown carves the work, so the consolidation does not lose decomposability.
- **Slice-shape gate enforcement is the cheap invariants only this cycle** (operator decision). `breakdown-gate` mechanically enforces only cross-cutting ⇒ no-impl and contract-evolving ⇒ retired-list; the full four-way shape-to-work-unit match is breakdown-leaf authoring guidance until one real feature exercises it. This avoids re-introducing the per-item classifier machinery Decision 2 cut.
- **The code-review gate is a new `code_review.py` module** (was an open question), not folded into `review.py` (which gates a different phase). Its hash + shadow-test check calls `test_hash.verify_manifest` rather than a second hash path. This keeps `review.py`/`review-gate`/`validate_review` untouched, so the spec-review and breakdown callers and the review tests are unaffected.
- **The test-lock manifest is restructured, not merely extended.** The shipped flat `{path: hash}` map in `test-hashes.json` becomes per-entry objects `{sha256, slice, test-discipline}`, and a list-driven lock mode is added for pre-existing tests; `test_hash.py` is reclassified refactor-then-extend and its existing tests change. The runtime filename stays `test-hashes.json`.
- **`detect_injections` is promoted to a shared `fbk/injection.py` module** and imported by the spec, intent, and design gates, so the new gates get injection-detection parity and the pattern list can't drift across copies.
- **Durable docs are a third path class** (operator-project-relative), distinct from installed assets and feature artifacts. The installed-path constraint governs firebreak-asset references only. The installer auto-discovers assets, so there is no manifest-registration step — the only registration is `COMMAND_MAP` for the new gate subcommands.
- **`fbk-architect` is author-only this cycle.** The "superset the council architect collapses into" framing is dropped from the build requirement and recorded as a decisions-log note, since the council migration is out of scope and the superset can't be validated until it happens.
- **Concept docs ship as routed leaves only.** `capability-entry`, `slice-shapes` (+ leaves), and the two phase guides are routed at runtime; the unrouted patterns (hybrid-gate, technique-skills, design-manifest, durable-artifact-discipline) fold into the architecture overview rather than shipping as leaves nothing loads.
- **The slice→breakdown handoff is the `## Slices` YAML block** per the slice-shapes design page (see §"Slice declaration format"); breakdown consumes one slice entry plus its contract pointer.
- **Grilling technique is a new firebreak asset (`fbk-grilling`), adapted from Matt Pocock's grill-me skill**, not a change to the external `/grill-me`. Firebreak ships and installs its own assets; the external grill-me is itself an adaptation of Pocock's skill and carries a source-link credit, so `fbk-grilling` sits in the same lineage and carries the same attribution.
- **We dogfood the slice-declaration format in this spec** (reversing the earlier "built, not used here" stance, at operator direction). §Slices populates the `## Slices` block this project designs, carving the work into twelve declared vertical slices with test-discipline modes and dependency-derived waves. Rationale: it forces explicit decomposition (closing the review's "slices block empty / build-order edges hidden" findings) and sets up a parallel breakdown. The rest of the document keeps the current 9-section structure, the current `spec-gate` ignores the block, and the current breakdown consumes it as guidance — so dogfooding costs nothing in the current pipeline. Honest observation the exercise surfaced: the four-shape taxonomy assumes testable code, so prompt-asset slices map to `new-contract` via shell tests (red→green on asset presence/output), and `contract-preserving` never appears in this work.
- **Prompt-asset behavior is verified by gate tests + shell tests + manual UV, not fake unit tests** — and every mechanically-checkable property (frontmatter, routing, discipline presence, the grilling-log reflect-back line, agent tool lists) is checked rather than deferred to a manual step.
