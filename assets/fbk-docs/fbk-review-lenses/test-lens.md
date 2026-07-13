# Test Review Lens

## 1. Lens identity

This lens reviews test code and test plans to determine whether each test would actually fail if the behavior it claims to cover were broken, and whether the full test set faithfully implements what the spec requires.

```
output_mode: finding
output_contract: verdict-contract
```

---

## 2. Finding types

| Type | Definition | Ship decision |
|---|---|---|
| weakened-assertion | An assertion that was present and stronger in a prior version has been relaxed without justification, reducing the test's ability to catch the behavior it claims to cover. | Block |
| untested-behavior | A requirement, acceptance criterion, or declared integration seam has no planned or implemented test that would fail if the behavior were broken. | Block or request changes, depending on severity |
| trivially-passing | A test passes unconditionally regardless of implementation — the assertion is vacuous, the mock invalidates the check, or the test exercises no real behavior. | Block |
| manifest-drift | The locked test manifest does not match the actual test files — a locked test is missing, a test was added without a manifest entry, or a retired test is absent from the retirement justification list. | Request changes |

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

The test-integrity audit in `shared-detection.md` is the primary detection pass for this lens. Run it on every test in scope before running the mode-specific passes below.

The spec, test tasks, or contract pages under review may describe planned tests or planned contract amendments that do not yet exist in the shipped codebase — that is the artifact's subject matter at the spec and pre-lock checkpoints, not evidence of a defect. Before flagging a gap, confirm whether the missing element is planned-but-not-yet-built (not a finding at these checkpoints) versus genuinely absent from both the artifact's own plan and any implementation it claims to already cover (a finding). A test the lock manifest or a contract-preserving slice claims already exists must actually exist — its absence is a finding at every checkpoint.

### Spec checkpoint pass

Walk each requirement and acceptance criterion in the spec. For each one, ask:

- Is there a planned test that would fail if this requirement were violated?
- Does the planned test name describe the behavior it asserts, not just the component it touches?
- Is each declared integration seam covered by at least one end-to-end test or a documented justification for why a seam test is deferred?
- If the spec lists test-fixture or test-data requirements, are those requirements surfaced in the test plan?

- Does the acceptance criterion quantify over an idealized or infinite domain (for example, "for all finite elapsed values," "for all reals") that the implementation's numeric representation cannot literally satisfy? A planned test that only checks a tolerance-bounded approximation of such a claim does not prove the AC as worded — flag as `untested-behavior`.

Flag as `untested-behavior` (severity: `major` or `critical` based on the requirement's role in the feature contract) any requirement or seam with no planned test.

### Pre-lock pass

Walk each test task and its corresponding test implementation. For each pair:

- **Faithful translation:** does the implementation do what the task describes? Flag deviation as `untested-behavior` (major).
- **AC trace:** can each test be traced to at least one acceptance criterion? Flag an untraced test as `untested-behavior` (minor).
- **Red before implementation:** is the test structured so it would fail before the implementation under test exists? Flag a test that cannot fail as `trivially-passing` (critical or major depending on the assertion's centrality).
- **Assertion strength:** does the assertion check the actual behavior, or does it only check that no exception was raised or that a return value is truthy? Flag an error-absence-only assertion as `weakened-assertion` (major).
- **Observation-channel reach:** does the assertion target a channel (an event-log field, a mock call record, a fake client attribute) that the declared test double is structurally capable of carrying? An assertion on a field, argument, or side effect the fixture never populates cannot detect a regression in the behavior it claims to check, regardless of how strict the assertion looks. Flag as `trivially-passing` (major).

### Final pass

Review the full test set covering the changed module, including pre-existing locked tests.

- **Weakened assertions:** compare each test's assertion against the locked version. A narrowed comparison, a removed check, or a tolerance increase is `weakened-assertion` (severity: critical if the narrowing would let a broken implementation pass; major otherwise).
- **State versus log:** when a behavior writes durable state (a database row, a stored field) and also emits a transient signal (a log line, an event), a test that only asserts the transient signal is not equivalent coverage. Flag as `weakened-assertion` (major) when no test in the set asserts the persisted state for that behavior — the event can fire correctly while the persisted write silently fails or diverges. A test that deliberately asserts only the event is fine when a sibling test covers the persisted side.
- **Trivially-passing tests:** flag any test whose sole assertion is error-absence with no positive behavioral assertion as `trivially-passing` (critical or major). Flag any test where the mock setup invalidates the thing being asserted as `trivially-passing` (critical).
- **Unauthorized modification:** flag any locked test that differs from the hash-locked version (content, name, or location) as `manifest-drift` (major), unless the contract-evolving retirement list explicitly justifies the change.
- **Manifest drift:** compare the actual test files against the locked manifest. A test file present on disk but absent from the manifest is `manifest-drift` (minor). A manifest entry that references a file not on disk is `manifest-drift` (major).
- **Contract-evolving retired-test justification:** for contract-evolving slices, each retired test must appear in the retirement justification list with an explicit reason. A retired test absent from this list is `manifest-drift` (major). A retirement justification that merely says "no longer needed" without naming the surviving test that covers the same contract is `manifest-drift` (minor).

---

## 6. Source-of-truth handling

**When a spec is available:** compare planned tests against the spec's requirements, acceptance criteria, and integration-seam declarations. The researcher opens the spec and reads each requirement section before assessing coverage. The spec's acceptance criteria are the canonical list; the test plan or implementation must cover each one. A requirement is under-covered only when no section of the spec — including sibling ACs, the testing strategy, or a fixture contract — already pins the missing detail. Do not flag `untested-behavior` merely because an AC's own text does not restate information pinned elsewhere in the spec.

**When a locked manifest is available:** compare the actual test files against the manifest. The manifest is the source of truth for which tests exist and what their locked state is. The researcher must not accept the test file's own assertions about what it covers without comparing against the manifest.

**When neither spec nor manifest is available:** the researcher falls back to the lens-defined general criteria above and documents that no named source of truth was available for each finding.

**Inherited contracts:** when a test file declares it is preserving a prior contract verbatim (for example, a non-contract-evolving slice), the researcher locates the locked version and compares field by field. Accepting the test file's own copy as the source of truth is not acceptable.

---

## 7. Challenger instructions

The generic disciplines in `review-loop.md` apply. The following test-review-specific rules also apply.

**Reclassification rules:**

- A `trivially-passing` finding may be reclassified to `weakened-assertion` (same or lower severity) if the test does make a positive assertion but it is materially weaker than the claimed coverage. Use the more specific type.
- A `manifest-drift` finding may be reclassified from major to minor (or minor to major) when the challenger's filesystem check reveals the actual severity differs from what the researcher described.

**Provenance for dead-code trace:** when the researcher flags an untested path or a retired test, the challenger's provenance trace includes: the requirement or acceptance criterion the test was covering, the commit or task in which it was introduced or retired, and whether a surviving test now covers that path. If the trace is ambiguous — for example, the path was introduced for a planned dependency that has not arrived — the finding is surfaced with the ambiguity noted in the evidence field rather than rejected.

**Cited sources:** findings in test review commonly cite the spec (requirements and ACs), the locked manifest, the task file (for pre-lock), and the git log (for final). The challenger opens each cited document before issuing a verdict. A ruling based on what a source probably contains is not acceptable.

**Behavioral finding trace:** to confirm a `trivially-passing` or `weakened-assertion` behavioral finding, the challenger traces the assertion's call path to confirm that removing or weakening the assertion would let a broken implementation pass silently. A finding the challenger cannot trace this way is returned as `verified-pending-execution`, not rejected.

---

## 8. Verdict contract

This lens declares `output_contract: verdict-contract`.

### Artifact paths

Each mode of the test-review preset writes one artifact:

- Spec checkpoint: `ai-docs/<feature>/test-review-spec.md`
- Pre-lock: `ai-docs/<feature>/test-review-pre-lock.md`
- Final: `ai-docs/<feature>/test-review-final.md`

These are the canonical names the spec gate and code-review gate read. Do not rename them.

### Verdict line format

The artifact carries exactly one verdict line. The line must match:

```
Verdict: accepted
```

or

```
Verdict: needs-revision
```

No other value is valid. The line is case-sensitive. The prefix `Verdict:` (capital V, colon, space) is required exactly. No prose, qualifier, or additional content may appear on the verdict line. The verdict line appears once and only once in the artifact; a duplicate verdict line is a defect.

### Passing condition

A verdict of `accepted` means the challenger confirmed no findings at major or critical severity remain after all loop rounds. Minor findings may be noted but do not block an accepted verdict unless the lens author declares otherwise for a specific type (none do in this lens).

### Failing condition

A verdict of `needs-revision` is required when:

- Any confirmed finding at critical or major severity remains after all loop rounds, or
- The researcher could not complete the required passes (missing artifact, missing spec, missing manifest) and the gap affects a coverage-critical area.

### Gate behavior

The spec gate and the code-review gate read the artifact file, not the agent's conversation output. Both gates locate the artifact in the feature folder by canonical name and read the `Verdict:` line. A `needs-revision` verdict at any checkpoint blocks the downstream gate. The downstream gate passes only on `accepted`.
