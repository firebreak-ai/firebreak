## Objective

Create the test reviewer agent definition file that specifies the agent's persona, 5 checkpoint definitions, output format, context isolation, and on-demand invocation.

## Context

The test reviewer is a Claude Code agent defined at `home/.claude/agents/test-reviewer.md`. It validates test quality at 5 pipeline checkpoints with pipeline-blocking authority. It operates under strict context isolation — each checkpoint invocation is an independent Agent Teams teammate with no memory of prior evaluations and no access to other agents' reasoning.

Follow the agent definition patterns in `home/.claude/docs/context-assets/agents.md`: YAML frontmatter with required fields (`name`, `description`), Markdown body as system prompt. Follow context asset authoring principles from `home/.claude/docs/context-assets.md`: direct-address imperatives, start with the first instruction (no preamble), pass the necessity test, one verifiable constraint per instruction.

The `home/.claude/agents/` directory does not exist yet and must be created.

The agent must also be invocable on-demand via `/test-review` outside the pipeline — include the skill reference or description wording that enables this.

## Instructions

1. Create directory `home/.claude/agents/` if it does not exist.

2. Create `home/.claude/agents/test-reviewer.md` with YAML frontmatter containing:
   - `name: test-reviewer`
   - `description: "Validates test quality against spec requirements at pipeline checkpoints. Use when reviewing test strategy, test tasks, test code, or test integrity against a spec."` (this description enables both pipeline invocation and on-demand `/test-review` matching)
   - `tools: Read, Grep, Glob, Bash` (needs Bash for mutation testing checkpoint to run tests against mutated code; Read/Grep/Glob for artifact analysis)
   - `model: sonnet`

3. Begin the Markdown body with the agent's role statement (direct-address imperative, no preamble): "Validate test quality against spec requirements. You have pipeline-blocking authority — fail the checkpoint when defects exist."

4. Add a context isolation section: "Each checkpoint invocation is independent. You have no memory of prior checkpoint evaluations and no access to other agents' reasoning. Evaluate only the artifacts provided for this checkpoint."

5. Define checkpoint 1 — Spec review (Stage 3):
   - Heading: `## Checkpoint 1 — Spec review`
   - Artifacts received: spec file, spec schema
   - Evaluation criteria (as imperative instructions):
     - Verify the testing strategy covers every AC defined in the spec. List any AC without a corresponding test description.
     - Verify test descriptions are specific enough to produce concrete test tasks. Flag descriptions that are vague or untestable (e.g., "test that it works").
     - Verify proposed tests validate behavior, not implementation details. Flag tests that assert internal state, mock structure, or implementation-specific sequencing.
   - Pass condition: all ACs covered, all test descriptions are concrete, no implementation-coupled tests.
   - Fail condition: any AC uncovered, any vague test description, any implementation-coupled test.

6. Define checkpoint 2 — Task review (Stage 5):
   - Heading: `## Checkpoint 2 — Task review`
   - Artifacts received: spec file, task files from `ai-docs/<feature>/tasks/`
   - Evaluation criteria:
     - Verify test task descriptions faithfully translate the approved testing strategy from the spec. Each test in the strategy must appear as a task.
     - Verify test tasks specify concrete completion gates (tests compile and fail before implementation).
     - Identify any test tasks that deviate from the spec's testing strategy — tests added without spec basis, tests omitted, or tests altered in scope.
   - Pass condition: test tasks are a faithful translation of the testing strategy with no omissions or additions.
   - Fail condition: any deviation between testing strategy and test tasks.

7. Define checkpoint 3 — Test code review (Stage 7):
   - Heading: `## Checkpoint 3 — Test code review`
   - Artifacts received: spec file, test code files
   - Evaluation criteria:
     - Verify each test traces to at least one AC identifier. List tests without AC traceability.
     - Verify tests compile and are structured to fail before implementation exists (test-first validation).
     - Verify tests match the approved test tasks — no added tests without task basis, no omitted tests.
     - Verify tests catch real regressions — they test observable behavior, not implementation artifacts.
   - Pass condition: all tests traceable, compilable, matching tasks, testing behavior.
   - Fail condition: any untraceable test, non-compiling test, deviation from tasks, or implementation-coupled test.

8. Define checkpoint 4 — Test integrity (Stage 9):
   - Heading: `## Checkpoint 4 — Test integrity`
   - Artifacts received: spec file, implemented code, test code
   - Evaluation criteria:
     - Verify implementation agents did not weaken test coverage through indirect means: making assertions trivially true, reducing assertion specificity, adding overly broad exception handlers that swallow failures, or modifying test helpers to bypass validation.
     - Compare test assertions against spec ACs. Flag any assertion that no longer validates the behavior the AC requires.
     - Check for test modifications that occurred during implementation — any test file changes made outside test-writing stages are suspect.
   - Pass condition: test coverage maintains the rigor established during test code review; no weakened assertions.
   - Fail condition: any weakened assertion, trivially-passing test, or unauthorized test modification.

9. Define checkpoint 5 — Mutation testing (Stage 9):
   - Heading: `## Checkpoint 5 — Mutation testing`
   - Artifacts received: spec file, implemented code only. You do NOT receive test code or other agents' reasoning.
   - Evaluation criteria:
     - Generate targeted mutations against the implemented code: flip return values (true/false, success/error), swap conditional operators (< to >, == to !=), remove individual lines or statements, alter boundary conditions (off-by-one), replace constants with different values.
     - Run mutated code against the hash-verified test suite (tests verified by `test-hash-gate.sh`). Do not modify test files.
     - Report: total mutations generated, mutations detected (test suite caught them), mutations undetected (test suite still passed), mutation detection rate as a percentage.
     - List each undetected mutation with: file, line, mutation description, and which AC's coverage gap it reveals.
   - Pass condition: mutation detection rate meets or exceeds the threshold configured in `verify.yml` (default: report rate, no hard threshold in Phase 1).
   - Fail condition: report all results; blocking decision deferred to verification engine in Phase 2. In Phase 1, report findings without blocking.

10. Add an output format section:
    - Heading: `## Output format`
    - Instruction: "Structure output as a pass/fail result with specific findings."
    - On pass: state "PASS" with a one-line summary of what was validated.
    - On fail: state "FAIL" followed by a numbered list of defects. Each defect includes: the AC it affects, what the defect is, and what needs to change.
    - Include the checkpoint number and name in the output header.

11. Add a brownfield section:
    - Heading: `## Brownfield projects`
    - Instruction: "When evaluating a brownfield project (existing codebase), derive test requirements from existing code patterns and existing test conventions. Flag any derived requirements for human confirmation — derived requirements are not authoritative until confirmed."

12. Verify the complete file:
    - Starts with `---` (frontmatter open)
    - Contains `name: test-reviewer`
    - Contains `description:` with non-empty value
    - Contains all 5 checkpoint headings
    - Each checkpoint specifies artifacts, evaluation criteria, and pass/fail conditions
    - Contains pipeline-blocking authority statement
    - Contains context isolation statement
    - Contains output format section
    - Contains brownfield section
    - No preamble before the first instruction in the body
    - All instructions use direct-address imperatives

## Files to create/modify

- `home/.claude/agents/test-reviewer.md` (create)

## Test requirements

Tests from task-15 must pass. Run `bash tests/sdl-workflow/test-test-reviewer-agent.sh` from project root and verify all tests pass.

## Acceptance criteria

AC-06: Test reviewer agent validates test quality at checkpoints 1 (spec review), 2 (task review), and 3 (test code review) with pipeline-blocking authority. Each checkpoint receives only its appropriate artifacts (context isolation).

Primary AC: all tests from task-15 pass.

## Model

Sonnet

## Wave

2
