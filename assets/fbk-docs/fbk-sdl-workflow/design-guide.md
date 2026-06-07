## Design Phase Overview

The design phase produces a concrete module shape, contracts, and decomposition rationale for a feature before implementation begins. You surface each real structural choice one at a time — proposing a recommendation and naming the trade-off — rather than presenting a finished plan to approve or reject.

Design phase output lives in `ai-docs/<feature-name>/design/` (individual design pages) and `ai-docs/<feature-name>/design-manifest.md` (the manifest that lists them). Enduring decisions append to the durable decisions log at `ai-docs/<feature-name>/<feature-name>-decisions.md`.

---

## What the Design Phase Produces

**Design pages** — one `.md` file per bounded concern, placed in `ai-docs/<feature-name>/design/<slug>.md`. Typical pages:

- `overview.md` — module shape, component boundaries, and entry points
- `module-shape.md` — data structures and interfaces the implementation will depend on
- `contracts.md` — invariants, pre/post-conditions, error conditions

Add pages when a distinct concern warrants its own document. Split when a page exceeds one scrollable screen of meaningful content.

**Design manifest** — `ai-docs/<feature-name>/design-manifest.md`. Lists every design page, states the decomposition rationale, and counts decisions recorded. Format:

```
- design/overview.md
- design/module-shape.md
- design/contracts.md

Decomposition rationale: <why these page boundaries, not different ones>

Decisions recorded: <count of distinct decisions appended to the decisions log>
```

The manifest is the gate's primary artifact — keep it in sync with what exists on disk.

---

## Decomposition Rationale

The manifest requires a `Decomposition rationale:` line. Write one sentence naming the principle that determined where page boundaries fell — capability boundary, data-flow stage, ownership layer, or a named architectural pattern. A rationale like "vertical slices by capability boundary" is acceptable; "we split by topic" is not.

---

## Surfacing Decisions

Surface each real design choice one at a time. For each choice:

1. Name the decision and the alternatives considered.
2. Recommend one alternative and state the trade-off it accepts.
3. Record the decision in `ai-docs/<feature-name>/<feature-name>-decisions.md` after the user accepts or overrides.

Do not batch multiple choices into a single proposal. A user who disagrees with one part of a batch must reject the whole thing or manually untangle what they're accepting.

After each decision is recorded, increment `Decisions recorded:` in the manifest.

---

## Fresh-Eyes Anchor

Before the design gate runs, a fresh-eyes review of the design artifacts is required. The review output is `ai-docs/<feature-name>/fresh-eyes-design.md`. The gate requires this file and checks that the `## Critical` section is empty — no open critical observations may remain.

If the fresh-eyes review surfaces critical observations, resolve them before calling the gate.

---

## Manifest Format Reference

```
- design/<slug>.md        ← one line per design page; slug is a lowercase-hyphenated filename
[additional page lines]

Decomposition rationale: <one-sentence explanation of the boundary principle>

Decisions recorded: <positive integer>
```

Rules the gate enforces:

- Every page listed in the manifest must exist as a file under `design/`.
- Every `.md` file under `design/` must be listed in the manifest.
- The `Decomposition rationale:` line must be present.
- `Decisions recorded:` must be present and non-zero.
- `fresh-eyes-design.md` must exist with no open critical observations.

---

## Running the Gate

Call the gate after the fresh-eyes review passes and the manifest is complete:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py design-gate ai-docs/<feature-name>
```

The gate outputs JSON to stdout (exit 0 on pass, exit 2 on failure). On failure, the `failures` array lists what to fix. Resolve each failure and re-run until the gate exits 0.

An `injection_warnings` count in the output is informational — warnings alone do not fail the gate.

---

## Transition

When the design gate passes:

1. Confirm the gate output shows `"result": "pass"`.
2. Confirm all decisions are recorded in `<feature-name>-decisions.md`.
3. Ask: "Would you like to move to the spec phase?"
4. If agreed: invoke `/fbk-spec <feature-name>` to begin Stage 2 spec authoring per `fbk-docs/fbk-sdl-workflow/feature-spec-guide.md`.
