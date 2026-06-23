# Task Review Lens

This lens reviews a compiled task set (breakdown output) to determine whether each task gives an implementing agent enough information to act without making design decisions, and whether the tasks collectively satisfy all acceptance criteria in the spec.

```
output_mode: finding
output_contract: verdict-contract
```

---

## 1. Lens identity

This lens reviews a compiled breakdown — the set of task files produced by the breakdown stage — from the perspective of an implementing agent that will execute each task in isolation. The core question is: given only a task file and the context assets it names, can an agent implement the task correctly without guessing at scope, design, or intent?

```
output_mode: finding
output_contract: verdict-contract
```

---

## 2. Finding types

| Type | Definition | Ship decision |
|---|---|---|
| `under-specified` | A task instruction is ambiguous or incomplete in a way that would force the implementing agent to make a design decision not delegated to it. | Request changes — block until resolved. |
| `coverage-gap` | An acceptance criterion in the spec has no task that covers it, leaving the criterion unimplemented. | Block — a coverage gap means the spec's contract will not be satisfied. |
| `sizing-violation` | A task's scope exceeds the file-count or complexity limit declared in the breakdown spec, or its instructions touch files belonging to a different task's declared scope. | Request changes — scope must be repartitioned. |
| `spec-conflict` | A task instruction directly contradicts the spec or a prior task's instruction for the same artifact. | Block — contradiction leaves the implementing agent with no valid path. |

---

## 3. Severity levels

| Severity | Observability | Reviewer action |
|---|---|---|
| `critical` | The defect would cause the implementing agent to produce incorrect output or block entirely — the task cannot be executed as written. | Block — do not pass the breakdown gate. |
| `major` | The defect would cause the implementing agent to make an unintended design choice or miss a behavioral requirement, but execution is not prevented. | Request changes before gate. |
| `minor` | The defect reduces clarity or increases friction for the implementing agent but does not change the likely output materially. | Comment — flag for author review; does not block gate. |

---

## 4. Type-severity validity matrix

Human-readable table:

| Type | Valid severities |
|---|---|
| `under-specified` | critical, major, minor |
| `coverage-gap` | critical, major |
| `sizing-violation` | major, minor |
| `spec-conflict` | critical, major |

Machine-readable block (parsed by `pipeline.load_lens_matrix()`):

```lens-matrix
types: [under-specified, coverage-gap, sizing-violation, spec-conflict]
severities: [critical, major, minor]
matrix:
  under-specified: [critical, major, minor]
  coverage-gap: [critical, major]
  sizing-violation: [major, minor]
  spec-conflict: [critical, major]
required: [title, location, type, severity, mechanism, consequence, evidence]
```

---

## 5. What to look for (researcher instructions)

The deterministic `task-reviewer-gate` handles mechanical checks (YAML frontmatter fields, file existence, duplicate IDs, completion-gate syntax). This lens covers the semantic quality concerns those checks cannot reach.

### Pass A — Instruction completeness

For each task file, read the instructions section and ask: could an implementing agent execute this task from the instructions alone, loading only the files the instructions name, without consulting the spec or making a design choice? Flag any instruction that:

- names a behavior to implement without specifying the expected mechanism or output shape;
- defers a decision to the implementing agent by using language such as "as appropriate," "as needed," or "decide based on context";
- references a file, function, or contract without telling the agent where to find it;
- is ambiguous between two plausible interpretations that would produce different code.

Type: `under-specified`. Severity: `critical` when ambiguity would block execution; `major` when it would produce an unintended design choice; `minor` when it adds friction only.

### Pass B — Acceptance criteria coverage

Read the spec's acceptance criteria list. For each criterion, locate the task or tasks that implement it. A criterion is covered if at least one task names it in its `covers` frontmatter field or addresses it unambiguously in its instructions. Flag any criterion with no covering task.

Type: `coverage-gap`. Severity: `critical` when the missing criterion is load-bearing for a gated behavior; `major` otherwise.

### Pass C — Scope and file boundaries

Read each task's declared `files_to_create` and `files_to_modify` fields. Flag any task where:

- the declared file list is larger than the file-count limit stated in the breakdown spec;
- a file appears in two tasks' declared scope (scope overlap creates an ordering dependency that the task graph may not express);
- the instructions direct the agent to edit files not in the declared list.

Type: `sizing-violation`. Severity: `major` for scope overlap (creates merge-conflict risk) or instruction/declaration mismatch; `minor` for file-count excess that does not create an ordering dependency.

### Pass D — Spec consistency

For each task instruction that names a specific behavior, interface, or contract, compare it against the spec. Flag any instruction that:

- names a different interface signature than the spec declares;
- calls for a behavior the spec explicitly prohibits or restricts;
- names a constant, threshold, or format that differs from the spec's value.

Type: `spec-conflict`. Severity: `critical` when the conflict would cause a gate check to fail; `major` otherwise.

---

## 6. Source-of-truth handling

Primary source: the feature spec at `ai-docs/<feature>/<feature>-spec.md`, specifically its acceptance criteria and interface declarations.

Secondary sources: the breakdown spec (file-count limits, wave ordering rules) and any interface contracts named in the spec.

When a task instruction copies a contract from the spec verbatim, the researcher must locate the spec's original and compare field by field — the task file's copy is not the source of truth.

When no spec is available: the breakdown task set itself is the primary artifact; compare tasks against each other for internal consistency (Pass D reduces to cross-task consistency only). Flag the absence of a spec as a `coverage-gap` at `major` severity.

---

## 7. Challenger instructions

### Reclassification rules

The challenger may reclassify severity within a valid combination for the type (see matrix above). The challenger must not reclassify type.

Reclassify `under-specified` from `critical` to `major` only when the challenger confirms that, while the instruction is ambiguous, both plausible interpretations produce outputs that satisfy the spec and would both pass the relevant gate check.

Reclassify `coverage-gap` from `critical` to `major` only when the challenger locates a task that addresses the criterion implicitly (through implementation logic, not frontmatter) and confirms the gate check does not read the `covers` field for that criterion.

Do not reclassify `spec-conflict`. The spec's text is authoritative; if a conflict exists, severity is a factual question about gate impact.

### Provenance for dead-scope trace

When the researcher flags a file as appearing in no task's scope (a coverage-gap for file creation), the challenger traces the file's provenance: does the spec require it, does an existing task implicitly create it as a side effect, or did the spec supersede the requirement? A file whose creation is a side effect of an explicitly named task is not a coverage gap.

### Cited source reading

Task review findings commonly cite: the feature spec, a prior task file, an interface contract document, or the breakdown spec. The challenger opens and reads the cited document before issuing a verdict on any finding that turns on what the document says.

---

## 8. Verdict contract

**This section applies because this lens declares `output_contract: verdict-contract`.**

**Artifact path:** `ai-docs/<feature>/task-review.md`

**Verdict line format:** The artifact must end with exactly one line matching:

```
Verdict: accepted
```

or

```
Verdict: needs-revision
```

No other content may appear on that line. The verdict must be the final meaningful line of the artifact. The gate locates the verdict by scanning for a line matching `^Verdict: (accepted|needs-revision)$`.

**Accepted condition:** No confirmed findings of type `coverage-gap` or `spec-conflict`, no `under-specified` findings at `critical` severity, and no `sizing-violation` findings at `major` severity.

**Needs-revision condition:** Any confirmed finding of type `coverage-gap` (any severity) or `spec-conflict` (any severity), or any `under-specified` finding at `critical` severity, or any `sizing-violation` at `major` severity triggers `needs-revision`.

A `needs-revision` verdict blocks the breakdown gate. The gate reads the artifact file; the conversation output is not authoritative.
