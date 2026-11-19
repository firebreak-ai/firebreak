---
description: >-
  Durable-doc reconciliation between shipped module code and the project's
  durable docs. Invoked for documentation drift review. Advisory
  output, two classes — drift and note. Self-scopes when no durable docs
  reference the shipped module.
argument-hint: "[feature-name]"
---

Compare the shipped module's code against the project's durable docs and flag every mismatch. The reconciler surfaces drift; it does not propose fixes and it does not gate. The operator decides per item whether to update the doc, accept the asymmetry as intentional, or mark it as historical.

## Reviewer execution

Resolve the installed directory from `${CLAUDE_PROJECT_DIR:-$PWD}/.claude` when
it contains `fbk-scripts/fbk.py`, otherwise `$HOME/.claude`. Read
`fbk-docs/workflow/reviewer-execution.md` there and launch each reviewer as it
describes. Publish the requested report after the round completes. A missing
check is a limitation, never an invented result.

## Workflow

0. **Resolve feature scope.** Use the argument value when provided. Otherwise, derive it from the `.fbk/` unit containing the spec for the shipped module. Otherwise, fall back to the shipped module's top-level package name. The resolved value becomes `<feature>` in every path below.

1. **Locate durable docs.** Search the project for each of the five durable-doc kinds in its common locations (full list below). Build a list of `(kind, path)` pairs for the docs actually present.

2. **Self-scope.** If no durable docs are found, or none reference the shipped module by name, file path, or feature scope, write `no durable docs to reconcile` to `reviews/doc-reconcile.md` and exit. The skill's flow stays uniform whether or not docs exist.

3. **Run the reconciler round.** Write the reviewer's instruction file under `.fbk/runtime/` (for example `.fbk/runtime/doc-reconcile-instructions.txt`). It contains, in this order: `fbk-docs/review/researcher-role.md` in full; `fbk-docs/fbk-review-lenses/doc-reconcile-lens.md`; the cardinality statement (0 challengers, round cap 1) per the shared review-loop spine in `fbk-docs/fbk-review-lenses/review-loop.md`; the in-scope `(kind, path)` pairs and the shipped-module file paths; and the output instructions: return findings as a JSON array with fields `class`, `doc`, `doc_says`, `code_shows`, `rationale` under `result`, proposing no fixes and modifying no file. The per-doc comparison guidance and classification rules in `fbk-docs/fbk-review-lenses/doc-reconcile-lens.md` govern what to look for and how to classify each observation. Include no authoring history and no prior conversation context; the researcher reads cold.

   Then launch the round, with `firebreak_dir` resolved as the reviewer-execution section describes and `--required` naming the in-scope docs and the shipped-module files:

   ```bash
   python3 "$firebreak_dir/fbk-scripts/fbk.py" review-round begin --root "$PWD" \
     --instructions .fbk/runtime/doc-reconcile-instructions.txt \
     --contributors reviewer --required <in-scope-docs> <shipped-module-files>
   python3 "$firebreak_dir/fbk-scripts/fbk.py" review-round run --round ID --contributors reviewer
   python3 "$firebreak_dir/fbk-scripts/fbk.py" review-round require-complete --round ID
   ```

   Use the returned round ID. Read the reviewer's result path that `run` returns; the findings array is under `result`.

4. **Write the artifact.** Take the reviewer's findings from the round result and write them to `reviews/doc-reconcile.md`, overwriting any existing file at that path. List drift items first, then notes. If the reviewer returns no findings, write `no drift found` and exit.

## Durable docs the skill sweeps

Five kinds, in this order:

1. **Decisions ledger** — the project's record of architectural decisions and rationale. Common locations: `decisions.md`, `design-decisions.md`, `.fbk/<unit>/decisions.md`, an `adr/` directory.
2. **Contracts file** — defines public interfaces, data shapes, and behavioral promises for the shipped module. Common locations: `contracts.md`, `.fbk/<unit>/contracts.md`, schema files referenced by the spec.
3. **Package layout** — describes module organization, what lives where, dependency direction. Common locations: README architecture section, `.fbk/<unit>/layout.md`, a dedicated architecture doc.
4. **Changelog** — user-facing change history. Common location: `CHANGELOG.md` at the project root.
5. **Spec** — feature spec with acceptance criteria, user value statements, and behavioral claims. Common location: `.fbk/<unit>/spec.md`.

## Output format

Each finding written to `reviews/doc-reconcile.md` includes:

- **Class**: `drift` or `note`
- **Doc**: which durable doc and where in it
- **What the doc says**: the doc's claim, quoted or summarized
- **What the code shows**: the contradicting or diverging code observation
- **Why this is drift / note**: one sentence justifying the classification

## Advisory-only constraint

This skill does not invoke any agent with Write or Edit tools. It does not gate code-review pass/fail. The operator reviews the output and decides per item whether to update the doc, clarify why the doc intentionally describes a prior state, or mark the drift as expected (a doc that is a historical record).
