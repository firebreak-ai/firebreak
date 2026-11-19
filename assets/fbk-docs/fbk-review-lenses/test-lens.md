# Test Review Lens

## 1. Lens identity

This lens reviews test code and test plans to determine whether each test would actually fail if the behavior it claims to cover were broken, and whether the full test set faithfully implements what the spec requires.

```
output_mode: finding
output_contract: test-findings-and-coverage
```

---

## 2. Finding types

| Type | Definition | Ship decision |
|---|---|---|
| weakened-assertion | An assertion that was present and stronger in a prior version has been relaxed without justification, reducing the test's ability to catch the behavior it claims to cover. | Block |
| untested-behavior | A requirement, acceptance criterion, or declared integration seam has no planned or implemented test that would fail if the behavior were broken. | Block or request changes, depending on severity |
| trivially-passing | A test passes unconditionally regardless of implementation — the assertion is vacuous, the mock invalidates the check, or the test exercises no real behavior. | Block |
| manifest-drift | The locked test manifest does not match the actual test files — a locked test is missing, a test was added without a manifest entry, or a changed test lacks required authorization. | Request changes |

These types refine the generic `test-integrity` type defined in `review-loop.md`. Each type is distinct: `weakened-assertion` requires a prior-version comparison; `trivially-passing` requires demonstrating that the test passes without the implementation under test; `manifest-drift` requires comparing the manifest to the filesystem.

---

## 3. Severity levels

| Severity | Observability | Reviewer action |
|---|---|---|
| critical | A defect that can make the test suite produce green results while the implementation is actively broken — invisible to anyone running the suite, only visible on deliberate adversarial inspection. | Block |
| major | A defect that causes the test suite to miss a class of regression without producing any warning signal — visible only by tracing the test against the requirement or by injecting a deliberate fault. | Request changes |
| minor | A defect that reduces coverage fidelity or creates a maintenance hazard, but does not cause the suite to pass silently on a broken implementation in normal usage. | Comment or request changes |

---

## 4. Type-severity validity matrix

Human-readable:

| Type | critical | major | minor |
|---|---|---|---|
| weakened-assertion | yes | yes | yes |
| untested-behavior | yes | yes | yes |
| trivially-passing | yes | yes | — |
| manifest-drift | — | yes | yes |

Machine-readable (used by `pipeline.load_lens_matrix()` and `validate_sighting()`):

```lens-matrix
types: [weakened-assertion, untested-behavior, trivially-passing, manifest-drift]
severities: [critical, major, minor]
matrix:
  weakened-assertion: [critical, major, minor]
  untested-behavior: [critical, major, minor]
  trivially-passing: [critical, major]
  manifest-drift: [major, minor]
required: [title, location, type, severity, mechanism, consequence, evidence]
```

The `required` list excludes `id` — the researcher does not emit `id`; the pipeline assigns sighting identifiers (S-NN) after schema validation.

---

## 5. What to look for (researcher instructions)

Read `shared-detection.md` for the test-integrity audit used by this lens.

The test-integrity audit in `shared-detection.md` is the primary detection pass for this lens. Run it on every test in scope before running the target-specific passes below.

The spec, test tasks, or contract pages under review may describe planned tests or planned contract amendments that do not yet exist in the shipped codebase — that is the artifact's subject matter when reviewing a test plan, not evidence of a defect. Before flagging a gap, confirm whether the missing element is planned-but-not-yet-built (not a finding in a test plan) versus genuinely absent from both the artifact's own plan and any implementation it claims to already cover (a finding). A test the reviewed artifact claims already exists must actually exist — its absence is a finding in every review.

Read `../review/test-integrity.md` for the shared inputs, targeted checks and
stage-specific evidence expectations. These criteria apply to standalone test
review and managed breakdown/implementation review.

Use `weakened-assertion` only with a stronger prior version. For new tests missing a
required observation use `untested-behavior`; use `trivially-passing` only when the
claimed behavior can be absent/broken and the check still passes as described by
that type. Severity follows the concrete consequence, not the pattern's name.

---

## 6. Source-of-truth handling

**When a spec is available:** compare planned tests against the spec's requirements, acceptance criteria, and integration-seam declarations. The researcher opens the spec and reads each requirement section before assessing coverage. The spec's acceptance criteria are the canonical list; the test plan or implementation must cover each one. A requirement is under-covered only when no section of the spec — including sibling ACs, the testing strategy, or a fixture contract — already pins the missing detail. Do not flag `untested-behavior` merely because an AC's own text does not restate information pinned elsewhere in the spec.

**When a locked manifest is available:** compare the actual test files against the manifest. The manifest is the source of truth for which tests exist and what their locked state is. The researcher must not accept the test file's own assertions about what it covers without comparing against the manifest.

**When neither spec nor manifest is available:** the researcher falls back to the shared test-integrity criteria and documents that no named source of truth was available for each finding.

**Inherited contracts:** when a test file declares it is preserving a prior contract verbatim , the researcher locates the locked version and compares field by field. Accepting the test file's own copy as the source of truth is not acceptable.

---

## 7. Challenger instructions

The generic disciplines in `review-loop.md` apply. The following test-review-specific rules also apply.

**Reclassification rules:**

- A `trivially-passing` finding may be reclassified to `weakened-assertion` (same or lower severity) only if a prior-version comparison establishes a weakened assertion. A missing observation in a new test is `untested-behavior`.
- A `manifest-drift` finding may be reclassified from major to minor (or minor to major) when the challenger's filesystem check reveals the actual severity differs from what the researcher described.

**Provenance for dead-code trace:** when the researcher flags an untested path or a retired test, the challenger's provenance trace includes: the requirement or acceptance criterion the test was covering, the commit or task in which it was introduced or retired, and whether a surviving test now covers that path. If the trace is ambiguous — for example, the path was introduced for a planned dependency that has not arrived — return `unresolvable` identifying the deciding missing evidence; ambiguity alone cannot confirm or reject the claim.

**Cited sources:** findings in test review commonly cite the spec (requirements and ACs), the locked manifest, the task file, and the git log. The challenger opens each cited document before issuing a verdict. A ruling based on what a source probably contains is not acceptable.

**Behavioral finding trace:** to confirm a `trivially-passing` or `weakened-assertion` behavioral finding, the challenger traces the assertion's call path to confirm that removing or weakening the assertion would let a broken implementation pass silently. If the challenger cannot establish this from source, request a focused execution check. Until the mechanism is established, return `unresolvable` with the deciding check; do not classify lack of confirmation as verified. Use `verified-pending-execution` only when source reasoning already establishes the defect and execution remains to confirm a stated runtime detail.

---

## 8. Findings artifact

The Detector returns `{"findings": [...], "coverage": [...]}`. Findings use the
generic researcher schema and this lens's type matrix. Each coverage row contains:

- `obligation`: the requirement reference or named check in the shared test-integrity criteria.
- `status`: `covered`, `gap`, `unknown`, or `not-applicable`.
- `evidence`: specific source/test and the failure it detects, or the missing
  evidence, applicability reason or uncovered behavior. Distinguish planned,
  source-inspected and executed evidence; cite the execution artifact when run.

Account for each material obligation and each targeted check, grouping related
ones where the same evidence applies. This compact account is required even with
zero findings. It documents inspection, not a new acceptance gate or proof of
exhaustive correctness. The runtime validates the shape; reviewers remain
responsible for the truth and adequacy of the evidence.

The Challenger receives only normalized candidates and original sources, never the
Detector's coverage conclusions. Return one verdict per candidate in order. The
coordinator retains coverage alongside confirmed findings, unresolved evidence and
actual execution results. Do not describe an unknown or gap as clean coverage.
Managed test locks and acceptance remain controlled by the workflow runtime.
