# Interface contracts — Specification

> **Reads on top of the planning package — not a restatement of it.** This spec maps the "how" onto the upstream artifacts; read these first rather than expecting them repeated here:
> - `ai-docs/interface-contracts/prd.md` — the "what" and "why"
> - `ai-docs/interface-contracts/behavior-inventory.yaml` — the ten behaviors (B-001…B-010)
> - `ai-docs/interface-contracts/design/` — the six design pages (module shape, the standard, the worked contracts page, spec-section shapes, gate algorithms, neighboring-asset edits)
> - `ai-docs/interface-contracts/design-manifest.md` — index of the design pages
> - `docs/decisions-log.md` — the six enduring decisions (all dated 2026-06-09)
>
> **Bootstrap note.** This feature builds the gate checks that enforce the interface-contracts discipline. Those checks do not exist yet, so this spec's own gate run is judged by the *current* spec gate (nine sections + slices). This document nonetheless **dogfoods** the new `## Interface contracts` and `## Uncovered acceptance criteria` sections, so it is the first worked spec-layer example of the format it defines.

## Problem

A feature's interface contracts are enumerated once, at design, and then lost. The spec author re-derives them from the intent's prose; the breakdown step re-derives signatures again from the spec's prose. Each hop is a compression, and at each compression a contract can vanish with no signal — specified at design, forgotten at spec, never tested, never built, and nothing in the pipeline notices. The carrying mechanism that would move the design's contract list intact into the spec is missing, the structured anchor that would let a mechanical completeness check run is missing, and the gate that would run that check is missing. This feature supplies all three: a structured spec section that carries the contracts, a standardized design page the check can read, and four deterministic spec-gate checks that turn a silent drop into a named gate failure.

## Goals / Non-goals

### Goals

- Add a `fbk/gates/contracts.py` module with four pure check functions — structural completeness, design-anchor, acceptance-criteria coverage, and a light seam-coverage heuristic — each returning a list of teaching failure strings.
- Wire those four checks into the existing spec gate (`fbk/gates/spec.py`) so they run on every feature spec, after the existing slice check.
- Give the spec author a permanent, progressively-disclosed home for the three new section formats (`## Interface contracts`, `## Excluded contracts`, `## Uncovered acceptance criteria`) and the blast-radius derivation step, routed from `feature-spec-guide.md` only when the author actually has contracts to enumerate.
- Give the design author a permanent, progressively-disclosed home for the standardized `design/contracts.md` page shape and identifier scheme, routed from `design-guide.md` only when the feature has contracts.
- Make `design/contracts.md` a required output of every design phase (a one-sentence file when the feature changes no contracts).
- Extend the architecture reviewer's brief so spec review elevates contract drift and leaves disposition to the operator.

### Non-goals

- No change to the wave or commit model for implementation (the sibling `wave-commit-model` feature owns that).
- No semantic comparison of `signature` or `invariants` between same-identifier entries in the deterministic gate — that judgment stays with spec review (the identifier-only-carry tradeoff).
- No snapshot or hash of the design page; a design edit after the spec gate passes is not auto-detected. Spec review elevates the drift on its next run.
- No recomputation of the blast-radius caller set inside the gate. The gate checks each blast-radius entry is present and well-formed; per-language completeness verification is a deferred follow-on (the gate is language-blind and runs inside arbitrary target projects).
- No new top-level directory. Everything lands inside artifacts the SDL already produces or installs.

## User-facing behavior

The operator is a technical lead who makes the product and architecture calls and relies on the agents to carry detail across phase boundaries. After this ships:

- **The spec carries a contract list.** Every feature spec now has a `## Interface contracts` section. When the feature changes no contracts, one sentence — `No new or changed contracts in this feature.` — satisfies it. Otherwise it lists each contract as a block with six fields, carrying the design's `IF-D-NN` identifiers verbatim and minting `IF-S-NN` identifiers for pre-existing-but-touched contracts and for contracts the spec discovers that design never enumerated.
- **Two escape hatches for honest scope shifts.** `## Excluded contracts` records a design contract the spec deliberately does not carry, with a rationale. `## Uncovered acceptance criteria` records a criterion intentionally not served by any contract, with a rationale. Both rationales are mandatory; the gate rejects an empty one.
- **The gate names what dropped.** When a design contract is neither carried nor excused, or an acceptance criterion is neither covered nor excused, the gate fails with the specific item named, points at the artifact that defines it, and states the two ways to resolve it — carry/cover it, or excuse it with a rationale. The operator never has to interpret a vague failure.
- **A heuristic catch for un-contracted seams.** When the technical approach declares an integration seam between two components and no contract entry names that pair, the gate raises a heuristic flag — explicitly labelled as a heuristic, with the operator as the final judge.
- **Design always produces a contracts page.** Every design phase now writes `design/contracts.md`. A no-contracts feature writes one sentence.
- **Spec review elevates drift.** When the spec and design quietly disagree — a spec-added contract design never had, a same-identifier entry whose name or signature has moved, a design page that changed mid-stream — the architecture reviewer reports it as informational. The operator decides the response.

Failure and edge behavior is enumerated in `prd.md` "Edge cases and failure modes"; those are the acceptance targets for the gate-behavior criteria below.

## Technical approach

The system is Python gate scripts plus Claude Code context assets (skills, referenced docs). Source lives under `assets/` and installs to `~/.claude/` via the auto-discovering installer — a new file under `assets/` installs automatically; no manifest registration is needed for the new module or the new leaves. **This spec uses source `assets/...` paths to say what to build; the assets themselves must reference installed paths** (`.claude/fbk-docs/...`, `python3 "$HOME"/.claude/fbk-scripts/fbk.py ...`) per the project's path-class rule.

### The gate module and its wiring

The four checks live in a new module, `fbk/gates/contracts.py`, mirroring the precedent that put the code-review gate in its own module rather than bloating an existing one. The existing spec gate, `fbk/gates/spec.py`, imports the four functions at module top level and calls them inside its `if scope == "feature":` branch, **after** the existing `check_slices` call, accumulating their failures into the shared `fails` list (no short-circuit — consistent with how the gate already accumulates across checks). Data crossing the boundary: the spec text (all four checks) and the feature directory (the design-anchor check only) go in; a `List[str]` of failure strings comes back. This mirrors how `spec.py` already delegates to `fbk.injection` and `fbk.slices`.

The four algorithms — parse rules, set logic, exact teaching-error wording, and the AC-coverage trap (coverage is drawn only from `covers:` lists, never a body-wide scan) — are fully pinned in `design/gate-checks.md` and restated as this spec's own contracts in §Interface contracts. They are not re-derived here.

**Activation is unconditional.** The four checks run on every feature spec, full stop (operator decision during scoping — strongest enforcement over a backward-compat hinge). Two consequences follow and are carried into Testing strategy:

1. Because the structural check treats a *missing* `## Interface contracts` section as a failure, every feature spec must now carry the section (the one-sentence no-contracts form suffices). The existing `test_gates_spec.py` fixtures that expect a pass must gain that sentence.
2. Because the design-anchor check treats a *missing* `design/contracts.md` as a failure, every feature spec must now have a design contracts page on disk. The existing pass-fixtures must write a no-contracts `design/contracts.md` into their temporary feature directory.

This feature's own spec is unaffected today: the checks do not exist until this feature is implemented, so the current gate judges this document on the nine-section-plus-slices criteria only.

### Where the new format guidance lives (progressive disclosure)

The author-facing detail for the new formats is split so that **only the always-required instruction loads on every phase run**, and the conditional detail loads only when the author has contracts to write (per the always-on progressive-disclosure discipline — "every instruction in a loaded asset must apply every time the asset loads"). Two new routed leaves, each gated by its own sub-condition:

- **`assets/fbk-docs/fbk-sdl-workflow/design-contracts-standard.md`** (new leaf) — the normative `design/contracts.md` schema: the no-contracts and entry forms, the `IF-D-NN` / `IF-S-NN` identifier scheme, the `## IF-D-NN — <name>` entry schema (`signature`, `invariants`, `consumed-by`, `produced-by`), and the `^## (IF-D-[0-9]{2,})` parse rule. `design-guide.md` keeps only the always-true bullet — "`contracts.md` is required on every feature; no-contracts is one sentence" — plus a conditional route: *when the feature introduces or changes contracts, read the standard leaf*.
- **`assets/fbk-docs/fbk-sdl-workflow/interface-contracts-format.md`** (new leaf) — the three spec-side section shapes, their field rules, the three valid `design-ref` forms, the section ordering, and the **blast-radius derivation** instruction (derive the dependent set with the project's reference tooling against the modules the spec declares changed; mark each `design-ref: pre-existing` with an `IF-S-NN` id). `feature-spec-guide.md` keeps only the always-true note — "`## Interface contracts` is a required section; no-contracts is one sentence" — plus a conditional route: *when enumerating contracts, excluding one, or leaving an acceptance criterion uncovered, read the format leaf*.

They are two separate leaves, not one: a shared leaf would have to be valid under both the design-author route and the spec-author route, but the design-page schema (`## IF-D-NN` headings, `consumed-by`/`produced-by`) and the spec-section schema (YAML-block list items with `covers`/`design-ref`) are different shapes.

### Neighboring-asset edits

- **`design-guide.md`** — make `contracts.md` required output, with the conditional route to the standard leaf (above). The design gate enforces this indirectly: `contracts.md` must appear in the manifest and the manifest must match disk; a missing page also surfaces downstream as the spec gate's design-anchor "page not found" failure.
- **`feature-spec-guide.md`** — add the required-section note and the conditional route to the format leaf (above).
- **`review-perspectives.md`** — extend the architecture reviewer's brief: when the feature has a `design/contracts.md`, report three drift conditions as informational findings — a spec-added `IF-S-NN` contract absent from design; an `IF-D-NN` entry whose identifier is preserved but whose name or signature has materially changed; a count/name mismatch between the design page's `IF-D-NN` entries and what the spec carries or excludes. Report all three as informational; leave disposition to the operator.

### Integration seam declaration

The code seams this feature introduces. Each names two components, the shared interface, and the convention both sides honor.

- [ ] spec.py → contracts.py: import-and-call contract — `spec.py` imports the four functions at module top level and calls them in the feature-scope branch after `check_slices`; inbound `spec_text: str` (all four) plus `feature_dir: str` (design-anchor only); outbound `List[str]`; an absent module surfaces as `ImportError` at startup, consistent with `fbk.injection` / `fbk.slices`.
- [ ] contracts.py → design/contracts.md: page-parse contract — the design-anchor check reads `<feature_dir>/design/contracts.md` and extracts identifiers with `^## (IF-D-[0-9]{2,})` (`re.MULTILINE`); a missing file returns one "page not found" failure rather than raising.

### Module-touch policy

- [ ] `fbk/gates/contracts.py`: create (new module — the four checks plus its four-function public interface).
- [ ] `fbk/gates/spec.py`: extend (add the top-level import and the four unconditional calls after `check_slices`; the existing CLI / JSON-result / exit-code contract is preserved unchanged).
- [ ] `assets/fbk-docs/fbk-sdl-workflow/design-contracts-standard.md`: create (new routed leaf).
- [ ] `assets/fbk-docs/fbk-sdl-workflow/interface-contracts-format.md`: create (new routed leaf).
- [ ] `assets/fbk-docs/fbk-sdl-workflow/design-guide.md`: extend (required-page bullet + conditional route).
- [ ] `assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md`: extend (required-section note + conditional route).
- [ ] `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md`: extend (architecture-reviewer drift brief).
- [ ] `GLOSSARY.md`: extend (new terms — see Documentation impact).
- [ ] `CHANGELOG.md`, `README.md`: extend (see Documentation impact).

### Runtime values that must be exact

- New module: `fbk/gates/contracts.py`; the four exported names `check_interface_contracts_structure`, `check_design_anchor`, `check_ac_coverage`, `check_seam_coverage`; each returns `List[str]`.
- Identifier forms: `IF-D-NN` (design-originated) and `IF-S-NN` (spec-originated); `NN` is zero-padded, minimum two digits. The gate id regex is `^IF-[DS]-[0-9]{2,}$`.
- The exact no-contracts sentence: `No new or changed contracts in this feature.`
- Design-page identifier parse: `^## (IF-D-[0-9]{2,})` with `re.MULTILINE`.
- Valid `design-ref` values: a path/anchor string (shape-only; the gate does not resolve it), the literal `pre-existing`, or the literal `none`.
- The seam-coverage arrow is Unicode U+2192 (`→`); the extraction is anchored to line start so a mid-prose arrow is not matched.
- Gate exit codes and result shape are unchanged: `0` pass, `2` fail; `{"gate": "spec", "result": "pass"|"fail", ...}` to stdout.

## Testing strategy

This is a context-asset project. Two artifact kinds need different verification:

1. **Python gate code** — ordinary code with testable return values (a list of failure strings; the gate's JSON + exit code). Unit-tested with pytest under `assets/fbk-scripts/tests/`.
2. **Prompt assets** (the two leaves, the three guide/brief edits) — no unit-test surface. Their observable outcome is the gate verdict over the artifacts they shape (covered by the gate unit tests) and the end-to-end dogfood run (the UV steps). Where a property is mechanically checkable (a guide names the required section, a guide routes to its leaf, a leaf carries the schema, a brief carries the three drift conditions), a shell integration test checks it rather than deferring to the manual step.

### New tests needed

Unit tests (`assets/fbk-scripts/tests/`):

- `test_gates_contracts.py` (new) — drives `fbk/gates/contracts.py` directly. **Every failure-path case asserts the exact teaching string defined in `design/gate-checks.md` (the canonical source for all teaching-error wording) — not merely that a non-empty failure list was returned.** A test that only asserts `len(result) > 0` does not protect the message quality these checks exist to deliver, so it is not acceptable for any message-bearing case.
  - **Structural** — a missing `## Interface contracts` returns the exact "section missing" string; a present-but-empty section (heading present, blank body) returns the exact "present but empty" failure (distinct from missing); the no-contracts sentence passes; a real single `IF-D` entry with all six fields and a covered AC passes (this is the **UV-1 real-entry pass**, distinct from the no-contracts form); an entry missing each of the six fields returns one failure per field naming the entry and field; a non-`IF-[DS]` id prefix returns the exact id-format string; an empty `covers` returns the exact empty-covers string; a `covers` AC absent from `## Acceptance criteria` returns the exact absent-AC string; **each of the three valid `design-ref` forms (a path/anchor, `pre-existing`, `none`) passes individually**, and any other value returns the exact invalid-`design-ref` string; an `## Excluded contracts` entry with an empty rationale or a non-`IF-D` id returns the matching exact string; an `## Uncovered acceptance criteria` entry with an empty rationale returns the exact string — covers AC-01 through AC-07.
  - **Design-anchor** — a design page whose every `IF-D-NN` is carried passes; one neither carried nor excluded asserts the exact "contract listed in design but not carried" string, including the `IF-D-NN` identifier and both resolution paths; an excluded one passes; a missing `design/contracts.md` asserts the exact "page not found" string (and no Python traceback); a design page with no `IF-D` headings passes vacuously — covers AC-08, AC-09.
  - **AC-coverage** — every AC covered passes; an uncovered AC asserts the exact "not covered" string, including the criterion identifier and both resolution paths; an AC excused in `## Uncovered acceptance criteria` passes; **an AC that appears only inside a `signature`/`invariants` field (never in a `covers:` list) is still reported uncovered** — the body-scan trap — covers AC-10.
  - **Seam-coverage** — a seam whose two components both appear in the contracts body passes; one absent component asserts the exact heuristic string, including the clause that states the check is a heuristic; no declared seam passes; **a `→` written inside a prose line under `## Technical approach` (not a checklist item) produces zero seam failures** — the line-anchor guard — covers AC-11.
  - **Module interface** — the four names import from `fbk.gates.contracts`; each returns a list whose **every element is a `str`** (not merely a `list` — `[None]` or `[1]` must fail this assertion) — covers AC-12.
- `test_gates_spec.py` (refactor-then-extend) — a full-path run proving the wiring: a feature spec carrying the no-contracts section plus a matching no-contracts `design/contracts.md` passes; a feature spec with the section absent fails on the structural check; failures from the new checks appear alongside (not instead of) the existing slice/AC checks — covers AC-13.

Shell integration tests (`tests/sdl-workflow/`, matching the existing `test-*.sh` style):

- Instruction-hygiene, enumerated by name: `design-guide.md` states `contracts.md` is required on every feature and routes to the standard leaf; the standard leaf carries the `IF-D-NN` heading schema and the `^## (IF-D-` parse rule — covers AC-14. `feature-spec-guide.md` states `## Interface contracts` is required and routes to the format leaf; the format leaf carries the three section shapes and the blast-radius derivation instruction — covers AC-15. `review-perspectives.md`'s architecture-reviewer brief contains the three drift conditions as informational findings — covers AC-16.
- Reference-integrity: the two new leaves' routed paths resolve, and no installed asset body contains the literal `assets/` source-path prefix (the new leaves and guide edits use installed paths).

### Existing tests impacted

- `test_gates_spec.py` — unconditional wiring means every spec the suite feeds to `main()` must now carry a `## Interface contracts` section **and** a `design/contracts.md` on disk, because a missing section fails the structural check and a missing page fails the design-anchor check independently. Three concrete, known edits (not deferred to implementation):
  1. `_MINIMAL_VALID_SECTIONS` gains the no-contracts `## Interface contracts` section and sentence.
  2. The `run_spec_gate` helper writes a no-contracts `design/contracts.md` into its `tmp_path` **unconditionally**, so every spec it produces is contract-clean — this is the actual file-writer, and it does not create a `design/` directory today.
  3. The inline `SLICES_SPEC_WITHOUT_TS_AC` constant is rebuilt the same way (or converted to the shared helper) so it, too, carries the section and page.
  
  **Correction to an earlier framing:** the failure-path / sentinel tests are *not* unaffected. Because they share `run_spec_gate` and currently write no design page, tests like the testing-strategy-traceability sentinel would otherwise exit non-zero for the wrong reason (the missing page) while their pass/fail assertion stays green — a silent test-intent corruption that edits 2 and 3 prevent. Scope: roughly 14 pass-expecting executions across 11 test methods (one parametrized ×4), but only the two shared edit sites above plus the one inline constant. Affected path: `fbk/gates/spec.py`.
- No other existing test file imports the new `contracts.py` module, so no other suite is touched.

### Test infrastructure changes

- New shared fixtures in `test_gates_contracts.py`: a minimal valid `## Interface contracts` entry string and a minimal valid `design/contracts.md`, both reused by `test_gates_spec.py`. All file I/O uses pytest `tmp_path` — fast and deterministic.
- The exact no-contracts sentence is defined once as a module constant in `contracts.py` and imported by both the check and the test fixtures, so the check that recognizes it and the fixtures that produce it cannot drift by a character (the gate-module slice owns the constant; the wiring slice's fixture migration imports it rather than retyping the literal).

### Mocking justifications

- None. The checks are pure text/file operations; every test uses the real functions against real `tmp_path` files. Default-to-real-collaborator holds — there is no slow, non-deterministic, or unavailable collaborator to justify a mock.

### User verification steps

Run against a throwaway sample feature directory after the gate is wired.

> UV-1: Author a sample spec with one `## Interface contracts` entry whose `covers` lists an acceptance criterion, plus a matching `design/contracts.md` → run `spec-gate` → gate passes.
> UV-2: Remove that entry from the spec without adding an `## Excluded contracts` entry → run `spec-gate` → fails naming the dropped `IF-D-NN`, its design anchor, and the two resolution paths.
> UV-3: Add an acceptance criterion not listed in any `covers` and not in `## Uncovered acceptance criteria` → run `spec-gate` → fails naming that criterion and the two paths.
> UV-4: Replace the section body with the no-contracts sentence and use a no-contracts `design/contracts.md` → run `spec-gate` → passes vacuously.
> UV-5: Declare an integration seam whose two components no contract entry names → run `spec-gate` → raises the heuristic seam failure, labelled as a heuristic.
> UV-6: Move the dropped contract into `## Excluded contracts` with a rationale → re-run `spec-gate` → passes.

Each UV step maps to a `test_gates_contracts.py` case (the gate functions are directly testable, so the end-to-end check is a real gate run). The cross-cutting verification slice drives them as the dogfood pass — covers AC-17.

## Documentation impact

### Project documents to update

- `GLOSSARY.md` — add: **interface contract**, **design contracts page** (`design/contracts.md`), the **`IF-D-NN` / `IF-S-NN`** two-namespace identifier scheme, **blast radius** (the dependent set of a changed module), **design-anchor check**, **contract drift**. Confirm **integration seam** is already present.
- `CHANGELOG.md` — under **Added**: the interface-contracts carrying mechanism (the three spec sections), the four spec-gate checks (`fbk/gates/contracts.py`), the two routed authoring leaves, and the required `design/contracts.md` output; under **Changed**: the spec gate now runs the four contract checks unconditionally, and the architecture reviewer's brief now elevates contract drift.
- `README.md` — review for required updates after the `CHANGELOG.md` edit and discuss proposed changes with the operator before applying (per project convention).

### New documentation to create

- The two routed leaves are themselves the new documentation artifacts: `design-contracts-standard.md` and `interface-contracts-format.md`. No standalone runbook or ADR — the enduring rationale already lives in `docs/decisions-log.md`.

## Acceptance criteria

- AC-01: The structural check reports a missing or empty `## Interface contracts` section as a failure, and accepts the exact no-contracts sentence as satisfying the presence requirement.
- AC-02: The structural check reports one failure per missing required field (`id`, `name`, `signature`, `invariants`, `covers`, `design-ref`) on any contract entry, naming the entry and the field.
- AC-03: The structural check rejects any entry `id` not matching `IF-D-NN` or `IF-S-NN`.
- AC-04: The structural check rejects an empty `covers` list and reports any `covers` identifier absent from `## Acceptance criteria`.
- AC-05: The structural check accepts only the three `design-ref` forms (path/anchor, `pre-existing`, `none`) and rejects any other value.
- AC-06: An `## Excluded contracts` entry with an empty rationale, or an id that is not `IF-D-NN`, is reported as a failure.
- AC-07: An `## Uncovered acceptance criteria` entry with an empty rationale is reported as a failure.
- AC-08: The design-anchor check reports, by name, every `IF-D-NN` heading in `design/contracts.md` that is neither carried into `## Interface contracts` nor excused in `## Excluded contracts`, with the two resolution paths in the message.
- AC-09: A missing `design/contracts.md` yields a "page not found" failure that names the expected path and the design phase, with no Python traceback.
- AC-10: The AC-coverage check reports every acceptance criterion not present in any entry's `covers:` list and not excused in `## Uncovered acceptance criteria`, drawing coverage only from `covers:` lists and never from a body-wide scan.
- AC-11: The seam-coverage check reports every integration-seam component pair not named (case-insensitive substring) by some contract entry, in a message that states the check is heuristic.
- AC-12: `fbk/gates/contracts.py` exposes exactly the four check functions, each returning `List[str]`.
- AC-13: `fbk/gates/spec.py` imports the four functions and calls them in the feature-scope branch after `check_slices`, accumulating their failures into the shared list without short-circuiting, and preserving the gate's existing exit-code and JSON-result contract.
- AC-14: `design-guide.md` states `contracts.md` is required on every feature and routes to the standard leaf only when the feature has contracts; the standard leaf carries the `IF-D-NN` entry schema and the design-page parse rule.
- AC-15: `feature-spec-guide.md` states `## Interface contracts` is a required section and routes to the format leaf; the format leaf carries the three section shapes and the blast-radius derivation instruction.
- AC-16: `review-perspectives.md`'s architecture-reviewer brief carries the three contract-drift conditions as informational findings, with disposition left to the operator.
- AC-17: On a throwaway sample feature, the wired gate fails with a named item for a dropped contract (UV-2), an uncovered criterion (UV-3), and an un-named seam pair (UV-5), and passes once each is carried, covered, excused, or reduced to the no-contracts form (UV-1, UV-4, UV-6).

## Interface contracts

> Dogfooded. These carry the five design-originated contracts from `design/contracts.md` verbatim, plus one spec-minted blast-radius entry for the pre-existing spec-gate contract this feature touches.

- id: IF-D-01
  name: check_interface_contracts_structure
  signature: `check_interface_contracts_structure(spec_text: str) -> List[str]` — reads spec text only; returns failure strings (empty = pass).
  invariants: Pre: `spec_text` is a non-empty string (empty is treated as a missing section). Post: each returned string names the failed item, the defining artifact, and the resolution paths; empty list means every structural sub-check passed. Validates `## Interface contracts` (six fields, id form, non-empty covers, AC existence, valid design-ref), `## Excluded contracts` (IF-D-NN id + non-empty rationale), and `## Uncovered acceptance criteria` (AC-NN id + non-empty rationale).
  covers: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07]
  design-ref: design/contracts.md#if-d-01

- id: IF-D-02
  name: check_design_anchor
  signature: `check_design_anchor(spec_text: str, feature_dir: str) -> List[str]` — reads spec text and the feature directory; returns failure strings.
  invariants: Pre: `feature_dir` is a string; a missing `design/contracts.md` returns one failure rather than raising. Post: one failure per `IF-D-NN` identifier in the design page absent from both `## Interface contracts` and `## Excluded contracts`; empty means all carried or excused. One-directional — spec-originated `IF-S-NN` entries are not failures here.
  covers: [AC-08, AC-09]
  design-ref: design/contracts.md#if-d-02

- id: IF-D-03
  name: check_ac_coverage
  signature: `check_ac_coverage(spec_text: str) -> List[str]` — reads spec text only; returns failure strings.
  invariants: Pre: `spec_text` non-empty. Post: one failure per acceptance criterion found in `## Acceptance criteria` that appears in no entry's `covers:` list and in no `## Uncovered acceptance criteria` entry. Coverage is drawn only from `covers:` lists, never a body-wide scan. A missing `## Acceptance criteria` returns empty (the existing section check already reports it).
  covers: [AC-10]
  design-ref: design/contracts.md#if-d-03

- id: IF-D-04
  name: check_seam_coverage
  signature: `check_seam_coverage(spec_text: str) -> List[str]` — reads spec text only; returns failure strings.
  invariants: Pre: `spec_text` non-empty. Post: no declared seam returns empty; otherwise one failure per extracted component pair where either name is absent (case-insensitive substring) from the `## Interface contracts` body. The message states the heuristic nature explicitly.
  covers: [AC-11]
  design-ref: design/contracts.md#if-d-04

- id: IF-D-05
  name: contracts.py module public interface
  signature: Module `fbk/gates/contracts.py` exports exactly `check_interface_contracts_structure`, `check_design_anchor`, `check_ac_coverage`, `check_seam_coverage`; `spec.py` imports the four by name.
  invariants: Pre: each function accepts only the arguments defined in IF-D-01..04. Post: all four return `List[str]` — the integration contract `spec.py` relies on; changing the return type is contract-evolving. Error: an `ImportError` fails the gate at startup as a traceback, consistent with `fbk.injection` / `fbk.slices`.
  covers: [AC-12, AC-13]
  design-ref: design/contracts.md#if-d-05

- id: IF-S-01
  name: spec-gate CLI / result contract (pre-existing)
  signature: `python3 fbk.py spec-gate <spec-path>` → exit `0` pass / `2` fail; `{"gate": "spec", "result": "pass"|"fail", ...}` JSON to stdout.
  invariants: Pre: a spec path ending `-spec.md` (feature scope). Post: this feature adds four checks to the feature branch but does not change the exit-code or JSON-result contract; existing callers and the dispatcher are unaffected. Regression-protect this contract through the wiring change.
  covers: [AC-13]
  design-ref: pre-existing

## Uncovered acceptance criteria

> Dogfooded. These criteria are served by a documentation change, a reviewer-brief change, or end-to-end verification — not by a named code interface contract.

- id: AC-14
  rationale: Served by the `design-guide.md` edit and the new `design-contracts-standard.md` leaf — a documentation change verified by a shell instruction-hygiene test, not by a code interface.

- id: AC-15
  rationale: Served by the `feature-spec-guide.md` edit and the new `interface-contracts-format.md` leaf — a documentation change verified by a shell instruction-hygiene test, not by a code interface.

- id: AC-16
  rationale: Served by the `review-perspectives.md` architecture-reviewer brief edit — a prompt-asset change verified by a shell test; the drift judgment itself is a reviewer behavior, not a deterministic interface.

- id: AC-17
  rationale: An end-to-end dogfood criterion verified by running the assembled gate over a sample feature (the UV steps); it exercises the contracts already named under §Interface contracts rather than introducing a new one.

## Slices

```yaml
slices:
  - name: contracts-gate-module
    description: New fbk/gates/contracts.py with the four pure check functions and its four-function public interface; unit-tested in test_gates_contracts.py.
    test-discipline: new-contract
    contract: §Interface contracts IF-D-01..IF-D-05; AC-01..AC-12
    covers: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12]
    depends-on: []
    retired-tests: none
  - name: spec-gate-wiring
    description: spec.py imports the four functions and calls them unconditionally after check_slices; existing test_gates_spec.py pass-fixtures migrated to carry the no-contracts section and a design/contracts.md so they survive unconditional activation.
    test-discipline: contract-evolving
    contract: §Technical approach "The gate module and its wiring"; AC-13; IF-S-01
    covers: [AC-13]
    depends-on: [contracts-gate-module]
    retired-tests: "test_gates_spec.py pass-expecting fixtures (_MINIMAL_VALID_SECTIONS string and the tmp-feature-dir helper) — updated, not deleted, to include the no-contracts ## Interface contracts sentence and a no-contracts design/contracts.md"
  - name: design-contracts-standard-leaf
    description: New design-contracts-standard.md leaf (the design/contracts.md schema, identifier scheme, parse rule); design-guide.md gains the required-page bullet and the conditional route.
    test-discipline: new-contract
    contract: §Technical approach "Where the new format guidance lives" + "Neighboring-asset edits"; AC-14
    covers: [AC-14]
    depends-on: []
    retired-tests: none
  - name: spec-contracts-format-leaf
    description: New interface-contracts-format.md leaf (the three section shapes, design-ref forms, ordering, blast-radius derivation); feature-spec-guide.md gains the required-section note and the conditional route; GLOSSARY terms added.
    test-discipline: new-contract
    contract: §Technical approach "Where the new format guidance lives"; §Documentation impact; AC-15
    covers: [AC-15]
    depends-on: []
    retired-tests: none
  - name: review-drift-brief
    description: review-perspectives.md architecture-reviewer brief gains the three informational contract-drift conditions.
    test-discipline: new-contract
    contract: §Technical approach "Neighboring-asset edits"; AC-16
    covers: [AC-16]
    depends-on: []
    retired-tests: none
  - name: dogfood-verification
    description: End-to-end dogfood over a throwaway sample feature — the six UV steps exercise drop, uncovered-AC, un-named-seam, no-contracts, and excuse paths through the wired gate. Test-only; implementation exists across the other slices.
    test-discipline: cross-cutting
    contract: §Testing strategy "User verification steps"; AC-17
    covers: [AC-17]
    depends-on: [contracts-gate-module, spec-gate-wiring]
    retired-tests: none
```

**Wave ordering** (build-order `depends-on` only):

- **Wave 1** (4, parallel — no build-order predecessors): `contracts-gate-module`, `design-contracts-standard-leaf`, `spec-contracts-format-leaf`, `review-drift-brief`.
- **Wave 2** (1): `spec-gate-wiring` — imports the four functions from `contracts-gate-module`.
- **Wave 3** (1): `dogfood-verification` — runs the assembled, wired gate end to end.

The three documentation slices carry only a *soft* runtime dependency on the gate (the leaves describe shapes the gate reads), not a build-order edge — those shapes are pinned in §Interface contracts and the design pages, so the slices author and test independently.

## Open questions

None.

## Dependencies

- **Slice-block hygiene fix (landed).** The spec gate's canonical slice vocabulary is `new-contract | contract-preserving | contract-evolving | cross-cutting` (the surviving shape named in `prd.md`). This spec's `## Slices` block uses it. Note: the installed `feature-spec-guide.md` and the `/fbk-spec` skill text still show the older `unit | integration | e2e | contract` list — a stale-doc drift to reconcile separately; it does not affect this gate run.
- **Existing `AC-NN` convention.** The AC-coverage check reads acceptance-criterion identifiers from `## Acceptance criteria` using the convention the spec gate already enforces.
- **Existing integration-seam declaration block.** The seam-coverage check reads the existing required `## Technical approach` checklist format (`- [ ] A → B: ...`).
- **Spec review runs.** Drift elevation, signature-correctness, mislabel detection, and the hollow-carry guard all depend on spec review actually running — a load-bearing assumption named in `prd.md`.
- **Python / pytest test infrastructure** under `assets/fbk-scripts/tests/`, and the `fbk.py` dispatcher (`spec-gate` already registered; no new dispatcher entry needed — `contracts.py` is imported by `spec.py`, not invoked directly).

---

## Decisions resolved during scoping

- **Gate activation is unconditional.** The four checks run on every feature spec rather than behind a backward-compat hinge. The operator chose strongest enforcement, accepting that every in-flight feature spec must carry the `## Interface contracts` section (one sentence suffices) and a `design/contracts.md`, and that the existing `test_gates_spec.py` pass-fixtures are migrated to match. This feature's own spec is exempt only because the checks do not exist at its gate time.
- **New format guidance lives in two routed leaves, not folded into the guides.** Applying the progressive-disclosure rule ("every instruction in a loaded asset must apply every time the asset loads"), the detailed entry schemas apply only when an author has contracts to write — a sub-condition — so they belong in separately-routed leaves gated by that condition, with the guides keeping only the always-required minimal instruction plus a conditional route. Two leaves, not one, because the design-page schema and the spec-section schema are different shapes valid under different parent routes.
- **This spec dogfoods the new sections.** It carries the five design contracts plus one spec-minted blast-radius entry under `## Interface contracts`, and routes the four documentation/process criteria through `## Uncovered acceptance criteria` — making the document the first worked spec-layer example of the format it defines.
