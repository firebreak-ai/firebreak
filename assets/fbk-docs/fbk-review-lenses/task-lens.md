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
| `sizing-violation` | A task's scope exceeds the file-count or complexity limit declared in the breakdown spec, its instructions touch files belonging to a different task's declared scope, or its instructed code cannot build together with sibling tasks' instructed code in the same compilation unit. | Request changes — scope must be repartitioned. |
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
- is ambiguous between two plausible interpretations that would produce different code;
- pins a qualitative assertion (a strict inequality, a not-equal check) at a boundary or extreme parameter value without a hand-derived expected value — floating-point behavior at extremes (underflow, saturation) can make a correct implementation fail a qualitative claim; the task must state the computed expected value instead.

Type: `under-specified`. Severity: `critical` when ambiguity would block execution; `major` when it would produce an unintended design choice; `minor` when it adds friction only. The boundary/extreme-parameter bullet is `critical` when computing the actual value shows it fails a correct implementation, `major` when unverified but plausible.

### Pass B — Acceptance criteria coverage

Read the spec's acceptance criteria list. For each criterion, locate the task or tasks that implement it. A criterion is covered if at least one task names it in its `covers` frontmatter field or addresses it unambiguously in its instructions. Flag any criterion with no covering task.

A task's `covers` entry is coverage only when that task's own instructions implement or verify the named criterion. When a `covers` list includes a criterion the task's instructions neither implement nor verify — for example, an infrastructure task whose list was populated only to satisfy a no-task-unlinked-from-AC requirement — locate the task that actually implements or verifies the criterion, or flag the criterion as a coverage gap.

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

### Pass E — Compile coherence

Passes A–D each read one task against the spec, or one task's declared file list against another's. Neither view catches a defect that only exists across the whole set of task-instructed code in one compile unit (a Go package, a module, or equivalent). For each wave, assemble every instructed code fragment that lands in the same compile unit and read it as a single body. Flag:

- two tasks that declare the same top-level identifier (a function, type, constant, or variable) in that unit — a compile-time redeclaration even when neither task's declared file list overlaps the other's;
- an instructed import that the same task's instructed code does not use, or an instructed use that the task's declared imports do not cover;
- for each wave, any symbol an instructed test references (a function, type, or field it calls or accesses) with no implementation task creating that symbol in the same wave or an earlier one — the wave cannot reach a green state without it.

Type: `sizing-violation` for the three checks above. Severity: `major` — each is a guaranteed compile failure or a permanently red wave.

Flag separately: an instructed expression whose operation is illegal for the real type it operates on — an accessor's actual signature used with an incompatible operation (for example, map-style indexing on a slice-typed return), or a whole-value equality (`==`) on a type with a non-comparable field (for example, a slice).

Type: `spec-conflict`. Severity: `critical` when the mismatch would fail to compile; `major` otherwise.

---

## 6. Source-of-truth handling

Primary source: the feature spec at `ai-docs/<feature>/<feature>-spec.md`, specifically its acceptance criteria and interface declarations.

Secondary sources: the breakdown spec (file-count limits, wave ordering rules) and any interface contracts named in the spec.

When a task instruction copies a contract from the spec verbatim, the researcher must locate the spec's original and compare field by field — the task file's copy is not the source of truth.

For Pass E's type-legality check, when the spec does not itself state an accessor's or type's real signature, the researcher reads that signature in the shipped codebase rather than treating the task's assumed signature as ground truth.

When no spec is available: the breakdown task set itself is the primary artifact; compare tasks against each other for internal consistency (Pass D reduces to cross-task consistency only). Flag the absence of a spec as a `coverage-gap` at `major` severity.

---

## 7. Challenger instructions

### Reclassification rules

The challenger may reclassify severity within a valid combination for the type (see matrix above). The challenger must not reclassify type.

Reclassify `under-specified` from `critical` to `major` only when the challenger confirms that, while the instruction is ambiguous, both plausible interpretations produce outputs that satisfy the spec and would both pass the relevant gate check.

Reclassify `coverage-gap` from `critical` to `major` only when the challenger locates a task that addresses the criterion implicitly (through implementation logic, not frontmatter) and confirms the gate check does not read the `covers` field for that criterion.

Do not reclassify `spec-conflict`. The spec's text is authoritative; if a conflict exists, severity is a factual question about gate impact.

A task instruction that directs an agent to edit a file outside its own declared scope is a `sizing-violation` under Pass C regardless of how the instruction frames the edit — describing it as coordinated, guided, or delegated does not exempt it. Reject only by showing the target file is actually inside the task's own declared scope, or that the instruction does not actually direct an edit to it; framing language in the instruction is not counter-evidence.

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
