## Scope Recognition

Determine scope from the user's description before drafting anything:

- **Feature-level**: User describes a specific capability, behavior change, or bounded piece of work. Proceed directly to the 9-section feature spec.
- **Project-level**: User describes a new application, platform, or major initiative. Produce a 6-section project overview first; feature boundaries emerge through iteration.

When scope is ambiguous, ask one clarifying question before starting.

---

## Feature-Level Spec (9 Required Sections)

Write each section. Do not skip or combine sections.

**1. Problem** — State the problem the feature solves. One focused paragraph. Avoid restating the solution.

**2. Goals / Non-goals** — List explicit scope boundaries. Non-goals prevent scope creep during review and task breakdown; include at least one.

**3. User-facing behavior** — Describe what the user sees or experiences. Reference UI states, error messages, and edge cases the user encounters. Omit implementation details.

**4. Technical approach** — Describe architecture, data flow, and key design decisions. Be specific enough that another engineer can review it and a task compiler can derive implementation tasks without asking follow-up questions. Name the components, data stores, APIs, and integration points.

- **Integration seam declaration** (required when the technical approach references multiple interacting components): Declare integration seams as a checklist. Each entry identifies two components, the shared state or interface, and the convention that must be consistent across both sides. Example:
  > - [ ] InputHandler → WeaponSystem: key string convention (`event.key` values: `' '` for spacebar)
  > - [ ] InvaderGrid → main.js: enemy projectile array wiring (spawn, update, collision, cleanup)

  Use checklist format, not freeform prose. The test reviewer at CP1 validates that each declared seam has integration or e2e test coverage.

- **Runtime value precision**: When a spec references runtime values — key codes, event names, API paths, configuration keys, enum values, string constants — use the exact runtime representation, not conceptual shorthand. Conventions that cross module boundaries should be documented once in the spec and used consistently. Example: "The InputHandler stores `event.key` values: `' '` for spacebar, `'Enter'` for enter, `'ArrowLeft'`/`'ArrowRight'` for movement."

**5. Testing strategy** — Three required subsections. Generic phrases like "add unit tests" are not acceptable; fail any draft that contains them.

- **New tests needed**: For each test, state what behavior it validates, at what level (unit / integration / e2e), and which AC it covers. Example: "Unit test: `parseToken()` returns null for expired JWTs — covers AC-03."
- **Existing tests impacted**: In brownfield, search the test suite for tests that cover the files and functions this feature modifies. List each test file or test name, the affected code path, and the expected change (update assertions / fixtures / mocks). In greenfield, write: "None — no existing test suite."
- **Test infrastructure changes**: List new fixtures, mocks, test utilities, or test data needed. In greenfield, include bootstrapping the test framework if no test infrastructure exists.
- **User verification steps**: "How would a human verify this feature works?" Numbered steps, each following a structured **action → observable outcome** format:
  > UV-1: Press spacebar → projectile fires and moves upward
  > UV-2: Projectile hits invader → invader is destroyed and explosion particles appear

  Typically 3-8 for user-facing features. Infrastructure or internal features may have fewer with documented rationale. If a step cannot be parsed into an action-outcome pair, the spec is not ready for review.

  Each UV step maps to at least one e2e or integration test entry in "New tests needed." The mapping is explicit — each test entry references the UV step(s) it covers (e.g., "E2e test: fire projectile and verify movement — covers UV-1"). The test reviewer at CP1 validates this mapping. At CP2, the reviewer verifies the mapping survived into the task breakdown.

**6. Documentation impact** — Required even when there is nothing to update.

- **Project documents to update**: Name each document and state the specific change. Write "Add `POST /token` endpoint to API reference" — not "update docs." Write "None — no project documents affected" when nothing requires updating.
- **New documentation to create**: List any new doc artifacts the feature requires (e.g., runbook, ADR, user guide section).

**7. Acceptance criteria** — List independently verifiable conditions for "done." Use short identifiers: AC-01, AC-02, ... Each AC must be testable by a single automated check or a reproducible manual step. Avoid vague qualities ("fast," "easy to use").

**8. Open questions** — List unresolved decisions the user or stakeholders must answer before Stage 2. Before approving the gate, every item must either be resolved or have explicit rationale for deferral. When a question is resolved, move its conclusion into the relevant spec section and remove it from this list. An empty list is valid and expected when the spec is complete.

**9. Dependencies** — List external systems, libraries, APIs, and other features this feature requires. Include version constraints when relevant.

---

## Project-Level Overview (6 Required Sections)

**1. Vision** — What the project is and why it exists. One or two paragraphs.

**2. Architecture** — System-level design: major components, data flow, integration points. Specific enough that individual feature specs can reference it rather than re-derive architectural decisions.

**3. Technology decisions** — Language, framework, infrastructure choices with rationale. Rationale prevents re-litigation in feature specs.

**4. Feature map** — List all features with brief descriptions. Include dependency ordering: state which features must complete before others can begin.

**5. Cross-cutting concerns** — Shared infrastructure, conventions, and patterns that apply across features (e.g., auth, logging, error handling, CI/CD).

**6. Open questions** — Unresolved project-level decisions. Apply the same resolution requirement as feature-level open questions before Stage 2.

After the user agrees on the overview and feature decomposition, ask: "Which feature would you like to spec first?" That feature enters Stage 1 as a feature-level spec.

---

## Iterative Authoring

Draft sections and ask clarifying questions on meaningful design decisions — trade-offs the user must weigh, not implementation details you can resolve independently.

Ask about: data ownership, consistency guarantees, API contracts, security boundaries, rollout strategy, and scope edge cases.

Do not ask about: naming conventions, internal variable types, or choices that have no user-visible or architectural consequence.

Surface open questions explicitly in section 8 rather than silently assuming an answer.

Refuse to write code. Stage 1 produces specification artifacts only. If the user asks for code, explain that implementation begins in Stage 3 after review.

---

## Greenfield vs. Brownfield

Discover which environment applies by examining the codebase. Do not ask the user to classify it.

**Brownfield indicators**: Existing source files, test suite, dependencies, CI configuration.
- Testing strategy section 5b: search the test suite for tests covering the files and functions this feature modifies. Reference them by name.
- Technical approach: identify integration risk with existing components.
- Task compilation will modify existing files — note which ones.

**Greenfield indicators**: No source files or test suite present.
- Testing strategy section 5b: write "None — no existing test suite."
- Testing strategy section 5c: include bootstrapping the test framework as a required infrastructure change.
- For project-level greenfield: the first feature is often scaffolding (build config, directory structure, CI, test infrastructure).

---

## Artifact Paths

Write output files to these paths:

- Feature-level spec: `ai-docs/<feature-name>/<feature-name>-spec.md`
- Project-level overview: `ai-docs/<project-name>/<project-name>-overview.md`
- Individual feature specs within a project: `ai-docs/<project-name>/<feature-name>/<feature-name>-spec.md`

Create the directory if it does not exist.

---

## Verification Gate

**Structural prerequisites** (deterministic — call the gate script when the user signals completion):

Feature-level:
- All 9 sections present and non-empty.
- Open questions section is empty or each deferred item has explicit rationale.

Project-level:
- All 6 sections present and non-empty.
- Feature map contains at least one feature with a description.
- Open questions section is empty or each deferred item has explicit rationale.

**Semantic criteria** (present these to the user for assessment after structural pass):
- AC phrasing: each AC is independently verifiable, not a vague quality.
- Testing strategy: identifies specific behavioral coverage with AC traceability; no generic phrases.
- Technical approach: specific enough for a reviewer and task compiler to work from without additional questions.
- Feature boundaries (project-level): cohesive capabilities, not arbitrary splits.

---

## Transition

When the user signals the spec is complete:

1. Run structural prerequisites by calling the gate script.
2. If the gate fails: report which checks failed and what is missing.
3. If the gate passes: confirm structural completeness and present the semantic criteria for the user to assess.
4. If the user is satisfied: ask "Would you like to move to spec review?"
5. If agreed: invoke `/spec-review <feature-name>`.

For project-level: after the user agrees on the overview and feature decomposition, ask which feature to spec first. Do not invoke `/spec-review` until a complete feature-level spec passes the gate.
