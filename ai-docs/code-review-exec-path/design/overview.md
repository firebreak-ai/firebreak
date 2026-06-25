# Overview — code-review executable-path follow-on

## What this feature is

A merge prerequisite for the `fbk/unified-review-shape` branch. The unified-review-shape migration moved every review type onto two generic agents — a **researcher** that surfaces candidate problems and a **challenger** that verifies them independently. Code review is the one review type whose validation runs as a real Python program (the `pipeline`), and that program was not fully migrated to the new generic-agent contract. This feature finishes the migration of the executable path and then extends the same tool-enforced guarantees to every other finding-mode review type.

Two original defects drive it:

- **The live validator rejects every finding.** The new researcher deliberately emits no sighting `id` (the pipeline assigns one after validation), but the code-review skill runs the validator with no lens at the **detection round** (the first validate/filter call, before any id exists), so it falls back to a built-in required-field set that still demands `id`. Validation runs before id-assignment, so every id-less finding is rejected before it can be given an id. Code review comes back empty. (The later post-challenge validation is not the broken call — by then ids exist; see the handoff page for why that call still changes.)
- **The challenger sees the researcher's framing.** The independence the researcher/challenger split exists for requires the handoff to pass through a normalization step that strips a finding to six neutral fields. The code-review skill hands the challenger the full findings instead, so its "independent" verdict is quietly biased.

An operator decision (the full enforcement sweep) extends the fix: rather than repair code review alone, the same tool-enforced validation and normalization apply to **every finding-mode review type** — test review, coherence review, and task review — so the guarantees are enforced by the program everywhere, not trusted to prose in each skill.

## The component map

Two kinds of thing change: the Python pipeline program, and the review-skill documents that call it.

**Pipeline program (`assets/fbk-scripts/fbk/pipeline.py`):**
- The `validate` and `run` subcommands gain an optional `--lens <path>` argument. When supplied, the validator loads that lens's vocabulary (its finding types, severities, type-severity matrix, and required-field set) and validates against it. When absent, behavior is byte-for-byte what it is today.
- A new `normalize` subcommand reads findings on input and emits the six neutral handoff fields on output, one record per input record, in the same order. This is the tool-enforced strip step that replaces the prose instruction to "hand the challenger only six fields."

**Review skills (the documents that orchestrate each review):**
- `fbk-code-review` — repoints its existing `run`/`validate` calls to pass the code lens, inserts a `normalize` call before the challenger, and re-joins the challenger's verdicts to the full findings it kept.
- `fbk-test-review`, `fbk-coherence-review`, `fbk-task-review` — each gains the same shape, expressed with its own lens. Because these three have no entry in the pipeline's preset file, they use the composable pipe (`validate --lens | severity-filter`) rather than code review's all-in-one `run` command. See `composable-pipe-for-lens-presets.md`.

**Out of scope — the scan-mode review types.** Fresh-eyes, the top-five quality scan, and durable-doc reconciliation declare a scan output mode. They have no challenger handoff to enforce (fresh-eyes is a single cold pass; the scan presets bypass finding-validation entirely), so the sweep does not touch them. The shared loop document also stays abstract — it describes what must happen, while each preset names the concrete commands that make it happen.

## What stays unchanged

- The default no-lens path through the validator: identical required fields, enums, and matrix as today, so any caller that still relies on it does not move.
- The minimum-length quality check on `title`, `mechanism`, and `consequence` stays a fixed structural gate, applied regardless of lens.
- Code review's findings report and its detection-round history file: same shape, same content.
- Every existing verdict and gate artifact for the other three review types.

## Decomposition rationale

Pages are split by the boundary the whole feature protects: **the validation vocabulary must be set at the program's command-line boundary and never assumed from built-in constants inside a function the command calls.** One page covers wiring that vocabulary in (the lens flag), one covers the neutral-handoff-and-rejoin data flow, one covers why the three new review types drive the pipeline through a different command shape, and one records every contract. See `design-manifest.md`.
