# Test-Review Checkpoint 1 — Hook-Harvesting Remediation

**Mode:** Pre-lock (spec-review checkpoint 1 — pre-implementation)  
**Artifact:** `ai-docs/hook-harvesting-remediation/hook-harvesting-remediation-spec.md`  
**Test suite read:** `assets/fbk-scripts/tests/` (all `.py` files)  
**Date:** 2026-06-11

---

## Summary verdict

**needs-revision**

Three blocking problems: the subagent-count test still masks the exact bug it claims to fix; the injection seam guard does not assert metric *content* and therefore cannot catch the stub regression; and the "demonstrated to fail against pre-fix code" claim is an unmeasured promise with no defined procedure. Two additional moderate issues affect the gate-rate-all-gates and install-seam tests. Detail follows.

---

## 1. AC-to-test coverage

Coverage is evaluated for every acceptance criterion.

### Criteria with adequate test coverage

- **Shared non-active-state set (covers terminal and checkpoint-state return):** Spec calls for a unit test of `resolve_active_stage` against COMPLETED and every checkpoint/idle state. `test_capture_active_stage.py` is listed in the impacted list but **does not exist** in the test suite at the time of this review. The spec schedules it as a test to run and confirm, implying it will be written — but there is no file to confirm. This is a gap rather than a confirmed defect in an existing test, and the spec explicitly plans to create it. Flagged as an implementation-phase watch item.

- **Kill rate / first-try rate arithmetic:** Covered by `test_report_arithmetic.py` with exact fractional assertions. The assertions are specific (exact value via `pytest.approx`). These would fail if the arithmetic changed.

- **Retention concurrency (locked-set under lock):** The spec calls for a unit concurrency test; `test_capture_retention.py` already exercises `prune_if_needed` with a `protect_specs` argument and `test_capture_event_writer.py` tests the exclusive file lock. The spec's planned new test covers the narrower gap (reading the locked-set *inside* the lock scope). No existing test contradicts or masks this.

- **Per-round detail (redaction and rendering):** The spec plans a new rendering integration test. Existing `test_report_rendering.py` checks for the "detection round" row label. The spec's new test adds per-round exact numeric assertions. Coverage path is clear.

- **Token boundary on working stages:** `test_capture_token_harvester.py` exists and tests hard-split attribution. The new unit test (turns during checkpoint periods) is additive. No masking gap observed.

- **DoS bound / bounded read:** The spec plans a new unit test for a 5 MB newline-less line. See finding 5 below for the assertion-strength issue on the existing related test.

- **Source attribution / validation:** The spec plans unit tests for gate event shapes. Coverage path is clear.

- **Installer atomic write:** The spec plans a new test for `settings.json` temp-then-rename. No existing test covers this. Coverage gap is acknowledged by the spec.

- **Structural cleanups (chokepoint return type, retention typing, round_count):** The spec calls for running existing tests to confirm no regression. These are contract-preserving — no new tests needed. Acceptable.

---

## 2. Masking-test corrections — bug-exercising analysis

### 2a. Subagent-count test (`test_report_arithmetic.py` — covers the "count reads from source field" bug)

**The spec says the correction rebuilds the test with `source="hook_router"` and identity in `data["agent_type"]`.**

The current test (`test_subagent_count_excludes_unknown_identity`) already uses `data={"agent_type": scanned_identity}` in its event fixtures — see lines 346–365. The `source` field is set to `scanned_identity`, not `"hook_router"`.

**Finding:** The current test sets `source=scanned_identity` (the agent identity). If the buggy code reads `source` instead of `data["agent_type"]`, the test still passes, because both fields carry the agent identity in this fixture. The spec correctly identifies this as the envelope-shape masking problem, but the test **has already been partially updated** — the `data["agent_type"]` field is present — while `source` still holds the agent identity rather than `"hook_router"`. This means the test does not yet fail against the buggy code: a buggy `count_known_subagents` that reads `source` would still return count=1.

The required rewrite must set `source="hook_router"` (the production writer name, not the agent identity) so that the buggy code — which reads `source` — counts zero, while the fixed code — which reads `data["agent_type"]` — counts one. The current test does not achieve this distinction.

- **Criterion violated:** Criterion 6 (behavioral completeness — the test would not fail against the buggy code it claims to correct)
- **Severity:** blocking
- **Rationale category:** N/A
- **Show your work:** `source=scanned_identity` at line 345 and `source=""` at line 353 and `source="random-unknown-bot"` at line 360. With buggy code reading `source`: first event has known source → counts 1, matching the expected value. Test passes on buggy code. The fix requires `source="hook_router"` on all three events so only `data["agent_type"]` distinguishes known from unknown.

---

### 2b. Injection test (`test_capture_retro_injector.py` — covers the "heading-only stub" bug)

**The spec says: extend the test to assert real metric content; must fail against the stub.**

The current `test_injects_block_under_metrics_heading` (lines 80–112) asserts:
- The heading `## IMPLEMENTING — metrics` is present.
- A provenance marker line is present with correct prefix/suffix.
- The `generated=` field is non-empty.

It does **not assert** that any metric value (gate rate, parks count, rework count, or any numeric field) appears between the heading and the marker. The test fixture in `_setup_project` writes a single LIFECYCLE event with no gate or task data. A stub `inject_stage_metrics` that writes only the heading and the marker — exactly the buggy behavior described in the spec — passes every assertion in this test.

**Finding:** The current test is the masking test the spec says it will fix. The spec's planned correction is to "extend to assert metric content." That correction has not been made yet; the test retains the heading-only assertion shape. This is expected in pre-lock (we are reviewing the *plan*, not the implementation). The spec's stated fix is correct — but the test-authoring discipline requires confirming the planned assertion would genuinely fail against the stub. It would, provided the assertion checks for a specific metric value (e.g., `gate_rate:` or `parks:` line with a number), not just any non-marker content.

**Concern:** The spec says "must fail against the stub" but does not specify what metric assertion to use. The `_setup_project` fixture writes only a LIFECYCLE event — there are no gate attempts in the fixture. A `stage_summary` over this empty fixture would produce metrics showing `gate_rate: N/A` or `0/0` — values that are technically present but may pass a weak "non-empty content below heading" check even if the stub produces a different but still-non-empty body. The assertion must be specific enough: e.g., assert a line matching `gate_rate: \d` or `parks: \d+`, with a fixture that drives at least one real gate event so the value is non-zero and distinguishable from a stub render.

- **Criterion violated:** Criterion 5 (test-level adequacy — the planned assertion is not specified concretely enough to confirm it fails against the stub)
- **Severity:** blocking
- **Rationale category:** N/A
- **Show your work:** `_setup_project` writes `event_type="LIFECYCLE"`. The planned metric-content assertion must name the specific field and value it expects. Without a gate or task event in the fixture, the metric values are structurally present but zero/N/A, which a stub might render as well.

---

### 2c. Bounded-read test (`test_capture_gate_check.py` — covers unbounded `readline()`)

**The spec says: rebuild the test so the payload is a single newline-less first line; must fail against the unbounded `readline()`.**

The current `test_level_reads_only_one_line` (lines 110–128) writes a valid `capture_level=standard\n` first line, then appends `~5MB` of padding **on a second line**. It asserts the result is still `"standard"`.

This test exercises "large content on the second line," which the current `readline()` already handles correctly — reading only the first line. It does **not** exercise the bug: a single 5 MB line with no embedded newline, which the current unbounded `readline()` would read entirely, consuming 5 MB per hot-path call.

The spec correctly identifies this: "rebuild with a newline-less first line." The existing test will not fail against the unbounded code. The planned rewrite — writing one 5 MB line with no newline — would fail if `readline()` is unbounded (in terms of the DoS-bound unit test which measures wall-clock; the gate-check unit test measures correct behavior, not timing).

**However:** The spec plans a *separate* DoS-bound unit test (in the new-tests-needed list) that uses a 5 MB newline-less line with a wall-clock bound. The correction to the existing gate-check test should make the test fail on the buggy unbounded read from a correctness standpoint (e.g., if the test measures only that the correct level is returned, the buggy unbounded read still returns the correct level — just slowly). This is a pure timing problem, not a correctness problem.

**Finding:** The spec says the corrected gate-check test "must fail against the unbounded `readline()`" — but a newline-less payload still returns the correct `capture_level` value from any implementation, bounded or not. The only way this test fails against the unbounded code is via timing, not via a wrong return value. Without a timing assertion, the rewritten test cannot distinguish the bounded from the unbounded path. The DoS-bound unit test carries the timing assertion; the gate-check correction needs to clarify what "fail" means here, or the two tests must be carefully coordinated.

- **Criterion violated:** Criterion 6 (behavioral completeness — the correction cannot fail on a correctness assertion alone; the spec needs to clarify how this test distinguishes bounded from unbounded behavior)
- **Severity:** blocking
- **Rationale category:** N/A
- **Show your work:** Both bounded and unbounded `readline()` return the same value for a single-line file, regardless of length. The only observable difference is wall-clock time or memory use. The gate-check test as described tests correctness (returns "standard"), not the bound. A new test that uses a byte-capped `readline(256)` can be verified by checking that a 5 MB line is truncated to its first 256 bytes and either returns a safe default (if the truncated line is not valid config) or the correct level (if the first 256 bytes contain the valid config text). The spec must clarify which of these shapes the corrected test takes.

---

### 2d. Central-redaction test (`test_capture_event_writer.py` — covers single hand-built payload)

**The spec says: replace the single hand-built payload with a `schema.SOURCES`-driven enumeration.**

The current redaction tests (`test_standard_level_strips_freetext_payload`, `test_full_level_preserves_payload`) use a fixed `source="hook_router"` event with `tool_input` as the free-text key. They do not enumerate all registered sources.

The planned correction is to iterate `schema.SOURCES` and assert that for each registered source, a `standard`-level record carries no free-text payload. This is the right shape — it catches a new producer that registers a source but bypasses redaction.

The current tests would not fail if a new source wrote free-text fields. The planned test would. The correction is sound, provided `schema.SOURCES` exists and enumerates all producers. This is the one corrected test with no catching-power concern.

- **Criterion:** Criterion 6 (behavioral completeness)
- **Severity:** no defect — correction is correctly specified

---

## 3. Existing-test impact accuracy

### 3a. File existence check

All files named in the spec's impacted list were checked:

| Spec-named file | Exists? |
|---|---|
| `tests/test_report_arithmetic.py` | Yes |
| `tests/test_capture_retro_injector.py` | Yes |
| `tests/test_capture_gate_check.py` | Yes |
| `tests/test_capture_event_writer.py` | Yes |
| `tests/test_capture_gate_check_hardening.py` | Yes |
| `tests/test_install_migration.py` | Yes |
| `tests/test_capture_active_stage.py` | **Does not exist** |
| `tests/test_capture_chokepoint*.py` | Yes (two files) |
| `tests/test_capture_token_harvester.py` | Yes |
| `tests/test_report_rendering.py` | Yes |

`test_capture_active_stage.py` is listed as a file to "run to confirm" but it does not exist. If the active-stage resolver test is expected to be pre-existing (the spec says "run to confirm"), this is a gap in the impacted list. If it will be written as new, it belongs in the new-tests-needed section, not the existing-tests-impacted section.

- **Criterion violated:** Criterion 8 (seam declaration completeness — missing test file named as existing)
- **Severity:** blocking
- **Rationale category:** N/A
- **Show your work:** `ls /home/rahvin/context-assets/assets/fbk-scripts/tests/` confirms `test_capture_active_stage.py` is absent.

### 3b. Tests not named in the spec's impacted list that touch affected functions

**`test_capture_report_integration.py`** (`test_real_producers_drive_nonzero_report_rows`) drives the real gate and task-completion through the writer and asserts first-try rate and kill rate. This test:
- Uses `source="task_completed"` in the real VERIFICATION_RESULT events (via the real chokepoint). This is the correct producer shape.
- Does **not** include a `SUBAGENT_STOP` event, so it does not exercise the subagent-count bug.
- **Does** cover the gate-rate path (first-try rate = 1.0 from one passing verification). After the fix extends the gate-rate classifier to include PIPELINE_COMMAND outcomes, this test's rate assertion may change if `classify_gate_attempts` now counts PIPELINE_COMMAND outcomes in addition to VERIFICATION_RESULT. If a task-completed `PIPELINE_COMMAND` is now classified as a gate attempt, the rate calculation changes. This test is not named in the spec's impacted list.

**`test_capture_e2e_seam.py`** (`test_two_source_cycle_joins_in_one_report`) is an end-to-end test the spec describes as one of the seam guards to add. This file already exists in the test suite. The spec's "seam-guards" slice implies these are new tests to write — but they are already present. The spec does not name this file in its impacted list. This needs clarification: are these tests being added (duplicating existing coverage) or is the spec's plan to extend/update these already-existing seam tests?

The existing `test_two_source_cycle_joins_in_one_report` asserts the retrospective carries `## VALIDATING — metrics` and the provenance marker prefix — **but does not assert any metric value**, exactly the heading-only masking problem the spec describes. This test will need to be updated under the injection-render slice, but it is not named in the spec's impacted list.

- **Criterion violated:** Criterion 6 (behavioral completeness — `test_capture_e2e_seam.py` carries the same heading-only weakness and is not named in the impacted list; `test_capture_report_integration.py` may be affected by the gate-rate extension but is not named)
- **Severity:** blocking (the e2e seam test carries the same masking gap; moderate for the report integration test)
- **Rationale category:** N/A
- **Show your work:** `test_capture_e2e_seam.py` lines 270–281 assert `## VALIDATING — metrics` heading and provenance marker prefix only, no numeric metric content. This is the heading-only masking shape the spec is correcting in `test_capture_retro_injector.py` — but the e2e seam test has the same gap and is not in the impacted list.

---

## 4. "Demonstrated to fail against pre-fix code" claim

The spec states (Technical approach, Test corrections section): "Each corrected test must be demonstrated to fail against the pre-fix code and pass after."

This is an unmeasured promise. The spec provides no:
- Named pre-fix reference point (no branch name, no commit hash, no tag)
- Defined procedure for running the corrected tests against the pre-fix code
- CI step or script that automates the demonstration

Without a reference commit or a defined procedure, "demonstrated to fail" is a verbal claim that implementation will make true. It cannot be verified at spec-review time, and there is no mechanism to check it in the pipeline.

The spec could fulfill this concretely in one of two ways: (a) name the pre-fix branch/commit the corrected tests must fail against, with a CI step that runs them there; or (b) annotate each corrected test with the specific assertion that fails on the buggy code and the reason, so a reviewer can verify mechanically without running anything. Neither is present.

- **Criterion violated:** Criterion 6 (the "fail before implementation" discipline requires the claim to be structurally verifiable, not just asserted)
- **Severity:** blocking
- **Rationale category:** N/A
- **Show your work:** Spec testing strategy section says "must fail on current code" for each of the four corrected tests. No procedure, reference commit, or CI step is named anywhere in the spec.

---

## 5. Trivially-passing or weak assertions

### 5a. DoS-bound unit test — wall-clock assertion

The spec describes: "Unit (DoS bound): `resolve_capture_level` over a `capture.cfg` that is a single 5 MB line with no newline returns a safe default within a generous wall-clock bound — covers AC-10."

The spec adds: "the DoS-bound test measures wall-clock against a generous threshold and is marked non-gating on flake, matching the existing overhead-budget test's convention."

The existing overhead-budget test (`test_capture_gate_check_overhead.py`) uses a 100ms threshold and marks the timing assertion non-gating. If the DoS-bound test follows this convention, the wall-clock assertion is advisory and does not gate the suite. This means the test can pass even when the unbounded behavior regresses (since the timing assertion is explicitly non-gating).

The correctness assertion (returns a safe default) is gating — but as established in finding 2c, a safe default is returned by both bounded and unbounded `readline()` implementations. The DoS protection is therefore tested only by the advisory timing assertion, which is explicitly non-gating.

**Finding:** The DoS-bound test as described cannot gate on the bounded-read behavior. The only protection is an advisory timing threshold. A regression to unbounded `readline()` would go undetected on a fast machine. This is a structural weakness but matches the existing convention the spec acknowledges. The spec should be explicit that this is the accepted trade-off, or the gate-check test correction (finding 2c) must carry the load by testing a behavior that is only observable when the read is bounded (e.g., the return value when the first 256 bytes contain an invalid value that the full 5 MB line would contain valid config in).

- **Criterion:** Criterion 1 (silent failure detection — the gating correctness assertion does not distinguish bounded from unbounded; the advisory timing assertion is the real guard but is non-gating)
- **Severity:** overridden by convention (spec explicitly cites the existing overhead-budget test as the model)
- **Rationale category:** "Behavior verified by [other mechanism]" — the overhead-budget test convention is the accepted pattern for timing-only regressions; the bounded-byte-cap test at the implementation level is the enforcement mechanism
- **Show your work:** `test_capture_gate_check_overhead.py` is the model: correctness assertion gating, timing assertion advisory. The DoS-bound test follows this shape. The risk is accepted by convention.

### 5b. Injection assertion — heading-only (existing test)

Already covered in finding 2b. The existing heading-only assertion is weak by the spec's own diagnosis.

### 5c. `test_attempt_after_ready_reentry_classifies_after_rework`

This test asserts `len(after_rework) >= 1` — at least one after-rework attempt. The fixture has exactly two events, one before and one after the re-entry timestamp. The expected value is exactly 1 after-rework attempt. The `>= 1` assertion would also pass if both attempts were classified as after-rework (i.e., if the boundary logic were wrong in the opposite direction). The AC-06 requirement is that the *first* re-entry timestamp is the boundary; a test that also checks the count of first-try attempts (expected 1) would catch boundary errors in both directions.

- **Criterion violated:** Assertion specificity guideline (test-authoring.md: "pair every upper-bound or ceiling assertion with a corresponding presence or lower-bound assertion")
- **Severity:** moderate — the test catches the missing after-rework case but not the over-classification case; it is not a Tier 1 violation but weakens regression protection for AC-06

---

## 6. Retired-tests justification

### `subagent-identity-field` slice: retiring "subagent-count test building source=<agent-name>"

The rationale is valid: the retired test fixture set `source=<agent-name>` rather than `source="hook_router"`, masking the always-zero bug. The surviving test (as planned) must use `source="hook_router"` and identity in `data`. As established in finding 2a, the current test has not yet completed this correction — but the retirement rationale is sound.

### `injection-render` slice: retiring "heading-only injection assertion"

The rationale is valid: the heading-only assertion passes against the metrics-less stub. The surviving test must assert metric content. The existing test has not been corrected yet (expected at pre-lock), but the retirement rationale is sound.

### `gate-config-read-bounded` slice: retiring "bounded-read test with payload on the second line"

The rationale is valid: the payload-on-second-line test does not exercise the unbounded path. The retirement is justified.

### `stage-attribution-shared-constant` slice: retiring "any active_stage/report fixture asserting COMPLETED or checkpoint state is an active stage"

The retirement is stated as a pattern description rather than a named test. Since `test_capture_active_stage.py` does not exist, it is unclear what concrete tests are being retired. If no such tests exist, the retirement list is vacuous. The spec should either name actual test functions being retired or confirm there are none to retire.

- **Criterion:** Criterion 6 (contract-evolving retirement-list awareness — the retired entry is a pattern description, not a named test)
- **Severity:** moderate — no harm done if no tests exist, but the breakdown agent cannot act on a pattern description

---

## 7. Two seam guards — injection seam and install seam

### Injection seam guard

The spec calls for an "Integration (real producer → real consumer)" test under the seam-guards slice that "drives a real gate and a real task-completion through the writer, then runs `stage_summary` for that stage and asserts the injected block contains the actual gate-rate and parks values, not just the marker."

The existing `test_capture_e2e_seam.py:test_two_source_cycle_joins_in_one_report` covers the injection seam in part — it runs real producers through the writer and checks the retrospective heading — but asserts only the heading and provenance marker, not metric values. The spec's planned injection-seam guard must assert metric content (a specific gate-rate or parks value) to be distinguishable from the existing test and from the stub.

The spec does not clarify whether the planned injection-seam guard replaces or extends the existing e2e seam test. If it extends, the existing test's heading-only assertion persists as a separate test that does not catch the stub regression.

### Install seam guard

The spec calls for an "Integration (install → capture seam)" test that "runs the install routine's sentinel-creation and settings-merge against a `tmp_path` project, then runs the router."

The existing `test_capture_gate_check.py:test_instrumented_true_for_firebreak_marked_project` checks that a pre-created sentinel marks the project instrumented — but it manually creates the sentinel rather than invoking the installer. The planned install-seam guard must invoke the installer's sentinel-creation step (not manually create the sentinel) so that a broken installer is detected.

No existing test invokes the installer shell directly in a `tmp_path` context and then confirms `project_is_instrumented` is True and a router event is recorded. The planned test is genuinely new coverage.

- **Criterion:** Criterion 7 (integration seam coverage — the injection seam has partial e2e coverage with an insufficient assertion; the install seam has no e2e coverage today)
- **Severity:** the injection-seam finding overlaps with finding 2b and 3b; the install-seam gap is correctly identified by the spec and planned to be closed

---

## Findings summary table

| # | Finding | Criterion | Severity | Blocking? |
|---|---|---|---|---|
| 1 | Subagent test sets `source=scanned_identity`, not `"hook_router"` — passes on buggy code | Criterion 6 | blocking | yes |
| 2 | Injection test asserts heading only; planned fix not specified to a concrete failing assertion | Criterion 6 | blocking | yes |
| 3 | Bounded-read test correction cannot fail on correctness alone; spec doesn't clarify the failure mode | Criterion 6 | blocking | yes |
| 4 | "Demonstrated to fail against pre-fix code" has no named reference or defined procedure | Criterion 6 | blocking | yes |
| 5 | `test_capture_active_stage.py` named in impacted list but does not exist | Criterion 8 | blocking | yes |
| 6 | `test_capture_e2e_seam.py` carries heading-only injection assertion, not in impacted list | Criterion 6 | blocking | yes |
| 7 | Retirement list for stage-attribution slice names a pattern, not a test function | Criterion 6 | moderate | no |
| 8 | `after_rework` classification assertion uses `>= 1` where `== 1` is the specific verifiable value | Assertion specificity | moderate | no |
| 9 | DoS-bound test: timing-only guard is advisory/non-gating; accepted by convention | Criterion 1 | overridden | no |

---

## What must change before re-review

1. **Subagent test (finding 1):** Correct `source` to `"hook_router"` in all three fixture events in `test_subagent_count_excludes_unknown_identity`. Show that with this change a count-via-source implementation returns 0 but the fixed implementation returns 1.

2. **Injection test (finding 2):** Add a concrete fixture-driven metric assertion to the injection test plan. The fixture must include at least one real gate event (a VERIFICATION_RESULT with a known outcome) so the expected gate-rate value is exactly computable. The planned assertion must be stated in the spec (e.g., "assert a line matching `gate_rate:` with a numeric value appears in the injected block"). Also update `test_capture_e2e_seam.py`'s injection assertion or add it to the impacted list.

3. **Bounded-read test (finding 3):** Clarify how the corrected gate-check test distinguishes bounded from unbounded behavior on a correctness assertion. One viable approach: the rewritten test uses a newline-less line whose first 256 bytes contain an invalid `capture_level` value so the bounded read returns the safe default, while the unbounded read would read the entire line and might parse a valid value embedded later. The spec must name the failure mode.

4. **Pre-fix demonstration procedure (finding 4):** Name the reference point (branch or commit of the pre-fix code) and the procedure for running the corrected tests against it, or annotate each corrected test with the specific assertion line and the reason it fails on the buggy code (e.g., "this assertion fails on the buggy code because count_known_subagents reads source, which is 'hook_router' in the production envelope, and 'hook_router' is not in the known-agents set").

5. **Missing test file (finding 5):** Clarify whether `test_capture_active_stage.py` is a pre-existing file that will be written as part of this work (in which case it belongs in new-tests-needed) or a file that must exist already (in which case it needs to be created before spec-review closes). Move it to the correct section.

6. **E2e seam test (finding 6):** Add `test_capture_e2e_seam.py` to the existing-tests-impacted list with the update: extend `test_two_source_cycle_joins_in_one_report` to assert at least one metric value in the injected block, not only the heading and provenance marker.

needs-revision
