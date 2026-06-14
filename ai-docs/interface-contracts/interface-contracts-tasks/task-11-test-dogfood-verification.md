---
id: task-11
type: test
wave: 3
covers: [AC-17]
files_to_create:
  - tests/sdl-workflow/test-e2e-contracts-dogfood.sh
completion_gate: "tests compile and fail before implementation (red phase before the wired gate exists); after Wave 1 module + Wave 2 wiring land, the six UV steps pass end-to-end"
---

# task-11 — End-to-end dogfood of the wired contracts gate

## 1. Objective

Produces `tests/sdl-workflow/test-e2e-contracts-dogfood.sh`: a TAP-style shell test that runs the assembled, wired spec gate over a throwaway sample feature directory and exercises the six user-verification steps end to end.

## 2. Context

Test task for the `dogfood-verification` slice — the **cross-cutting** slice. There is NO paired implementation task: the implementation already exists across the other slices (the contracts module from Wave 1, the wiring from Wave 2). This is a test-only invariant that drives the real, assembled gate through its public CLI. It depends on the Wave 1 contracts module and the Wave 2 wiring, so it runs in Wave 3.

This is an e2e test: per test-authoring discipline, the production-path-exercise rule that forbids re-implementing logic still holds, but e2e tests exercise the gate through its real CLI rather than importing functions. It is also an E2E-harness case (harness setup + the tests that exercise it in one file), which the task-separation rule explicitly allows as a single combined task.

How the gate is invoked (follow `tests/sdl-workflow/test-e2e-spec-gate-parity.sh` and `test-e2e-breakdown-gate-parity.sh`): `python3 "$DISPATCHER" spec-gate "$SPEC_PATH"` where `DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"`. The gate exits `0` on pass and `2` on fail, and prints the failure strings to stderr. The gate derives the feature directory as the spec file's PARENT — so the sample spec and its `design/contracts.md` must be siblings: write the spec at `$SAMPLE/sample-spec.md` and the page at `$SAMPLE/design/contracts.md`.

The six UV steps (from the spec's user-verification steps), each a separate TAP assertion:

- UV-1 (real-entry pass): a sample spec with one `## Interface contracts` entry whose `covers` lists an acceptance criterion, plus a matching `design/contracts.md` carrying that same `IF-D-NN` → gate passes (exit 0).
- UV-2 (dropped contract fails): remove that entry from the spec without adding an `## Excluded contracts` entry → gate fails (exit 2), naming the dropped `IF-D-NN`, its design anchor, and the two resolution paths.
- UV-3 (uncovered AC fails): add an acceptance criterion not listed in any `covers` and not in `## Uncovered acceptance criteria` → gate fails (exit 2), naming that criterion and the two resolution paths.
- UV-4 (no-contracts vacuous pass): replace the section body with the no-contracts sentence and use a no-contracts `design/contracts.md` → gate passes (exit 0).
- UV-5 (un-named seam heuristic failure): declare an integration seam in `## Technical approach` whose two components no contract entry names → gate fails (exit 2) with the heuristic seam message (the message states it is a heuristic).
- UV-6 (excused contract passes): move the dropped contract into `## Excluded contracts` with a rationale → gate passes (exit 0).

Path-class note: this test asserts against the source dispatcher under `assets/` and builds throwaway sample specs under a temp dir — that is correct (it is a test, not an installed asset). The sample specs are fixtures, not installed assets, so they need no installed-path treatment.

Sample-spec construction note: each UV sample spec must be a valid feature spec that passes the EXISTING gate checks (the nine sections plus a `## Slices` block and any AC-format / testing-strategy-traceability rules), so the only failure exercised is the contract check under test. Build the samples by starting from a known-good minimal feature spec body (mirror the section set the existing gate requires — Problem, Goals, User-facing behavior, Technical approach, Testing strategy with an `AC-NN` reference, Documentation impact, Acceptance criteria, Dependencies, Open questions, and a `## Slices` block with a `new-contract` discipline) and adding/removing the `## Interface contracts` / `## Excluded contracts` / `## Uncovered acceptance criteria` / seam content per UV step. The spec file name must end `-spec.md` so the gate treats it as feature scope.

## 3. Instructions

1. Create `tests/sdl-workflow/test-e2e-contracts-dogfood.sh`, `chmod +x`, `set -uo pipefail` (match the e2e parity tests, which use `-uo` not `-e`, so a failing gate run does not abort the script).
2. `SCRIPT_DIR`/`PROJECT_ROOT` derivation; `DISPATCHER="$PROJECT_ROOT/assets/fbk-scripts/fbk.py"`.
3. Create a temp working area with `mktemp -d`; `trap 'rm -rf "$WORK"' EXIT`. Export a `LOG_DIR="$(mktemp -d)"` as the parity tests do, so gate audit logging writes to a throwaway dir.
4. Copy the `ok`/`not_ok` TAP helpers; print `echo "TAP version 13"`.
5. Write a shell helper that, given a spec body and a `design/contracts.md` body, creates `$WORK/uv-N/sample-spec.md` and `$WORK/uv-N/design/contracts.md`, runs `python3 "$DISPATCHER" spec-gate "$WORK/uv-N/sample-spec.md"`, and captures exit code and stderr. Each UV step uses its own subdir so the design pages do not collide.
6. Implement the six UV steps as six assertions per §5. For pass steps assert exit 0; for fail steps assert exit 2 AND that the required substrings appear in stderr.
7. Emit `echo "1..$TOTAL"`; `exit 1` when `FAIL > 0`.
8. Run the test. Before the gate is wired (Wave 1 + Wave 2 not yet landed) it FAILS — the gate does not run the contract checks, so UV-2/UV-3/UV-5 exit 0 instead of 2 (red phase). State this expectation in a comment.

## 4. Files to create/modify

- Create: `tests/sdl-workflow/test-e2e-contracts-dogfood.sh`

Do not modify any other file. No paired implementation task exists for this slice.

## 5. Test requirements

E2E shell test, TAP style, invoking the real gate via `python3 "$DISPATCHER" spec-gate`. Six assertions:

- UV-1: real entry + matching page → exit 0.
- UV-2: dropped contract, no exclusion → exit 2; stderr contains the dropped contract's `IF-D-NN` identifier and the "listed in design but not carried" message including both resolution paths. Assert stderr contains the substring `is listed in design/contracts.md but is not carried into ## Interface contracts` and the dropped `IF-D-NN` token.
- UV-3: uncovered AC → exit 2; stderr contains the substring `is not covered by any contract's covers: list and has no entry in ## Uncovered acceptance criteria` and the uncovered `AC-NN` token.
- UV-4: no-contracts section + no-contracts page → exit 0.
- UV-5: un-named seam → exit 2; stderr contains the substring `This is a heuristic check` and the two seam component names. Use the Unicode U+2192 arrow (`→`) in the `- [ ]` seam declaration.
- UV-6: dropped contract moved to `## Excluded contracts` with a rationale → exit 0.

Pair each fail assertion's exit-2 check with the stderr-substring check (per the assertion-specificity rule: an exit-2 alone could be the wrong failure; the substring proves it is the intended contract failure).

## 6. Acceptance criteria

- Covers AC-17.
- All six UV steps are exercised against the real wired gate via its CLI.
- Each fail step asserts both exit 2 and the intended-message substring.
- Test FAILS before Wave 1 module + Wave 2 wiring land (red phase: UV-2/UV-3/UV-5 pass-through instead of failing); passes once the gate is assembled and wired.

## 7. Model

Sonnet

## 8. Wave

Wave 3
