---
id: task-05
type: test
wave: 1
covers: [AC-15]
files_to_create:
  - tests/sdl-workflow/test-spec-contracts-format-leaf.sh
completion_gate: "tests compile and fail before implementation (red phase before the interface-contracts-format.md leaf and feature-spec-guide.md edit exist)"
---

# task-05 — Test the spec interface-contracts-format leaf and feature-spec-guide route

## 1. Objective

Produces `tests/sdl-workflow/test-spec-contracts-format-leaf.sh`: a TAP-style shell test that checks `feature-spec-guide.md` carries the required-section note and conditional route, and that the new `interface-contracts-format.md` leaf carries the three section shapes and the blast-radius derivation instruction.

## 2. Context

Test task for the `spec-contracts-format-leaf` slice (new-contract discipline). The paired implementation task (task-06) creates the leaf `assets/fbk-docs/fbk-sdl-workflow/interface-contracts-format.md` and edits `feature-spec-guide.md`. Neither exists yet — this test compiles and FAILS (red phase) until they do.

What the leaf and guide must contain (the properties this test checks):

- `feature-spec-guide.md` states `## Interface contracts` is a required section (a no-contracts feature writes one sentence), and routes to the format leaf *only when the author enumerates contracts, excludes one, or leaves an acceptance criterion uncovered*.
- `interface-contracts-format.md` carries the three spec-side section shapes — the headings `## Interface contracts`, `## Excluded contracts`, and `## Uncovered acceptance criteria` — and the blast-radius derivation instruction (derive the dependent set with the project's reference tooling against the modules the spec declares changed, marking each pre-existing entry with an `IF-S-NN` id).

Path-class rule: source files under `assets/`, so the test asserts against `assets/fbk-docs/fbk-sdl-workflow/...`. Any path the leaf/guide body instructs an agent to read or run must be an INSTALLED path (`.claude/fbk-docs/...`), never an `assets/` source path. The reference-integrity assertion enforces the leaf body contains no literal `assets/` prefix.

Convention to follow: `tests/sdl-workflow/test-instruction-hygiene-coverage.sh` — PROJECT_ROOT from `BASH_SOURCE`, `ok`/`not_ok` helpers, `grep -q` structural-marker assertions, `1..$TOTAL` plan, non-zero exit on failure. Use anchored/structural greps, not body vocabulary.

## 3. Instructions

1. Create `tests/sdl-workflow/test-spec-contracts-format-leaf.sh`, `chmod +x`, `set -euo pipefail`.
2. `PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"`.
3. Define:
   - `GUIDE="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md"`
   - `LEAF="$PROJECT_ROOT/assets/fbk-docs/fbk-sdl-workflow/interface-contracts-format.md"`
4. Copy the `ok`/`not_ok` TAP helpers from `test-instruction-hygiene-coverage.sh`.
5. Write the assertions in §5. Let schema assertions fail naturally (red phase) when `LEAF` is absent — do not `[ -f ]`-skip them.
6. Emit `echo "1..$TOTAL"`; `exit 1` when `FAIL > 0`.
7. Run the test and confirm it FAILS (leaf absent, guide edit not made) — red phase.

## 4. Files to create/modify

- Create: `tests/sdl-workflow/test-spec-contracts-format-leaf.sh`

Do not modify any other file. (The leaf and guide edit are made by task-06.)

## 5. Test requirements

Shell integration tests, TAP style, asserting against source files under `assets/`.

Instruction-hygiene (AC-15):

- `feature-spec-guide.md` states `## Interface contracts` is a required section — grep for the anchored heading token `## Interface contracts` paired with a required-marker term. Pair with a presence check.
- `feature-spec-guide.md` routes to the format leaf conditionally — grep the guide for a reference to `interface-contracts-format.md` and a conditional clause near it (the route fires only when the author has contracts to enumerate/exclude or an AC to leave uncovered).
- `interface-contracts-format.md` carries the three section shapes — grep the leaf for each anchored heading token: `## Interface contracts`, `## Excluded contracts`, `## Uncovered acceptance criteria`. Three separate assertions.
- `interface-contracts-format.md` carries the blast-radius derivation instruction — grep the leaf for the structural marker `blast` (or the anchored phrase the leaf uses for the derivation step) AND for the `IF-S-` token (the pre-existing entries are marked with `IF-S-NN` ids). Two assertions so the derivation step and its id-minting rule are both present.

Reference-integrity (scoped to this leaf):

- The format leaf's routed path resolves: `[ -f "$LEAF" ]`.
- No installed asset body contains the literal `assets/` source-path prefix: `grep -q 'assets/' "$LEAF"` must return non-zero.

## 6. Acceptance criteria

- Covers AC-15.
- All assertions use structural-marker greps.
- Leaf body contains no `assets/` source-path prefix (installed-path rule).
- Test FAILS before task-06 creates the leaf and edits the guide (red phase).

## 7. Model

Haiku

## 8. Wave

Wave 1
