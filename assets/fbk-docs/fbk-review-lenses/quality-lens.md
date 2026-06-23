# Quality Lens

This lens surfaces the top code-quality opportunities in a diff or change set. It reviews source code from a maintainability perspective, asking: what in this change will make the code harder to read, modify, or extend over time?

```
output_mode: scan
output_contract: observation-format
```

---

## Lens identity

The quality lens is a read-only, scan-mode lens. It does not produce finding-shaped output and does not route through the finding validator. The researcher produces at most five ranked sightings using the output schema below; output is validated only against that schema.

This lens has zero challengers and a round cap of 1. There is no challenge stage.

---

## Finding types

Not applicable. This lens is scan-mode; the researcher produces sightings, not typed findings. Finding types and the type-severity matrix are finding-mode concepts that do not apply here.

---

## Severity levels

The quality lens uses its own severity vocabulary. These labels are distinct from the finding-validator's enum and must not be substituted.

| Severity | Meaning | Reviewer action |
|---|---|---|
| `critical` | The pattern will cause an observable defect or makes the code materially hard to reason about in a way that is likely to propagate. | Address before merging. |
| `substantive` | A real quality problem that degrades maintainability without causing an immediate defect. | Address in this cycle or the next. |
| `minor` | A low-priority improvement: cleaner but not urgent. | Address at convenience. |

The severity vocabulary for this lens is `critical` / `substantive` / `minor`. The finding-validator's `major` / `info` severities are not valid in quality-scan output.

---

## Type-severity validity matrix

Not applicable. Scan-mode lenses carry no `lens-matrix` block. Output bypasses `validate_sighting()`.

---

## What to look for

The researcher reads the diff or change set and looks for quality opportunities across these areas. Tag each sighting with the area it comes from.

**Readability**
- Variable, function, and parameter names that do not convey their domain meaning — names requiring a reader to look elsewhere to understand what the value is.
- Functions that mix abstraction levels in the same body: setup, logic, and side effects interleaved with no clear seam.
- Comment-to-code mismatches: a comment that describes something different from what the code does.
- Boolean blindness: bare `True`/`False` arguments at call sites with no named-parameter or named-constant clarity.

**Maintainability**
- Magic literals (numbers, strings) used directly rather than bound to a named constant, making the meaning unclear and the value hard to update consistently.
- Repeated logic that appears in two or more places without being extracted into a named function or class.
- Deep nesting (more than three levels) that makes the control flow hard to follow and test.
- Hidden coupling: a function that modifies state in a place the caller cannot see from the signature (module-level mutables, shared mutable defaults).

**Structural clarity**
- Functions that do more than one conceptually distinct thing, making them hard to name precisely and hard to test in isolation.
- A class or module that has grown past its original responsibility without a clear seam for decomposition.
- Dead code: unreachable branches, unused imports, unused parameters — material that a reader must evaluate and determine is safe to ignore.

**Naming**
- Names that are technically accurate but misleading in context (a function named `check_X` that also mutates, a variable named `result` that holds an intermediate value).
- Inconsistent naming for the same concept across the change set (two names for the same domain entity).

**Duplication**
- Copy-paste blocks where a shared abstraction would eliminate the repetition. Flag only when the copies are close enough that they would diverge on the next edit.
- Test fixtures or setup code that is rebuilt per-test when a shared helper would serve.

**Fragile patterns**
- Ordering dependence: code that is correct only if callers invoke methods or steps in a specific undocumented order.
- Exception swallowing: bare `except` clauses or `except Exception` blocks that discard diagnostic information.
- Assertion-free tests that pass vacuously.
- Mutable default arguments in function signatures.

---

## Source-of-truth handling

This lens does not compare against a spec or contract. It applies the detection areas above to the diff or change set directly.

When the change set includes a stated design or rationale comment that explains a pattern (for example, a comment explaining why a global is intentional), the researcher considers that rationale before flagging the pattern. An explained and intentional choice is not a quality opportunity; an unexplained one is.

---

## Challenger instructions

This lens has zero challengers. The challenger section is included here because the lens format requires it, but no challenge stage runs for quality-scan.

---

## Observation format (`output_contract: observation-format`)

The researcher produces at most five sightings, ranked from highest to lowest severity. When the researcher identifies more than five opportunities, it keeps only the top five.

Each sighting entry must carry exactly these fields, in this order:

```
- **Severity**: critical | substantive | minor
- **Location**: file path and line range
- **Description**: what the quality issue is and why it matters for readability or maintainability
- **Opportunity**: what a better approach would look like
```

The severity value must be one of `critical`, `substantive`, or `minor`. The finding-validator's severity vocabulary (`major`, `info`) must not appear in quality-scan output.

The report is written to `ai-docs/<feature>/quality-scan.md`. It lists findings ranked highest-to-lowest. No verdict line is produced. No changes are applied automatically; the operator decides which findings to act on.

The gate check for quality-scan reads the report for `Severity:` lines matching the pattern `^\s*[-*]?\s*\**Severity\**:\s*(critical|substantive|minor)`. The count must be at most 5; zero is permitted when the change set contains no quality opportunities, in which case the researcher writes an explicit "no quality opportunities found" note and the gate treats that as passing.
