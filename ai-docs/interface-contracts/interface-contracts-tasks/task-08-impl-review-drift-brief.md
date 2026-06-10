---
id: task-08
type: implementation
wave: 1
covers: [AC-16]
files_to_modify:
  - assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md
test_tasks: [task-07]
completion_gate: "task-07 tests pass"
---

# task-08 — Extend the architecture-reviewer brief with the contract-drift conditions

## 1. Objective

Produces an edit to `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` that extends the architecture reviewer's brief so spec review reports three contract-drift conditions as informational findings when the feature has a `design/contracts.md`.

## 2. Context

Implementation task for the `review-drift-brief` slice (new-contract discipline). The paired test task (task-07) wrote a shell test that greps `review-perspectives.md` for the three drift conditions and the informational framing; your edit makes it pass. The behavioral intent: the deterministic spec gate carries contracts and runs mechanical completeness checks, but it deliberately does NOT do semantic comparison — whether a same-id contract's name or signature has drifted, or whether the spec added a contract design never had, is left to spec review. This edit gives the architecture reviewer the brief to elevate that drift, reporting it informationally and leaving disposition to the operator.

The three drift conditions the brief must carry (all reported as informational findings, applicable when the feature has a `design/contracts.md`):

1. A spec-added `IF-S-NN` contract that is absent from design (the spec minted it; design never enumerated it).
2. An `IF-D-NN` entry whose identifier is preserved but whose name or signature has materially changed between design and the spec carry.
3. A count/name mismatch between the design page's `IF-D-NN` entries and what the spec carries or excludes.

All three are informational, not blocking — the reviewer reports; the operator decides.

**Where to add it — name the real anchor.** Read `review-perspectives.md` first. The architecture reviewer's brief lives in the "SDL concerns table," in the **Architectural soundness** row (Primary: Architect) — the "Review prompt framing" cell already carries the architect's instructions (it currently covers integration risk, pattern consistency, integration-point existence, convention visibility). The classification-signals table below also has an **Architect** row. Extend the **Architectural soundness** review-prompt framing so it adds the three drift conditions, gated on the feature having a `design/contracts.md`, framed as informational. Do not create a new top-level section and do not add a new SDL-concern row — extend the existing architecture-reviewer framing in place, so the architect agent receives the drift brief as part of its existing prompt.

**Severity vocabulary.** `review-perspectives.md` already defines the three severities (`blocking` / `important` / `informational`) in its "Review document structure" section. Use the existing literal `informational` so the drift findings sort into that band; task-07 greps for the literal `informational`.

## 3. Instructions

1. Read `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` and locate the **Architectural soundness** row's "Review prompt framing" cell in the SDL concerns table.

2. Extend that framing so the architect, when the feature has a `design/contracts.md`, additionally reports the three contract-drift conditions as informational findings with disposition left to the operator. Name all three conditions explicitly:
   - a spec-added `IF-S-NN` contract absent from design;
   - an `IF-D-NN` entry whose identifier is preserved but whose name or signature materially changed;
   - a count/name mismatch between the design page's `IF-D-NN` entries and what the spec carries or excludes.
   Use the literal tokens `IF-S-` and `IF-D-` in the text (task-07 greps for both) and the literal word `informational` (task-07 greps for it). Completion: the framing cell contains the `IF-S-` condition, the `IF-D-` name/signature-change condition, the count/name mismatch condition, and the word `informational`.

3. Keep the edit inside the existing table cell / architecture-reviewer framing — do not add a new SDL-concern row or a new top-level section. If the framing cell is a single long string, append the drift brief as additional sentences within it. Completion: the file still has the same table structure; the new content is part of the Architectural soundness framing.

4. Run `bash tests/sdl-workflow/test-review-drift-brief.sh` from the repo root and confirm it passes (green phase): three distinct drift-condition assertions plus the informational-framing assertion all green.

## 4. Files to create/modify

- Modify: `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md`

Do not touch any other file.

## 5. Test requirements

This task writes no tests. It must make task-07's `tests/sdl-workflow/test-review-drift-brief.sh` pass — one assertion per drift condition (spec-added-`IF-S-`-absent, preserved-`IF-D-`-but-changed-name/signature, count/name mismatch) plus one for the `informational` framing. A partial edit (one condition present, two missing) must fail; so all three conditions and the framing must be present. Re-read task-07 §5 for the exact greps.

## 6. Acceptance criteria

- Primary: task-07's tests pass (green phase).
- Covers AC-16.
- The architecture-reviewer brief carries all three contract-drift conditions, each framed as informational, with disposition left to the operator.
- The edit extends the existing Architectural soundness framing — no new SDL-concern row or top-level section.

## 7. Model

Sonnet

Rationale: a single-file edit, but it requires judgment to weave three precise conditions into an existing prompt-framing cell without disturbing the table structure or the gate-sensitive heading conventions noted in the same file (the `## Test*` reservation). Prose-integration judgment into a loaded reviewer brief — above bounded-mechanical. Per the when-in-doubt-Sonnet rule. Sonnet.

## 8. Wave

Wave 1
