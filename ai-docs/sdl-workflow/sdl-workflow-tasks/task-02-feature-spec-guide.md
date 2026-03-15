# Task 02: Create Feature Spec Guide

## Objective

Create the leaf doc that provides detailed Stage 1 (Spec) guidance for agents co-authoring specifications with users.

## Context

This doc is loaded by the `/spec` skill when Stage 1 is active. It is the agent's primary reference for how to guide spec creation. The agent reads this doc, not the pipeline spec — everything the agent needs must be here.

### Scope recognition

The agent handles two scope modes, determined from the user's description:

- **Feature-level**: A single capability going through the full 4-stage pipeline. The user describes a specific feature, behavior change, or bounded piece of work.
- **Project-level**: An entire system or major initiative. The user describes a new application, platform, or project. Feature boundaries emerge naturally as the design is iterated.

### Feature-level spec structure (9 required sections)

1. **Problem** — What problem does this feature solve?
2. **Goals / Non-goals** — Explicit scope boundaries.
3. **User-facing behavior** — What the user sees or experiences.
4. **Technical approach** — Architecture, data flow, key design decisions.
5. **Testing strategy** — Three subsections, all required:
   - *New tests needed*: what each test validates, at what level (unit/integration/e2e), which AC it covers.
   - *Existing tests impacted* (brownfield): specific tests covering affected code paths, with expected change (update assertions/fixtures/mocks). In greenfield: state "None — no existing test suite."
   - *Test infrastructure changes*: new fixtures, mocks, utilities needed. In greenfield: includes bootstrapping test framework.
   **"Add unit tests" is not a testing strategy.** The agent must identify specific behavioral coverage and, in brownfield, search the test suite for tests covering affected files and functions.
6. **Documentation impact** — Required even when empty. Subsections:
   - *Project documents to update*: which docs and what changes (e.g., "Add endpoint to API docs," not "update docs").
   - *New documentation to create*: any new doc artifacts the feature requires.
   "None — no project documents affected" is valid. Omitting the section is not.
7. **Acceptance criteria** — Verifiable conditions for "done." Each independently testable. Short identifiers: AC-01, AC-02, ... These IDs trace through task breakdown and test coverage.
8. **Open questions** — Unresolved decisions. Must be empty or each deferred item has explicit rationale before Stage 2.
9. **Dependencies** — External systems, libraries, prerequisites, other features.

### Project-level overview structure (6 required sections)

1. **Vision** — What this project is and why.
2. **Architecture** — System-level design, major components, data flow.
3. **Technology decisions** — Language, framework, infrastructure with rationale.
4. **Feature map** — Features with brief descriptions and dependency ordering (which features must complete before others can begin).
5. **Cross-cutting concerns** — Shared infrastructure, conventions, patterns across features.
6. **Open questions** — Unresolved project-level decisions.

The overview captures decisions that span features. Feature specs reference it for architectural decisions rather than re-deriving them. After agreement on feature decomposition, each feature enters Stage 1 independently.

### Iterative authoring behavior

- Draft sections, ask clarifying questions on meaningful design decisions (trade-offs the user must weigh, not implementation details the agent can resolve).
- Surface open questions explicitly rather than making assumptions.
- Refuse to implement code — Stage 1 produces only specification artifacts.
- For project-level: identify feature boundaries naturally as design is iterated. Propose decomposition when boundaries become clear.

### Greenfield vs. brownfield

The agent discovers which environment it's in by examining the codebase (it does not require explicit classification from the user):

- **Brownfield**: Analyze existing code, tests, and architecture. Testing strategy references impacted existing tests (search the test suite). Review focus: integration risk. Tasks modify existing files.
- **Greenfield**: No existing codebase. Testing strategy defines the approach from scratch. In project-level greenfield, the first feature is often scaffolding (build config, directory structure, test infrastructure).

### Artifact paths

- Feature-level: `ai-docs/<feature-name>/<feature-name>-spec.md`
- Project-level: `ai-docs/<project-name>/<project-name>-overview.md` + individual feature spec files in subdirectories

### Verification gate

**Structural prerequisites** (deterministic — the `/spec` skill calls a gate script):

Feature-level:
- All 9 sections present and non-empty
- Open questions section is empty or each deferred item has rationale

Project-level:
- All 6 overview sections present and non-empty
- Feature map has at least one feature with description
- Open questions section is empty or each deferred item has rationale

**Semantic evaluation** (human judgment during co-authoring):
- AC phrasing: independently verifiable conditions, not vague qualities
- Testing strategy: specific behavioral coverage, not generic ("add unit tests" fails)
- Technical approach: specific enough for review and task compilation
- Feature boundaries (project-level): natural, cohesive capabilities — not arbitrary splits

### Transition behavior

When user signals the spec is complete:
1. Run structural prerequisites (call gate script).
2. If pass: report structural completeness and present semantic criteria for user assessment.
3. If user satisfied: "Would you like to move to spec review?"
4. If agreed: invoke `/spec-review <feature-name>`.

For project-level: after overview and feature decomposition are agreed, ask "Which feature would you like to spec first?" The selected feature enters Stage 1 as a feature-level spec.

## Instructions

1. Create `home/.claude/docs/sdl-workflow/feature-spec-guide.md`.
2. Read `home/.claude/docs/context-assets.md` for authoring principles. Apply them.
3. The doc's audience is an agent running Stage 1. Write direct imperatives. Start with the first instruction.
4. Structure the doc with these sections:

   - **Scope recognition** — How to determine project-level vs. feature-level from the user's description.
   - **Feature-level spec** — The 9-section structure with content requirements. Invest extra tokens on testing strategy (section 5) and documentation impact (section 6) — these are where agents most commonly produce generic output.
   - **Project-level overview** — The 6-section structure. Include the transition to individual feature specs.
   - **Iterative authoring** — Question style, surfacing open questions, refusing code. Keep brief — iterative dialogue is natural agent behavior; focus on what's non-obvious (e.g., meaningful vs. trivial questions, refusing code).
   - **Greenfield vs. brownfield** — Discovery-based adaptation, key differences.
   - **Artifact paths** — Where to write outputs.
   - **Verification gate** — Structural checks and semantic criteria.
   - **Transition** — What to do when user signals completeness.

5. Apply the Necessity Test: "If removed, would the agent produce a worse spec?" Testing strategy specificity is a known failure mode — invest tokens there. Generic authoring advice ("ask good questions") fails the test — the agent already does this.
6. Target: 140-200 lines.

## Files to Create/Modify

- **Create**: `home/.claude/docs/sdl-workflow/feature-spec-guide.md`

## Acceptance Criteria

- AC-02: Enables iterative spec authoring for both scopes with all required sections, testing strategy specificity, and gate behavior
- AC-15: Follows authoring principles — imperatives, self-contained, necessity-tested

## Model

Sonnet

## Wave

1
