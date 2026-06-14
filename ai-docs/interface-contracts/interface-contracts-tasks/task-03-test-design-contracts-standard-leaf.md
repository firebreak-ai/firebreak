---
id: task-03
type: test
wave: 1
covers: [AC-14]
files_to_create:
  - tests/sdl-workflow/test-design-contracts-standard-leaf.sh
completion_gate: "tests compile and fail before implementation (red phase before the design-contracts-standard.md leaf and design-guide.md edit exist)"
---

# task-03 — Test the design contracts-standard leaf and design-guide route

## 1. Objective

Produces `tests/sdl-workflow/test-design-contracts-standard-leaf.sh`: a TAP-style shell test that mechanically checks `design-guide.md` carries the required-page note and conditional route, and that the new `design-contracts-standard.md` leaf carries the entry schema and the design-page parse rule.

## 2. Context

Test task for the `design-contracts-standard-leaf` slice (new-contract discipline). The paired implementation task (task-04) creates the leaf `assets/fbk-docs/fbk-sdl-workflow/design-contracts-standard.md` and edits `design-guide.md`. Neither change exists yet — this test compiles and FAILS (red phase) until they do.

What the leaf and guide must contain (the properties this test checks):

- `design-guide.md` states `contracts.md` is required on every feature (a no-contracts feature writes one sentence), and routes to the standard leaf *only when the feature has contracts*.
- `design-contracts-standard.md` carries the `IF-D-NN` entry schema — the `## IF-D-NN — <name>` heading form with the four fields `signature`, `invariants`, `consumed-by`, `produced-by` — and the design-page parse rule `^## (IF-D-` (the line-anchored regex the gate uses).

Path-class rule: these are source files under `assets/`, so the test asserts against the source path `assets/fbk-docs/fbk-sdl-workflow/...`. But any path the leaf/guide *body* instructs an agent to read or run must be an INSTALLED path (`.claude/fbk-docs/...`, `python3 "$HOME"/.claude/fbk-scripts/fbk.py ...`), never an `assets/` source path. The reference-integrity assertion below enforces that no installed asset body contains the literal `assets/` source-path prefix.

Convention to follow: `tests/sdl-workflow/test-instruction-hygiene-coverage.sh` (PROJECT_ROOT derivation from `BASH_SOURCE`, `ok`/`not_ok` helpers, `TOTAL`/`PASS`/`FAIL` counters, `grep -q` assertions, `1..$TOTAL` plan line, non-zero exit when `FAIL > 0`). Use structural-marker greps (anchored headings, exact regex literals) per test-authoring discipline — not body-vocabulary greps.

## 3. Instructions

1. Create `tests/sdl-workflow/test-design-contracts-standard-leaf.sh`, `chmod +x` it, `set -euo pipefail`.
2. Derive `PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"`.
3. Define paths:
   - `GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/design-guide.md"`
   - `LEAF="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/design-contracts-standard.md"`
4. Copy the `ok`/`not_ok` TAP helpers from `test-instruction-hygiene-coverage.sh`.
5. Write the assertions in §5. Use `grep -q` with anchored/structural patterns. Guard each file read: if `LEAF` does not exist, the schema assertions naturally fail (red phase) — let them, do not `[ -f ]`-skip them.
6. Emit `echo "1..$TOTAL"` and `exit 1` when `FAIL > 0`.
7. Run `bash tests/sdl-workflow/test-design-contracts-standard-leaf.sh` and confirm it FAILS (the leaf is absent; the guide edit is not yet made) — red phase.

## 4. Files to create/modify

- Create: `tests/sdl-workflow/test-design-contracts-standard-leaf.sh`

Do not modify any other file. (The leaf and guide edit are made by task-04.)

## 5. Test requirements

Shell integration tests (instruction-hygiene + reference-integrity), TAP style. All assert against source files under `assets/`.

Instruction-hygiene (AC-14):

- `design-guide.md` states `contracts.md` is required on every feature. Grep for an anchored marker naming `contracts.md` as required — e.g. `grep -q 'contracts.md' "$GUIDE"` combined with a required-marker term. Pair it with a presence check so the test fails when the note is absent.
- `design-guide.md` routes to the standard leaf conditionally — grep the guide for a reference to `design-contracts-standard.md`. Assert the route is conditional (the guide text gates the route on the feature having contracts) by greping for both the leaf filename and a conditional clause near it.
- `design-contracts-standard.md` carries the `IF-D-NN` entry schema — grep the leaf for the heading form `## IF-D-NN — <name>` (assert the literal `## IF-D-NN` token appears) and for each of the four field names `signature`, `invariants`, `consumed-by`, `produced-by`.
- `design-contracts-standard.md` carries the design-page parse rule — grep the leaf for the literal regex `^## (IF-D-` (the line-anchored parse rule the gate uses). Use a fixed-string grep (`grep -qF '^## (IF-D-'`) so the regex characters are matched literally.

Reference-integrity (the spec's "Shell integration tests" bullet, scoped to this leaf):

- The standard leaf's routed path resolves: assert the file referenced by the route exists at `$LEAF` (`[ -f "$LEAF" ]`).
- No installed asset body contains the literal `assets/` source-path prefix: assert the leaf body contains no `assets/` substring — `grep -q 'assets/' "$LEAF"` must return non-zero. Pair with a presence check that the leaf is non-empty so the absence assertion is meaningful (an empty/absent file trivially has no `assets/`, but the schema assertions above already fail red in that case).

## 6. Acceptance criteria

- Covers AC-14.
- All assertions use structural-marker greps, not body vocabulary.
- The leaf body assertion confirms no `assets/` source-path prefix (installed-path rule).
- Test FAILS before task-04 creates the leaf and edits the guide (red phase).

## 7. Model

Haiku

## 8. Wave

Wave 1
