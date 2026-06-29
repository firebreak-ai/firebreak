---
description: >-
  Second-opinion review of a document or code change by a different model.
  Produces candidate findings — observations from a cold, skeptical reviewer
  that treats the author as unreliable — triaged by severity. Results are
  candidate findings, never verified findings.
argument-hint: "[document-path or feature-name for a doc review; omit for a code-diff review]"
---

A cross-model review gets an outside opinion from a different AI model on a document or a code change. The other model reads cold — no authoring history, no prior discussion — and surfaces what it thinks the author missed. Results come back as candidate findings. You decide what to act on.

## 1. Check the opt-in first

Before doing anything else, run:

```
fbk.py cross-review --check-opt-in --project-root <root>
```

If the returned JSON has `"status": "skipped"`, this project has not opted in to cross-model review. Stop here and tell the user the project has not enabled cross-model review. Present no findings.

If the returned JSON has `"status": "success"`, the project is opted in — continue to step 2.

## 2. Gather the target

**Document review** — if `$ARGUMENTS` names a document (a PRD, spec, design, or breakdown), that file path is the target. If `$ARGUMENTS` is a feature name without an extension, resolve it to `ai-docs/<feature>/<feature>-spec.md` unless the user says otherwise.

**Code-change review** — if `$ARGUMENTS` is empty or refers to a code change, produce a unified diff of the staged or committed change and save it to a temp file. That file path is the target.

## 3. Read the matching lens for criteria

Choose the lens that matches the target type. Both are criteria references — read them for the severity words and what to look for, not as instructions for Codex to follow.

- **Document** (PRD, spec, design, breakdown): read `assets/fbk-docs/fbk-review-lenses/fresh-eyes-lens.md`. This is the `fresh-eyes-lens` criteria set.
- **Code change** (diff): read `assets/fbk-docs/fbk-review-lenses/code-lens.md`. This is the `code-lens` criteria set.

Extract the severity labels the lens uses (typically Critical, Substantive, Minor) and the things it says to look for. State these in plain language — you will embed them in the reviewer prompt.

## 4. Compose the reviewer prompt

Write a short prompt to a temp file. The prompt must:

- Tell the reviewer to read cold and treat the author as unreliable.
- State the criteria in plain language using the lens's own severity words.
- Ask for concise candidate findings only — no suggested fixes, no praise, no acknowledgment of context that was not in the material.
- Specify the output format: findings grouped under the lens's severity headings.

See `assets/skills/fbk-cross-model-review/references/cross-model-review-guide.md` for the full prompt template and outcome wording.

## 5. Call the runner

With the prompt file written, invoke the runner:

```
fbk.py cross-review --prompt-file <p> --review-type <slug> --report-dir <dir> --project-root <root> --target-label <text>
```

- `<p>` — path to the prompt file from step 4.
- `<slug>` — `fresh-eyes` for a document review, `code-review` for a code-change review.
- `<dir>` — directory where the report should land (typically `ai-docs/<feature>/` or the project's review output folder).
- `<root>` — project root (same value passed to `--check-opt-in`).
- `<text>` — a short human-readable label for the thing being reviewed (filename, feature name, or "diff of <branch>").

## 6. Handle the result

Branch on the `status` field in the runner's returned JSON.

**`status: success`** — Read the report the runner wrote. Before presenting anything:

1. Check that the report contains actual review content, not a refusal (phrases like "I cannot review", "as an AI I should not", or a blank findings section). If it looks like a refusal, rewrite the prompt with a clearly technical framing (not a command to do something harmful — just remove any phrasing the model may have misread) and re-run the runner once.
2. Triage the candidate findings: set aside any finding that is factually incorrect given what you know about the target. Keep the rest.
3. Present a summary to the user labelled explicitly as "candidate findings from a different model's review." Use the lens's severity headings. Do not present these as verified — the user decides which to act on.

**`status: skipped`** — The opt-in check (step 1) should have caught this earlier, but if it surfaces here, tell the user the project has not enabled cross-model review and present nothing.

**`status: failed`** — Relay the cause from the JSON `cause` field verbatim. If the message mentions `codex login`, tell the user they need to run `codex login` in the sandbox before cross-model review can proceed. Present no findings.
