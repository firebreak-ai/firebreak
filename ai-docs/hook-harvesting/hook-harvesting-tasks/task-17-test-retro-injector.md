---
id: task-17
type: test
wave: 4
covers: [AC-18, AC-11]
files_to_create:
  - assets/fbk-scripts/tests/test_capture_retro_injector.py
completion_gate: "tests compile and fail before implementation"
---

# Objective

Write the tests for the per-stage retrospective injector: it appends a provenance-marked metrics block under a `## <STAGE> — metrics` heading distinct from the agent's plain `## <STAGE>` heading without disturbing existing prose; a reworked stage produces a second marked block; and an injector exception is swallowed.

# Context

After a working stage completes, the injector writes a metrics block for that stage into `ai-docs/<spec>/<spec>-retrospective.md`, resolved internally from `os.getcwd()` and the spec name (no path parameter). It appends via the existing `retro.append_section`, under the heading `<STAGE> — metrics` — distinct from the plain `<STAGE>` heading the retrospective skill uses for prose — so the machine block and the agent's prose coexist in one file, neither overwriting the other. Each block opens with a provenance marker of exactly the form `<!-- fbk-metrics stage=<STAGE> spec=<SPEC> generated=<ISO-8601> -->` (no trailing space); a test matches it by STRUCTURE (fixed prefix + field shape, with `generated=` as a free field), never by exact string with a fixed timestamp. A reworked stage that completes again produces a SECOND marked block, distinguished by its provenance timestamp. Every exception inside the injector is caught, so a failed injection never blocks anything.

The predicate that decides when injection fires lives in `transition_state` (covered as a state-engine integration in the Wave-4 state task); THIS task covers the injector function itself and its block-writing behavior. The injector resolves the retrospective path from `os.getcwd()`, so drive it with the subprocess/working-directory set to a `tmp_path` project, or — if the injector exposes a path override for testing — use that. The existing `fbk/retro.py append_section` writes `## <stage_name>\n\n<content>\n`. Use `from fbk.capture import retro_injector` inside `try/except ImportError` with a module-level skipif.

Signature to call verbatim: `retro_injector.inject_stage_metrics(spec, completed_stage) -> None`.

# Instructions

1. Create `tests/test_capture_retro_injector.py`; import `retro_injector` inside `try/except ImportError`; module-level skipif.
2. Because the injector resolves the retrospective path from `os.getcwd()`, set the working directory to a `tmp_path` project for each test — use `monkeypatch.chdir(tmp_path)` so `os.getcwd()` resolves there and the file lands at `<tmp_path>/ai-docs/<spec>/<spec>-retrospective.md`. The injector reads the spec's events and state to build the block; lay these down at their pinned locations under the project: events at `.fbk-capture/events.jsonl` relative to the cwd, and state at `<state_dir>/<spec>.json` where `state_dir = os.environ.get("STATE_DIR", ".claude/automation/state")` — so either write the state under `.claude/automation/state/<spec>.json` or `monkeypatch.setenv("STATE_DIR", ...)` and write it there. Build both with `capture_fixtures` so `stage_summary` has data.
3. `test_injects_block_under_metrics_heading`: `monkeypatch.chdir` to the project; call `inject_stage_metrics("demo-spec", "IMPLEMENTING")`; read `ai-docs/demo-spec/demo-spec-retrospective.md`; assert it contains the heading `## IMPLEMENTING — metrics` AND a line matching the provenance-marker structure for that stage/spec. Match the marker by structure: assert a line that starts with `<!-- fbk-metrics stage=IMPLEMENTING spec=demo-spec generated=` and ends with ` -->`, with a non-empty `generated=` value between — NOT an exact-string-with-fixed-timestamp.
4. `test_does_not_disturb_existing_prose_section`: pre-create the retrospective with a plain `## IMPLEMENTING` prose section (agent prose) via `retro.append_section` or a direct write; call `inject_stage_metrics(...)`; assert the original `## IMPLEMENTING` prose section is still present and byte-intact, and the new `## IMPLEMENTING — metrics` section was added after it (the two coexist).
5. `test_rework_produces_two_marked_blocks`: call `inject_stage_metrics("demo-spec", "IMPLEMENTING")` twice (simulating a stage completing, being reworked, and completing again); assert the file contains exactly TWO `## IMPLEMENTING — metrics` blocks, each opened by a provenance marker, and the two markers differ (by their `generated=` field — assert there are two marker lines for that stage/spec). Since the clock is real and not mocked, assert the count of marker lines is 2 rather than asserting two different timestamp values (which could collide if the two calls land in the same instant) — if the injector guarantees distinct timestamps, additionally assert they differ, but the load-bearing assertion is two blocks.
6. `test_injector_exception_is_swallowed`: force the injector to fail internally (e.g. make the `ai-docs/<spec>/` path unwritable, or monkeypatch `retro.append_section` to raise); call `inject_stage_metrics(...)`; assert it returns `None` and raises nothing.

# Files to create/modify

- `tests/test_capture_retro_injector.py`

# Test requirements

- `test_injects_block_under_metrics_heading` (integration): block appended under `## <STAGE> — metrics` with a structurally-matched provenance marker.
- `test_does_not_disturb_existing_prose_section` (integration): existing plain `## <STAGE>` prose preserved; metrics block coexists.
- `test_rework_produces_two_marked_blocks` (integration): two injections → two marked metrics blocks.
- `test_injector_exception_is_swallowed` (integration): internal failure → returns None, no raise.

# Acceptance criteria

AC-18 (provenance-marked block under the distinct heading, rework two-block outcome), AC-11 (fail-silent injection). Gate: tests compile and fail before implementation.

# Model

Sonnet — provenance-marker structural matching, coexistence, and rework two-block behavior.

# Wave

4
