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
