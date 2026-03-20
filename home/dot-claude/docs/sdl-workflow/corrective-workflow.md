## Full Diagnostic Workflow

Use when: new bug class, unknown root cause, or multiple systems affected with unclear interaction.

1. **Write behavioral tests** that define "working" from the user's perspective. Tests should verify real user interactions, not just the absence of errors. Writing tests first prevents the fixing agent from writing tests that validate its own fix rather than the intended behavior.
2. **Run tests and identify failures** — the failing tests are the bug specification. Each failure is a concrete, observable deviation from intended behavior.
3. **Root cause analysis** by context-independent diagnosis agents. The diagnosis agent has no access to the implementing agents' reasoning — it reads the codebase, failing tests, and bug description independently. Context independence prevents inheriting the assumption that the code is correct.
4. **Spec the fix**, constrained by diagnosis findings and pre-existing tests. The fix spec references the diagnostic tests as completion gates.
5. **Review** — council evaluates fix design and test coverage. The test reviewer applies Tier 2 corrective guidance: existing failing tests map to UV steps as "currently fails because [bug], fix will make it pass by [mechanism]."
6. **Breakdown and implement** — fix constrained by behavioral tests as completion gate. Use `category: corrective` in `task.json` for relaxed gate invariants (test tasks can cover ACs without paired implementation tasks).
7. **Retest** — if failures remain, return to step 3. Each iteration may reveal a different root cause or a test design issue.

---

## Fast-Track

Use when all four conditions are met:
- Root cause is known and identical to a previously-reviewed fix
- Fix is mechanical (same pattern, different file)
- Test patterns are already validated (reuse existing calibrated approaches)
- No design decisions involved

**Process**: Identify bug → write fix → write/update test → verify. No council review, no breakdown gate, no agent team — single agent executes the fix directly. Fast-track bypasses `/spec` entirely.

---

## Escalation

If a fast-track fix does not resolve on first attempt, escalate to the full diagnostic workflow. Do not iterate within fast-track — the value of fast-track is that it works on the first try because the pattern is known.

Enter the full diagnostic workflow at step 1 (write behavioral tests) if no adequate tests exist from the fast-track attempt, or at step 3 (root cause analysis) if the fast-track's tests are adequate but the fix failed.

---

## Entry-Point Classification

The `/spec` skill detects corrective intent from the developer's description — bug reports, references to failing tests, or explicit fix intent. When detected, the skill asks: "This sounds like corrective work. Should I follow the diagnostic workflow (behavioral tests first) or the standard feature flow?"

On confirmation, the spec records `workflow: corrective` in its frontmatter. This propagates through the pipeline:
- `/breakdown` sets `category: corrective` in `task.json`
- The task reviewer gate applies relaxed invariants (test tasks can cover ACs without paired implementation tasks)
- The test reviewer applies Tier 2 corrective guidance (existing failing/passing test variants)

Fast-track does not enter the pipeline. The developer applies the fix directly without invoking `/spec`.

---

## Pipeline Integration

- **Test reviewer** (CP1): Tier 2 behavioral completeness accommodates corrective specs with two additional "show your work" variants — existing failing tests ("currently fails because [bug]") and existing passing tests ("must continue to pass after fix"). See `test-reviewer.md`, Criterion 3.
- **Task reviewer gate**: `category: corrective` relaxes the AC coverage invariant — test tasks can cover ACs without paired implementation tasks. See `task-reviewer-gate.sh`.
- **Baseline-snapshot regression check**: Failing diagnostic tests are automatically excluded from the baseline because they fail at capture time. After the final wave, all tests (including diagnostic tests) must pass. See `implementation-guide.md`.
