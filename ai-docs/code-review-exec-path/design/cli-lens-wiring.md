# Lens wiring on the validator — the first defect

## The problem in one line

The live validator rejects every finding the new researcher produces, so code review returns empty.

## Why it happens

The researcher is told, by design, not to put an `id` on a finding — the pipeline assigns a sequential `S-NN` id *after* validation. But the code-review skill runs the validator with no lens, so it falls back to the built-in required-field set (`REQUIRED_FIELDS`, which includes `id`). The required-field check runs before the id-assignment loop, so an id-less finding is rejected as "missing field 'id'" before the line that would have added the id is ever reached.

The building blocks to fix this already exist as functions — but no command-line path reaches them, and the two commands that validate do not pass a vocabulary today:
- Each lens file declares its own `required:` set. Every finding-mode lens (`code-lens`, `test-lens`, `coherence-lens`, `task-lens`) declares `[title, location, type, severity, mechanism, consequence, evidence]` — correctly omitting `id`. (Verified across all four lenses.)
- `load_lens_matrix(path)` already parses a lens file into a vocabulary object, but no command calls it.
- `validate_sighting(finding, vocab)` already accepts a vocabulary, but `cmd_validate` and `cmd_run` both call it as `validate_sighting(s)` with no vocabulary, so it falls back to the built-in constants.

So the fix is real editing in three places, not just plumbing: add the `--lens` option to the two subcommands, load the lens once per invocation, and change the `validate_sighting` call sites in `cmd_validate` and `cmd_run` to pass the loaded vocabulary.

## The shape of the fix

Add an optional `--lens <path>` argument to the `validate` and `run` subcommands.

```
pipeline validate [--lens PATH]
pipeline run --preset P --min-severity S [--lens PATH] [--output-markdown]
```

Inside each command, when `--lens` is supplied:
1. Call `load_lens_matrix(PATH)` once, before the first finding is validated.
2. Thread the resulting vocabulary into every `validate_sighting(finding, vocab)` call in that invocation.

When `--lens` is absent, the vocabulary is `None` and validation falls back to the built-in constants exactly as today. `validate_sighting(s, None)` is behavior-identical to the current `validate_sighting(s)` (confirmed by reading the function: the `vocab is None` branch selects the same module constants). The default path is therefore byte-identical, which is what keeps every existing caller from moving.

The code-review skill then passes its lens on the two calls that need it:
- The detection-round validate/filter call gains `--lens <install>/fbk-docs/fbk-review-lenses/code-lens.md`.
- The post-challenge validate call gains the same lens.

Id assignment still happens immediately after validation, so the domain-filter and severity-filter stages downstream still operate on id-bearing records, unchanged.

## Path resolution

The lens value is passed straight to `pathlib.Path` inside `load_lens_matrix`. The caller supplies an absolute installed path (`"$HOME"/.claude/fbk-docs/fbk-review-lenses/<type>-lens.md`). No install-root resolution happens inside the program — this matches how every other path in the pipeline (the preset file) is already handled. `load_lens_matrix` already raises a not-found error whose message names the path when the file is absent — but no command calls it today, so this is a **new** command-line behavior, not an inherited one. The new `--lens` handling in `cmd_validate`/`cmd_run` must wrap the load so the command exits non-zero with that clean named message before processing any finding, rather than surfacing a raw traceback. This makes a missing or misnamed lens a loud, legible failure on the command line.

## What stays fixed regardless of lens

The minimum-length check on `title`, `mechanism`, and `consequence` runs against built-in constants for every lens. This is deliberate — it is a structural quality floor, not a per-type vocabulary. No lens needs a different minimum, and every finding-mode lens already requires those three fields, so the check never fires spuriously. Making it per-lens is scope this fix does not need.

## Realizes

The runtime half of the parameterized-validator contract the spec stated but left unwired, and the loud-failure-on-missing-lens behavior on the command-line path. See `contracts.md`.
