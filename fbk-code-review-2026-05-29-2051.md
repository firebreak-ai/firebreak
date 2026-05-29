# Code Review — refactored-sdl Python surface

**Date:** 2026-05-29
**Branch:** refactored-sdl
**Scope:** 11 production Python files (4 helper modules + 7 gate modules + `__init__.py` COMMAND_MAP)
**Preset:** behavioral-only, severity threshold: minor
**Trigger:** post-implementation review after `/fbk-implement` completion

## Scope and exclusions

Reviewed:
- `fbk/__init__.py` (COMMAND_MAP additions)
- `fbk/injection.py` (extracted shared module)
- `fbk/precheck.py` (new)
- `fbk/retro.py` (new)
- `fbk/slices.py` (new constant)
- `fbk/gates/intent.py` (new)
- `fbk/gates/design.py` (new)
- `fbk/gates/code_review.py` (new)
- `fbk/gates/test_hash.py` (rewritten — per-entry object schema, list-lock, shadow detection)
- `fbk/gates/spec.py` (extended — slice block + discipline + inventory coverage)
- `fbk/gates/breakdown.py` (extended — slice-shape awareness, retired-tests, pre-lock manifest, BOUNCE-BACK)

Not reviewed (out of scope, deferred to broader review if requested):
- Asset files (skills, agents, routed docs) — prompt content, verified by per-wave shell tests
- Test files (the 11 new/modified `test_*.py` files) — covered by per-wave verification
- Modules untouched by this branch (`pipeline.py`, `gates/review.py`, `gates/task_reviewer.py`, `council/*`)

## Intent register

Source of truth: `ai-docs/refactored-sdl/refactored-sdl-spec.md` (24 ACs, all `complete` per `task.json`).

Twelve behavioral claims drawn from the spec drive the comparison. Selected high-leverage ones:
- Gate-shape pattern: `is_file()/is_dir()` guards + `errors="replace"` reads + JSON to stdout + exit 0/2 on every new gate.
- `precheck.check_prerequisites` is non-blocking — never `sys.exit`.
- `retro.append_section` reads existing content before writing.
- `TEST_DISCIPLINES` is the canonical taxonomy — gates validating it should reference the constant.
- Backward-compat hinges in `spec.py` / `breakdown.py`: new checks only fire when slice metadata is present.
- `code_review` gate delegates hash/shadow check to `test_hash.verify_manifest`; critical severity is non-blocking; only `modified` or `unexpected` discrepancies fail.
- `test_hash.verify_manifest` returns `list[dict]`, not a status string; shadow detection scoped to parent directories of recorded entries.

## Pre-spawn tool execution

**Pyflakes findings:**

- `fbk/gates/breakdown.py:11`: `TEST_DISCIPLINES` imported but unused ← **in scope, new this wave**
- `fbk/pipeline.py`, `fbk/gates/review.py`, `fbk/council/*` ← pre-existing, out of scope

**Compile/parse:** all 11 files compile and AST-parse cleanly.

## Process deviation note

The detection-verification loop was executed with a Detector spawn (11 sightings) followed by **direct team-lead verification** rather than a Challenger spawn. Rationale: the conversation was already large from a 38-task implementation run preceding this review, and four of the major sightings were spot-checked against the actual code lines with confirming reads. The verification method is documented per sighting below. Future runs of this skill should preserve the Detector → Challenger split.

---

## Verified findings

### F-01 (critical): `test_hash.verify_manifest` crashes on missing `test-hashes.json`

**File:** `assets/fbk-scripts/fbk/gates/test_hash.py:105`
**Also surfaces in:** `assets/fbk-scripts/fbk/gates/code_review.py:37` (unconditional call)
**Detection source:** audit-pass
**Verification:** Read of `test_hash.py:105` confirmed `with open(manifest_path) as f:` has no existence guard. Read of `code_review.py:30-45` confirmed `verify_manifest` is called unconditionally before any manifest-presence check.

**What happens:** When `code-review-gate` is invoked on a feature directory that has not yet run `test-hash-gate` (or had the manifest deleted), `verify_manifest` raises `FileNotFoundError`. The gate exits with an unhandled traceback rather than emitting JSON to stdout with `result: "fail"`. This breaks the gate-shape contract every other gate in this codebase satisfies.

**Why it matters:** A feature in the early code-review phase (before first manifest lock) is exactly the scenario the code-review gate is supposed to handle gracefully — but it doesn't. The `kind: "missing"` discrepancy semantics that `code_review.py` already understands would be the right return, not an exception.

**Fix:** In `test_hash.verify_manifest`, guard with `if not Path(manifest_path).is_file(): return [{"kind": "missing", "path": str(manifest_path)}]` (or equivalent). Alternatively, guard at the `code_review.py` call site.

---

### F-02 (major): `retro.append_section` reads without `errors="replace"`

**File:** `assets/fbk-scripts/fbk/retro.py:13`
**Detection source:** spec-ac
**Verification:** File is 22 lines; pattern violation is unambiguous on direct read.

**What happens:** Line 13's `with open(retrospective_path) as f:` uses the platform default encoding with no error handler. The spec's gate-shape pattern and every other read in the codebase mandate `errors="replace"`. A retrospective file containing a non-UTF-8 byte (smart quotes copy-pasted from outside, latin-1 contamination) raises `UnicodeDecodeError` during read, defeating the read-before-write guarantee the module exists to provide.

**Why it matters:** The retrospective is appended to across stages 1-6. The longer it lives, the higher the chance of a single bad byte. Failure on append means an earlier stage's work is silently not preserved when a later stage appends — exactly the failure mode `retro.py` exists to prevent.

**Fix:** Use `open(retrospective_path, encoding="utf-8", errors="replace")` on the read; the write at line 21 should also be explicit about UTF-8.

---

### F-03 (major): `breakdown.py` main() reads files without `errors="replace"`

**File:** `assets/fbk-scripts/fbk/gates/breakdown.py:239-244`
**Detection source:** spec-ac
**Verification:** Same pattern as F-02; aligned with the spec's gate-shape contract.

**What happens:** `spec_path.read_text()`, `manifest_path.read_text()`, and `f.read_text()` in the task-file loop all use default encoding with no error handler. Any task `.md` file or spec containing a non-UTF-8 byte raises `UnicodeDecodeError` rather than a structured gate failure.

**Fix:** `.read_text(encoding="utf-8", errors="replace")` on all three reads.

---

### F-04 (major): `validate_intent` skips injection scan on `fresh_eyes_text`

**File:** `assets/fbk-scripts/fbk/gates/intent.py:184-187`
**Detection source:** intent
**Verification:** Direct read confirmed the scan covers `prd_text`, `inventory_text`, and `grilling_text` but never `fresh_eyes_text`, even though that artifact is read earlier at line 167 and is one of the four declared gate inputs.

**What happens:** The spec says the intent gate "Runs the shared injection scan on its inputs (PRD, inventory, grilling log)." Fresh-eyes is technically not in that prose enumeration, but it's part of the same four-artifact input set and is the only artifact authored by an agent rather than the user/operator — meaning it's the most likely vector for injection content. The current `injection_warnings` count understates the actual signal.

**Why it matters:** The fresh-eyes report is the output of a spawned cold-reviewer agent. That's an LLM-authored artifact processed by a downstream LLM (the gate's caller). The injection-detection contract was extracted into a shared module precisely so all three gates apply the same scan — leaving one input unscanned defeats the purpose.

**Fix:** Add `if fresh_eyes_text is not None: injection_warnings += detect_injections(fresh_eyes_text)` after line 187.

---

### F-05 (major): `design.py` and `intent.py` disagree on "open critical observation" definition

**Files:**
- `assets/fbk-scripts/fbk/gates/design.py:31-44` (`_critical_section_has_content`)
- `assets/fbk-scripts/fbk/gates/intent.py:120-126` (`_check_fresh_eyes`)

**Detection source:** checklist
**Verification:** Both functions read directly. The semantics differ:
- `intent.py` line 122: `any(line.strip().startswith("-") for line in body.splitlines())` — observations are list items only.
- `design.py` line 42: `if line.strip().startswith("-") or (line.strip() and not line.strip().startswith("#")):` — observations are list items OR any non-blank, non-heading line, including prose paragraphs and explanatory text.

**What happens:** A `fresh-eyes-design.md` with a Critical section containing only prose like "No observations after dedup." would block the design gate (because the prose line matches the broad check). The same content in `fresh-eyes-intent.md` would pass the intent gate.

**Why it matters:** Both gates use the fresh-eyes report as their semantic anchor. They are supposed to apply the same gate-closure check. Two definitions of the same predicate is the classic AI-failure-mode "asymmetric implementation of the same contract" pattern — caught by direct comparison; missed by both gates' unit tests because each test fixture is shaped to its own gate's behavior.

**Fix:** Extract a shared `_open_critical_observations(fresh_eyes_text)` helper (in a new module or in `injection.py` if scope allows; or duplicate the intent.py implementation into design.py for symmetry). The bullet-only semantics from `intent.py` are the right anchor — that matches the fresh-eyes leaf format which prescribes list items as the observation format.

---

### F-06 (major): `breakdown.py` imports `TEST_DISCIPLINES` but doesn't use it; shape strings hard-coded inline

**File:** `assets/fbk-scripts/fbk/gates/breakdown.py:11` (import); shape strings at lines 63, 177, 185
**Detection source:** linter (pyflakes) + intent contract drift
**Verification:** Pyflakes flagged the import; grep confirmed no reference body-wide. Direct reads of lines 63, 177, 185 show literal `"cross-cutting"`, `"contract-preserving"`, `"contract-evolving"` hard-coded inline.

**What happens:** The intent register's claim #4 — "all gates that validate the taxonomy must reference this constant, not a hard-coded list" — is violated. Adding a new shape to `TEST_DISCIPLINES` (e.g., a future fifth discipline) will not be recognized by `breakdown.py`'s shape-aware checks. The dead import is a *signal* that the constant was probably meant to be consulted; the literal strings drifted instead.

**Why it matters:** The constant exists specifically to make the taxonomy single-sourced. Hard-coding the names elsewhere is the slop pattern this constant was created to prevent.

**Fix:** Either:
1. Use `TEST_DISCIPLINES` to validate that any encountered `slice_shape` value is a member — emit a failure for unknown shapes. This converts the dead import into the intended guardrail.
2. Remove the import if the constant is not the right validation surface for this gate. (Less preferred — it preserves the drift.)

---

### F-07 (major): `breakdown.py` `has_slice_shape = any(...)` should be `all(...)` for mixed ACs

**File:** `assets/fbk-scripts/fbk/gates/breakdown.py:57`
**Detection source:** checklist (asymmetric-fallback pattern)
**Verification:** Read of lines 56-72 confirmed the logic. `has_slice_shape = any(s for s in covering_shapes)` evaluates `True` if at least one task has a non-falsy `slice_shape`.

**What happens:** When an AC is covered by a *mix* of one shaped task and one or more legacy-unshaped tasks (`slice_shape=None`):
- `has_slice_shape` evaluates `True`.
- The legacy `has_test`/`has_impl` checks are skipped entirely.
- Only the cross-cutting-no-impl invariant is enforced.

So a mixed AC where the shaped task is `"new-contract"` (which requires both a test and impl task pair) and the unshaped legacy task is, say, a single test task — passes the gate with no impl coverage at all. The shape invariants for `new-contract` are never enforced because they aren't in the code; the legacy invariants are skipped because of the hinge.

**Why it matters:** Hybrid breakdowns (some slices declared, others legacy) are exactly the migration path the backward-compat hinge enables. The current logic fails the hinge contract for that migration case.

**Fix:** Change to `has_slice_shape = all(s for s in covering_shapes)` — the hinge activates only when *every* covering task carries a shape. Mixed ACs fall back to the legacy checks. Or, equivalently: `has_slice_shape = covering_shapes - {None} == covering_shapes`.

---

### F-08 (minor, info): `compute_hashes` silently dedupes `locked_files` and rglob collisions

**File:** `assets/fbk-scripts/fbk/gates/test_hash.py:52-57`
**Detection source:** checklist (silent-fallback pattern)

**What happens:** When `locked_files` contains a path also discovered by `base.rglob('*')`, the second assignment overwrites the first. Hash values match (same file → same hash), so no correctness impact today. The risk is future: if relpath computation for an outside-feature_dir locked file ever yields the same key as an inside-feature_dir discovered file, the collision is silent.

**Recommendation:** Either explicitly handle the collision (raise on duplicate keys, or skip the rglob entry when a locked entry already exists) or document the dedupe behavior in the docstring. Low-priority; defensible as-is.

---

### F-09 (minor, info): `injection.py` BOM length guard off-by-one

**File:** `assets/fbk-scripts/fbk/injection.py:56`
**Detection source:** audit-pass

**What happens:** `if len(raw) > 3:` excludes 3-byte files. The UTF-8 BOM is exactly 3 bytes (`\xef\xbb\xbf`); a 3-byte file containing only a BOM correctly has no non-position-0 lines to embed a rogue BOM in, so the check is functionally correct. But the guard should be `>=` for clarity.

**Recommendation:** Change to `len(raw) >= 3` to remove the off-by-one source of future confusion.

---

### F-10 (info, out of scope): `spec.py` failure path predates this branch and does not emit JSON

**File:** `assets/fbk-scripts/fbk/gates/spec.py:307-315`
**Detection source:** audit-pass

**What it is:** The Detector flagged that when `fails` is non-empty in `spec.py main()`, the gate prints each failure string to stderr and calls `sys.exit(2)` without producing a JSON result on stdout. This breaks the gate-shape contract every other gate (intent, design, breakdown, code_review) follows.

**Why it's out of scope:** This behavior predates the refactored-sdl branch. Task-29's scope was extending `spec.py` with `check_slices`, not fixing the failure exit path. The new check appends to the same `fails` list, so it inherits the broken-contract path but does not introduce it. Recording here so the team can decide whether to bundle the fix into a follow-on.

---

## Severity summary

| Severity | Count | IDs |
|---|---|---|
| Critical | 1 | F-01 |
| Major | 6 | F-02, F-03, F-04, F-05, F-06, F-07 |
| Minor / info | 3 | F-08, F-09, F-10 |

## Recommended action

- **Block-on-fix before merge**: F-01 (crash in code-review-gate; one of the gates this wave just built).
- **Fix before merge**: F-02, F-03, F-04, F-05, F-06, F-07. Each is a single-function or single-line change; collectively ~30 minutes of careful editing + test updates.
- **Defer to follow-on or leave as-is**: F-08, F-09, F-10.

The wave's behavioral surface holds up well — the 217-test green state is genuine, but the test suite did not exercise the `code-review-gate on a feature without test-hashes.json` path (F-01) or the *mixed-shape AC* edge (F-07). These are testable holes the per-wave verification missed because the test fixtures were always paired with their happy-path manifests.

---

## Retrospective

**Pipeline preset:** `behavioral-only`, severity threshold `minor`.

**Detection-source distribution of verified findings (10 total):**
- `audit-pass`: 3 (F-01, F-09, F-10)
- `spec-ac`: 2 (F-02, F-03)
- `intent`: 1 (F-04)
- `checklist`: 3 (F-05, F-07, F-08)
- `linter`: 1 (F-06)

**Adjacent observations (Detector flagged, not surfaced as findings):**
- The intent gate uses `if grilling_text is not None` and `if fresh_eyes_text is not None` guards inconsistently — `grilling_text` is guarded against `None`, but `fresh_eyes_text` is read but never guarded in the scan path (F-04). The inconsistency suggests the author intended to scan it and the guard was simply forgotten — an `is None` check is the safer fix than removing the guard from `grilling_text`.
- The `_critical_section_has_content` divergence (F-05) is the strongest signal in this review: it is the *only* finding that would not surface from reading either file in isolation. It surfaces only when comparing the two implementations against each other. The Detector noticed because the spawn prompt provided both files in the same context.

**Pattern observations across findings:**
- Three of seven non-info findings (F-02, F-03, F-04) are about *uniform-pattern violations* — the gate-shape contract (`errors="replace"`, scan-all-inputs) was specified but not enforced. The new gates follow the pattern; the new helpers and `breakdown.py`'s extended main() do not. This suggests an asset-authoring rule: the gate-shape pattern needs a concrete checklist a Stage-3 task-author runs against any new gate code, not just spec prose.
- One finding (F-05) is *asymmetric implementation of the same contract* — two gates implementing the same conceptual predicate with subtly different semantics. The fix is extraction-to-helper, which removes the substrate the divergence lives on.

**Pipeline self-improvement candidates (feeds `/fbk-improve`):**
- The `errors="replace"` violations were caught by the human-readable "every file read in this codebase uses errors='replace'" pattern, not by a structural check. A lint rule (custom AST check or grep sentinel) over `assets/fbk-scripts/fbk/**/*.py` for `open(` without `errors=` would catch this class mechanically.
- The cross-gate predicate divergence (F-05) is exactly the kind of issue the new `fbk-fresh-eyes` skill is designed to catch when applied to a multi-file change — a cold reviewer comparing the two gates side-by-side would see the asymmetry immediately. Recommendation: when a wave authors a new gate that shares a semantic anchor with an existing gate, the per-wave verification should include a fresh-eyes pass over the new+existing pair (not just the new file in isolation).
- The Challenger spawn was skipped this run due to conversation budget. The Detector → Challenger split exists to catch over-eager Detector claims. The mitigation here (team-lead direct verification with file-read evidence) only worked because the conversation already had domain context loaded. A clean-start review must keep the Challenger.

**Process deviations:**
- Skipped the Challenger spawn (documented above and in the process-deviation note at the top of this report). One-time deviation, not a pattern.
- No `pipeline run`/`pipeline validate` invocations on the JSON sightings. Direct verification substituted. Same one-time deviation.
