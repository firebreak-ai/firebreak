---
description: >-
  Durable-doc reconciliation between shipped module code and the project's
  durable docs. Auto-invoked by fbk-code-review at gate-pass time. Advisory
  output, two classes — drift and note. Self-scopes when no durable docs
  reference the shipped module.
argument-hint: "[feature-name]"
---

Compare the shipped module's code against the project's durable docs and flag every mismatch. The reconciler surfaces drift; it does not propose fixes and it does not gate. The operator decides per item whether to update the doc, accept the asymmetry as intentional, or mark it as historical.

## Workflow

0. **Resolve feature scope.** Use the argument value when provided. Otherwise, derive it from the `ai-docs/` subdirectory containing the spec for the shipped module. Otherwise, fall back to the shipped module's top-level package name. The resolved value becomes `<feature>` in every path below.

1. **Locate durable docs.** Search the project for each of the five durable-doc kinds in its common locations (full list below). Build a list of `(kind, path)` pairs for the docs actually present.

2. **Self-scope.** If no durable docs are found, or none reference the shipped module by name, file path, or feature scope, write `no durable docs to reconcile` to `ai-docs/<feature>/doc-reconcile.md` and exit. The skill's flow stays uniform whether or not docs exist.

3. **Spawn the reconciler agent.** Spawn `fbk-code-review-detector` in doc-reconciliation mode. Pass the in-scope `(kind, path)` pairs, the shipped-module file paths, and the per-doc comparison guidance and classification rules from below. Instruct it to return findings as a JSON array with fields `class`, `doc`, `doc_says`, `code_shows`, `rationale`. Do not allow the agent to propose fixes or modify any file.

4. **Write the artifact.** Take the agent's output and write it to `ai-docs/<feature>/doc-reconcile.md`, overwriting any existing file at that path. List drift items first, then notes. If the agent returns no findings, write `no drift found` and exit.

## Durable docs the skill sweeps

Five kinds, in this order:

1. **Decisions ledger** — the project's record of architectural decisions and rationale. Common locations: `decisions.md`, `design-decisions.md`, `ai-docs/<feature>/decisions.md`, an `adr/` directory.
2. **Contracts file** — defines public interfaces, data shapes, and behavioral promises for the shipped module. Common locations: `contracts.md`, `ai-docs/<feature>/contracts.md`, schema files referenced by the spec.
3. **Package layout** — describes module organization, what lives where, dependency direction. Common locations: README architecture section, `ai-docs/<feature>/layout.md`, a dedicated architecture doc.
4. **Changelog** — user-facing change history. Common location: `CHANGELOG.md` at the project root.
5. **Spec** — feature spec with acceptance criteria, user value statements, and behavioral claims. Common location: `ai-docs/<feature>/spec.md`.

## Per-doc comparison guidance

- **Decisions ledger** — code that contradicts a recorded decision is drift; a decision whose mechanism the code has refactored but still honors is a note.
- **Contracts file** — signature or shape mismatch is drift; renamed-but-equivalent surfaces are a note.
- **Package layout** — files in a package the layout doesn't describe, or imports against the layout's stated direction, are drift.
- **Changelog** — unrecorded user-facing changes are drift; recorded entries whose described change doesn't match the diff are also drift.
- **Spec** — unmet claims the spec implies are now true are drift; claims whose phrasing has gone stale but whose intent is met are notes.

When a doc carries a claim whose shape doesn't fit its doc kind (e.g., a spec containing a contracts-shaped claim about a function signature), apply the per-doc guidance that most closely matches the claim's shape rather than the guidance keyed to the doc kind.

## Classification rules

- **drift** — concrete divergence. The doc names something (a function, a file, a contract field, a stated decision) the code doesn't contain or contradicts. Clear mismatch.
- **note** — ambiguous signal. The doc references something at a name the code might still implement under a different name, or describes a behavior that's been refactored such that direct comparison is hard. Worth a look but might be benign.

## Output format

Each finding written to `ai-docs/<feature>/doc-reconcile.md` includes:

- **Class**: `drift` or `note`
- **Doc**: which durable doc and where in it
- **What the doc says**: the doc's claim, quoted or summarized
- **What the code shows**: the contradicting or diverging code observation
- **Why this is drift / note**: one sentence justifying the classification

## Advisory-only constraint

This skill does not invoke any agent with Write or Edit tools. It does not gate code-review pass/fail. The operator reviews the output and decides per item whether to update the doc, clarify why the doc intentionally describes a prior state, or mark the drift as expected (a doc that is a historical record).
