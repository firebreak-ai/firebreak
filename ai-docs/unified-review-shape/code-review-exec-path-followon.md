# Code-review executable-path follow-on — design seed

**Status:** merge prerequisite for the `fbk/unified-review-shape` branch. Requires design (route through `/fbk-design` → `/fbk-spec`, or a small focused spec). Do **not** merge the unified-review-shape branch until this is resolved.

**Why this exists, in one breath:** the unified-review-shape migration changed every review type to use two generic agents (a *researcher* that finds candidate problems and a *challenger* that verifies them). For most review types the checking is done by the agent reading instructions — but **code review is the one type that runs a real Python program** (the `pipeline`) to validate and pass findings. That program was not fully migrated to the new generic-agent contract, so it has two real defects that only wake up once the new assets are installed and run together. A same-family code review missed both; an independent GPT-5.5 cross-model review (2026-06-23) caught them. This doc is the self-contained pickup point — you should not need the original implementation session's context to act on it.

**Source of truth:** `ai-docs/unified-review-shape/unified-review-shape-spec.md` (AC-05, AC-06, AC-16, AC-18; contracts IF-S-01, IF-S-02, IF-S-09, IF-S-10). Full review write-up: `fbk-code-review-2026-06-23-1307.md` (repo root) — "Cross-model review" and "Follow-on" sections.

---

## Defect 1 (X-1) — the live code-review validator rejects every finding

**Plain version:** when this ships, code review will discard every candidate the researcher produces and come back empty.

**Mechanism:**
- The new generic researcher (`assets/agents/fbk-review-researcher.md`) is told, by design, **not** to emit a sighting `id` — the pipeline assigns sequential `S-NN` ids *after* validation.
- But `fbk-code-review/SKILL.md` (step 3) runs the executable `pipeline run`/`pipeline validate` with **no lens**, so `validate_sighting()` falls back to the module-level `REQUIRED_FIELDS` in `assets/fbk-scripts/fbk/pipeline.py:18`, which still **includes `id`**.
- In `cmd_run`/`cmd_validate`, `validate_sighting()` runs **before** the id-assignment loop (`for i, s in enumerate(valid, 1): s["id"] = ...`). So a finding with no id is rejected as "missing field 'id'" before the line that would have added the id is ever reached. Chicken-and-egg.
- The per-lens machinery to fix this already exists but is never wired in: `assets/fbk-docs/fbk-review-lenses/code-lens.md` declares a `required:` set (`[title, location, type, severity, mechanism, consequence, evidence]`) that **correctly omits `id`**, and `pipeline.load_lens_matrix()` already parses it into a `LensVocabulary` that `validate_sighting(finding, vocab)` already accepts. Nothing calls them.

**Why tests/our own review missed it:** the pipeline's unit tests feed findings that already carry an id; the live review run during the session used the *old* installed agents (which still emit id), not the new generic researcher. The same-family Challenger saw "no CLI caller for the per-lens path" and wrongly concluded "prose-by-design" — true for the prose-validated presets, but code-review uses the *executable* validator, so it actually breaks here.

**Chosen direction (operator, 2026-06-23): wire the lens vocabulary in (the proper fix).**
- Add a CLI surface — e.g. `pipeline run --lens <path>` and `pipeline validate --lens <path>` — that calls `load_lens_matrix(path)` and threads the resulting `LensVocabulary` into `validate_sighting(finding, vocab)` and `validate_against_mode(record, vocab, output_mode)`.
- Repoint `fbk-code-review/SKILL.md` steps 3 and 5 to pass `fbk-docs/fbk-review-lenses/code-lens.md`.
- Bonus payoff: this makes AC-16 (per-lens validation) and AC-18 (scan-mode routing) **real at runtime** instead of prose-deferred, and it lights up AC-06's loud-failure-on-missing-lens on the CLI (a missing/misnamed lens then exits non-zero with the path in the message, instead of silently using the default vocabulary).

**Open design questions to resolve in the spec:**
1. Exact CLI shape — one `--lens` flag on `run`/`validate`, or a lens-aware subcommand? How is the lens path resolved (absolute, or relative to an install root)?
2. Should *every* preset that runs the executable pipeline pass its lens, or only code-review for now? (The scan-mode presets are prose-only today; decide whether they also move onto the CLI or stay prose.)
3. Ripple to audit before changing `REQUIRED_FIELDS` behavior: every caller of `validate_sighting` / `REQUIRED_FIELDS`, the gate modules, and `test_pipeline*` / `test_gates_*`. The default (no-lens) path must stay byte-identical for anything that still relies on it, or those callers move to passing a vocab.
4. Does `MIN_LENGTH_FIELDS` (the min-length check that still runs against module constants regardless of lens) need to become per-lens too, or is it correctly a fixed structural gate?

## Defect 2 (X-2) — code-review leaks the researcher's framing to the challenger

**Plain version:** the challenger is supposed to judge each candidate independently, but code-review hands it the researcher's full findings — titles, "how I found this" tags, suggested fixes, confidence — so its "independent" check is quietly biased.

**Mechanism:**
- The isolation invariant (AC-05 / IF-S-02) requires the handoff to pass through `pipeline.normalize()`, which strips a finding down to exactly six neutral fields (`mechanism`, `consequence`, `evidence`, `type`, `severity`, `source_of_truth_ref`) before the challenger sees it.
- The `review-challenger` agent's own contract (`assets/agents/fbk-review-challenger.md`) says it receives "the normalized candidate findings… no detection-source tags, no remediation hints, no confidence signals."
- But `fbk-code-review/SKILL.md` step 4 spawns the challenger with "the filtered JSON sightings to verify… no format translation between agents" — i.e. the full sightings, framing intact. So the wiring contradicts both the spec and the challenger's own contract.

**Fix direction:** insert a normalization step before the challenger spawn — either a `pipeline normalize` CLI applied to the filtered sightings, or an explicit step-4 instruction to pass only the six allowlisted fields. Keep finding IDs/titles on the **orchestrator** side for assembling the human-facing report; just don't hand them to the challenger.

**Open design questions:**
1. CLI `pipeline normalize` vs a prose step in the skill — which fits the substrate better? (X-1's CLI work may make a `normalize` subcommand natural to add alongside.)
2. The challenger needs the cited-source documents too (per the cited-source discipline). Confirm normalize + cited-source injection compose correctly in the code-review wiring.

---

## Scope note

X-1 and X-2 are **one focused iteration**: "migrate the code-review executable validation/handoff path onto the generic-agent contract." They touch the same fragile spot (`pipeline.py` + `fbk-code-review/SKILL.md`) and should be designed and shipped together, with the full ripple sweep done once. They do **not** reopen the rest of the feature, which is structurally complete (4 waves, 650 tests green). After this lands, run the deferred live end-to-end SDL review pass (the real-artifact validation that would have exposed X-1) before merge.
