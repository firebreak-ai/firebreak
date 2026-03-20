---
id: T-04
type: implementation
wave: 2
covers: ["AC-03"]
files_to_modify: ["../../home/dot-claude/docs/sdl-workflow/feature-spec-guide.md"]
test_tasks: ["T-02"]
completion_gate: "feature-spec-guide.md contains user verification steps subsection, integration seam declaration subsection, and runtime value precision guidance"
---

## Objective

Updates the feature spec guide with three new required subsections: user verification steps (in testing strategy), integration seam declaration (in technical approach), and runtime value precision guidance.

## Context

The current spec template at `home/dot-claude/docs/sdl-workflow/feature-spec-guide.md` has 9 required sections but no user verification steps, no integration seam declarations, and no guidance on runtime value precision. The greenfield test showed that without UV steps, specs produced only unit tests (no e2e). Without seam declarations, integration boundaries went untested. Without runtime precision, specs used conceptual shorthand that caused key-code bugs.

The existing testing strategy section (section 5) has three subsections: "New tests needed", "Existing tests impacted", "Test infrastructure changes." The UV steps subsection goes after these.

## Instructions

1. In section 5 (Testing strategy), after the existing three subsections, add:

   **User verification steps** — "How would a human verify this feature works?" Numbered steps, each following action → observable outcome format. State: "Typically 3-8 for user-facing features. Infrastructure or internal features may have fewer with documented rationale." Each step maps to at least one e2e or integration test entry in "New tests needed". The mapping is explicit — each test entry references the UV step(s) it covers. Give the examples from the spec: UV-1 through UV-3 with the space-invaders format.

2. In section 4 (Technical approach), add at the end:

   **Integration seam declaration** — When the feature introduces or modifies interactions between modules, declare integration seams as a checklist. Each entry: two components, the shared state or interface, and the convention. Use the examples from the spec. State: checklist format, not freeform. Required when the technical approach references multiple components.

3. Add a new guidance note (can be at the end of section 4 or as a standalone subsection):

   **Runtime value precision** — When a spec references runtime values (key codes, event names, API paths, configuration keys, enum values, string constants), use the exact runtime representation, not conceptual shorthand. Conventions crossing module boundaries should be documented once and referenced consistently.

## Files to create/modify

Modify:
- `home/dot-claude/docs/sdl-workflow/feature-spec-guide.md`

## Test requirements

Semi-manual: Verify the updated guide contains all three subsections by running `/spec` on a test feature and confirming the skill prompts for UV steps and seam declarations.

## Acceptance criteria

AC-03: UV steps subsection with action→outcome format, integration seam declaration with checklist format, and runtime precision guidance are present in the spec template.

## Model

Sonnet

## Wave

Wave 2
