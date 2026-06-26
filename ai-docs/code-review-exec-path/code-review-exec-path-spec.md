# Code-review executable-path follow-on — Specification

Brownfield feature. Finishes wiring code review's executable validation/handoff path onto the unified-review-shape generic-agent contract, and extends the same tool-enforced guarantees to every finding-mode review type. A merge prerequisite for the `fbk/unified-review-shape` branch. Design is complete and gate-passed (`design-manifest.md`, five pages under `design/`, nine decisions in `docs/decisions-log.md` dated 2026-06-24). This spec transcribes that design into implementable form, pins the two items design handed to spec (the prose wording of the verdict-field check, and the concrete test list), and incorporates the spec-review resolutions of 2026-06-24 — most notably extracting the verdict-to-finding re-join into a tool-enforced, testable pipeline subcommand.

## Problem

The live code-review validator rejects every finding the new researcher produces, so code review comes back empty. The new researcher deliberately emits findings with no `id` (the pipeline assigns a sequential `S-NN` id after validation), but the code-review skill runs the validator with no lens at the detection round, so the validator falls back to its built-in required-field set — which still demands `id` — and rejects every id-less finding before the id-assignment step is ever reached. A second, quieter defect rides alongside it: the challenger is meant to judge each candidate cold, but the skill hands it the researcher's full findings (titles, detection-source tags, remediation hints) instead of the six neutral fields, so its "independent" verdict is biased. Both defects are failures to enforce, in the running program, guarantees the unified-review-shape design stated but left as prose the skill was trusted to follow.

## Goals / Non-goals

**Goals**

- Make the executable validator accept the new researcher's id-less findings by validating against the active lens's required set (which omits `id`) instead of the built-in set.
- Replace the prose "hand the challenger only six fields" instruction with a tool step (`pipeline normalize`) that provably emits exactly the six neutral fields.
- Replace the prose verdict-to-finding re-join with a tool step (`pipeline rejoin`) that enforces the count guard and the verdict-only overlay, so the feature's highest-consequence behavior is program-checked, not trusted to skill prose.
- Replace the prose verdict-field check with a tool step (`pipeline validate-verdicts`) that confirms each verdict carries a valid status and the evidence its status requires, so a malformed challenger verdict fails loudly instead of silently dropping a confirmed finding.
- Extend lens-aware validation, tool-enforced normalization, the tool-enforced re-join, and the tool-enforced verdict check to every finding-mode review type: code, test, coherence, and task review.
- Keep the default no-lens path through the validator byte-identical, so any caller still on it does not move.

**Non-goals**

- Scan-mode review types (fresh-eyes, top-five quality scan, doc reconcile) are out of scope. They declare a scan output mode and have no challenger handoff to enforce; the sweep does not touch them.
- The shared `review-loop.md` spine stays abstract and is not modified. It describes what must happen; each preset names the concrete commands.
- No new entries are added to the pipeline preset file for the three new review types. The lens is their single type-filter authority; a preset entry would duplicate the lens's type list and invite drift.
- Hardening the positional re-join against a same-length reordering is declined this iteration (locked 2026-06-24). Position-only is settled, not reopened here.
- Lens-governing the verdict check is out of scope. The five verdict statuses are generic across all review types (defined once in the shared review-loop spine), so the new `validate-verdicts` step takes no lens. Reclassification validity remains the job of the finding re-validation (`validate --lens`), which already checks a reclassified type/severity against the active matrix.

## User-facing behavior

The "user" is the operator running a review. Observable changes:

- **Code review stops returning empty.** A run over real code surfaces findings again, because the detection-round validator now accepts the researcher's id-less findings.
- **A missing or malformed lens fails loudly.** If a skill points `--lens` at a path that does not exist, the command exits non-zero with a clean message naming the path (`lens not found: <path>`), printed before any finding is processed — not a raw Python traceback. A lens file with no `lens-matrix` block exits non-zero with a clean parse error naming the file.
- **A miscounted challenger handoff fails loudly.** If the challenger returns a different number of verdicts than the orchestrator sent, `pipeline rejoin` exits non-zero naming the discrepancy, rather than silently mis-joining verdicts to findings.
- **A malformed verdict fails loudly.** If a verdict carries a status word that is not one of the five allowed values, or claims a finding is verified without attaching evidence, `pipeline validate-verdicts` exits non-zero naming the offending record — instead of the finding silently vanishing because its bad status fails to match the verified filter downstream.
- **The three other finding-mode review types gain tool-enforced validation.** Test, coherence, and task review now drive their detection through the pipeline (`validate --lens | severity-filter`), their handoff through `normalize`, and their re-join through `rejoin`, the same as code review. A finding whose type is outside the active lens is rejected at validation and logged as `REJECTED: invalid type …`, rather than silently passed to the challenger.
- **No visible change to code review's report or round history.** The findings report and the `.code-review-rounds.json` history file keep the same schema and format, with no new fields. Their content does change in one expected way — findings that were previously rejected for lacking an `id` now surface.
- **The default no-lens path is unchanged.** Any existing invocation that does not pass `--lens` produces byte-identical output — stdout, stderr, and exit code — to today.

## Technical approach

The feature changes two kinds of thing: the Python pipeline program (`assets/fbk-scripts/fbk/pipeline.py`), and the four finding-mode review-skill documents that orchestrate each review. The building-block functions already exist from the parent feature — `load_lens_matrix(lens_path)`, `validate_sighting(finding, vocab=None)`, and `normalize(finding)` — but no command-line path reaches them with a lens, there is no list-level `normalize` command, and the verdict-to-finding re-join exists only as prose the skill is trusted to perform. This is real editing, not pure plumbing.

### Pipeline program changes

**The `--lens` option on `validate` and `run`.** Add an optional `--lens PATH` argument to both the `validate` and `run` subparsers in `main()`. In `cmd_validate` and `cmd_run`, when `args.lens` is present, call `load_lens_matrix(args.lens)` once — before the first finding is validated — and thread the resulting `LensVocabulary` into every `validate_sighting` call (today both call `validate_sighting(s)` with no vocabulary; change the call sites to `validate_sighting(s, vocab)`). The two production call sites are the only ones: `cmd_validate` (`pipeline.py:212`) and `cmd_run` (`pipeline.py:350`); `validate_against_mode` already forwards `vocab` and is unaffected. When `args.lens` is absent, the vocabulary is `None` and `validate_sighting(s, None)` is behavior-identical to the current `validate_sighting(s)` (the `vocab is None` branch selects the same module constants), so the default path is byte-identical in stdout, stderr, and exit code.

The lens load is wrapped so failure is a clean command-line error, not a traceback: `load_lens_matrix` already raises `FileNotFoundError` (`lens not found: <path>`) for a missing file and `ValueError` (`no lens-matrix block found in: <path>`) for a file with no matrix block. Catch both in the command, print the message to stderr, and exit non-zero (`sys.exit(1)`, matching the existing in-band error convention used by `read_stdin_json`, `cmd_domain_filter`, and `cmd_severity_filter`) before any finding is read. No command loads a lens today, so this is new command-line behavior, not inherited. Note: under a lens, `vocab.required` is a `set`, so when more than one required field is missing the specific `missing field '<x>'` message is non-deterministic in which field it names; tests on the lens path must omit exactly one required field if they assert a specific message. The lens path is passed straight to `pathlib.Path`; the caller supplies an absolute installed path, matching how the preset file path is already handled.

**The `normalize` subcommand.** Add a `normalize` subparser (no arguments) and a new `cmd_normalize(args)`. It reads the finding list via the existing `read_stdin_json()` (which already exits non-zero with `ERROR: malformed JSON input` on non-JSON), applies the existing per-finding `normalize()` to each record in input order, and writes the result with `write_json`. A JSON empty array `[]` yields `[]` and exits zero. A finding missing one or more of the six source fields yields a record with empty strings for those fields and never raises, because `normalize()` reads every field via `.get(key, "")`. The six neutral fields are the independence boundary itself, identical for every finding-mode review type, so `normalize` takes no `--lens`.

**The `rejoin` subcommand (new this spec, from the spec-review resolution).** Add a `rejoin` subparser with one argument, `--verdicts PATH`, and a new `cmd_rejoin(args)`. It reads the orchestrator's kept full findings (id-bearing) on stdin, reads the challenger's verdict array from PATH, and overlays each verdict onto the kept finding at the matching position:

- **Count guard.** If `len(verdicts) != len(kept)`, print an error to stderr naming the discrepancy (the two counts and which is larger) and `sys.exit(1)`. Neither direction is tolerated: fewer verdicts leaves findings unmatched; more means the challenger invented records.
- **Verdict-only overlay.** For each position `i`, overlay onto `kept[i]` only the verdict fields the challenger adds — `status`, `verification_evidence`, `rejection_reason`, `adjacent_observations`. The six neutral fields the challenger received are never copied back (copying `evidence` back would re-fold the location into it a second time). The merged record's `evidence` therefore equals the kept finding's `evidence` byte-for-byte.
- **Reclassification rule.** Overlay `type` and `severity` from the verdict record only when its `reclassified_from` is a non-empty object; when `reclassified_from` is `{}` (the challenger's "unchanged" signal), retain the kept finding's original `type`/`severity`. Carry `reclassified_from` onto the merged record when non-empty.

The result is written with `write_json`. This makes the re-join a tool-enforced, unit-testable transform rather than prose each skill is trusted to perform. `rejoin` does not adjudicate verdict validity, only count and overlay — that is the next subcommand's job.

**The `validate-verdicts` subcommand (new this spec, from the spec-review resolution).** Add a `validate-verdicts` subparser (no arguments) and a new `cmd_validate_verdicts(args)`. It reads the challenger's verdict array on stdin and checks each record against the generic verdict contract that the shared spine and the challenger agent define — independent of any lens, because the five statuses are the same for every review type:

- `status` is one of `verified`, `verified-pending-execution`, `rejected`, `rejected-as-nit`, `unresolvable`.
- `verification_evidence` is present and at least 10 characters when `status` is `verified` or `verified-pending-execution` (matching the challenger's own contract minimum).
- `rejection_reason` is present and at least 10 characters when `status` is `rejected`.

On the first violation, print an error to stderr naming the offending record's position and what failed, and `sys.exit(1)` — a malformed verdict is a challenger protocol violation that fails the handoff loudly, the same posture as the count guard, rather than letting a bad status word slip through to the verified filter where it would silently drop a confirmed finding. On an all-valid array it writes the input through unchanged (so it can sit in a pipe); a JSON empty array passes (exit zero); non-JSON keeps the existing read-error behavior. This subcommand is the single place the five-status vocabulary is enforced in the program, replacing the prose verdict-field check that each skill carried; the canonical definition still lives in the spine and the challenger contract, and this check does not duplicate the per-skill prose copies — they are removed in favor of the call.

`validate-verdicts` takes no lens: reclassification validity (a changed type/severity against the active matrix) stays the job of the finding re-validation (`validate --lens`), so this command never needs the lens vocabulary.

**The minimum-length check stays fixed.** `validate_sighting` applies the `MIN_LENGTH_FIELDS` check (`title`, `mechanism`, `consequence` ≥ 10 chars) against module constants regardless of lens — a structural quality floor, deliberately not per-lens.

### Review-skill changes

Each finding-mode skill drives the same eight-stage flow: detect → validate-and-filter with lens → normalize → challenge → validate-verdicts → re-join by position → re-validate findings with lens → report/verdict. The concrete pipeline commands live in each skill; the shared `review-loop.md` spine stays abstract.

**Code review is a repoint** — it already invokes the pipeline (`run`/`validate`/`to-markdown` at steps 3, 5, 7). It gains `--lens code-lens.md` on the detection-round `run` (step 3) and the post-challenge `validate` (step 5); it inserts `normalize` before the challenger spawn (step 4), `validate-verdicts` on the challenger's returned verdicts, and `rejoin --verdicts <file>` to merge them (step 5). Its existing prose verdict-field check is replaced by the `validate-verdicts` call. Its report and round-history shapes are unchanged.

**Test, coherence, and task review are a prose→executable conversion, not an extension.** None of the three invokes the pipeline today — each describes the loop purely in prose and routes to the abstract spine. This feature introduces executable orchestration into all three for the first time. Because none has a preset-file entry, they use the composable pipe — `pipeline validate --lens <type>-lens.md | pipeline severity-filter --min-severity <threshold>` — in place of code review's `run`; the lens-parameterized validator does their type-filtering, so no domain-filter step and no preset entry is needed.

**The cited-source seam must be preserved.** The shared spine and the challenger contract require the orchestrator to collect the documents named in each kept finding's `source_of_truth_ref` and inject them into the challenger spawn, after the normalized findings and before the verification instructions. Each migrated skill's wiring must keep this step — the challenger's input order is: artifact, lens, normalized findings, cited-source documents, verification instructions. Dropping it would remove a locked verification input.

**The concrete eight-stage step template** each of the three converted skills adopts, expressed with its own lens path and severity threshold:

1. Spawn researcher (cold), collect candidate findings as JSON.
2. `<findings> | pipeline validate --lens <type>-lens.md | pipeline severity-filter --min-severity <threshold>` → the kept, id-bearing list; retain it as the orchestrator's record store.
3. `<kept> | pipeline normalize` → the six-field records handed to the challenger.
4. Collect each kept finding's `source_of_truth_ref` documents.
5. Spawn challenger (cold) with: artifact, lens, normalized findings, cited-source documents, verification instructions. Collect the verdict array as JSON; write it to a temp file.
6. `<verdicts-file> | pipeline validate-verdicts` → fails the handoff if any verdict has an invalid status or is missing the evidence its status requires.
7. `<kept> | pipeline rejoin --verdicts <verdicts-file>` → the merged records (count guard enforced here).
8. `<merged> | pipeline validate --lens <type>-lens.md` → re-validated survivors. Then author the `Verdict: accepted | needs-revision` artifact from the orchestrator's reasoning.

The threshold defaults to each preset's existing default (the same value the skill already uses for its prose severity filter); where a skill has no prior default, use `minor`, overridable by operator instruction.

**The post-challenge re-validation** runs the merged records back through `pipeline validate --lens <type>-lens.md`. This is a filter-and-renumber, not a pure check: `cmd_validate` drops rejected records and reassigns contiguous `S-NN` ids to survivors. That is safe because the re-join has already completed and `F-NN` identifiers are assigned afterward. The lens is mandatory so reclassifications are checked against the correct matrix. This command validates finding fields and the matrix only; the verdict fields are checked by the separate `validate-verdicts` step (stage 6) above.

**Only code review renders a findings report** from the surviving merged records. The other three write their verdict artifact from the orchestrator's own reasoning, so for them the re-join exists to enforce the count guard and satisfy stage-eight re-validation, not to feed a formatter.

### Integration seams

- [ ] fbk-code-review → pipeline.py: `--lens` passed on the `run` and post-challenge `validate` calls (code-lens path); `normalize` before the challenger; `validate-verdicts` on the returned verdicts; `rejoin --verdicts` to merge verdicts; cited-source documents injected into the challenger spawn; detection round accepts id-less findings; report and round-history shapes unchanged.
- [ ] fbk-test-review → pipeline.py: composable pipe `validate --lens test-lens.md | severity-filter`, a `normalize` call, a `validate-verdicts` call, a `rejoin --verdicts` call, post-challenge `validate --lens test-lens.md`, and cited-source injection — introduced as new executable wiring.
- [ ] fbk-coherence-review → pipeline.py: composable pipe `validate --lens coherence-lens.md | severity-filter`, `normalize`, `validate-verdicts`, `rejoin --verdicts`, post-challenge `validate --lens coherence-lens.md`, and cited-source injection — introduced as new executable wiring.
- [ ] fbk-task-review → pipeline.py: composable pipe `validate --lens task-lens.md | severity-filter`, `normalize`, `validate-verdicts`, `rejoin --verdicts`, post-challenge `validate --lens task-lens.md`, and cited-source injection — introduced as new executable wiring.

### Module touch policy

- [ ] `assets/fbk-scripts/fbk/pipeline.py`: extend — add `--lens` to the `validate` and `run` subparsers, add the `normalize` subparser and `cmd_normalize`, add the `rejoin` subparser and `cmd_rejoin`, add the `validate-verdicts` subparser and `cmd_validate_verdicts`, and change the two `validate_sighting(s)` call sites to pass the loaded vocabulary. No restructure precedes the additions, so no preparatory refactor task is warranted.
- [ ] `assets/skills/fbk-code-review/SKILL.md`: extend — repoint the existing `run`/`validate` calls (steps 3, 5) to pass the code lens, and add the `normalize`, `rejoin`, and cited-source steps.
- [ ] `assets/skills/fbk-test-review/SKILL.md`: convert prose loop to executable wiring — the skill invokes no pipeline command today; introduce the full seven-stage executable flow with `test-lens.md`.
- [ ] `assets/skills/fbk-coherence-review/SKILL.md`: convert prose loop to executable wiring — same, with `coherence-lens.md`.
- [ ] `assets/skills/fbk-task-review/SKILL.md`: convert prose loop to executable wiring — same, with `task-lens.md`.
- [ ] `assets/fbk-docs/fbk-review-lenses/review-loop.md`: leave alone — the spine stays abstract (per-preset wiring decision).
- [ ] `assets/fbk-scripts/fbk/data/fbk-presets.json`: leave alone — no entries added for the three new review types (the lens is their single type-filter authority).

## Testing strategy

Pipeline-level behavior is unit- and subprocess-testable in `assets/fbk-scripts/tests/`. The re-join and count guard — previously consigned to skill prose — are now a pipeline subcommand and are unit-tested directly. The skill-wiring behavior (which executable steps each skill contains, in order) is covered by skill-conformance tests that read each skill's markdown. The verdict-field *presence* check remains prose with no automated coverage, by the design decision that it stays prose; the validation ladder names this explicitly rather than hiding it.

**New tests needed**

- Unit test: `cmd_validate` with `--lens code-lens.md` accepts an otherwise-valid finding carrying no `id` — covers AC-01. Without the lens the same finding is rejected `missing field 'id'`.
- Subprocess test: `pipeline validate --lens <path>` over an id-less finding exits zero and emits it with an `S-NN` id; `pipeline validate` (no lens) rejects it — covers AC-01, AC-02.
- Subprocess test: `pipeline run --preset behavioral-only --min-severity minor --lens code-lens.md` accepts an id-less finding; and `run` with a missing and a malformed lens exits non-zero with the clean message — covers AC-01, AC-03, AC-04 on the `run` path.
- Subprocess test: `pipeline validate` and `pipeline run` with no `--lens` produce byte-identical stdout, stderr, and exit code to the current build over a fixed fixture, captured as golden values — covers AC-02. This is a genuinely new assertion: the existing `test_pipeline_backward_compat.py` checks warning substrings and output length but never asserts exit code or byte-identical stdout/stderr, so it does not already backstop AC-02.
- Subprocess test: `pipeline validate --lens /nonexistent/path.md` exits non-zero, prints `lens not found: /nonexistent/path.md` to stderr, processes no findings — covers AC-03. (Extends `test_pipeline_missing_lens.py`; fix its stale `AC-06` docstring reference inherited from the parent feature.)
- Subprocess test: `pipeline validate --lens <file-with-no-matrix-block>` exits non-zero with `no lens-matrix block found in:` before processing — covers AC-04.
- Ordering proof for the two above: feed a payload that would itself be rejected or fail to parse (malformed JSON, or a would-be-rejected finding) together with the missing/malformed lens, and assert the *only* stderr is the lens error, stdout is empty, and no `REJECTED:` or `ERROR: malformed JSON input` line appears — proving the lens loads and fails before any finding is read, not merely that the message text exists — covers AC-03, AC-04.
- Unit test: `cmd_normalize` over a multi-finding list returns one record per input in input order, each with exactly the six allowlisted keys and no others, location folded into evidence — covers AC-05. A finding missing source fields yields empty strings for them and does not raise — covers AC-05.
- Subprocess test: `pipeline normalize` on `[]` emits `[]` and exits zero; on non-JSON input exits non-zero with `ERROR: malformed JSON input` — covers AC-06.
- Unit test: `cmd_rejoin` happy path with position rigor — at least **three** kept findings and three verdicts, each carrying distinct sentinel values for `status`, `verification_evidence`, and `adjacent_observations`; assert each merged record `i` received exactly verdict `i`'s sentinels (exact index-to-index overlay). A reversal, a same-length off-by-one, or an "always overlay verdict[0]" bug must fail this test — a one-or-two-record fixture would not catch them — covers AC-09.
- Unit test: `cmd_rejoin` neutral-field protection — the verdict records carry sentinel-different values for **all six** neutral fields (`mechanism`, `consequence`, `evidence`, `type`, `severity`, `source_of_truth_ref`); assert every one of those six on each merged record equals the kept finding's value, not the verdict's. A bug that copied back any neutral field (not only `evidence`) must fail — covers AC-13.
- Unit test: `cmd_rejoin` reclassification — a verdict with non-empty `reclassified_from` overlays its `type`/`severity` **and** the non-empty `reclassified_from` itself is carried onto the merged record exactly (the report renderer reads `reclassified_from`); a verdict with `reclassified_from == {}` leaves the kept finding's original `type`/`severity` and carries no reclassification — covers AC-13.
- Subprocess test: `pipeline rejoin --verdicts <file>` exits non-zero naming the discrepancy when the verdict array has length N+1 and when it has length N−1 against N kept findings — covers AC-09.
- Unit/subprocess test: `pipeline validate-verdicts` — a verdict with a status outside the five allowed values exits non-zero naming the record; a `verified` verdict with empty or under-10-character `verification_evidence` exits non-zero; a `rejected` verdict missing `rejection_reason` exits non-zero; an all-valid array passes through unchanged with exit zero; a JSON empty array passes — covers AC-15. One case must prove the silent-loss path is closed: a verdict typed `approved` (not a real status) is rejected loudly here rather than slipping to the verified filter and disappearing.
- Per-type catching test (one per new review type): `pipeline validate --lens test-lens.md` rejects a finding typed `behavioral` with `REJECTED: invalid type 'behavioral'`; likewise `coherence-lens.md` and `task-lens.md`. The fixture is otherwise-valid (all required fields present, min-lengths met) so the type-enum branch is the one that fires, not the required-field check — covers AC-07, AC-12.
- Skill-conformance test (one per finding-mode skill): assert the skill markdown contains its required executable steps in order — for code review, `run … --lens`, `normalize`, `validate-verdicts`, `rejoin`, post-challenge `validate … --lens`; for the three converted skills, `validate --lens <type>-lens.md`, `severity-filter`, `normalize`, `validate-verdicts`, `rejoin --verdicts`, post-challenge `validate --lens <type>-lens.md` — and that each contains the cited-source injection instruction — covers AC-07, AC-08, AC-10, AC-14. Use anchored structural markers (the step prefix, not a bare substring) so the assertion does not pass on an incidental mention in prose. **Stated limitation:** this proves the documented command sequence is present and ordered, not that the running skill executes it correctly — the latter is the operator manual end-to-end run (UV-3). The gap is narrowed by the next test.
- Chained-integration subprocess test (composition proof): pipe a fixture finding list through the real command sequence end to end — `validate --lens <lens> | severity-filter --min-severity <t> | normalize`, then `validate-verdicts` over a challenger-verdict fixture, then `rejoin --verdicts <challenger-fixture>`, then `validate --lens <lens>` — using real repo-relative lens files, and assert the final output is well-formed and the verdicts landed on the right findings. This catches inter-command contract drift (a field one command emits that the next does not read) that per-command unit tests miss, and is the automated backstop for the skill seams short of spawning agents — covers AC-07, AC-08, AC-09 (composition).

**Existing tests impacted**

- `test_pipeline_backward_compat.py` — pins the default no-lens `validate`/`run` path and the 30%-rejected warning (single-arg `validate_sighting` calls). Stays green under the new `vocab=None` default; extend with the stdout/stderr/exit-code byte-identical fixture for AC-02. No assertion changes.
- `test_pipeline_normalize.py` — tests the per-finding `normalize()`. Stays valid unchanged; the new `cmd_normalize` wraps the same function. Add the list-level subcommand cases.
- `test_pipeline_missing_lens.py` — tests the function-level `load_lens_matrix` raise. Stays valid; add the command-line wrapping cases for AC-03/AC-04 and fix the stale `AC-06` docstring reference.
- `test_pipeline.py` — exercises `validate`/`run`/`severity-filter`. No call site asserts a fixed `validate_sighting` argument count; the optional `vocab` is backward-compatible. No changes expected; re-run to confirm zero regressions.

**Test infrastructure changes**

- Lens fixtures: tests load the four lenses **repo-relative** under `assets/fbk-docs/fbk-review-lenses/` (not the `$HOME/.claude` install state, so CI does not depend on installation), plus a malformed-lens fixture (a markdown file with no `lens-matrix` fence) for AC-04. The skills' runtime `--lens` paths stay installed-absolute; only the tests use repo-relative paths. No new framework: the existing pytest suite, the `subprocess_run_pipeline_validate` helper, and plain file-content assertions for the skill-conformance tests cover all cases.

**Mocking justifications**

- None. Every test runs the real `pipeline.py` against real lens files and JSON fixtures, or reads a skill markdown file directly. No external service, clock, randomness, or third-party side effect is involved.

**Validation ladder, cheapest first**

1. Unit tests on `cmd_validate`/`cmd_normalize`/`cmd_rejoin`/`cmd_validate_verdicts` and `validate_sighting(finding, vocab)` — required-set, six-field, type-rejection, count-guard, overlay-selectivity, and verdict-status/evidence behavior.
2. Subprocess tests invoking the real CLI — default-path byte-identity (stdout/stderr/exit), missing/malformed-lens behavior, empty/non-JSON normalize input, `run --lens`, rejoin count-mismatch exits.
3. Skill-conformance tests reading each skill markdown — the required executable steps are present and ordered, and the cited-source injection instruction is present.
4. Operator manual end-to-end run (most expensive, genuine source of truth) — the migrated skills run against a real artifact, exercising the full agent-spawning orchestration that no Python test reaches (the researcher and challenger are live agents). Every command-level guarantee below the agents — lens validation, normalize, validate-verdicts, rejoin, re-validate — is now tool-enforced and automatically tested, so this run confirms the orchestration wires them together correctly rather than standing in for any single unchecked behavior.

**User verification steps**

- UV-1: Run code review over a real changed module → findings surface in the report (not empty), confirming the detection round accepts id-less findings. Covers AC-01.
- UV-2: Point a skill's `--lens` at a deleted path and run → `lens not found: <path>` on stderr, non-zero exit, no traceback, no findings emitted. Covers AC-03.
- UV-3: Run test review (or coherence/task review) over a real artifact → the run completes through validate-with-lens, normalize, challenge, validate-verdicts, rejoin, and re-validate, and the challenger's spawn input contains only the six neutral fields plus the cited-source documents. Covers AC-07, AC-08, AC-14.
- UV-4: Inject a challenger response with one extra verdict → `pipeline rejoin` exits non-zero naming the count discrepancy and the handoff fails. Covers AC-09.

## Documentation impact

**Project documents to update**

- `GLOSSARY.md`: add entries for *composable pipe* (the `validate --lens | severity-filter` command shape the three preset-less review types use) and *neutral handoff* (the six-field normalized record the challenger receives). Both are load-bearing terms in this spec and neither is currently defined — the parent feature minted researcher/challenger/lens/preset entries but not these. This feature introduces them, so it owns the entries.
- `docs/decisions-log.md`: **done** — a spec-phase entry was written 2026-06-24 recording (1) the re-join-as-subcommand resolution, (2) the verdict-field check tool-enforced via `pipeline validate-verdicts` superseding the design's "stays prose" lock, and (3) the reaffirmed full-sweep scope. The design's Contract 4 was also annotated with a forward-pointer noting the supersession. No breakdown task needed for this item.
- `CHANGELOG.md`: not updated at spec time. Add a Fixed/Changed entry when this feature is part of a tagged release (code review no longer returns empty; finding-mode review types enforce validation, normalization, and the re-join via the tool).

**New documentation to create**

- None. The design pages and this spec are the durable record; no runbook or ADR is required.

## Acceptance criteria

- AC-01: With `--lens <type>-lens.md` supplied, `pipeline validate` and `pipeline run` validate every finding against the lens's required set (which omits `id`) and accept an otherwise-valid finding carrying no `id`; without `--lens`, the same finding is rejected `missing field 'id'`.
- AC-02: With no `--lens`, `pipeline validate` and `pipeline run` produce byte-identical stdout, stderr, and exit code to the pre-change build over a fixed fixture.
- AC-03: A missing lens path makes `validate`/`run` exit non-zero with `lens not found: <path>` printed before any finding is processed, with no Python traceback.
- AC-04: A lens file with no `lens-matrix` block makes `validate`/`run` exit non-zero with `no lens-matrix block found in: <path>` before any finding is processed.
- AC-05: `pipeline normalize` emits one record per input finding, in input order, each containing exactly the six allowlisted fields (`mechanism`, `consequence`, `evidence`, `type`, `severity`, `source_of_truth_ref`) and nothing else, with location folded into evidence; a finding missing source fields yields empty strings for them and does not raise.
- AC-06: `pipeline normalize` on a JSON empty array `[]` emits `[]` and exits zero; on non-JSON input it exits non-zero with `ERROR: malformed JSON input`.
- AC-07: Test, coherence, and task review each drive detection through `validate --lens <type>-lens.md | severity-filter --min-severity <threshold>`, and `validate --lens` rejects a finding whose type is outside that lens (for example a `behavioral` finding under `test-lens.md`).
- AC-08: Each finding-mode review skill inserts a `normalize` call between validation and the challenger spawn, so the challenger receives only the six neutral fields.
- AC-09: Each finding-mode review skill re-joins challenger verdicts to its kept findings by position through `pipeline rejoin --verdicts <file>`, which exits non-zero naming the discrepancy when the verdict count differs from the kept-finding count in either direction.
- AC-10: After the challenge, each finding-mode review skill re-validates the merged records with `validate --lens <type>-lens.md` (finding fields and matrix) and checks the challenger's verdicts with `pipeline validate-verdicts` (status and evidence), replacing the prose verdict-field check each skill carried.
- AC-11: code-review's `run` and post-challenge `validate` calls pass `code-lens.md`; the detection round accepts id-less findings, and the findings report and `.code-review-rounds.json` keep the same schema and format with no new fields.
- AC-12: No entries are added to `fbk-presets.json` for test, coherence, or task review; the lens remains their single type-filter authority.
- AC-13: `pipeline rejoin` overlays only the four verdict fields onto each kept finding and never copies back the six neutral fields (the merged `evidence` equals the kept finding's `evidence`); it overlays a reclassified `type`/`severity` only when the verdict's `reclassified_from` is a non-empty object, otherwise retaining the kept finding's original classification.
- AC-14: Each finding-mode review skill collects the documents named in each kept finding's `source_of_truth_ref` and injects them into the challenger spawn, positioned after the normalized findings and before the verification instructions.
- AC-15: `pipeline validate-verdicts` exits non-zero naming the offending record when any verdict has a status outside the five allowed values, a `verified`/`verified-pending-execution` verdict missing `verification_evidence` (or shorter than 10 characters), or a `rejected` verdict missing `rejection_reason`; it passes through an all-valid array unchanged (exit zero), passes a JSON empty array, and takes no lens.

## Interface contracts

- id: IF-D-01
  name: `--lens` flag on `validate` and `run`
  signature: `pipeline validate [--lens PATH]` and `pipeline run --preset P --min-severity S [--lens PATH] [--output-markdown]`, consumed by `cmd_validate`/`cmd_run` in pipeline.py, produced by each review skill's shell call (fbk-code-review passes code-lens.md).
  invariants: when `--lens` is supplied the lens vocabulary is loaded once before the first finding and every `validate_sighting` call receives it; when absent the vocabulary is `None` and the path is byte-identical (stdout, stderr, exit code) to today; a missing or malformed lens exits non-zero with a clean named message before any finding is processed.
  covers: [AC-01, AC-02, AC-03, AC-04, AC-11]
  design-ref: design/contracts.md#contract-1
- id: IF-D-02
  name: the `normalize` subcommand
  signature: `pipeline normalize` (no arguments) in pipeline.py; reads a finding list on stdin, emits a list of six-field records on stdout; produced by every finding-mode review skill as the strip step before the challenger.
  invariants: output length equals input length; output order matches input order; every record contains exactly the six allowlisted fields and nothing else; location is folded into evidence as `normalize()` already does; a finding missing source fields yields empty strings for them and never raises; a JSON empty array yields an empty array (exit zero); non-JSON input exits non-zero.
  covers: [AC-05, AC-06, AC-08]
  design-ref: design/contracts.md#contract-2
- id: IF-D-03
  name: orchestrator retention and the re-join call
  signature: each finding-mode review skill keeps the full validated findings before the challenger spawn, hands the challenger only the normalized six fields plus cited-source documents, and merges verdicts by calling `pipeline rejoin --verdicts <file>` (IF-S-01).
  invariants: the challenger returns exactly one verdict record per kept finding in the same order; the count guard in `rejoin` fails the handoff on any inequality in either direction; position is the only correlation key (same-length reordering is an accepted documented limitation, position-only locked 2026-06-24).
  covers: [AC-09]
  design-ref: design/contracts.md#contract-3
- id: IF-D-04
  name: post-challenge re-validation uses the lens
  signature: `pipeline validate --lens <type>-lens.md` over the re-joined merged records, for every finding-mode review type; consumed by `cmd_validate`, depends on IF-D-01.
  invariants: validates finding fields and the matrix only (not verdict fields); drops rejected records and renumbers survivors' `S-NN` ids, safe because the re-join precedes it and `F-NN` ids are assigned afterward; the lens is mandatory so reclassifications are checked against the correct matrix; the verdict-field check is the separate `validate-verdicts` step (IF-S-03).
  covers: [AC-10]
  design-ref: design/contracts.md#contract-4
- id: IF-D-05
  name: the composable pipe for the three new review types
  signature: `<findings> | pipeline validate --lens <type>-lens.md | pipeline severity-filter --min-severity <threshold>`, produced by fbk-test-review, fbk-coherence-review, and fbk-task-review in place of code review's `run`.
  invariants: out-of-type and out-of-matrix findings are rejected and logged at `validate --lens`; below-threshold findings are removed at `severity-filter` (which does not renumber, so surviving `S-NN` ids can be non-contiguous — unlike `run`, which renumbers a second time after filtering); no domain-filter step and no preset-file entry — the lens is the single type-filter authority.
  covers: [AC-07, AC-12]
  design-ref: design/contracts.md#contract-5
- id: IF-S-01
  name: the `rejoin` subcommand
  signature: `pipeline rejoin --verdicts PATH` in pipeline.py; reads the kept full findings on stdin, the challenger verdict array from PATH; emits merged records or exits non-zero on count mismatch; produced by every finding-mode review skill, consumed by the post-challenge re-validation.
  invariants: exits non-zero naming the discrepancy when verdict count differs from kept count in either direction; overlays only `status`, `verification_evidence`, `rejection_reason`, `adjacent_observations`; never copies back the six neutral fields (merged `evidence` equals the kept finding's `evidence`); overlays `type`/`severity` only when the verdict's `reclassified_from` is a non-empty object, otherwise retains the kept finding's classification; does not adjudicate verdict-field validity.
  covers: [AC-09, AC-13]
  design-ref: design/contracts.md#contract-3
- id: IF-S-02
  name: cited-source injection into the challenger spawn
  signature: each finding-mode review skill collects the documents named in each kept finding's `source_of_truth_ref` and injects them into the challenger spawn, after the normalized findings and before the verification instructions.
  invariants: the challenger's input order is artifact, lens, normalized findings, cited-source documents, verification instructions; a kept finding with an empty `source_of_truth_ref` contributes no document; the step is present in every migrated skill (verified by skill-conformance test).
  covers: [AC-14]
  design-ref: assets/fbk-docs/fbk-review-lenses/review-loop.md
- id: IF-S-03
  name: the `validate-verdicts` subcommand
  signature: `pipeline validate-verdicts` (no arguments, no lens) in pipeline.py; reads the challenger verdict array on stdin; passes the input through unchanged on success or exits non-zero naming the offending record; produced by every finding-mode review skill after the challenger returns, replacing the prose verdict-field check.
  invariants: rejects a status outside the five allowed values (`verified`, `verified-pending-execution`, `rejected`, `rejected-as-nit`, `unresolvable`); requires `verification_evidence` (≥10 chars) on `verified`/`verified-pending-execution` and `rejection_reason` (≥10 chars) on `rejected`; first violation exits non-zero (the count-guard posture); an all-valid array passes through unchanged (exit zero); a JSON empty array passes; non-JSON keeps the existing read-error behavior; takes no lens because the five statuses are generic across review types.
  covers: [AC-10, AC-15]
  design-ref: assets/fbk-docs/fbk-review-lenses/review-loop.md

## Open questions

None.

## Dependencies

- `assets/fbk-scripts/fbk/pipeline.py` — the existing functions `load_lens_matrix`, `validate_sighting(finding, vocab=None)`, and `normalize(finding)`, shipped by the parent unified-review-shape feature, are prerequisites this feature wires to the command line.
- The four finding-mode lenses (`code-lens.md`, `test-lens.md`, `coherence-lens.md`, `task-lens.md`), each carrying an `id`-less `required:` set and its own type/severity matrix (verified present).
- The `fbk-review-challenger` agent's output contract — "the same array you received, with verdict fields added," `reclassified_from` empty `{}` when unchanged — which the positional re-join and the reclassification rule depend on.
- The shared `review-loop.md` spine's cited-source collection-and-injection requirement, which the cited-source seam (IF-S-02) preserves.
- The five verdict statuses and their evidence rules, defined canonically in the `review-loop.md` spine and the `fbk-review-challenger` contract, which `validate-verdicts` (IF-S-03) enforces in the program.
- Python 3 standard library only (`json`, `argparse`, `pathlib`, `re`) — no new third-party dependency.

## Slices

```yaml
slices:
  - name: lens-flag-on-validate-and-run
    description: Add --lens to the validate and run subcommands, load the lens once, thread the vocabulary into every validate_sighting call, and wrap the load so a missing or malformed lens exits non-zero with a clean named message.
    test-discipline: new-contract
    covers: [AC-01, AC-03, AC-04, AC-11]
  - name: default-path-byte-identical
    description: Keep the no-lens path through validate and run byte-identical (stdout, stderr, exit code) to today, so any caller still on it does not move.
    test-discipline: contract-preserving
    covers: [AC-02]
  - name: normalize-subcommand
    description: Add the no-argument normalize subcommand that maps the existing per-finding normalize() over the input list and emits exactly the six neutral fields in input order, with empty strings for missing source fields.
    test-discipline: new-contract
    covers: [AC-05, AC-06]
  - name: rejoin-subcommand
    description: Add the rejoin subcommand that overlays challenger verdicts onto kept findings by position, enforces the count guard, applies the reclassification rule, and never copies back the six neutral fields.
    test-discipline: new-contract
    covers: [AC-09, AC-13]
  - name: validate-verdicts-subcommand
    description: Add the no-lens validate-verdicts subcommand that checks each challenger verdict's status enum and the evidence its status requires, failing loudly on a malformed verdict.
    test-discipline: new-contract
    covers: [AC-15]
  - name: code-review-skill-rewire
    description: Repoint code review's run and post-challenge validate to pass the code lens, and insert the normalize, rejoin, and cited-source steps, preserving the report and round-history shapes.
    test-discipline: new-contract
    covers: [AC-08, AC-10, AC-11, AC-14]
  - name: three-skill-executable-migration
    description: Convert test, coherence, and task review from prose orchestration to the executable seven-stage flow (composable-pipe validate, normalize, cited-source injection, rejoin, post-challenge re-validate), introducing pipeline wiring into each for the first time.
    test-discipline: new-contract
    covers: [AC-07, AC-08, AC-10, AC-12, AC-14]
```

---

## Decisions resolved during spec

- **Re-join extracted into a tool-enforced subcommand (spec-review resolution, operator-confirmed 2026-06-24).** The design had the verdict-to-finding re-join as prose each skill performs. Spec review found this the feature's highest-consequence behavior (position is the only correlation key) with zero automated coverage, and that it is a pure two-list transform. Resolution: add `pipeline rejoin --verdicts PATH` (IF-S-01), so the count guard and verdict-only overlay are program-enforced and unit-tested, and every migrated skill calls it. This supersedes the design's "re-join is skill prose" for the count and overlay mechanics; the verdict-field *presence* check stays prose per the unchanged design lock.
- **Full four-skill sweep reaffirmed, framing corrected (operator-confirmed 2026-06-24).** The three non-code skills have no executable pipeline wiring today, so the sweep is a prose→executable conversion, not an extension. The operator reaffirmed keeping all four review types in scope; the spec's module-touch policy and technical approach now state the true cost (net-new wiring) and the coarse migration slice was split into a code-review repoint slice and a three-skill conversion slice.
- **Cited-source injection seam preserved (IF-S-02).** Spec review caught that the seven-stage flow omitted the shared spine's requirement to inject each finding's cited-source documents into the challenger spawn. Restored as an explicit step in every migrated skill, covered by skill-conformance tests.
- **No threat model (operator-confirmed 2026-06-24).** No new trust boundary, auth change, data storage, or external API; rationale recorded in the review document.
- **Verdict-field check tool-enforced, superseding the design lock (operator-confirmed 2026-06-24).** The design handed spec the prose *wording* of the verdict-field check and locked that it "stays prose." Two test-review passes flagged it as the one remaining trusted-prose gap with no automated coverage, in the same place the feature already decided the challenger cannot be trusted (the count guard). Because the silent failure is real — a status word outside the five allowed values fails the downstream verified filter and the confirmed finding silently vanishes — the operator chose to tool-enforce it. Resolution: a separate `pipeline validate-verdicts` subcommand (IF-S-03), no lens, checking the status enum and the evidence each status requires, failing loudly on a violation. This supersedes the design's "stays prose" lock. A separate step was chosen over folding the check into `rejoin` to keep each subcommand single-purpose and independently testable. The five-status vocabulary is now enforced in one program location, replacing the four per-skill prose copies; its canonical definition still lives in the spine and challenger contract.
- **Lens-load failure exit code.** `sys.exit(1)`, matching the existing in-band error convention, rather than argparse's exit code 2.
- **Slice `covers` references.** This feature entered mid-pipeline with no intent phase, so there is no `behavior-inventory.yaml`. Slice `covers` lists reference acceptance-criterion identifiers, the most concrete behavioral units available.
- **Two skill slices reclassified to `new-contract` at breakdown (operator-confirmed 2026-06-24).** The code-review skill rewire and the three-skill conversion were originally labeled `cross-cutting` (tests-only, no implementation task). Breakdown found this incompatible with the work: three of the four skill files have no pipeline wiring today and the module-touch policy mandates editing all four, so each slice needs a real implementation task that rewrites the skill file plus a conformance test that pins the new command-step sequence — the shape of a `new-contract` slice. The breakdown gate also forbids an implementation task on any acceptance criterion a cross-cutting slice touches, several of which are shared with the pipeline work that requires implementation. Reclassified both to `new-contract`.
