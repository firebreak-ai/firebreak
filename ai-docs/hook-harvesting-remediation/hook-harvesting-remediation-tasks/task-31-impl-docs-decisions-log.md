---
id: task-31
type: implementation
wave: 2
covers: [AC-18]
files_to_modify:
  - docs/decisions-log.md
test_tasks: [task-18]
dependencies: []
completion_gate: "The remediation entry is appended to docs/decisions-log.md following the file's existing entry format (## date — title / Status / Author / Decided / Alternative considered / Rationale / Constrains); the GLOSSARY verification outcome is recorded in the slice's completion notes"
---

## Objective

Record the remediation's three durable decisions in the project decisions log, and confirm (read-only) the glossary against the corrected behavior.

## Context

Docs task for the spec's Documentation impact section. `docs/decisions-log.md` (repo-relative path, at the repository root) is an append-only log; every entry follows the same template — see the two 2026-06-10 entries at the end of the file for the exact shape: `## <YYYY-MM-DD> — <title>`, then bold `Status`, `Author`, `Decided`, `Alternative considered`, `Rationale`, `Constrains` paragraphs, separated from the previous entry by `---`.

The spec names exactly three decisions to record: the shared non-active-state constant, the install-time sentinel creation, and the gate-rate "all gate types" resolution. They are decided facts from the remediation spec (operator-confirmed at spec review 2026-06-12); this task documents them — it does not re-litigate them.

Glossary note (verified at compilation): `GLOSSARY.md` at the repo root contains NO entries named "capture gate," "event envelope," or "chokepoint" — the spec's "confirm the entries still match" step assumes entries that do not exist. The verification step below records that finding; it does NOT add entries (the spec says "no new terms," and adding glossary entries is outside this task's file scope).

Constraints: do NOT modify any test file; do NOT modify `GLOSSARY.md`; file scope is exactly `docs/decisions-log.md`.

## Instructions

1. Append one entry to `docs/decisions-log.md`, dated with the actual implementation date, separated by `---` from the previous entry, titled `## <date> — Hook-harvesting remediation: shared non-active-state constant, install-time capture sentinel, gate rates cover all gate types`. Fill the template fields with this content (tighten wording to match the file's voice; keep every factual claim):
   - **Status**: accepted (remediation spec, operator-confirmed at spec review 2026-06-12).
   - **Decided**: three resolutions from the hook-harvesting remediation. (1) One authoritative "not an active working stage" set, `NON_ACTIVE_STATES`, lives in `fbk/state.py` beside `WORKING_STAGES`, derived from the same transition map; the active-stage resolver and the report import it by identity — no module may carry its own copy. (2) The installer creates the `.claude/automation/.fbk-managed` sentinel at install time, so a freshly-installed Firebreak project is instrumented and captures events with no manual step. (3) Gate pass-rates cover all gate types: the rate classifier reads the chokepoint's `PIPELINE_COMMAND` outcomes for the spec, task-reviewer, and code-review gates alongside task-completion verification, and the chokepoint is the single writer of gate-outcome events (the gates' own duplicate writes are removed).
   - **Alternative considered**: (1) homing the constant in the capture package — rejected because `state.py` already imports the capture package, so the reverse import would close a cycle. (3) relabelling the metric as verification-only, or keeping the gates as a second event writer — rejected because two events per dispatch double-count attempts and break exact-fraction rates, and a gates-as-source design would need a second two-module name agreement of exactly the parallel-literal kind the shared constant eliminates.
   - **Rationale**: the independent review found the remediation's own code reproducing the producer/consumer drift class the feature measures; each decision removes a place where two modules had to agree by convention.
   - **Constrains**: any new pipeline state lands in the shared sets automatically (derived, not listed); uninstall does not remove the sentinel; a future gate command must be added to the report's `GATE_COMMAND_NAMES` to enter the rates.
   Done when the entry parses under the file's existing format and names all three decisions.
2. Verification step (read-only, no file modification): open `GLOSSARY.md` and search for "capture gate," "event envelope," and "chokepoint." Record the outcome in the slice's completion notes — expected finding: the entries are absent (the glossary covers SDL process terms only), so there is nothing to drift; note this explicitly rather than silently passing, and flag it to the operator as a spec-assumption mismatch. Done when the completion notes carry the recorded outcome.

## Files to create/modify

- `docs/decisions-log.md` (modify — repo-relative)

## Test requirements

- None gate this task (documentation). The full-suite gate (task-18, wave 9) is unaffected by this file.

## Acceptance criteria

- AC-18 (documentation share): the decisions log carries the remediation entry the spec's Documentation impact section defines; the glossary confirmation is performed and its outcome recorded.

## Model

Haiku

## Wave

Wave 2
