## Intent Phase

The intent phase answers: *What is this work, and why are we doing it?* The output is a PRD (Product Requirements Document) and a behavior inventory that together give the feature a defined boundary before any design begins.

Open with a structured interview. Draw out the user's understanding of the problem, the goals, and the constraints. For an established project, read the architecture and intent overview first (`ai-docs/<project-name>/<project-name>-overview.md`) and ask only about the delta — what is different or new about this feature relative to what is already understood.

Write the PRD and behavior inventory in plain language. Do not sketch technical designs here; those belong in the design phase.

---

## Required PRD Sections (10)

Write each section as a bare `##` heading in the PRD file — `## Vision`, `## Problem statement`, and so on, in the order below, with no leading number. The gate's section parser does not recognize numbered headings such as `## 1. Vision`. Do not skip or combine sections.

**Vision** — One or two sentences on what this work enables and why it matters.

**Problem statement** — The specific problem this work solves. Focused paragraph; avoid restating the solution.

**Goals and non-goals** — Explicit scope boundaries. Non-goals prevent scope creep; include at least one.

**Use cases** — The concrete user scenarios this work supports. Reference behavior IDs (B-NNN) where applicable so the gate can verify bidirectional consistency with the inventory.

**Functional requirements** — What the system must do. Reference behavior IDs.

**Non-functional requirements** — Performance, availability, security, scalability constraints.

**Edge cases and failure modes** — How the system behaves when things go wrong. Graceful degradation paths and known boundary conditions.

**Dependencies** — External systems, services, libraries, or prior features this work requires.

**Success metrics** — How you will know the work succeeded. Measurable outcomes, not vague qualities.

**Open questions** — Unresolved decisions that must be answered before design begins. When all questions are resolved, write `None.`

---

## Behavior Inventory

`behavior-inventory.yaml` is a YAML file listing every discrete behavior the feature introduces or changes. Each behavior has an identifier (B-NNN), a description, and a PRD reference.

The gate enforces bidirectional consistency:
- Every B-NNN in the inventory must be referenced in the PRD.
- Every B-NNN referenced in the PRD must appear in the inventory.

Example entry:

```yaml
behaviors:
  B-001:
    description: User authentication flow
    prd_reference: prd.md
```

---

## Required Artifacts

| Artifact | Path | Purpose |
|---|---|---|
| PRD | `ai-docs/<feature>/prd.md` | 10-section requirements document |
| Behavior inventory | `ai-docs/<feature>/behavior-inventory.yaml` | B-NNN behavior registry |
| Grilling log | `ai-docs/<feature>/grilling-log-intent.md` | Interview record with decision blocks |
| Fresh-eyes report | `ai-docs/<feature>/fresh-eyes-intent.md` | Independent review of the PRD |

### Grilling log

The grilling log records the intent interview. A well-formed log must contain at least one `### ` decision-slug heading and a `Confirmed:` reflect-back line. Example:

```markdown
### scope-clarification
- Question: Does B-001 need bulk mode?
- Recommendation: Defer to v2.
- Answer: Not in scope.
- Confirmed: Yes, bulk mode deferred to v2.
```

### Fresh-eyes report

The fresh-eyes report is an independent read of the PRD by a reviewer who was not in the grilling session. The gate checks that the `## Critical` section is empty — no open critical observations before the phase gate passes.

---

## Established Projects: Read the Overview First

When working within an established project, load the project overview before opening the interview:

```
ai-docs/<project-name>/<project-name>-overview.md
```

Ask only about what is new or different. Do not re-derive architectural decisions already established in the overview.

---

## Gate

When the user signals the intent phase is complete, run the intent gate:

```
python3 fbk.py intent-gate ai-docs/<feature>
```

The gate checks:
1. PRD is present with all 10 required sections.
2. Behavior inventory is present and bidirectionally consistent with the PRD.
3. Grilling log is present and well-formed (has a `### ` decision block and a `Confirmed:` line).
4. Fresh-eyes report is present with no open critical observations.
5. Runs an injection scan on the PRD, inventory, and grilling log (non-blocking — counts are reported but do not fail the gate).

Exit 0 = pass. Exit 2 = structural failures (listed in the JSON output).

On gate pass, proceed to the design phase (`/fbk-design`).
