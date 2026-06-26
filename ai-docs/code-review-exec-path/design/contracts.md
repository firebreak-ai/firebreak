# Contracts

This feature changes the pipeline program's command surface and the data flow each review skill drives through it. Five contracts. Identifiers in the "Realizes" lines refer to the unified-review-shape spec (`ai-docs/unified-review-shape/unified-review-shape-spec.md`), which this feature finishes wiring at runtime.

Shared-convention check: the `--lens` flag and lens-path handling were compared against the existing pipeline. All path-like inputs in the program (the preset file, the lens path already passed to `load_lens_matrix`) use `pathlib.Path` directly with no resolution beyond the OS, and `--lens` follows that established pattern. The flag name reuses the parameter name already used throughout the code. No new convention is introduced.

---

## Contract 1 — the `--lens` flag on `validate` and `run`

- **Signature:** `pipeline validate [--lens PATH]` and `pipeline run --preset P --min-severity S [--lens PATH] [--output-markdown]`. PATH points at a lens file carrying a lens-matrix block.
- **Produced by:** each review skill's shell invocation (it hardcodes its own installed lens path).
- **Consumed by:** `cmd_validate` and `cmd_run` in `pipeline.py`.
- **The edit this requires** (not just plumbing): add the `--lens` option to both subparsers; in each command, load the lens once when the option is present; and change the `validate_sighting(s)` call sites — which today pass no vocabulary — to `validate_sighting(s, vocab)`. The functions `load_lens_matrix` and `validate_sighting(finding, vocab=None)` already exist; the commands do not yet call them with a lens.
- **Invariant:** when `--lens` is supplied, the lens vocabulary is loaded once before the first finding is validated, and every `validate_sighting` call in that invocation receives it. When `--lens` is absent, the vocabulary is `None` and validation falls back to the built-in constants — behavior-identical to today, so the default path is byte-identical.
- **Behavior when the lens is missing or malformed:** the command wraps the load so a missing file exits non-zero with the not-found message naming the path, and a file with no lens-matrix block exits non-zero with the parse error — both before any finding is processed, and as clean messages rather than raw tracebacks. This is new command-line behavior (no command loads a lens today). Malformed input findings keep the existing read-error behavior.
- **Realizes:** the parameterized-validator contract's command-line path (stated in the spec, previously unwired) and the loud-failure-on-missing-lens behavior; makes per-lens *finding* validation real at runtime. It does not touch scan-mode routing — `load_lens_matrix` does not parse the output mode and `validate_against_mode` has no command-line caller; scan-mode review types are out of scope for this feature.

---

## Contract 2 — the `normalize` subcommand

- **Signature:** `pipeline normalize` — no arguments. Reads a list of findings on input; emits a list of six-field records on output.
- **Produced by:** a new `cmd_normalize` in `pipeline.py` that reads the input list, applies the existing per-finding `normalize()` to each record in order, and writes the result. The `normalize()` function operates on a single finding and already exists; the list-reading command wrapper (including the standard input read-error path) does not and must be written.
- **Consumed by:** every finding-mode review skill, as the enforced strip step between validation and the challenger spawn.
- **Invariant:** output length equals input length; output order matches input order; every output record contains exactly the six allowlisted fields (`mechanism`, `consequence`, `evidence`, `type`, `severity`, `source_of_truth_ref`) and nothing else; location is folded into evidence exactly as `normalize()` already does.
- **Behavior when input is empty or malformed:** empty input yields empty output (not an error); a finding missing fields yields a six-field record with empty strings; non-JSON input keeps the existing read-error behavior and exits non-zero.
- **Realizes:** the normalization callable and the routing half of the isolation invariant, made executable rather than prose-trusted.

---

## Contract 3 — orchestrator retention and positional re-join

- **Signature:** before the challenger spawn the orchestrator keeps the full validated findings; after the challenge it overlays onto each kept finding only the verdict fields (`status`, `verification_evidence`, `rejection_reason`, `adjacent_observations`) and any reclassified `type`/`severity`, at the matching position `i`. It does **not** copy back the six neutral fields the challenger received — those are unchanged copies, and copying `evidence` back would re-fold the location into it a second time.
- **Produced by:** the orchestration steps in each finding-mode review skill.
- **Consumed by:** the post-challenge re-validation, code review's report renderer, and each review type's verdict-artifact authoring.
- **Invariant:** the challenger is expected to return exactly one verdict record per kept finding, in the same order. The orchestrator checks that the counts are equal and treats any inequality — too few or too many — as a challenger protocol violation that fails the handoff, never a fall-through. Verdict fields overlay the kept finding's fields, so a reclassified type or severity wins.
- **Known limitation (position is not reorder-proof), accepted:** the count check catches a dropped or inserted record but not a same-length reordering — a shuffled array would mis-join every record silently, because position is the only key once `id`/`title` are withheld. The challenger reads cold, is instructed same-order, and has nothing meaningful to reorder by, so the residual risk is low. **Locked 2026-06-24: position-only, no hardening.** An echoed index token was declined this iteration (it would add a carried field to the just-locked six-field isolation invariant for a low-probability risk); it is a future follow-on only if a real reorder is observed, not a spec open item.
- **Behavior when counts differ:** either direction fails the handoff with an error naming the discrepancy — fewer verdicts than findings leaves findings unmatched; more verdicts than findings means the challenger invented records, which violates the no-new-objects rule. Neither is silently tolerated. An invalid reclassified type-severity pair is separately dropped by the post-challenge re-validation.
- **Realizes:** the neutral-handoff isolation invariant (the challenger sees only the six fields) and the routing requirement that the normalize step sits in the path.

---

## Contract 4 — post-challenge re-validation uses the lens

> **Superseded in part at spec review (2026-06-24):** this contract's statement that "the verdict-field check stays prose" no longer holds. The spec extracted it into a separate `pipeline validate-verdicts` subcommand (spec Contract IF-S-03). `validate --lens` still checks only finding fields and the matrix, as below; the verdict-field check is now tool-enforced, not prose. See `code-review-exec-path-spec.md` and the spec-phase decisions-log entry.

- **Signature:** `pipeline validate --lens <type>-lens.md` over the re-joined merged records, for every finding-mode review type. Depends on Contract 1 — this command consumes a lens only after `cmd_validate` is taught the `--lens` option.
- **Produced by:** each review skill's post-challenge step.
- **Consumed by:** `cmd_validate` in `pipeline.py`.
- **What the command actually does (not a pure check):** `cmd_validate` drops every record it rejects and reassigns contiguous `S-NN` ids to the survivors. So this stage is a filter-and-renumber, not a read-only validation. This is acceptable because the positional re-join (Contract 3) has already completed before this stage runs, so dropping a record cannot corrupt the correlation, and the human-facing `F-NN` identifiers are assigned afterward, so the `S-NN` renumber is invisible downstream. It matches how code review already treats challenger output today.
- **What it validates, and what it does not:** `cmd_validate` checks only the finding-shaped fields — required fields, enums, the type-severity matrix. It does **not** check the verdict fields (`status`, presence of `verification_evidence` on verified statuses, and so on). Those stay a separate prose check in each skill, exactly as code review does today in its post-challenge step. This stage does not turn verdict validation into a tool guarantee — it makes the finding-field and matrix validation lens-aware for every review type. Naming this avoids implying the tool adjudicates verdicts.
- **Invariant:** the merged records carry `title` and `location` again (from the kept findings), so survivors pass the lens required set. Any reclassified type-severity pair is checked against the active lens's matrix — an invalid reclassification is dropped here.
- **Why the lens is mandatory here:** without it, re-validation falls back to code review's built-in matrix, which does not know the other review types' finding types and would reject their valid reclassifications as unknown types.
- **Realizes:** the parameterized-validator contract on the post-challenge finding-field validation step, for every finding-mode review type rather than code review alone. (The verdict-field check stays prose, unchanged.)

---

## Contract 5 — the composable pipe for the three new review types

- **Signature:** `<findings> | pipeline validate --lens <type>-lens.md | pipeline severity-filter --min-severity <threshold>`, used by test review, coherence review, and task review in place of code review's `run`.
- **Produced by:** the `fbk-test-review`, `fbk-coherence-review`, and `fbk-task-review` skills.
- **Consumed by:** the output feeds the `normalize` step and then the challenger spawn.
- **Invariant:** findings with a type, severity, or type-severity combination outside the lens are rejected and logged at the `validate --lens` stage; findings below the severity threshold are removed at the `severity-filter` stage. The domain-filter step is intentionally absent — the lens-parameterized validator rejects out-of-type findings, so the lens is the single type-filter authority for these review types. Note `severity-filter` does not renumber after dropping, so surviving `S-NN` ids can be non-contiguous on this path (unlike `run`, which renumbers); the positional re-join does not depend on id contiguity.
- **Why no preset-file entry:** adding these review types to the preset file would duplicate the type list the lens already declares, creating two lists that can drift. The lens stays the single source.
- **Realizes:** the parameterized-validator contract extended to the review types that have no preset-file entry.
