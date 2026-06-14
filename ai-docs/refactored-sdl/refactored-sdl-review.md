Perspectives: Architecture, Pragmatism, Quality, Measurability, Security

# Refactored SDL — Spec Review

**Initial result: FAIL** — 13 blocking, 11 important, 8 informational; independent checkpoint-1 test-strategy review FAIL.

**Resolution (revision 2): PASS.** The spec was revised to address every blocking finding; it passes `spec-gate`. A focused re-review (Architect, Guardian, and the independent test reviewer — the perspectives that raised the blockers) confirmed all 13 prior blockers resolved against the real code, and the **independent checkpoint-1 test reviewer flipped to PASS** with full schema compliance. The re-review surfaced one further blocking edge (the code-review stage-ordering contract was testable but left UV-only) plus a few important edges (a negative test case for the new shadow-test/list-lock mechanic; one omitted impacted shell test `test-code-review-structural.sh`; a structured return for `verify_manifest`; grounded agent tool lists; a precise uninstall observable) — all addressed in revision 2. Builder's and Security's revision-1 findings (slice-shape over-enforcement, code_review.py separation, injection-detection parity, the test-reviewer refactor reclassification) were folded into the revision. The original findings are retained below as the record of what the review caught.

Near-full council (Architect, Builder, Guardian, Analyst, Security) plus the independent test reviewer. The reviews converged: the spec's domain reasoning was sound, but several "extend" claims understated rewrites of shipped gate code, two gate integrations contradicted the existing checks they claimed to preserve, and the testing strategy had real coverage holes — all concentrated in the gate-script surface (the actual executable code) and all now resolved.

---

## Architectural soundness

### [blocking] The test-lock manifest is a flat auto-discovered scan product, not a per-entry record — AC-07 is a rewrite, not an "extend"
**Category:** Architectural soundness. The shipped `fbk/gates/test_hash.py` produces `{"files": {path: hash}}` by rglob auto-discovery; there is no per-entry object to hang `slice`/`test-discipline` on, and no acceptance step that "adds" a test — the gate discovers files, it is not told about them. AC-07 ("each entry records path, sha256, slice, test-discipline") plus locking *named pre-existing* tests (which live in the project test tree, not the feature dir) requires a list-driven lock mode and a changed manifest shape — a rewrite of `compute_hashes`/`create_manifest`/`verify_manifest`, not a field addition. Also a naming divergence: the design and PRD call this `test-lock-manifest.json`; the shipped file is `test-hashes.json`. **Resolution:** state whether the flat map is restructured (and that the verify loop and every `test_gates_test_hash.py` assertion change) or whether slice metadata lives in a sidecar keyed by path; name the single file the runtime uses; reclassify the module-touch policy for `test_hash.py` from "extend" to "refactor-then-extend"; correct the "new fields optional/back-fillable" claim in §Existing tests impacted (it is false against the current flat shape).

### [blocking] The breakdown gate's AC-coverage invariant contradicts two of the four slice shapes; "existing checks preserved" is internally inconsistent with AC-05
**Category:** Architectural soundness. `fbk/gates/breakdown.py` enforces, per AC, a test task AND (unless `category == "corrective"`) an impl task, plus "every code-modifying task has a corresponding test task." The **cross-cutting** shape is test-only (no impl) and **contract-preserving** is impl-without-a-new-test — both trip the existing checks. You cannot both "preserve the AC-coverage check" (spec §breakdown.py) and introduce test-only/impl-only slices (AC-05); they fight on the first such slice. **Resolution:** say the AC-coverage check becomes slice-shape-aware (the rule branches on the slice's declared discipline), acknowledge it as a behavior change to a shipped check, and extend the same "fire only when slice metadata is present" backward-compat hinge the spec applies to the spec gate to the breakdown gate too. Pin whether slices map onto the existing `covers: [AC-NN]` field (reuse the loop) or tasks gain a `slice` field (rewrite the loop) — the spec defers this to an open question, but it decides whether the gate is extended or rewritten, so resolve it now.

### [blocking] The `review-gate` caller enumeration is incomplete and the deferral violates the spec schema
**Category:** Architectural soundness. The spec names callers as "`fbk-spec-review` and `test_gates_review.py`." Missing: `fbk-breakdown/SKILL.md` invokes `review-gate` as its prior-stage fail-fast check (a runtime caller, more load-bearing than the test); `test_gates_review.py` imports `validate_review` directly (a symbol move breaks the import even if the command name is preserved); and shell tests `test-gate-output-review-python.sh`, `test-review-integration.sh`, `test-skill-guide-dedup.sh` assert against `review-gate`. Separately, the code-review skill changes are not traced to `test-code-review-skill.sh`, `test-code-review-guide-extensions.sh`, `test-code-review-integration.sh`. The schema requires caller enumeration *before* tasks are authored; the conditional "if split, enumerate later" defers a list the spec already knows. **Resolution:** enumerate all of the above now; if the review.py-vs-code_review.py question is still open, state both branches' impacted callers explicitly, and commit that `fbk.gates.review.validate_review` stays an import surface.

### [blocking] "Register every new asset in the installer manifest" is a phantom integration point
**Category:** Architectural soundness. `installer/install.sh` discovers assets by `find` over the source dir; `.firebreak-manifest.json` is *generated* at install time for uninstall, not an input you register into. New skills/agents/docs install automatically once the files exist under `assets/`. The ~6 spec references to "wire every new asset into the installer manifest" (incl. AC-17 and the install seam) describe work that does not exist and risk an implementer inventing a parallel registration path. The *only* real registration surface is `COMMAND_MAP` in `fbk/__init__.py` (for the new gate subcommands). **Resolution:** replace "installer manifest registration" with "files placed under `assets/` install automatically; the only registration is `COMMAND_MAP`"; keep AC-17's real content (files land under `~/.claude/`; asset bodies use installed paths).

### [blocking] Durable docs at `docs/` sit outside the install boundary, contradicting the spec's own installed-path constraint
**Category:** Architectural soundness. `fbk-intent` (reads/updates the architecture overview) and `fbk-design` (appends to the decisions log) are installed skills, but `docs/decisions-log.md` / `docs/architecture-overview.md` are per-repo working-tree paths that never install to `~/.claude/`. The spec's hard constraint (every path referenced inside an installed asset uses the installed form) is unsatisfiable for these references. **Resolution:** carve out a third path class — operator-project-relative durable docs (like `ai-docs/<feature>/...` already is) — and state that the installed-path constraint governs *firebreak asset* references, while feature artifacts and durable docs are project-relative.

### [important] The consolidated spec hides real build-order edges breakdown will have to rediscover
**Category:** Architectural soundness. Three hard ordering constraints are nowhere in the spec: the per-entry test-lock manifest must land before the breakdown shape-match check and the code-review no-shadow check (both read it); the slice-shape taxonomy strings must be fixed before both the spec gate and breakdown gate validate against them; the detector mode-neutral refactor must precede quality-scan reusing it. The breakdown DAG check validates task acyclicity, not whether human-implied asset ordering was captured. **Resolution:** name these dependency edges explicitly in the technical approach.

### [informational] `test_dispatcher.py` hard-codes "14 commands" and uses `issubset`, so a forgotten new-gate registration would not be caught
**Category:** Architectural soundness. Adding `intent-gate`/`design-gate`/code-review gate changes the count and the test name literal; the subset assertion won't fail on a *missing* addition. **Resolution:** add a positive assertion that each new gate command is present; rename the test.

---

## Over-engineering / pragmatism

### [important] The four-shape taxonomy re-introduces complexity-classification machinery the decision spine cut — enforce only the cheap invariant first
**Category:** Over-engineering / pragmatism. Decision 2 cut per-feature complexity classification; the four-value per-slice taxonomy is a different classifier with the same enforcement cost, threaded through the spec gate (membership), breakdown gate (shape→structure match), and the test-lock manifest (metadata), plus four progressive-disclosure leaves. Keep the shapes as authoring guidance, but in `breakdown.py` enforce mechanically only the high-value, cheap invariants — `cross-cutting ⇒ no impl task`, and `contract-evolving ⇒ retired-tests list present with rationale` — and defer the full four-way shape-to-structure match until one real feature exercises it, rather than building and unit-testing four enforcement branches whose value is unproven. **Resolution:** narrow AC-05's gate-enforced portion; document the rest as breakdown-leaf guidance.

### [important] The code-review gate belongs in a new module, not `review.py`; resolve the open question now
**Category:** Over-engineering / pragmatism. `review.py` gates the spec-review council artifact (a different phase). Folding code-review close-out checks into it makes one file's tests cover two unrelated gates and drags the council's `review-gate` tests into the blast radius. **Resolution:** resolve the open question to `code_review.py`; and have its hash check *call* `test_hash.verify_manifest` rather than reimplement a second hash-comparison path.

### [important] "Widen the test-reviewer invocation contract" is a refactor of a checkpoint-keyed agent, not a description tweak
**Category:** Over-engineering / pragmatism. The test-reviewer agent is built around a fixed CP1/CP2/CP3 model; pre-lock/final-pass modes, the widened "all tests covering the module" scope, and contract-evolving retirement awareness rewire most of the document. **Resolution:** reclassify from "extend" to "refactor-then-extend" so breakdown sizes the work unit correctly.

### [important] `fbk-architect` "written as a superset the council architect can collapse into" is speculative generality
**Category:** Over-engineering / pragmatism. The council migration is explicitly out of scope (Decision 15); designing for it now can't be validated and risks over-scoping the persona. **Resolution:** write `fbk-architect` for its one job this cycle (author designs in isolation for `fbk-design`); record the future-collapse intent as a decisions-log note, not a build requirement.

### [important] The concept-doc set (~11 new leaves) needs a named runtime consumer per doc
**Category:** Over-engineering / pragmatism. Several (hybrid-gate-pattern, technique-skills, design-manifest) document patterns the assets already embody and read like architecture-overview material; the project's own necessity test says a leaf earns its place only if a skill routes to it at runtime. `capability-entry` and `slice-shapes/*` are routed-to (real). **Resolution:** name the runtime consumer for each concept doc; fold the unrouted ones into the durable architecture overview.

### [informational] Reuse posture is otherwise correct
**Category:** Over-engineering / pragmatism. Quality-scan reusing the detector (via spawn-prompt parameterization, not a sibling note), test-review reusing the reviewer, and preserving the hash-lock are the right calls; the fresh-eyes/council split correctly avoids a "review family" abstraction.

---

## Quality: testing strategy and impact

### [blocking] AC-18 (durable-artifact discipline) has no test and no UV step
**Category:** Quality. None of the unit tests, shell tests, installer test, or UV-1..UV-10 cover AC-18. It is the cheapest AC to check mechanically (file existence at two fixed paths + a grep for the convention statement + an overview non-emptiness check) and the most load-bearing for the intent phase (which inherits from the overview). **Resolution:** add a shell test asserting both durable docs exist, the overview is non-empty, and the authoring docs state the conventions.

### [blocking] The capability-entry test for AC-09 only checks "no hard failure," not the required content
**Category:** Quality. AC-09 requires the output to *name what is missing* and *offer the upstream phase*. The described test asserts only that the process doesn't exit non-zero — it cannot detect a prerequisite check that silently does nothing. **Resolution:** assert stdout/stderr contains the missing-artifact name and the upstream-phase name, for each of the four upstream-missing cases (intent-missing-at-design, design-missing-at-spec, spec-missing-at-breakdown, impl-missing-at-code-review); make this a gate/script unit test, not only a one-shot shell smoke test.

### [blocking] AC-14's "reads before writing to preserve prior stages" is untested; UV-10 has no test entry
**Category:** Quality. A skill that overwrites the retrospective would still pass "a stage section appears." **Resolution:** add an integration test that runs two phases in sequence and asserts *both* stage sections are present after the second runs; map UV-10 to it.

### [blocking] UV-7, UV-8, UV-9 have no corresponding test entries (schema requires each UV map to a test)
**Category:** Quality. UV-7 (standalone technique invocation) and UV-8 (capability-entry) name no test; UV-9's plain-language spot-check is an unmappable manual judgment. **Resolution:** add a shell test that invokes each technique skill with minimal input and asserts its named output file appears (UV-7); map UV-8 to the corrected capability-entry test; for UV-9's plain-language sub-step, mark it intentionally manual with documented rationale per the schema's allowance.

### [blocking] The grilling-log seam (skill writes → gate reads) has no end-to-end test
**Category:** Quality. The intent-gate unit test checks the gate's *read* of the log in isolation; nothing tests that `fbk-grilling` produces a log in the shape the intent/design dedup step consumes. **Resolution:** add an integration test — a pre-authored grilling log in the declared shape makes the intent gate pass; a wrong-shape log makes it fail — testing the contract both sides honor.

### [blocking] The spec-gate backward-compat regression test, as described, cannot catch the regression it targets
**Category:** Quality. The existing `test_gates_spec.py` only exercises two pure functions, not `main()`. "Behaves exactly as today" can only be proven by running the full feature path on a no-slices spec and asserting pass, plus an adversarial case where a legacy spec contains the literal token `test-discipline` in prose/code-fence and asserting no slice check fires. **Resolution:** add a full-path regression test and the adversarial-prose case.

### [important] AC-12/AC-13 must enumerate all five disciplines by name; "enforceable" overstates what is verified
**Category:** Quality. A presence-and-shape grep passes when four of five ship. The existing `test-instruction-hygiene-coverage.sh` already enumerates targets by name — copy that. AC-13's "enforceable instructions" promises enforcement nothing measures. **Resolution:** enumerate the five disciplines individually in both CLAUDE.md and the rules and in the test; downgrade "enforceable" to "present as instructions."

### [important] The breakdown-gate shape additions modify existing checks #1 and #8 — call them modified, and add a passing contract-preserving case
**Category:** Quality. The new `test_gates_breakdown.py` cases must include a contract-preserving slice (impl, no new test) that *passes* — the exact case the current check #8 rejects. **Resolution:** name `validate_breakdown` checks #1/#8 as modified; add the passing case.

### [important] The new SDL's narrowing may break `_check_testing_strategy_traceability`; pin the intended behavior
**Category:** Quality. The existing spec gate requires the testing-strategy section to reference ≥1 `AC-NN`. If slices-bearing specs express coverage via slices, this check fails well-formed specs. **Resolution:** state whether the AC-NN-in-testing-strategy check is suppressed or kept when slices exist, and test both ways.

### [informational] Prose-anchored shell tests will break on the spec/guide rewrites
**Category:** Quality. `test-skill-guide-dedup.sh` greps exact sentinels in `fbk-spec/SKILL.md` and `feature-spec-guide.md`, both modified by this work. **Resolution:** list it under existing-tests-impacted so the rewrite doesn't surprise CI.

### [informational] Strengthen the design-manifest bidirectional test with a simultaneous both-directions case
**Category:** Quality. Add a case where the directory has both an extra unlisted page and a missing one, to confirm the gate reports both rather than short-circuiting.

---

## Measurability

### [important] AC-08, AC-10, AC-11 bundle multiple independent conditions behind one pass/fail and assert some unobservable qualities
**Category:** Measurability. AC-08 packs six conditions (bug-pass-unchanged, ≤5 ranked findings, final review ran, artifacts required, hash intact, no shadow tests) — a single fail can't localize. AC-10's "reflects each answer back before recording" has no observable. AC-11's "runs in isolated context" is unfalsifiable and "scan/observe-only" is the load-bearing safety property buried in a bundle. **Resolution:** split each into per-condition ACs; make reflect-back leave a trace in the grilling log (e.g., a `confirmed`/reflect-back line per recorded decision) so it's checkable; make "no auto-fix" checkable by asserting the technique agents carry no Write/Edit tool (their specs already list Read/Grep/Glob only); drop or operationalize "isolated context" (assert the skill body uses a sub-agent spawn rather than inline work). Also assert the "≤5 and ranked" property of the quality-scan artifact — nothing currently does.

### [important] AC-03's "appends to the decisions log" is asserted but unmeasured
**Category:** Measurability. Neither `test_gates_design.py` nor the design-gate checks the decisions-log append. **Resolution:** have the design gate check the manifest's "Decisions recorded" count line is present and non-zero, or move the append to a UV step and say so.

### [important] AC-17's "no source-path references" sub-check must be adversarial, not incidental
**Category:** Measurability. A path can resolve and still be the wrong (source `assets/`) form — the recurring install-path failure mode. **Resolution:** grep installed asset bodies for the literal `assets/` prefix and fail on any hit.

### [informational] AC-06's bounce-back trigger is a false-negative blind spot
**Category:** Measurability. The gate can verify an unresolved marker fails, but cannot detect a breakdown that *should* have bounced but didn't. **Resolution:** state explicitly that the warranted-bounce judgment is UV-only; keep the marker-resolution check as the mechanical half.

### [informational] AC-04's "design pages referenced by the spec exist" is contingent on an open question
**Category:** Measurability. The reference format depends on the unresolved slice-handoff artifact. **Resolution:** note the dependency rather than hiding an unimplementable sub-check inside "passes the gate."

### [informational] The PRD's headline success metric is unmeasured aspiration — name it as deferred
**Category:** Measurability. "Resembles the clean-substrate signature" / "threshold-crossing rate drops" map to zero ACs (correctly — they need longitudinal/diff baselines). "Spec meaningfully shorter" has no baseline or target. Usage signals need telemetry the project isn't building (audit log is a non-goal). **Resolution:** state in the spec that the primary qualitative success signal is not gated by any AC and won't be known at ship; optionally line-count the sample spec vs an old spec as a UV observation.

### [informational] AC numbering is out of order (AC-19 before AC-18)
**Category:** Measurability. Passes the format check but made the AC-to-test audit error-prone. **Resolution:** reorder.

---

## Threat modeling

### [blocking] Injection-detection parity is missing for the two new gates
**Category:** Threat modeling. The shipped spec gate runs `detect_injections()` (control/zero-width chars, HTML-comment instructions, embedded "you are now/new instructions" patterns) on the spec. The new `intent-gate` (PRD + behavior inventory + grilling log) and `design-gate` (design pages + manifest) read the furthest-upstream agent-/operator-authored artifacts — which steer every downstream agent — but the spec defines these gates as structural-only. A poisoned PRD or design page (e.g., from a pasted external requirements doc or a confused upstream agent) rides untouched into the spec author, breakdown, and implementation agents. **Resolution:** run `detect_injections()` on each new gate's inputs at gate time (scan on structural pass, emit `injection_warnings` in the JSON), and add it to AC-02/AC-03. Calibration: internal single-operator tooling, so this is medium not critical, but the fix is near-zero cost because the detector exists.

### [important] Promote `detect_injections()` to a shared module before wiring it into the new gates
**Category:** Threat modeling. It currently lives privately in `spec.py`; copying it into two more gates forks the pattern list and invites detection drift. **Resolution:** move it to a shared module (e.g., `fbk/injection.py`), import it from spec/intent/design, and unit-test it once.

### [important] The "no-shadow-tests" check is undefined and conflicts with `verify_manifest`'s UNEXPECTED-fails behavior
**Category:** Threat modeling. `verify_manifest` already flags any unlisted file present as UNEXPECTED and fails — so either the flow can never add a sanctioned new test, or "shadow test" needs a new definition distinguishing a sanctioned addition from one that bypasses a locked contract. AC-16 makes this load-bearing (a shadow test is one of only two things that hard-fail the gate). **Resolution:** define a shadow test operationally (a test file in the changed module's scope not in the lock manifest), reuse `verify_manifest`'s UNEXPECTED mechanism rather than a parallel scan, and add the explicit case to the code-review gate test. This likely needs the per-entry manifest from the first blocking architecture finding (you can't tell a shadow from a sanctioned addition without knowing which slice owns the locked set).

### [important] Locking pre-existing tests shifts the integrity baseline from "reviewed test unchanged" to "arbitrary file unchanged" — the pre-lock review must inspect them
**Category:** Threat modeling. For contract-preserving slices the gate locks whatever bytes are on disk at lock time; if that file was never reviewed, the lock blesses an unverified baseline and every later verify passes green. **Resolution:** make explicit that for contract-preserving slices the pre-lock test-review scope *must include the pre-existing files being locked* (the widened "all tests covering the module" scope supports this) — so the `accepted` verdict isn't rubber-stamping unread bytes.

### [informational] New gate scripts take path args — follow the existing validate-before-open / exit-2 pattern
**Category:** Threat modeling. Path traversal is not a real threat (single-operator, local), so don't add sandboxing. But match the existing `is_file()/is_dir()` + `sys.exit(2)` guards and `errors="replace"` reads so a bad or binary artifact fails cleanly rather than crashing.

### [informational] Do not over-rotate into signing first-party verdict artifacts
**Category:** Threat modeling. Fresh-eyes/quality-scan/test-review verdicts are first-party agent outputs; their correctness is a quality concern covered by the operator + UV steps, not an attack surface. Scan externally-influenced artifacts (PRD, design pages) at their admission gate; trust the verdict artifacts.

---

## Documentation impact

### [informational] Documentation-impact section is specific and adequate
**Category:** Documentation impact. The spec names GLOSSARY additions/removals, CHANGELOG groups, the SDL workflow leaves to modify, the concept docs to create, and the two durable docs — concrete, not "update docs." One gap to fold in from the architecture findings: the durable-doc path class needs documenting (project-relative, not installed). Otherwise present and specific.

---

## Independent checkpoint-1 review

The independent test reviewer (no access to the council discussion) returned **VERDICT: FAIL** with five defects, all blocking, which corroborate the Quality findings above:

1. Capability-entry shell test is an error-absence check with no positive behavioral assertion (AC-09). → folded into the AC-09 blocking finding.
2. AC-14 retrospective-append has no test and UV-10 cannot catch a clobber. → folded into the AC-14 blocking finding.
3. UV-7/UV-8/UV-9 have no corresponding test entries. → folded into the UV-mapping blocking finding.
4. The grilling-log write→read seam has no integration test. → folded into the grilling-log seam blocking finding.
5. The `review-gate` caller enumeration is deferred conditionally and omits the code-review shell tests. → folded into the caller-enumeration blocking finding.

It confirmed the prompt-asset "no unit-test surface, rely on manual UV" architecture is a *legitimate* limitation here (not evasion), and that the named tests are specific and not implementation-coupled — the FAIL is about the coverage holes, not the testing philosophy.

---

## Testing strategy

**New tests needed (to add in the revision):**
- Full-path spec-gate regression test (no-slices spec passes identically; adversarial-prose `test-discipline` token fires no slice check) — AC-15.
- Script-side capability-entry prerequisite unit test asserting missing-artifact name + upstream-phase name for all four upstream-missing cases — AC-09.
- Two-phase retrospective preservation integration test (both stage sections present after the second phase) — AC-14.
- Standalone technique-invocation shell test (each technique produces its named output file) — AC-10/AC-11, UV-7.
- Grilling-log seam integration test (correct-shape log passes the gate; wrong-shape fails) — AC-10.
- Durable-doc existence + overview-non-empty + conventions-present shell test — AC-18.
- Per-discipline enumeration in the instruction-hygiene test (all five named) — AC-12/AC-13.
- Contract-preserving passing case + cross-cutting no-impl case in breakdown-gate tests — AC-05.
- Shared `detect_injections()` unit test + intent/design-gate injection-scan tests — AC-02/AC-03.
- No-source-path adversarial grep over installed asset bodies — AC-17.

**Existing tests impacted (the spec must enumerate, beyond what it already lists):**
- `test_gates_test_hash.py` — manifest shape change; reclassify the touch as refactor-then-extend; enumerate which assertions change.
- `test_gates_breakdown.py` — checks #1/#8 become shape-aware; existing fixtures pass only because they carry no slices block.
- `test_gates_review.py` — `validate_review` import surface if review.py is split.
- `test_dispatcher.py` — count literal + named-set; add a positive presence assertion for new gates.
- `tests/sdl-workflow/`: `test-skill-guide-dedup.sh`, `test-gate-output-review-python.sh`, `test-review-integration.sh`, `test-code-review-skill.sh`, `test-code-review-guide-extensions.sh`, `test-code-review-integration.sh`, and any test enumerating the skill/agent/phase set.

**Test infrastructure changes:**
- As the spec lists (intent/design/spec-slices/per-shape-breakdown/extended-manifest fixtures, throwaway sample feature), plus: a shared injection-detection module to test once; fixtures for the per-entry (or sidecar) test-lock manifest shape once it is decided. No mocks needed — all collaborators are the real filesystem and gate code (sound justification, no change required).

---

## Threat model determination

**Decision: No** — no standalone threat-model artifact for this feature.

**Rationale:** Internal, single-operator developer tooling. No authentication, data storage, network, or external-API surface, and no new trust boundaries beyond the one that already exists: artifact text steering downstream LLM agents (prompt injection). That boundary is handled by the shipped `detect_injections()` control and is addressed directly by the injection-parity blocking finding (extend the scan to the intent and design gates). New entry points are local CLI subcommands and skills taking file-path arguments on the operator's own machine. The Security perspective's findings remain in this review and must be resolved in the revision regardless of the threat-model skip.
