# Interface contracts — Spec review (SDL Stage 2)

Perspectives: Architecture, Builder (over-engineering/pragmatism), Quality (testing strategy)

Reviewed: 2026-06-09. Prior-stage spec gate: **pass** (nine sections + slices). Mode: discussion — three council perspectives reviewed independently against the spec, the six design pages, and the real target code (`fbk/gates/spec.py`, `tests/test_gates_spec.py`), then synthesized here.

> **What's solid (so it isn't lost in the findings).** The module-boundary decision is correct: a new `fbk/gates/contracts.py` with four pure functions mirrors the code-review-gate precedent, and every helper and call site the algorithms depend on (`heading_line`, `section_body`, `check_section`, `check_slices`, the `feature_dir` already in scope) was verified to exist in `spec.py` with the claimed behavior. The accumulate-into-`fails`-no-short-circuit pattern and the module-top-level import precedent (`fbk.injection` / `fbk.slices`) are genuinely matched. The four core algorithms are specified to the character — an implementer would not have to invent the happy path. The spec's own dogfooding is internally clean: all 17 ACs are accounted for (AC‑01…13 covered, AC‑14…17 excused), the five `IF-D` ids match the design page, and both declared seams resolve — if the gate existed and ran on this spec, it would pass. The four-check split and the two-leaf progressive-disclosure split are right-sized, not over-engineered. The zero-mock claim is true.
>
> The findings below are about the *edges*: inconsistencies between the documents an implementer must reconcile, edge cases the test plan names in the design but omits from the strategy, and one testing-strategy claim that is simply wrong under unconditional activation.

---

## Threat model determination

**Decision: no threat model.** Rationale: the gate reads local, operator-authored spec and design files. There are no new trust boundaries, no auth/authz, no data storage, and no external API or network interaction. The one mild angle — spec text as untrusted input to a regex parser — is bounded by the existing injection-detection pass and by the fact that specs are operator-authored, not adversary-supplied. Security concerns, if any, surface through normal review. (Operator confirmed during this review.)

---

## Architectural soundness

### Integration points exist and patterns are matched — verified
**Severity: informational. Category: architectural soundness.**
Every helper and call site the design's algorithms reference exists in `fbk/gates/spec.py` with the claimed behavior: `heading_line` (case-insensitive `startswith`), `section_body` (terminates at the next `## `), `check_section`, `check_slices`, and the `if scope == "feature":` branch with `feature_dir = pathlib.Path(spec_path).parent` already in scope. The four `fails.extend(...)` calls after `check_slices` match the existing accumulate-no-short-circuit pattern, and the module-top-level import precedent is real. The `IF-S-01` claim that the CLI/JSON/exit-code contract is preserved holds — the new checks only append to `fails` before the existing `if fails:` block and touch neither exit codes nor the result dict. Caller sweep (dispatcher, the two skills, the test suites) is clean: nothing breaks beyond the documented fixture migration.

### Multi-section reads are unstated — an implementer can silently get empty escape-hatch sets
**Severity: important. Category: architectural soundness.**
`section_body` returns content only up to the *next* `## ` heading, so the body of `## Interface contracts` does **not** contain `## Excluded contracts` or `## Uncovered acceptance criteria`. Three of the four checks must read multiple sibling sections (structural reads all three; design-anchor reads Interface + Excluded; AC-coverage reads Acceptance + Interface + Uncovered). The algorithms in `design/gate-checks.md` imply this but never state it — the structural check's prose ("validated by this same function… proceed to the escape-hatch sections below") reads as if one body holds all three. An implementer who parses escape-hatch entries out of the Interface-contracts body gets an empty set, which makes every empty-rationale test pass when it should fail. **Resolution:** add an explicit step to each multi-section check naming the separate `heading_line` + `section_body` call per section. Location: `design/gate-checks.md` Checks 1, 2, 3.

### Section-ordering independence is assumed but never asserted
**Severity: important. Category: architectural soundness.**
The checks reuse `heading_line`, whose `startswith` semantics are safe for the one dangerous pair (`## Acceptance criteria` vs `## Uncovered acceptance criteria` — the latter does not start with the former, confirmed). But nothing guarantees section ordering, and `section_body` terminates at the next `## `. If an author places `## Uncovered acceptance criteria` before `## Acceptance criteria`, or introduces a stray `## ` line, the `covers`-AC-existence sub-check reads the wrong body. The design names ordering only as an author convention, not as a gate precondition. **Resolution:** add an order-independence test (escape-hatch section before `## Acceptance criteria` still validates), and state section-ordering independence as a gate invariant in `design/gate-checks.md` Checks 1 and 3.

### No-`## IF-` -heading guard in the spec body
**Severity: informational. Category: architectural soundness.**
The spec-side entries are deliberately YAML-block list items, not `## IF-D-NN` sub-headings — the right call, because a `## ` per entry would make `section_body` truncate the section at the first entry. Nothing rejects an author who mistakenly copies the design-page heading form into the spec; that silently truncates the contracts section and produces a confusing "missing field" cascade. **Resolution (breakdown discovery):** consider a teaching failure for a `## IF-` heading found inside the spec body.

### Em-dash name convention is load-bearing but unenforced
**Severity: informational. Category: architectural soundness.**
`check_design_anchor` extracts the entry name from `## IF-D-NN — <name>` (em-dash U+2014), falling back to "unnamed". A design author using a hyphen or colon produces "unnamed" in every teaching message — messages still function, names degrade silently. **Resolution:** either enforce the em-dash in the design-contracts-standard leaf with a checkable rule, or accept graceful degradation explicitly. Location: `design/contracts-standard.md` entry schema.

### In-flight spec migration cost is absent from Dependencies
**Severity: informational. Category: architectural soundness.**
Unconditional activation is the correct structural call (a backward-compat hinge would create the bimodal parallel path the gate should avoid). The cost it pays: every in-flight feature spec across other branches must gain a `## Interface contracts` section and a `design/contracts.md` on merge. That migration cost is not named in the spec's Dependencies section. **Resolution:** add a one-line Dependencies note so the team inheriting in-flight specs isn't surprised at merge.

---

## Over-engineering / pragmatism

### Core algorithms are buildable directly — informational
**Severity: informational. Category: over-engineering / pragmatism.**
The four algorithms are buildable straight from `design/gate-checks.md`: parse rules, regexes, set logic, and error strings are pinned. The four-check split is right-sized (distinct input signatures, failure vocabularies, AC clusters; merging would force the design-anchor's filesystem read into otherwise-pure functions). The two-leaf split is justified — the design-page schema and the spec-section schema are genuinely different shapes under different parent routes; a shared leaf would violate the progressive-disclosure rule. Keep both.

### The no-contracts sentence match mode is unpinned and the literal is duplicated
**Severity: important. Category: over-engineering / pragmatism.**
`design/gate-checks.md` Check 1 step 4 says the section is valid "if body **contains** the no-contracts sentence." "Contains" vs "equals-after-strip" is load-bearing and ambiguous: a substring test would let an entry-form section that mentions the sentence in prose falsely pass; an equality test rejects a section with the sentence plus a trailing note. Separately, the exact sentence (`No new or changed contracts in this feature.`) is carried as a string literal in the check, in the spec fixtures, and in the design pages independently — if any drift by one character, the wired gate rejects fixtures that pass locally (surfacing only in Wave 3). **Resolution:** pin it as `body.strip() == "No new or changed contracts in this feature."` in `gate-checks.md` step 4, and define the literal once as a module constant in `contracts.py` that the test helper imports — so the check and the fixtures cannot drift.

### The IF-D / IF-S namespace is a readability decision, not gate-enforced collision safety
**Severity: informational. Category: over-engineering / pragmatism.**
The two-namespace scheme is defensible for human legibility — a reader instantly sees which phase minted an id. But the spec sells it as structurally necessary ("collisions are impossible," "structurally separate"), and the gate never checks cross-namespace uniqueness: the structural check accepts both prefixes, and the design-anchor check filters to `IF-D` only because it reads the design page (which only ever holds `IF-D`), not because the prefix carries enforced weight. **Resolution:** keep the scheme for its real readability payoff, but reframe the rationale honestly — it is a legibility choice, not a collision-safety property the gate enforces. Location: `design/contracts-standard.md` "Identifier scheme."

### Seam heuristic: false-positive guidance is thin
**Severity: important. Category: over-engineering / pragmatism.**
The seam-coverage substring scan is case-insensitive and unanchored, so a component name like `main` matches `domain`/`remainder` anywhere in the contracts body (a silent false negative the operator never sees), and a seam whose contract entry names the components by a different token than the seam declaration false-positives (wasting operator time). Shipping a deliberately-approximate check is the pragmatic call for one AC — but "this is a heuristic" alone doesn't tell the operator *which* failure mode they're looking at. **Resolution:** keep the check; expand the failure message to say specifically that the match looks at component *name tokens* — "if your contract entry names this seam's components by a different token, the seam is covered and you can ignore this." Also document in `gate-checks.md` Check 4 that a colon inside a component name truncates extraction (group-2 is non-greedy to the first colon), so the implementer doesn't "fix" it with a greedier regex that swallows the interface description.

### Slice graph is correct; one shared-constant dependency the depends-on edges miss
**Severity: important. Category: over-engineering / pragmatism.**
The six slices and three-wave ordering are buildable; the build-order edges are right. But the test-fixture migration in `spec-gate-wiring` (Wave 2) and the dogfood setup in `dogfood-verification` (Wave 3) both depend on the exact no-contracts sentence defined by `contracts-gate-module` (Wave 1). This isn't a cycle, but it is a shared-constant dependency not expressed in the graph: if the check and the fixtures carry the literal independently, a one-character drift passes locally and fails only when the wired gate runs. **Resolution:** note in `spec-gate-wiring` that the test helper imports the no-contracts sentence from the single module constant in `contracts.py` (ties to the duplication finding above).

---

## Quality: testing strategy and impact

### Testing-strategy section coverage — present
**Severity: informational. Category: quality.**
All three required categories are present and specific: New tests needed (unit + shell), Existing tests impacted, Test infrastructure changes, plus Mocking justifications ("none", justified) and User verification steps. AC-to-test traceability is complete: every one of AC‑01…17 has a named home. The zero-mock claim was verified true for all four checks and the wiring test (the `audit.log_event` calls in `spec.py` are wrapped in `try/except… pass`, so they cannot force a mock).

### The test-fixture migration claim is wrong under unconditional activation — sentinel tests silently corrupt
**Severity: blocking. Category: quality.**
The spec (line 135) claims "the failure-path tests (missing/empty section, open-question, slice-shape) are unaffected." Verified against the real test file: this is materially wrong.
- `run_spec_gate` (the actual writer, `test_gates_spec.py:67`) writes only the spec file and optionally `behavior-inventory.yaml` — it creates **no** `design/` directory. Under unconditional activation, every pass-expecting test routed through it newly fails the design-anchor "page not found" check, independent of the structural check.
- `_MINIMAL_VALID_SECTIONS` has no `## Interface contracts` section, so every spec built from it newly fails the structural check.
- `SLICES_SPEC_WITHOUT_TS_AC` (an inline duplicate, lines 81–96) also lacks the section and routes through the same helper. The sentinel `test_slices_spec_without_ac_in_testing_strategy_fails` still exits 2 — but now *also* because of the missing section and missing page, not the testing-strategy-traceability gap it is meant to isolate. The assertion stays green while the test stops testing what it claims; this corruption is invisible to CI.

**Resolution:** enumerate the three concrete migration edits in the spec now (the "enumerated during implementation" hedge is unnecessary — they're knowable): (1) add the no-contracts section + sentence to `_MINIMAL_VALID_SECTIONS`; (2) have `run_spec_gate` write a no-contracts `design/contracts.md` into `tmp_path` **unconditionally**, so all specs it produces are contract-clean; (3) rebuild `SLICES_SPEC_WITHOUT_TS_AC` the same way or convert it to the shared helper. Correct the line-135 claim: the failure-path sentinel tests *are* affected because they share the helper and the no-design-page condition. (Note for scoping: the real blast radius is ~14 pass-expecting executions across 11 methods — one parametrized ×4 — but only two edit sites, the helper and the constant.)

### Exact teaching-error strings are inconsistent across the source documents
**Severity: blocking. Category: quality.**
Message quality is the entire point of these checks, and the strategy requires asserting the exact teaching string per check — but the strings disagree between the design pages, so the assertions cannot be written deterministically:
- "Section missing": `gate-checks.md:29` → "Carry at least one entry **or the** no-contracts sentence from design/contracts.md." vs `design/contracts.md:8` → "Carry at least one entry **(or a)** no-contracts sentence) from design/contracts.md."
- "Page not found": `gate-checks.md:61` → "run /fbk-design `<feature-name>` to produce it before running the spec gate." vs `design/contracts.md:15` → "run the design phase or rerun /fbk-design to produce it."

**Resolution:** make `design/gate-checks.md` the single source of truth for every teaching string (it is the "what to implement" page), reconcile `design/contracts.md` to match, and have the spec's Testing strategy state "assert the exact string from gate-checks.md." Without this the implementer asserts whichever doc they read last, against a message that may not be the one the operator sees.

### Three named edge cases have no test in the strategy
**Severity: important. Category: quality.**
Each is required behavior in `design/gate-checks.md` but absent from the strategy's test list (spec lines 121–126):
- **Present-but-empty `## Interface contracts`** (heading present, blank body) — `gate-checks.md:13` makes this a distinct failure from "section missing"; the strategy tests "missing" and "no-contracts passes" but never the blank-body path (a likely copy-paste-skeleton mistake).
- **The three valid `design-ref` forms each *pass*** — the strategy tests "an invalid design-ref fails" but never asserts that a path/anchor, `pre-existing`, and `none` each individually pass. A check that rejected everything would satisfy the stated test. This is a negative test missing its positive counterpart.
- **A `→` in prose yields no phantom seam** — `gate-checks.md:89` anchors seam extraction to line start precisely to avoid this; the strategy never tests it. This is the exact false-positive class that makes a heuristic check annoying enough to be disabled.

**Resolution:** name these three cases in the New-tests list.

### Escape-hatch cross-check between the two checks that share a section parser
**Severity: important. Category: quality.**
A validly-excluded `IF-D-NN` must simultaneously satisfy the structural check (accepts the entry) and the design-anchor check (counts it as excused). The structural check parses `## Excluded contracts` with `^\s*-\s+id:\s+(IF-D-[0-9]{2,})`; the design-anchor check extracts "all `id:` values matching `IF-D-[0-9]{2,}`". If those two parsers diverge, an entry can satisfy one and not the other. The strategy tests each side separately but never the agreement. **Resolution:** add one case feeding a single spec text to both functions and asserting a validly-excluded `IF-D-NN` produces zero failures from each.

### Shell instruction-hygiene tests repeat the grep-the-literal anti-pattern
**Severity: important. Category: quality.**
As specified ("a guide names the required section, a guide routes to its leaf, a leaf carries the schema"), the shell tests will be written as literal-phrase greps — the same brittleness this project already has retrospectives on (the SDL dedup "grep-the-prose" test). A grep for "Interface contracts is required" passes whether or not the routing works. **Resolution:** specify these as *structural* checks: (a) "routes to its leaf" asserts the routed path resolves to an existing file (reuse the path-resolution logic already in `tests/sdl-workflow/test-reference-integrity.sh`), not that prose mentions the leaf; (b) "leaf carries the schema" asserts the leaf contains the parse-rule token `^## (IF-D-` **and** all four field names as a set, so a leaf naming three of four fails; (c) AC‑16's three drift conditions assert three *distinct* anchor strings (one per condition) so a pasted duplicate fails — or state plainly that AC‑16 is presence-checked plus operator-inspected and stop claiming the shell test verifies behavior.

### Reference-integrity is already covered repo-wide — don't duplicate
**Severity: informational. Category: quality.**
The spec proposes a new shell test for "routed paths resolve" and "no `assets/` source-path prefix in installed bodies." Both are already enforced repo-wide by `tests/sdl-workflow/test-reference-integrity.sh` (path resolution; `assets/`-prefix leak), and its `find` walk picks up the two new leaves automatically. **Resolution:** drop the duplicate; keep only the leaf-specific schema-content assertions the generic test doesn't cover.

---

## Testing strategy coverage

The spec's testing-strategy section addresses all three required categories; this records what the review found in each (the defects are detailed under the perspective sections above and the Test Strategy Review below).

- **New tests needed** — covered. `test_gates_contracts.py` (unit, driving the four checks directly across structural / design-anchor / AC-coverage / seam / module-interface cases) and shell instruction-hygiene tests under `tests/sdl-workflow/`. Gap: several message-quality cases are described too loosely to guarantee they assert the exact teaching string (see Test Strategy Review), and three named edge cases (present-but-empty section, each valid design-ref form passing, mid-prose arrow) lack a case.
- **Existing tests impacted** — covered but mischaracterized. `test_gates_spec.py` is refactor-then-extended. The spec's claim that the failure-path tests are unaffected is wrong under unconditional activation — the shared `run_spec_gate` helper writes no `design/contracts.md`, so the sentinel tests fail for the wrong reason (blocking finding above). No other suite imports the new module.
- **Test infrastructure changes** — covered. New shared fixtures in `test_gates_contracts.py` (a minimal valid contract entry and a minimal `design/contracts.md`), reused by `test_gates_spec.py`; all file I/O via pytest `tmp_path`. Recommend the no-contracts sentence be a single shared module constant so the check and the fixtures cannot drift. Mocking: none, justified and verified true.

## Test Strategy Review

Independent checkpoint-1 review by the test-reviewer (no access to the council discussion). **Initial verdict: needs-revision; re-review after revision: accepted.** Four blocking findings, all since resolved in the revised spec — see "Resolution" below. The reviewer confirmed the strong parts: both declared code seams have named end-to-end tests using real `tmp_path` files (no mocking across the boundary); the three prompt-asset chains are legitimately out of the code-seam block (verified by shell hygiene tests + dogfood, a valid "not mechanically assertable" override); no runtime-dependent mock-only risk; and all 17 ACs map to a named test. The defects are about *assertion strength* — several message-quality tests are described in a way that permits a non-asserting implementation.

- **Strategy defect — UV-1 has no specifically named test.** Affects AC‑17. The strategy's blanket "each UV step maps to a `test_gates_contracts.py` case" is not a per-step mapping. UV-1 (gate passes over a spec with a *real* entry, a real covered AC, and a matching design-page identifier) is covered only by the implicit combination of individual unit tests; the full-path `test_gates_spec.py` case it points to uses the no-contracts form, not a real entry. **Change:** name the specific test that exercises a real-entry full pass.

- **Silent-failure-shaped test — "an uncovered AC fails."** Affects AC‑10. As described, the test verifies only that a failure is returned, not that the message names the specific AC and carries the two resolution paths the design pins. Implemented as `assert len(result) > 0`, it passes even when the message content is wrong. **Change:** assert the exact teaching string (the AC identifier + both resolution paths).

- **Advisory-language message tests — design-anchor and seam-coverage.** Affects AC‑08, AC‑09, AC‑11. "Named teaching failure with the design name and the two resolution paths" and "heuristic failure stating its nature" describe desired content without committing to assert it. A substring check on just the identifier prefix would miss a dropped resolution path or a dropped heuristic label. **Change:** assert the exact strings from `gate-checks.md` (which ties directly to the blocking error-string-divergence finding above — the canonical strings must exist first).

- **Module-interface assertion too weak — `list` vs `List[str]`.** Affects AC‑12. The test is described as "each returns a `list`"; the contract is `List[str]`. `[None, None]` or `[1, 2]` satisfies the described assertion but violates the contract. **Change:** assert the return is a list whose every element is a string.

The structural check's description does set the right bar in one place ("returns the **exact** 'section missing' failure") — the fix is to apply that exact-string discipline uniformly across all message-quality tests, which is only possible once the error-string divergence (blocking finding above) is resolved.

**Resolution (applied 2026-06-09).** The spec's testing strategy now opens with a blanket rule that every failure-path case asserts the exact teaching string from `gate-checks.md` (not a non-empty return); the UV-1 real-entry pass, the present-but-empty section, each valid `design-ref` form, and the mid-prose-arrow guard are now named cases; the module-interface test now asserts every element is a `str`. The re-review confirmed all four findings resolved and returned **accepted**. The test-reviewer added one non-blocking note: the reference-integrity shell test (path-class enforcement) traces to no acceptance criterion — a missing AC in the spec, not a strategy defect; recorded as informational for the breakdown.

---

## Verification gate — structural prerequisites

- Findings from all three classified perspectives present: **yes** (Architecture, Builder, Quality).
- Each finding carries a severity (blocking / important / informational): **yes**.
- Threat-model determination recorded (decision + rationale): **yes** — no threat model.
- Testing-strategy coverage entries for all three categories (new tests / impacted / infrastructure), empty categories explicit: **yes** — all present; mocking explicitly "none" with justification.

## Overall result: **pass** (initial fail resolved by revision, 2026-06-09)

The initial pass returned fail — the test-reviewer returned needs-revision and the council raised two blocking findings. The operator chose to revise immediately; all six blocking findings were addressed in the spec and design pages and the test-reviewer re-review returned accepted. The findings below are kept as the record; their resolutions are noted inline.

- **Blocking: 6 — all resolved.**
  - *Council (resolved by direct edits):* (1) the testing-strategy "failure-path tests unaffected" claim, wrong under unconditional activation — **resolved:** the spec now enumerates the three concrete test-helper edits (no-contracts section into `_MINIMAL_VALID_SECTIONS`; `run_spec_gate` writes a no-contracts `design/contracts.md` unconditionally; rebuild `SLICES_SPEC_WITHOUT_TS_AC`) and corrects the claim, naming the silent sentinel-corruption it prevents. (2) the divergent teaching-error strings — **resolved:** `gate-checks.md` is now declared the single source of truth for every teaching string, the two (actually four) divergent literals in `design/contracts.md` were aligned or converted to references, and the implementation defines each message as a shared module constant.
  - *Test-reviewer (resolved by revision, re-review accepted):* (3) UV-1 unnamed test; (4) silent-failure-shaped uncovered-AC test; (5) advisory-language message tests; (6) `list` vs `List[str]`. **Resolved:** the strategy now mandates exact-string assertions across all message-quality cases, names the UV-1 real-entry pass, and tightens the module-interface assertion to element-type.
- **Important: 6 — open, carried to breakdown.** Multi-section `section_body` reads unstated; section-ordering independence unasserted; seam-heuristic false-positive guidance thin (colon-truncation doc note); escape-hatch cross-check between the two checks sharing a parser; shell tests should be structural not grep-the-literal. (The "three edge cases untested" and "no-contracts literal duplicated" important findings were folded into the revision alongside the blocking fixes.) These do not block breakdown but the breakdown should absorb them as task-level detail.
- **Informational: 8** — integration points verified solid; core algorithms buildable; four-check and two-leaf splits right-sized; IF-D/IF-S namespace is readability not gate-enforced collision-safety; em-dash convention unenforced; in-flight migration cost absent from Dependencies; reference-integrity already covered repo-wide; the path-class shell test traces to no AC (test-reviewer note).

None of the findings was design rework — the resolution was reconciling documents and tightening test descriptions, exactly as scoped.

---

## Pre-existing test failures (MERGE BLOCKER — not introduced by this feature)

Captured at implementation baseline (2026-06-09), before any interface-contracts work. These four shell tests already fail on the branch base; they are excluded from the regression baseline (only passing tests enter it). **They do not block implementation, but must be fixed before merge.**

1. **`tests/sdl-workflow/test-instruction-hygiene-scope.sh`** — 1/10 fails. Real content drift: `ai-failure-modes.md` contains 15 numbered items; the test asserts exactly 14. Needs reconciliation of the doc or the test. Unrelated to interface-contracts.
2. **`tests/installer/test-install.sh`** — 2/14 fail. The two pyyaml-missing scenarios can't reproduce in this environment (pyyaml is installed). Likely environment-only; re-verify on a clean checkout.
3. **`tests/installer/test-refactored-sdl-install.sh`** — 14/16 fail. Read-only `~/.claude` sandbox prevents the installer from writing. Environment; re-verify where the install target is writable.
4. **`tests/installer/test-upgrade-uninstall.sh`** — 1/13 fails (uninstall removes empty fbk-prefixed dirs). Same read-only-fs cause.

Action before merge: fix #1 (genuine), and re-run #2–#4 in a writable environment to confirm they are environment artifacts rather than regressions.

---

## Wave 2 escalation — circular import between spec gate and contracts module

**Task:** task-10 (wire contract checks into spec.py), attempt 1.
**Check failed:** pytest collection — `ImportError: cannot import name 'heading_line' from partially initialized module 'fbk.gates.spec'` (circular import).
**What happened:** task-02's `contracts.py` imports `heading_line`/`section_body` from `fbk.gates.spec`. task-10 wiring makes `spec.py` import `contracts.py`, creating a module-init cycle. task-10's agent correctly halted under the Pause-on-Scope-Discrepancy rule and reverted spec.py to the clean red state (29 passed, 2 failed).
**Root cause classification:** Compilation gap (bordering spec gap) — the breakdown did not anticipate that the two text-section helpers shared by `spec.py` and `contracts.py` needed to live in a neutral module. task-02 reasonably reused spec.py's helpers; the dependency only became cyclic at wiring time.
**Resolution (discovered work, decomposed):** Extract `heading_line` and `section_body` into a new neutral module `fbk/gates/sections.py`; point both `spec.py` and `contracts.py` at it. Then task-10's two edits apply as written. This is the proper acyclic fix (no lazy-import workaround). Counts as escalation attempt 1 for task-10.

---

## Wave 2 — second discovered defect: AC-coverage vs. no-contracts form (spec inconsistency)

**Surfaced by:** wiring the gate broke 15 existing `test_gates_spec.py` tests + 1 `test_gates_contracts.py` unit test.
**The inconsistency:** the `check_ac_coverage` invariant prose (IF-D-03) says every AC must be covered or excused, no exception — but UV-3 and UV-4 together specify: enforce AC coverage when contracts exist (UV-3 fails on an uncovered AC), exempt it when the spec is reduced to the no-contracts form (UV-4 "passes vacuously"). The two readings cannot both hold for one function. UV-3+UV-4 are the authoritative intent.
**Resolution:** (1) `check_ac_coverage` now returns `[]` (vacuous pass) when `## Interface contracts` is the no-contracts sentence — mirrors the structural check's existing predicate. (2) The one unit test that contradicted UV-4 (`test_check_ac_coverage_returns_list_of_str`, which used the no-contracts form to manufacture a failure) was re-fixtured to use a real-contract spec with an uncovered AC, preserving its return-type-check intent.
**Spec correction needed (record for fbk-improve / spec edit):** the IF-D-03 invariant prose should state the no-contracts vacuous-pass explicitly so the invariant and the UV steps agree.
**Root cause classification:** Spec gap (internal inconsistency between an interface invariant and the UV steps).

## Wave 2 — third discovered defect: shell gate-tests blast radius (spec impact-analysis gap)

**Surfaced by:** wiring broke three shell tests that invoke the real spec-gate over static fixtures — `test-e2e-spec-gate-parity.sh`, `test-gate-output-spec-python.sh`, `test-spec-validator.sh`.
**The gap:** the spec's "Existing tests impacted" section reasoned "no other test file imports `contracts.py`, so no other suite is touched." That logic only catches suites that *import* the module; it missed every test that exercises the gate end-to-end via its CLI over fixture specs. Unconditional activation makes those fixtures (no `## Interface contracts` section, no `design/contracts.md`) fail the gate.
**Resolution:** migrated the four pass-expecting feature-scope fixtures (`valid-spec.md`, `injection-attempt-spec.md`, `legitimate-html-spec.md`, `unicode-spec.md`) to carry the no-contracts section, and added a single shared no-contracts `tests/fixtures/specs/design/contracts.md` (the gate derives feature_dir as the spec's parent, so one page serves the dir). Negative fixtures left unchanged — their assertions are exit-code/phrase-based and unaffected. Golden files still match (gate still returns pass). All three tests green.
**Root cause classification:** Spec gap (incomplete impact analysis — the impact rule keyed on imports, not on gate-behavior consumers).

---

## Wave 3 — observation: multi-line invariants block parsing (UNCONFIRMED)

During the dogfood, the test agent reported that a multi-line `invariants:` block (YAML sub-bullets) caused the contract-entry parser to treat the `covers` field as missing, and worked around it by using single-line `invariants` values. A direct reproduction (a contract entry with sub-bullet invariants whose sub-lines contain colons, e.g. `- Pre: ...`) did NOT reproduce a covers-missing failure — `check_interface_contracts_structure` returned no failures. So the exact trigger is uncharacterized and this is NOT a confirmed defect.

What is true: the field regex `_FIELD_RE = r"^\s+(\S[^:]*?):\s*(.*)"` is permissive across newlines, and the canonical entry format (the spec's own dogfood entries, the format leaf) uses single-line field values. Recommendation for follow-up (not this run): add a targeted unit test pinning the parser's behavior on multi-line block values, and decide whether to support or explicitly reject them. Out of scope here — no AC requires multi-line invariants.
