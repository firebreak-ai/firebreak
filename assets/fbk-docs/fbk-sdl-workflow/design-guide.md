## Design Phase Overview

The design phase produces a concrete module shape, contracts, and decomposition rationale for a feature before implementation begins. You surface each real structural choice one at a time — proposing a recommendation and naming the trade-off — rather than presenting a finished plan to approve or reject.

Design phase output lives in `ai-docs/<feature-name>/design/` (individual design pages) and `ai-docs/<feature-name>/design-manifest.md` (the manifest that lists them). Enduring decisions append to the durable decisions log at `ai-docs/<feature-name>/<feature-name>-decisions.md`.

---

## What the Design Phase Produces

**Design pages** — one `.md` file per bounded concern, placed in `ai-docs/<feature-name>/design/<slug>.md`. Typical pages:

- `overview.md` — module shape, component boundaries, and entry points
- `module-shape.md` — data structures and interfaces the implementation will depend on
- `contracts.md` — **required on every feature.** A feature that introduces or changes contracts documents each one as a structured entry. A feature that changes no contracts writes one sentence. See the no-contracts form in `design-contracts-standard.md`.

  When the feature introduces or changes contracts, read `design-contracts-standard.md` for the entry schema and identifier scheme — this route applies only when the feature has contracts to document.

  When a contract is shared — a config shape, a constructor signature, a naming scheme, a shared sentinel set, an event registry that other parts of the project also use — compare the design's version against the project's established convention before recording it. Find that convention in this order: prefer an authoritative conventions document if one exists; if none exists, infer the convention from the dominant pattern in the existing code; if neither exists, say plainly that you are setting a new convention, so the choice is visible rather than buried. Checking the feature's own foundational contract is not enough — a shared convention reinvented here slips through unless you compare against where it already lives. If a conventions document and the live code disagree, surface the conflict to the user with a recommendation: name what the document says, note that the code does something different and roughly how widely, recommend which to align to and why, and ask for confirmation. Do not silently pick a side, and do not hand over the raw conflict without a recommendation.

  When a contract's signature adds a config parameter to make one function's behavior runtime-tunable, check every other consumer named in the seam docs that shares the same tunable behavior — a sibling function left hardcoded while this one gains a config path is a design gap, not a scope boundary. Name the config path for each consumer that needs it in this same design pass.

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

When a decision's function is not yet settled — for example, a schema field whose purpose or identity role is still undefined — hold an open discussion of what the field needs to do before naming alternatives. Presenting a ranked option list is premature until the function is clear; recommend an alternative only once it is.

Do not batch multiple choices into a single proposal. A user who disagrees with one part of a batch must reject the whole thing or manually untangle what they're accepting.

After each decision is recorded, increment `Decisions recorded:` in the manifest.

---

## Establishing Ground Truth Before You Commit

When a design choice rests on how a dependency or some external behavior actually works, find out the truth early — before the design is committed — rather than carrying an unverified assumption into implementation, where it surfaces as a late failure that is far more expensive to fix.

Establish that ground truth the cheapest way that settles the question, escalating only if a cheaper check leaves it open:

1. **Read the dependency's own source directly.** The cheapest answer is usually already written down in the code you depend on. Open it and look.
2. **Run a small experiment script.** When reading the source does not settle it, write a few lines that exercise the real behavior and observe what actually happens.
3. **Run an evaluation.** When the behavior is large or statistical, stand up a proper evaluation against it.

Do the cheap end of this ladder on your own — reading a dependency or running a quick script needs no permission. When establishing the ground truth would take non-trivial effort — a sizable experiment, an evaluation that costs real time or money — raise it with the user first and agree it is worth the cost, rather than unilaterally sinking significant effort into it.

---

## Fresh-Eyes Anchor

Before the design gate runs, a fresh-eyes review of the design artifacts is required. The review output is `ai-docs/<feature-name>/fresh-eyes-design.md`. The gate requires this file and checks that the `## Critical` section is empty — no open critical observations may remain.

When the design touches a shared contract, give the cold reviewer the convention it should compare against — the authoritative conventions document if one exists, otherwise the existing code that carries the dominant pattern — so the review can catch a reinvented shared convention. A reviewer who sees only the design artifact has no way to notice that the design quietly re-derived a convention that already lives elsewhere.

When the design proposes amendments to existing shared docs (seam docs, foundational contracts, schema files), name those specific pages to the cold reviewer as specified changes this design is making, not existing code — a reviewer who cannot tell a proposed amendment from a defect will flag every not-yet-built change as absent-from-shipped-code. Naming the pages explicitly, rather than a generic reminder that unbuilt code is expected, is what suppressed this misread in practice.

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
4. If agreed: invoke `/fbk-spec <feature-name>` to begin spec authoring per `fbk-docs/fbk-sdl-workflow/feature-spec-guide.md`.
