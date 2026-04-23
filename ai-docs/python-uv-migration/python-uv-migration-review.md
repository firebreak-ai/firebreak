Perspectives: Architecture, Pragmatism, Quality

# python-uv-migration — Spec Review (Re-review)

This is a re-review after resolution of 10 blocking findings from the initial review. All three council agents (Architect, Builder, Guardian) verified all prior fixes and assessed the revised spec.

## Architectural Soundness

All prior architectural blockers resolved:

- **fbk-presets.json** relocated into `fbk/data/fbk-presets.json` with updated path resolution. Source layout, shared module consolidation, and files-removed list are internally consistent.
- **Cross-platform locking** abstraction provides conditional `fcntl`/`msvcrt` imports scoped to `session_manager`. Adequate for the session locking use case.
- **Dispatcher specification** now covers `realpath` resolution, `sys.path[1]` insertion, stdin passthrough, argv convention, and Python version check. Each addresses a concrete failure mode.
- **src/ layout** correctly dropped — `fbk/` is a direct sibling of `fbk.py`.

### N-01 [important] — `test-preset-config.sh` missing from impacted tests (FIXED)

`tests/sdl-workflow/test-preset-config.sh` hardcodes `PRESETS="$PROJECT_ROOT/assets/config/fbk-presets.json"`. After migration, the file moves to `fbk-scripts/fbk/data/fbk-presets.json`. Added to the spec's existing tests impacted section.

### N-02 [informational] — `msvcrt.locking` size parameter semantics

`msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)` locks 1 byte vs `fcntl.flock` which locks the entire file. For the session-manager use case (small JSON file, advisory mutex), this is functionally sufficient. Consider using a larger constant if the file grows beyond expectations. Low risk — address during implementation if needed.

## Over-engineering / Pragmatism

All prior pragmatism concerns resolved:

- **Script classification** now has 3 accurate categories. Builder verified against actual scripts — classifications match real conversion effort.
- **Testing strategy** is proportionate: 28 new test entries for a migration touching 15 source files, 38+ references, and 24 existing tests. UV-4 (full pipeline) correctly marked manual-only.
- **Dispatcher specification** is justified — each detail addresses a concrete failure mode, not speculative concerns.
- **pyproject.toml** correctly scoped to metadata and dev dependencies only. No `[build-system]` section.

No new pragmatism concerns — all informational. Builder assessment: "Spec is ready for implementation."

## Testing Strategy and Impact

All prior testing gaps resolved:

- **AC traceability**: All 10 ACs (AC-01 through AC-10) have at least one test entry.
- **UV step mapping**: UV-1 through UV-3 and UV-5 have test entries. UV-4 marked manual with rationale.
- **Existing test enumeration**: 24 impacted tests verified complete (14 direct invocation + 5 reference checks + 4 installer + 1 preset config), plus 1 fixture and 2 benchmark tests marked as not directly impacted.
- **Pipeline test scope**: 60+ `uv run` invocation pattern changes across 7 tests explicitly described.
- **Installer test redesign**: Specific mock structure and assertion changes itemized.
- **Council SKILL.md integration test**: Added, covering the 22-reference seam.

Guardian verified all AC and UV coverage against the spec. No gaps remain.

### Test strategy section

**New tests needed**: 28 entries covering all 14 modules at unit level, dispatcher at integration level, and behavioral parity at e2e level. All ACs and UV steps traceable.

**Existing tests impacted**: 24 test files + 1 fixture + 2 benchmark tests (awareness only). Enumeration verified complete via grep across test directory.

**Test infrastructure changes**: pytest dev dependency, test fixtures, and 24 existing test updates (7 pipeline tests require invocation pattern changes across 60+ lines).

## Threat Model Determination

**Decision**: No. **Rationale**: No new trust boundaries, no data handling changes, no auth/access control changes, no external API interaction. Injection detection logic ported from bash to Python without behavioral change.

## Summary

| Severity | Count | IDs |
|---|---|---|
| Blocking | 0 | — |
| Important | 0 | N-01 already fixed in spec |
| Informational | 1 | N-02 |

All 10 prior blocking findings verified resolved. 1 new important finding (N-01) fixed during re-review. Spec is structurally complete and ready for breakdown.
