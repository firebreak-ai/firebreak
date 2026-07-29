## Production-path exercise

Import the production module and call its exported function with known inputs. Assert on the return value or the observable state change.

When a test file does not import the module it claims to test, or imports it but does not call the function under test, flag it as not exercising the production path.

## Fixture consistency

When a test constructs multiple objects that interact (e.g., a store entry and a candidate struct that references it), verify that every field shared between them carries the same value. A mismatch between a fixture's stored object and the struct that references it creates an internally contradictory scenario — the test compiles and passes, but it does not prove what it claims to prove.

Before asserting on output, trace each fixture field that the production function reads. Confirm that the corresponding field in every dependent object is set to a consistent value.

## Zero-value fixture fields

Set every field in a test fixture that the production function reads. When a field's zero value is the intentional test input, add a comment stating that explicitly: `// zero value is the correct input for this scenario`.

## Recognizing re-implementation

A test re-implements production logic when the test body contains computation that mirrors what the production function does internally. Signals:

- The test contains a loop, conditional branch, or arithmetic that replicates the production function's algorithm
- The test manually constructs the expected behavior step-by-step instead of calling a function and asserting on its output
- The test's assertions verify the test's own inline logic rather than the production function's behavior
- Comments in the test say "we implement the logic here" or "replicate the production behavior"

## Self-assignment assertions

An assertion that sets a value and immediately asserts it is trivially true. Signals:

- The test assigns `obj.prop = value` then asserts `expect(obj.prop).toBe(value)`
- The assertion verifies the test's own setup, not a production function's output
- A contract comment explains why the test simulates a behavior from another module

When the production path that produces the side effect is not callable from the test, do not simulate it with a self-assignment. Add a contract comment documenting the expected behavior and omit the trivially-true assertion.

## When production code is not importable

When the behavior under test lives inside a function that cannot be imported in the test environment (a framework lifecycle method, a monolithic function mixing multiple concerns, a browser-only code path), flag it as a blocker: "This behavior is not testable through a direct function call. The production code needs to be restructured to expose this behavior as an importable function."

Report the blocker to the orchestrator or user to trigger an escalation that adds an extraction task.

## E2e tests

The production-path exercise principle applies to unit and integration tests, not e2e tests.

## Test isolation

Each test asserts on one behavior.

Receive test dependencies as setup, not as ambient state. Use beforeEach/setUp to create fresh state for each test.

## Shared test infrastructure

When multiple test files in the same package, module, or suite need the same helper function, fixture builder, script fragment, or field accessor, declare it once in a shared location and have every file reference it. Do not repeat the declaration in more than one file — a symbol declared identically in two files sharing a compilation scope is a redeclaration error, and duplicated inline logic (an ad hoc field accessor rewritten per file) drifts as the underlying data shape changes.

## Stand-ins only for code we don't own

Run the actual production code in every test. The purpose of testing is to verify the code we own; a stand-in that replaces code we own does not test that code.

Use a stand-in (mock, stub, fake) only when the collaborator is code we do not own — external services (databases, network APIs, model-inference endpoints), the operating system, the file system, the clock, random-number generation, and third-party libraries with side effects the test must control.

When the goal of a test is to evaluate the real behavior of external code — prompt quality from a real model, performance against a real database, an end-to-end integration — call the external code directly. Both stand-ins and real-call integration apply only to code we do not own.

Cost (slow, non-deterministic, expensive) is not justification to stand in for code we own. When an owned collaborator is too slow or non-deterministic to test against directly, refactor it to expose a faster seam, integrate at a higher level so the slow unit is exercised in context, or accept the cost. None of these uses a stand-in for owned code.

Each mock added raises the cost of refactoring — production-code changes break tests on mock interaction patterns rather than on behavioral regressions.

See `fbk-sdl-workflow/feature-spec-guide.md` §5 "Mocking justifications" for the spec-time counterpart.

## Assertion specificity

Assert on specific expected values, not truthiness or type alone. `expect(result).toBe(42)` catches regressions that `expect(result).toBeTruthy()` misses — any non-zero value would pass the truthiness check. When the expected value is not a fixed literal (e.g., it depends on input), assert on a derived property that is specific enough to catch behavioral changes: length, key presence, substring, or structural shape.

Weak assertion: `assert result is not None`
Specific assertion: `assert result.status_code == 200 and result.body["user_id"] == expected_id`

Pair every upper-bound or ceiling assertion with a corresponding presence or lower-bound assertion. A ceiling check (`length ≤ 40`) passes trivially when the target content is absent; a presence check (`length ≥ 5` or required-marker grep) fails when content is absent. Both together give regression protection in both directions.

When asserting behavior at a boundary or extreme input value, hand-derive the expected numeric result with shown arithmetic and assert equality to that derived value — do not substitute a qualitative comparison (`!=`, a strict inequality, "stays above/below"). Floating-point behavior at extremes (underflow, saturation to a floor or ceiling) can satisfy a qualitative check while the actual numeric path is wrong.

## Deriving expected values for existing behavior

When a test pins an expected value for equivalence with existing, already-shipped production code (a regex, a parser, a formatting function), derive that value by executing the shipped code or by quoting one of its existing test vectors — do not hand-simulate what the shipped code would produce. A hand-simulated expectation can silently diverge from the real implementation, and the test will assert the wrong value with full confidence.

## Assert the contract, not the incidental implementation

Before asserting on an implementation detail (an internal state value, a specific call sequence, a resource's exact final state), check whether the behavioral contract actually requires that detail, or whether a weaker assertion would still prove the contract. An assertion stricter than the contract forces the implementation to satisfy the stricter version, which can push it toward a worse implementation choice (withholding a cleanup call, over-fitting to a coincidental value) purely to make the test pass.

## Distinguish value-equivalence from code-path-equivalence

When two input scenarios are expected to produce the same output through different code paths, do not assume a test on one scenario "subsumes" the other. Write a distinct test for each code path — one whose fixture actually exercises that path — and confirm each test would fail if that specific path were deleted or altered.

## Structural assertions on text artifacts

When tests grep for content in text files (config, markdown, structured docs, logs), assert on anchored structural markers — section headings, frontmatter keys, config keys — rather than vocabulary or verb choices within body text.

Prefer: `grep -q '^## Section Name$'` or `grep -q '^key: value'` (structural marker)
Avoid: `grep -q 'review\|approve'` (body vocabulary)

Structural markers change only when the document's structure changes. Vocabulary inside a section changes on normal editing passes (synonyms, rephrasing). A test asserting on vocabulary breaks when wording is updated even though the structure the test meant to verify is intact.

## Anchored section extraction

When a test measures a subsection of a text file, anchor both the start and the end of the extraction range. A helper that stops at the first matching delimiter will silently measure only the preamble if that delimiter also terminates a different section.

After writing an extraction helper, verify the extracted range covers the full target section — not just its opening lines. Upper-bound assertions on a truncated range pass trivially for content that exceeds the real bound.

## Test name accuracy

Name tests after the behavior they verify, not the implementation mechanism they exercise. A test named "calls the database query function" describes an implementation detail; "returns user by email" describes the behavior. When the implementation changes but the behavior remains the same, implementation-named tests appear broken even though the behavior is intact.

When reviewing test names, check that the name would remain accurate if the implementation were rewritten to produce the same behavior through a different mechanism.

## Assertion label accuracy

When an assertion uses a regex or compound check, write the label to match the full scope of what the check asserts — not a subset. Update labels when the regex is expanded.

If the regex is `'reviewer|review|approve'`, the label must not read "checks for 'review' keyword" — write "checks for review/approve synonyms" instead.

A label describing a narrower check than the regex performs makes failures misleading: a reader diagnoses the wrong condition and may fix the wrong thing.
