# Installer hygiene — separate task (found 2026-06-10)

Surfaced while fixing four pre-existing test failures on `fbk/interface-contracts`. Three were fixed; this is the fourth, reclassified as its own task because it is a real installer problem unrelated to interface-contracts and larger than a test tweak.

## How it surfaced

`tests/installer/test-refactored-sdl-install.sh` was **passing vacuously** at baseline: it ran `HOME=X bash install.sh` with no `--source`, so the installer attempted a GitHub download and an interactive "global or project?" prompt, got no valid input, and exited — installing nothing. Its two end-state checks (no `assets/` path leak in installed files; `fbk-scripts` gone after uninstall) then passed because there was nothing installed to violate them.

Fixing the invocation to actually install (`--source "$PROJECT_ROOT/assets" --target "$MOCK_HOME/.claude"`) took it from 2/16 to 14/16 and exposed real problems (below). That invocation fix was reverted to keep the delivered change set clean; re-apply it when this task is taken up.

## Root findings

1. **The source `assets/fbk-scripts/` is contaminated with untracked dev artifacts.** `git status --ignored` shows: `.claude/`, `.pytest_cache/`, `.ruff_cache/`, `.venv/`, `venv/`, several `fbk/**/__pycache__/`, and `fbk_scripts.egg-info/`. All are local build/dev cruft.

2. **The installer's exclusion list is incomplete.** `install.sh` prunes `.venv`, `venv` (added during this pass), `__pycache__`, `.pytest_cache`, `*.pyc`, `.DS_Store` — but NOT `.ruff_cache`, `fbk_scripts.egg-info`, or `.claude`. So it copies those into the target. The editable-install finder under `venv/` was the first `assets/`-path leak (fixed by the `venv` exclusion); the next leak is a code comment in the shipped `tests/test_dispatcher.py`.

3. **The installer ships the `tests/` tree.** The fbk-scripts unit tests are dev-only; they have no role in an installed runtime and carry `assets/`-path references in comments. Decide whether to ship `tests/` at all.

4. **Uninstall leaves orphans / manifest is suspect.** After a real install + `--uninstall`, tracked files (e.g. `fbk/retro.py`) and `pyproject.toml`/`uv.lock` remained, so `fbk-scripts` was not removed. A separate oddity: an install reporting "142 files installed" wrote no locatable `.firebreak-manifest.json` under the target in one reproduction. The manifest-write and manifest-driven uninstall completeness need root-causing.

## Suggested fix shape (when taken up)

- Expand the installer's prune set to all dev/build artifacts (`.ruff_cache`, `*.egg-info`, `.claude`, `.git`, plus the existing ones); prefer detecting virtualenvs by `pyvenv.cfg` rather than by name.
- Decide and implement whether `tests/` ships; if not, exclude it.
- Root-cause the manifest write path and the uninstall leftover; make uninstall remove everything the install created (manifest files + the generated `.venv`).
- Re-apply the `test-refactored-sdl-install.sh` invocation fix and confirm 16/16.
- Optionally clean the untracked cruft from the working tree (it is gitignored, so it is a local-only concern, but it is what makes the live installer ship junk from this checkout).

## Already done in the related pass (kept)

- `install.sh`: `--uninstall` now removes the generated `fbk-scripts/.venv` (fixed the real bug behind `test-upgrade-uninstall.sh`).
- `install.sh`: prune `venv` as well as `.venv`; regression-covered by `test-install.sh` Test 12.
