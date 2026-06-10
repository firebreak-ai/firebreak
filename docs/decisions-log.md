# Decisions Log

Append-only, chronological record of constraining decisions made during Firebreak's design and development. A new entry supersedes rather than rewriting an old one — old entries are never edited.

Each entry records: what was decided, the alternative considered, the rationale, and what the decision constrains going forward.

---

## 2026-05-29 — fbk-architect is author-only this cycle

**Status**: accepted
**Author**: fbk-architect

**Decided**: `fbk-architect` is built as an author-only skill this cycle. The earlier framing that it should be a "superset the council architect collapses into" is dropped from the build requirement.

**Alternative considered**: Build fbk-architect as a superset persona that the council-architect role converges toward over time, embedding the collapse logic now.

**Rationale**: The council migration is out of scope for this cycle, and the superset relationship cannot be validated until the migration actually happens. Building for an unvalidatable future constraint is speculative scope.

**Constrains**: The future council-architect collapse remains a live design question. When the migration occurs, a decisions-log entry should record how fbk-architect's scope was updated. Until then, fbk-architect has no special relationship to the council pattern in code.

---

## 2026-05-29 — Code-review gate lands in a new code_review.py module

**Status**: accepted
**Author**: fbk-architect

**Decided**: The code-review gate is implemented as a new `code_review.py` module rather than being folded into the existing `review.py`.

**Alternative considered**: Extend `review.py` (which gates the spec-review phase) to also handle code-review gate logic, sharing the module across both gates.

**Rationale**: `review.py` gates a different phase and is called by the spec-review and breakdown flows. Folding code-review gate logic into it would couple two distinct gates into one module, entangle callers, and require changes to `review-gate`/`validate_review` paths that are tested and stable. The new module calls `test_hash.verify_manifest` for its hash check rather than duplicating a second hash path.

**Constrains**: `review.py`, `review-gate`, and `validate_review` remain untouched. Code-review gate callers import from `code_review.py`. If the two gate modules share enough logic in the future, extraction to a shared util is the right path — not a merge back into `review.py`.

---

## 2026-05-29 — Python runtime must not depend on system-wide packages

**Status**: accepted (documenting an existing constraint that was not previously written down)
**Author**: rahvin / operator constraint

**Decided**: Firebreak's Python runtime — installer, dispatcher (`fbk.py`), gate modules, shell tests — must not depend on system-wide Python packages. The dependency management and execution path is `uv`.

**Alternative considered**: Continue using `python3` directly with `pip install --user pyyaml` (the current pattern across the installer and all 60+ shell tests). This pattern is silently broken on systems that enforce PEP 668 (externally-managed-environment), which includes recent Arch, Debian/Ubuntu, and Homebrew-installed Python on macOS. On such systems, `pip install --user` fails and `python3 -c "import yaml"` returns ImportError unless the user has manually set up a venv outside Firebreak's awareness.

**Rationale**: Firebreak is most often installed globally (operator workflow) and should run reliably across systems regardless of how the system Python is locked down. `uv` handles project-local virtualenv creation, Python version pinning (already declared in `pyproject.toml`'s `requires-python = ">=3.11"`), and dependency resolution without touching system packages. The "easy option" — `uv run` at every Python invocation point — is also the correct one.

**Constrains**:
- The installer must bootstrap `uv` (or assume it's present and fail clearly if absent) rather than `pip install`-ing pyyaml.
- The shell-test pattern `python3 "$DISPATCHER"` must become `uv run python3 "$DISPATCHER"` (or the dispatcher must be invoked via a wrapper that itself calls `uv run`).
- Skill body invocations that read `python3 "$HOME"/.claude/fbk-scripts/fbk.py <gate>` must migrate to `uv run python3 ...` or to a wrapper command.
- The dispatcher's shebang should be reviewed for consistency.

This migration is out of scope for the refactored-sdl branch, which inherited the existing `python3`-direct pattern and would have produced an inconsistent codebase if it had unilaterally migrated only its own surface. The migration warrants its own feature spec.

**Tracked follow-up**: A future feature spec (`uv-runtime-migration` or equivalent) covers the installer rewrite, the shell-test pattern migration, the skill body invocation updates, and the dispatcher shebang. The refactored-sdl `/fbk-improve` proposals at `ai-docs/refactored-sdl/fbk-improve-proposals-2026-05-29.md` should be applied either before or after that migration without conflict.

---

## 2026-06-09 — Blast-radius set is derived by the spec-authoring agent using reference tooling

**Status**: accepted
**Author**: fbk-architect (operator-confirmed)

**Decided**: The spec-authoring agent computes the blast-radius set for `## Interface contracts` deterministically by running the project's reference-finding tooling ("find all callers" / "find all importers") against each module the spec's module-touch policy declares as changed. The resulting dependent set is the blast-radius set; each dependent's pre-existing interface contract becomes an `IF-S-NN` entry with `design-ref: pre-existing`. This is a mechanical derivation step, not a judgment call. The spec gate verifies only that blast-radius entries are present and well-formed — it does not recompute or check completeness of the caller set. Per-language completeness verification is a deferred follow-on.

**Alternative considered**: Author judgment — the spec author lists touched modules by inspection without running reference tooling.

**Rationale**: Author judgment introduced the risk of systematic under-listing (modules the author did not think to check), which the gate cannot detect and spec review can only partially catch — the exact silent-gap failure this feature exists to close. Reference tooling is available in every target project environment where a spec is authored, and the derivation is mechanical enough that the agent can execute it reliably. Keeping the gate responsibility shape-only (not completeness) avoids requiring per-language static analysis in a gate that is language-blind and runs across arbitrary target projects.

**Constrains**: The `feature-spec-guide.md` instruction for the spec-authoring agent must direct it to use reference tooling for blast-radius derivation. The spec gate enforces only field-completeness and identifier-form on blast-radius entries, not whether the set is complete. Per-language completeness checking is deferred to a follow-on feature.

---

## 2026-06-09 — Contract identifiers use separate namespaces: IF-D-NN for design, IF-S-NN for spec

**Status**: accepted
**Author**: fbk-architect (operator-confirmed)

**Decided**: The `IF` identifier space is split into two prefixed namespaces: `IF-D-NN` for design-originated contracts (minted in `design/contracts.md` during the design phase) and `IF-S-NN` for spec-originated contracts (minted by the spec author for pre-existing blast-radius entries and spec-discovered new contracts). When the spec carries a design contract forward, it copies the `IF-D-NN` identifier verbatim — inheritance, not re-minting. Collision between the two namespaces is structurally impossible.

**Alternative considered**: A single shared `IF-NN` sequence with operator-resolves as the collision response when design is re-edited after the spec has minted entries.

**Rationale**: Operator-resolves leaves an undetected collision possible — a hollow carry (same id, wrong content) that spec review may miss if it is not run. Separate namespaces make the collision impossible at the source, communicate different semantics visually (`IF-D` came from design, `IF-S` added at spec), and let downstream agents apply different handling rules by prefix alone. The added cost is two identifier patterns instead of one; the regex `^IF-[DS]-[0-9]{2,}$` handles both at the gate.

**Constrains**: Design pages use `## IF-D-NN — <name>` headings exclusively. Spec entries carrying design contracts use `IF-D-NN` verbatim; spec entries for blast-radius and spec-discovered contracts use `IF-S-NN`. The spec gate's id-format check validates both prefixes; the design-anchor walk extracts only `IF-D-NN` from `design/contracts.md`. Any future change to the prefix scheme is a contract-evolving change requiring a retired-tests entry and a gate-regex update.

---

## 2026-06-09 — Contract gate checks land in a new contracts.py module

**Status**: accepted
**Author**: fbk-architect (operator-confirmed)

**Decided**: The four new spec-gate check functions (structural completeness, design-anchor walk, AC-coverage, seam-coverage) are implemented in a new `fbk/gates/contracts.py` module, imported by `spec.py`.

**Alternative considered**: Extend `spec.py` directly with the four new functions.

**Rationale**: Consistent with the 2026-05-29 decision that placed the code-review gate in its own module rather than extending `review.py`. The new checks read a file outside the spec (the design contracts page), enforce a distinct invariant set, and will be tested in isolation. Folding them into `spec.py` would couple distinct concerns and make the module harder to test. The `fbk.injection` and `fbk.slices` helper-module pattern in the existing gate establishes the import-from-helper precedent.

**Constrains**: `spec.py` imports from `fbk.gates.contracts` at module top level. `ImportError` from this import fails the gate at startup — callers must ensure the module is installed. Any renaming of the module is a contract-evolving change requiring caller updates.

---

## 2026-06-09 — design/contracts.md parsed via level-two IF-D-NN headings

**Status**: accepted
**Author**: fbk-architect (operator-confirmed)

**Decided**: Identifiers in `design/contracts.md` are extracted using `re.findall(r"^## (IF-D-[0-9]{2,})", design_text, re.MULTILINE)`. Each level-two heading of the form `## IF-D-NN` or `## IF-D-NN — <name>` constitutes one contract entry.

**Alternative considered**: Fenced blocks per entry; flat field lines with no headings.

**Rationale**: Heading-level anchors are already how `spec.py` navigates all sections (`heading_line`, `section_body`). The `^##` anchoring prevents prose mentions of identifiers from being counted. The design page stays readable in any markdown renderer. Fenced blocks would require a new parser and look like code rather than design documentation.

**Constrains**: Design-page authors must use the `## IF-D-NN` heading form for each contract entry — any entry not starting with a level-two heading matching that pattern is not counted. Identifier mentions in prose (e.g., "see IF-D-01") do not constitute an entry.

---

## 2026-06-09 — Seam-coverage matching uses a case-insensitive substring scan

**Status**: accepted
**Author**: fbk-architect (operator-confirmed)

**Decided**: The seam-coverage check matches component names from integration-seam declarations against the full body of `## Interface contracts` using a case-insensitive substring scan. No dedicated `components:` field is added to the contract entry schema.

**Alternative considered**: Require a `components:` field per contract entry and exact-match against it; or exact string match against current contract fields.

**Rationale**: The PRD explicitly labels this a mechanical approximation. A substring scan is implementable on the existing section-body parse surface without schema changes. A `components:` field would add authoring cost to a heuristic before any feature has used the schema. The check's error message states the heuristic nature; the operator remains the final judge.

**Constrains**: The `components:` field remains available as a future refinement if the heuristic produces too many false passes. Adding a required `components:` field to the contract entry schema would be a contract-evolving change requiring a retired-tests entry.

---

## 2026-06-09 — Contract-drift elevation extends the architecture reviewer's brief

**Status**: accepted
**Author**: fbk-architect (operator-confirmed)

**Decided**: Spec review's contract-drift elevation is implemented by adding drift-detection instructions to the architecture reviewer's brief in `review-perspectives.md`, not by adding a required checklist entry to the review gate.

**Alternative considered**: A new required checklist entry in the review gate's structural prerequisites (would require a gate code change in `review.py`).

**Rationale**: Contract drift is a semantic concern — whether the spec's carried contracts match the design's intent — and semantic checks belong in the agent review layer, not the deterministic gate. The 2026-05-29 decision established that `review.py` is not modified for gate concerns outside its original scope. Extending the reviewer's brief requires only a text change, keeps the review gate's prerequisites deterministic, and the architecture reviewer is almost always engaged for features with contracts.

**Constrains**: The drift check runs only when the architecture reviewer is engaged. If a future feature bypasses that reviewer while having a `design/contracts.md`, drift detection will not run; adding "feature has design/contracts.md" as an engagement signal for the architecture reviewer is the natural follow-on.
