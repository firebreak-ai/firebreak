# Test integrity criteria

Apply these criteria at the review stage in scope. Use the invoking review's
existing output contract to report evidence and limitations.

### Inputs and proportionality

Identify the review stage: planned tests, executable tests before implementation,
or final/changed implementation. Read the accepted requirements, test tasks and
verification expectations, tests and helpers, relevant production interfaces and
callers. Include existing regression tests for the changed module. For locked or
retired tests, also supply the baseline content/manifest and current authorization.
A hash alone cannot show how an assertion changed. Missing inputs limit the review;
name what is unavailable rather than inventing a contract or declaring coverage.

Apply the checks below wherever relevant. A pattern is a search lead, not a defect.
A finding must identify the required behavior, a plausible wrong implementation,
and why the actual test set would miss it. Do not demand redundant tests, internal
APIs, new infrastructure, naming changes or a preferred test architecture without
a material contract gap. User preferences are requirements only when the user set
them. Existing behavior can suggest a brownfield requirement; it does not authorize
a new requirement without operator confirmation.

### Targeted test-integrity checks

1. **Positive behavioral evidence.** Error absence, truthiness or “did not throw”
   may miss wrong results, state or effects. Check the actual required observation;
   error absence is adequate when that is the contract. Trace helper assertions,
   framework expectations and exception assertions before calling a test empty.
   Logging, warning or catching an assertion without failing the runner is advisory,
   not an effective gate. Demonstrate the faulty behavior that would escape.
2. **Expected failures and skips.** Inspect xfail, expectedFailure, skips and broad
   exception suppression, including helpers and runner configuration. For existing
   and final tests, execute the focused test when needed to establish whether a
   stale marker masks a regression or turns an unexpected pass into apparent success.
   A newly authored preimplementation test may intentionally be red; identify its
   intended failure, distinguishing missing behavior from collection, syntax,
   dependency or fixture failure. Do not require unrelated planned tests to be green.
3. **Catching power.** Trace setup → production call → observed effect → assertion;
   for a named wrong implementation, that is the input, its wrong output, and the
   assertion that fails.
   Find assertions computed with the implementation's own algorithm, mocks that
   replace the behavior claimed as tested, tautologies, unreachable observations,
   contradictory fixtures and alternate paths that hide the targeted defect.
   A permanently failing test is not a trivially passing test. Use a focused probe
   or representative fault in a disposable copy when source inspection cannot
   decide catching power; mutation of every guard is not required.
4. **Runtime fidelity.** Look specifically for real browser geometry/events,
   Canvas/WebGL, WebAudio, network protocol and filesystem semantics replaced
   entirely by permissive mocks. Name the runtime-dependent behavior and the mock's
   missing constraint. Unit mocks are fine where another test or suitable check
   actually covers that obligation. Do not infer that every runtime interaction
   requires a new end-to-end environment.
5. **Requirement coverage.** Map each material acceptance/verification obligation
   to its planned or actual test and the specific incorrect behavior that would
   fail it. Check all required observation channels (for example persisted state
   as well as emitted events), including sibling tests. A test name or execution
   count is not coverage evidence. Corrective work should expose the defect and
   preserve required existing behavior. Missing trace labels alone are not defects.
6. **Integration seams.** Trace actual producer/consumer interactions and compare
   them with the declared seams; inspect relevant interactions omitted from the
   declaration as well. Check the real chain where its behavior matters. Verify a
   claimed alternative against the cited existing integration test, available
   infrastructure or other verification evidence. A deferral rationale is not proof
   of coverage; expose the remaining gap and current user decision without silently
   expanding scope or demanding a duplicate seam inventory.
7. **Changes and retirement.** Compare assertions, shared helpers, fixtures,
   tolerances and exception handling against the baseline, including pre-existing
   tests for the changed module. Check retired tests proactively: what contract did
   they protect, is retirement authorized, and what surviving check protects that
   contract? Inspect relevant source provenance only when needed; do not read prior
   reviewer opinions. When a managed manifest applies, compare actual files/names
   and locks against it and account for authorized changes. Do not invent a lock
   requirement for an unmanaged project.

### Stage-specific application

For plans, evaluate whether planned checks can distinguish correct from plausible
wrong behavior, including fixtures and integration constraints. Planned-but-unbuilt
tests are not missing implementation. Existing-test claims still require actual
source. If a numerical claim is stronger than finite tests can prove, inspect the
stated domain, tolerances and analytical justification before alleging a gap; do
not demand exhaustive proof from ordinary examples.

Before implementation, compare executable tests with accepted tasks and verify
meaningful expected red. At final review, include existing regressions for the
changed module and actual check outcomes. Passing execution alone does not establish
catching power; source reasoning alone must not be reported as an executed result.

