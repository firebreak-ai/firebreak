# Test review — spec checkpoint (re-review after additive revision)

Mode: spec checkpoint. Artifacts: `code-review-exec-path-spec.md`, feature-spec-guide §5 and verification gate. Read fresh (no prior-pass memory).

The single question, asked per requirement: **would the planned test fail if the behavior it claims to cover broke?**

## Verification grounding

I confirmed the additive revision is implementable as written against `assets/fbk-scripts/fbk/pipeline.py` and the real contracts:

- `read_stdin_json` (pipeline.py:100–105) exits non-zero with `ERROR: malformed JSON input` on non-JSON, and returns the parsed value for valid JSON. A JSON `[]` parses to an empty list, so a per-record loop is a no-op and the array passes through — the empty-array-passes claim for `validate-verdicts` (AC-15) is real, not asserted into existence.
- `write_json` (pipeline.py:108–110) gives the pass-through-unchanged behavior the all-valid case relies on.
- The new `validate-verdicts` subparser takes no arguments and no lens, matching the existing no-arg `validate`/`to-markdown` parsers — implementable exactly as IF-S-03 specifies (reads a verdict array on stdin, no lens).
- The five statuses and evidence rules in AC-15 / IF-S-03 are a faithful encoding of the real challenger contract (`fbk-review-challenger.md` lines 28–42): five statuses verbatim; `verification_evidence` min-10 on `verified`/`verified-pending-execution`; `rejection_reason` min-10 on `rejected`; `reclassified_from == {}` means unchanged. The check is not duplicating an invented rule — it enforces the agent's own stated minimums.
- All four lenses exist repo-relative under `assets/fbk-docs/fbk-review-lenses/` (code, test, coherence, task), so the AC-07 catching tests and the chained-integration test have real fixtures.
- The four existing tests the strategy says it extends or leaves untouched all exist (`test_pipeline_backward_compat.py`, `test_pipeline_missing_lens.py`, `test_pipeline_normalize.py`, `test_pipeline.py`).

## Focus 1 — AC-15 / `validate-verdicts` (the new subcommand)

Planned cases: bad status rejected; `verified` without (or under-10) evidence rejected; `rejected` without reason rejected; all-valid passes through unchanged; empty array passes; and the silent-loss case (a verdict typed `approved` rejected loudly).

- **Each rule's failure mode is distinct and catchable.** Bad-status, missing-evidence, and missing-reason are three different branches; each planned case omits exactly the one field its branch guards while keeping the rest well-formed, so a regression that drops any single branch leaves one case failing. If the status-enum check were removed, the `approved` case would pass through (wrong) and the test asserting non-zero exit would fail — that is the behavior breaking being caught.
- **The silent-loss case is non-vacuous.** It is not "any bad input errors." It pins the specific failure the feature exists to prevent: a status word outside the five (`approved`) that would otherwise survive `validate-verdicts`, reach the downstream verified filter, fail to match, and silently drop a confirmed finding. The test asserts the loud non-zero exit *at this step*, which is the only place that closes the path. A reviewer can name the mechanism: remove the enum check and the finding vanishes downstream with no error; the test catches exactly that.
- **The all-valid and empty-array cases guard over-rejection**, the opposite failure — a `validate-verdicts` that rejected everything would still "pass" the four negative cases but fail these two. Both directions are covered.

Cleared. AC-15 maps to a test that fails if any of the four rules, or the pass-through, breaks.

## Focus 2 — AC-10 as now written

AC-10 is split into two enforced halves: finding fields + matrix via `validate --lens` (stage 8), and verdict fields via `validate-verdicts` (stage 6). IF-D-04 covers the finding/matrix half, IF-S-03 the verdict half.

- The finding-field/matrix half is exercised by the post-challenge re-validation tests and the per-type catching tests (a reclassified type checked against the active matrix).
- The verdict-field half is exercised by the AC-15 tests above.
- The skill-conformance test asserts both calls are present and ordered in each skill markdown (anchored structural markers, per the test-authoring "structural assertions on text artifacts" rule).

No prose-only gap remains: the verdict-field check that AC-10 previously described as prose is now an executed subcommand with direct coverage. Cleared.

## Focus 3 — Regression on prior coverage

- **Re-join (AC-09, AC-13).** Happy-path test uses ≥3 findings with distinct per-position sentinels and asserts exact index-to-index overlay — a reversal, off-by-one, or always-overlay-[0] bug fails it. Neutral-field protection asserts all six neutral fields on each merged record equal the kept finding's value, so any copy-back fails. Reclassification test covers both the non-empty (`type`/`severity` overlaid, `reclassified_from` carried) and `{}` (original retained) branches. Count guard tested at N+1 and N−1. These hold as written and were not touched by the revision; the only interaction is that `rejoin` no longer adjudicates verdict validity (that moved to `validate-verdicts`), which the spec states explicitly (IF-S-01 "does not adjudicate verdict-field validity") — a clean separation, not a weakening.
- **Lens / normalize (AC-01..AC-06).** Lens-required-set acceptance of id-less findings (with and without lens), byte-identical default path as a genuinely new golden assertion (AC-02), missing/malformed lens with an ordering proof that the lens fails before any finding is read (AC-03/AC-04), six-field normalize with empty-string-for-missing and empty-array/non-JSON behavior (AC-05/AC-06). Each names a specific observable that changes if the behavior breaks. Unaffected by the revision.
- **Catching (AC-07, AC-12).** Per-type test rejects an out-of-lens type (`behavioral` under `test-lens.md`, etc.) with `REJECTED: invalid type …`; fixture is otherwise valid so the type-enum branch is the one that fires, not a required-field miss. Real for all three lenses (confirmed present).
- **Chained-integration test.** Now `validate --lens | severity-filter | normalize`, then `validate-verdicts`, then `rejoin --verdicts`, then `validate --lens`. Composition is coherent: `normalize` emits the six neutral fields, but `rejoin` reads the *kept* id-bearing list on stdin (not the normalized stream) and the verdict fixture from `--verdicts`, so `validate-verdicts` sitting between normalize and rejoin operates on the challenger-verdict fixture (its own stdin), not on the normalized findings — the new step is inserted on the verdict path, which is where it belongs, and does not break the finding-path pipe. The test asserts verdicts landed on the right findings end-to-end, catching inter-command contract drift. Coherent and non-weakened.

## Focus 4 — Integration seam coverage (Criterion 7) and seam declaration completeness (Criterion 8)

Four declared seams, all skill→pipeline.py:

- **fbk-code-review → pipeline.py** and the three converted skills (test/coherence/task) → pipeline.py. Each seam's executable steps — `validate --lens`/`run --lens`, `severity-filter`, `normalize`, `validate-verdicts`, `rejoin --verdicts`, post-challenge `validate --lens`, cited-source injection — are covered by (a) per-skill conformance tests asserting the ordered command sequence and the cited-source instruction are present, and (b) the chained-integration subprocess test exercising the real command chain end to end. The strategy is explicit that the conformance test proves documented presence/order, not live execution, and names the residual (live agent spawning) as the operator manual run UV-3 on the validation ladder — a legitimate "behavior verified by manual QA step" boundary for the agent-spawning portion no Python test can reach. The command-level seam behavior below the agents is automated.

No undeclared cross-module seam. The technical approach touches pipeline.py and four skill files plus two leave-alone modules (`review-loop.md`, `fbk-presets.json`); the leave-alone decisions are justified (spine stays abstract; lens is the single type-filter authority). The verdict-status vocabulary is declared as sourced from the spine and challenger contract, and `validate-verdicts` is the single enforcement point — that cross-asset dependency is listed under Dependencies and the cited-source seam (IF-S-02), not omitted.

## Criteria evaluated and cleared (Tier 1 spot-check at spec level)

- Silent-failure (C1): the `validate-verdicts` cases assert loud non-zero exits with positive content checks (offending record named), not mere error-absence. The byte-identical AC-02 case asserts on captured stdout/stderr/exit-code values, not "does not throw."
- Empty-gate / advisory (C3/C4): every planned test names a concrete assertion target (exit code, named message, exact field equality, index-to-index sentinel), none log-without-assert.
- Stale annotation (C2): skipped — pre-implementation, no executable tests yet.

## Findings

None blocking. The additive revision tool-enforces a previously-prose check with a non-vacuous, mechanism-specific test set; the silent-loss case pins the exact failure the subcommand exists to prevent; AC-10 has no remaining prose-only gap; prior coverage (re-join, lens/normalize, catching, chained-integration) holds as written and the new step composes coherently; every declared seam retains planned end-to-end coverage with the agent-spawning residual legitimately on the manual tier.

Verdict: accepted
