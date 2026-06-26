# Spec-phase handoff — code-review-exec-path

A cold-start pointer for a fresh-context spec session. Design is complete and gate-passed; this is what spec needs to know without re-reading the whole design.

## How to start

Invoke `/fbk-spec code-review-exec-path`. Feature directory: `ai-docs/code-review-exec-path/`. This is a merge prerequisite for the `fbk/unified-review-shape` branch (current branch). Design entered mid-pipeline with no intent phase — the operator-blessed seed `ai-docs/unified-review-shape/code-review-exec-path-followon.md` served as intent input.

## What the feature does (one breath)

Finish migrating code review's executable validation/handoff path onto the unified-review-shape generic-agent contract, and extend the same tool-enforced guarantees to every finding-mode review type (code, test, coherence, task review). Fixes two defects: the lens-less validator rejects every id-less finding (X-1), and the challenger receives the researcher's full framing instead of the six neutral fields (X-2). Scan-mode review types (fresh-eyes, quality scan, doc reconcile) are out of scope — no challenger handoff.

## Read these first

- `design-manifest.md` and the five pages under `design/` — `overview`, `cli-lens-wiring`, `normalized-handoff-and-rejoin`, `composable-pipe-for-lens-presets`, `contracts`.
- `docs/decisions-log.md` — two 2026-06-24 entries (nine decisions total).
- `fresh-eyes-design.md` — two cold passes (in-pipeline + GPT-5.5) and their resolutions.

## Settled at design — do NOT reopen

- **Lens wired into the validator** via an optional `--lens` flag on `validate`/`run`; default no-lens path stays byte-identical.
- **A new `pipeline normalize` subcommand** is the tool-enforced six-field strip (no arguments; maps the existing per-finding `normalize()` over the list).
- **Full enforcement sweep** across all four finding-mode review types; **two command paths accepted** — code review keeps `run`; the three others use `validate --lens | severity-filter` (no preset-file entries — the lens is their type-filter authority).
- **Verdict-to-finding re-join is position-only, locked.** The reorder limitation is accepted; the echoed-index-token hardening is declined and is NOT a spec open item.
- **Min-length check stays a fixed structural gate**; **per-preset wiring**, shared loop document stays abstract.
- The post-challenge `validate --lens` validates **finding fields and the matrix only** — the verdict-field presence check (status, evidence) stays prose in each skill.

## The two open questions spec owns

1. **The exact prose wording of the verdict-field check** that stays outside the tool in each migrated skill (status is one of the allowed values; evidence present on verified statuses). The design fixed that it stays prose and what it checks; spec pins the wording per skill.
2. **The per-type catching tests.** Each of the three newly-migrated review types needs a test proving its lens-parameterized validator rejects an out-of-type finding (e.g. a `behavioral` finding rejected under `task-lens`). The design fixed the principle; spec's testing-strategy section produces the concrete test list. Also cover: the `normalize` subcommand's six-field/order-preserving output, the count-guard failure on a mismatched challenger array, and the byte-identical default no-lens path.

## Files the implementation will touch (from the design ripple list)

- `assets/fbk-scripts/fbk/pipeline.py` — `--lens` on `validate`/`run`, new `cmd_normalize` + `normalize` subcommand, call-site edits to pass the vocab.
- `assets/skills/fbk-code-review/SKILL.md` — steps 3, 4, 5.
- `assets/skills/fbk-test-review/SKILL.md`, `assets/skills/fbk-coherence-review/SKILL.md`, `assets/skills/fbk-task-review/SKILL.md` — add the composable-pipe validate, the `normalize` call, and the post-challenge re-validate.
- The shared `review-loop.md` does NOT change (per-preset wiring decision).

## After implementation

A live end-to-end run of the migrated skills against a real artifact remains the operator's manual validation — the structural/contract tests cannot exercise the prose-orchestration behavior.
