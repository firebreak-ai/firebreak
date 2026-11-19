# Code Review Lens

## Lens identity

This lens reviews implementation code to determine whether behavior diverges from the stated spec, introduces AI failure modes, carries security vulnerabilities, or degrades structural quality. The core question is: does this code do what it claims, and will it keep doing so under realistic conditions?

```
output_mode: finding
output_contract: findings-artifact
```

---

## Finding types

| Type | What it means | Ship decision |
|---|---|---|
| `behavioral` | The code produces an incorrect or missing behavior under a realistic input, edge condition, or concurrent execution scenario. Covers spec divergence, AI failure modes, concurrency defects, and logic-inversion errors. | Block |
| `structural` | The code's organization creates a demonstrated maintenance risk under a plausible change, even when current behavior passes. Preferences or arbitrary size thresholds alone do not qualify. | Request changes or merge-and-flag |
| `test-integrity` | A test would not catch the regression it claims to cover — the assertion is too weak, a fixture patches away the behavior, or the test name misrepresents what it checks. | Request changes |
| `fragile` | The code is currently correct but depends on an implicit assumption that is plausible to violate by a nearby change — not a hypothetical future change, a realistic one. | Request changes or merge-and-flag |

`behavioral` and `fragile` are distinct: `behavioral` findings describe defects under current realistic inputs; `fragile` findings describe correctness that holds now but would break under a nearby legitimate change. Concurrent execution is normal operation — concurrency defects are `behavioral`, not `fragile`.

---

## Severity levels

| Severity | Observability | Reviewer action |
|---|---|---|
| `critical` | A user or external actor can observe incorrect behavior or a security failure under realistic inputs, no configuration change required. | Block |
| `major` | Incorrect behavior is reachable but requires a specific input, configuration, or environment that is plausible in production. | Block or request changes |
| `minor` | The defect exists but its observable impact is narrow, transient, or requires an unlikely input combination. | Request changes |
| `info` | Technically present but functionally irrelevant to correctness; observation only. | Comment or no comment |

---

## Type-severity validity matrix

The researcher and challenger both validate their output against this matrix before emitting. Invalid combinations are rejected.

```lens-matrix
types: [behavioral, structural, test-integrity, fragile]
severities: [critical, major, minor, info]
matrix:
  behavioral: [critical, major]
  structural: [minor, info]
  test-integrity: [critical, major, minor]
  fragile: [major, minor]
required: [title, location, type, severity, mechanism, consequence, evidence]
```

---

## What to look for (researcher instructions)

Read `shared-detection.md` for the test-integrity audit used by this lens.

Read `.claude/fbk-docs/review/code-review-guide.md` for the behavioral comparison methodology, finding format, sighting format, and orchestration protocol. Read `.claude/fbk-docs/review/ai-failure-modes.md` for the AI failure mode checklist applied alongside specs or intent. Read `.claude/fbk-docs/review/security-patterns.md` for security detection targets applied to all code reviews. Read `.claude/fbk-docs/review/detection-audits.md` for the concurrency audit, logic-inversion branch enumeration, cross-function API trace, and consistency audit passes the researcher runs before emitting sightings. Read `.claude/fbk-docs/review/quality-detection.md` for structural detection targets applicable to all code reviews.

### Detection passes

Run these passes in order. Tag each sighting with its detection source: `spec-ac`, `checklist`, `structural-target`, `audit-pass`, `intent`, or `linter`.

**Behavioral comparison pass** (`detection_source: spec-ac` or `intent`): Compare each module's actual behavior against the acceptance criteria and UV steps from the active spec, or against the intent register when no spec is available. Emit a sighting for every divergence — including missing behavior, excess behavior, and behavior that matches the letter but not the evident intent — except where the spec itself documents a tolerance, calibration range, or accepted degraded state that covers the observed behavior; treat that documented allowance as satisfied, not a divergence.

**AI failure mode checklist** (`detection_source: checklist`): Apply every item in `ai-failure-modes.md` to the reviewed code. When a checklist item matches a mechanism already sighted under behavioral comparison, emit one sighting and cite both sources.

**Security detection pass** (`detection_source: checklist`): Apply every target in `security-patterns.md`. Treat injection, trust-boundary violations, and improper credential handling as `behavioral`/`critical` unless the pattern's entry says otherwise.

**Audit passes** (`detection_source: audit-pass`): Run the four code-review-specific audit passes from `detection-audits.md`:

1. **Concurrency audit** — for each mutation, shared-state read, or cached value introduced or touched, enumerate concurrent execution scenarios and check invariants. Classify results as `behavioral`.
2. **Logic-inversion branch enumeration** — for each changed conditional, write out the old and new decision tables and check for unintended outcome changes.
3. **Cross-function API trace** — for every exported or public symbol the diff modifies, enumerate callers and verify shape compatibility.
4. **Consistency audit** — for each modified helper or pattern site, enumerate every sibling site and check whether the same change is required. Emit a sighting for every unpatched sibling where the answer is yes.

**Test-integrity audit** (`detection_source: audit-pass`): Read `shared-detection.md` for the full test-integrity audit. Apply it to every modified test in scope. Do not re-embed the audit body here — the reference resolves to the current `shared-detection.md` content.

**Structural quality pass** (`detection_source: structural-target`): Apply the targets and evidence threshold from `quality-detection.md`. Structural targets produce `structural` findings when a concrete maintenance consequence is demonstrated; they can require correction before acceptance despite green tests. Assess accepted design/spec decisions as possible origins and preserve evidence for the retrospective. Do not manufacture an upstream failure when implementation departed from a sound contract.

**Linter supplement** (`detection_source: linter`): When linter or typechecker output is provided, read it to understand what mechanical issues were already caught. Focus on issues these tools miss. Tag sightings derived from tool output as `linter`.

---

## Source-of-truth handling

**When a spec is available**: Use the acceptance criteria and UV steps from the active spec as the primary comparison target. Treat documented intent as authoritative over code behavior.

**When no spec is available**: The intent register (from the intent extraction pass) and the AI failure mode checklist together form the comparison target.

**When documentation and code diverge**: Emit the divergence as a sighting with both the documented claim and the observed behavior in the evidence field. Do not resolve the conflict by choosing one side.

**When the code carries an inherited contract verbatim** (for example, a copied interface definition): Locate the canonical source and compare field by field. Do not accept the code's copy as the source of truth.

---

## Challenger instructions

The challenger applies the generic disciplines from `review-loop.md` plus the following code-review-specific rules.

### Reclassification rules

The challenger may reclassify type or severity when it independently reads the code and finds a more accurate classification. Reclassification must state the concrete reason. The reclassification must land on a valid combination in the type-severity matrix above.

Specific reclassification cases for this lens:
- A `behavioral` finding downgraded to `fragile` requires the challenger to confirm that the defect requires a specific condition to trigger that is not currently present in production inputs.
- A `fragile` finding upgraded to `behavioral` requires the challenger to confirm a realistic current-input path that triggers the defect.
- A `structural` finding upgraded to `behavioral` requires the challenger to describe the specific behavioral consequence it produces, not a hypothetical.

### Provenance for dead code

When a sighting names material that appears unused — unreachable code, declared interfaces with no consumer, exported symbols with no callers — the challenger traces provenance through: requirements, design documents, spec ACs, task history, and git log for the file. If the trace confirms the material is genuinely dead, the finding is verified. If the trace is ambiguous (infrastructure shipped ahead of its first consumer, a task written against an undelivered dependency), return `unresolvable` with the missing fact when the ambiguity prevents establishing the defect; do not promote uncertainty into a confirmed finding.

### Cited-source reading

Code review findings commonly cite: spec ACs, UV steps, design documents, `code-review-guide.md` methodology sections, `ai-failure-modes.md` checklist items, `detection-audits.md` audit criteria, and `security-patterns.md` entries. The challenger opens and reads each cited document before ruling. A ruling based on what a cited document probably says is not acceptable.

### Consistency sightings

For sightings produced by the consistency audit (sibling sites that need the same fix), the challenger verifies that the sibling site exists at the named location and reads the current implementation, callers, and applicable contract. The challenger traces whether the named sibling shares the affected obligation and broken mechanism, and what its callers observe. Undocumented asymmetry alone does not confirm a partial fix. The challenger need not re-enumerate every sibling; it verifies the named claim.

---

## Findings artifact

This lens is loaded by the `fbk-code-review` preset, which produces a findings report and a supporting round log. There is no `Verdict:` line.

### Findings report

**Filename**: `.fbk/runtime/reports/fbk-code-review-<YYYY-MM-DD>-<HHMM>.md` under the project root; report updates stay outside the reviewed source snapshot.

**Sections**:
- Intent register (behavioral claims and Mermaid diagram from intent extraction)
- Verified findings — one entry per confirmed finding, in the format produced by `pipeline to-markdown`, with adjacent Challenger observations rendered at the end of each finding
- Retrospective (fields defined in `code-review-guide.md`)

**Finding entry format**: Each entry is produced by `python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline to-markdown` from the verified finding JSON. The format includes finding ID, title, type, severity, mechanism, consequence, evidence location, detection source, and any Challenger observations.
