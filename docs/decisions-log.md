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
