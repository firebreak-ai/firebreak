---
id: task-12
type: test
wave: 4
covers: [AC-01, AC-02, AC-08, AC-11, AC-12, AC-16, AC-21]
files_to_create:
  - assets/fbk-scripts/tests/test_capture_hook_router.py
completion_gate: "tests compile and fail before implementation"
---

# Objective

Write the integration tests for the standalone hook router: payload stripped at standard / present at full, no write and no stdout in an uninstrumented project, subagent identity recorded but excluded from counts, stage stamped null when no run is active, writes under the project cwd and never the global dir, gate-and-write against the same pinned working directory, and fully fail-silent.

# Context

The hook router is a standalone script fired by Claude's hook runtime (not routed through `fbk.py`). On each invocation it reads the hook event from stdin, resolves ONE working directory, runs the capture gate against it, resolves the level, assembles an envelope for the Claude-level event, filters subagent events by agent identity, writes the event under that same resolved directory, and exits `0`. It never writes to stdout and never raises. At `standard` it strips tool-call payloads and prompt text; at `full` it records them. The working directory is pinned to `os.getcwd()` as the authority — `payload['cwd']` and `$CLAUDE_PROJECT_DIR` are not silently trusted over it — and the gate decision and the write path always follow that same pinned directory. When no SDL run is active, the event's `stage` is `null` (present, not absent), and the event is still recorded.

The router runs as its own process. Drive it via subprocess feeding stdin, matching the suite's subprocess style. Locate the router script at its ported path `fbk/capture/hook_router.py` under `assets/fbk-scripts/`. Build payloads with `capture_fixtures.hook_payload` and projects with `make_project`. Control the router's working directory by passing `cwd=<project>` to `subprocess.run` (this is the `os.getcwd()` authority). Point any global-config dir at a fixture path via env (e.g. a fixture `HOME` / `XDG` / `$CLAUDE_PROJECT_DIR` override) so a "no write to global dir" assertion is hermetic.

# Instructions

1. Inspect the prototype `ai-docs/hook-harvesting/hooks/hook_router.py` for the stdin/envelope shape; the ported router lives at `assets/fbk-scripts/fbk/capture/hook_router.py`. Define `ROUTER = Path(__file__).parent.parent / "fbk" / "capture" / "hook_router.py"`; skip the file's tests (`pytest.skip` / a fixture-level skip) if `ROUTER` does not exist, matching the red-phase pattern.
2. Helper: `run_router(payload_json, project_dir, env_extra=None)` → `subprocess.run([sys.executable, str(ROUTER)], input=payload_json, cwd=str(project_dir), env={**os.environ, **(env_extra or {})}, capture_output=True, text=True)`.
3. `test_standard_strips_payload`: instrumented project at `standard`; feed a `PostToolUse` payload carrying a tool-call payload; assert the router exits 0, the project's `.fbk-capture/events.jsonl` contains one `TOOL_USE` event with the tool-call payload stripped (free-text field absent/emptied), and stdout is empty.
4. `test_full_records_payload`: same project with `capture.cfg` `capture_level=full` AND the out-of-tree corroboration (set `FBK_CAPTURE_LEVEL=full` in `env_extra`); feed the same payload; assert the written `TOOL_USE` event carries the tool-call payload present/verbatim.
5. `test_uninstrumented_writes_nothing_no_stdout`: bare project (no markers); feed any payload; assert exit 0, NO `.fbk-capture/events.jsonl` created, and stdout empty.
6. `test_subagent_empty_identity_recorded_but_excluded`: instrumented project; feed a `SubagentStop` payload with an empty agent identity; assert the event IS written (recorded) but carries the empty identity. (The report's exclusion of it from counts is covered in the report task; here assert the capture-time record-but-mark behavior.)
7. `test_stage_null_when_no_run_active`: instrumented project with NO state file (no active SDL run); feed a payload; assert the written event has `stage` present and equal to JSON `null` (the key exists, value is None), not absent.
8. `test_writes_under_cwd_never_global`: instrumented project; point a fixture global dir via env (e.g. `CLAUDE_PROJECT_DIR` set to a different fixture path, and/or a fixture `HOME`); feed a payload; assert the event lands at `<project>/.fbk-capture/events.jsonl` and NO file is created under the fixture global path.
9. `test_gate_and_write_follow_pinned_cwd`: instrumented project A as `cwd`; feed a payload whose `cwd`/`$CLAUDE_PROJECT_DIR` points at a DIFFERENT project B; assert the gate decision and the write both follow the pinned `os.getcwd()` (project A) — the event lands under A's `.fbk-capture/` and NOT under B's. This pins the working-directory authority.
10. `test_router_fail_silent_on_unwritable`: instrumented project but make the events path unwritable (e.g. `.fbk-capture/` is a read-only dir or a file where the dir should be); feed a valid payload; assert exit 0, stdout empty, and the subprocess raised nothing (no traceback in stderr — assert `"Traceback" not in result.stderr`).

# Files to create/modify

- `tests/test_capture_hook_router.py`

# Test requirements

- `test_standard_strips_payload` (integration): standard → TOOL_USE with payload stripped, exit 0, no stdout.
- `test_full_records_payload` (integration): full (with out-of-tree corroboration) → payload present.
- `test_uninstrumented_writes_nothing_no_stdout` (integration): bare project → no events file, no stdout.
- `test_subagent_empty_identity_recorded_but_excluded` (integration): empty-identity SubagentStop recorded with empty identity.
- `test_stage_null_when_no_run_active` (integration): no active run → `stage` present and null.
- `test_writes_under_cwd_never_global` (integration): write under project cwd, never the fixture global dir.
- `test_gate_and_write_follow_pinned_cwd` (integration): divergent payload cwd ignored; gate+write follow pinned cwd.
- `test_router_fail_silent_on_unwritable` (integration): unwritable events path → exit 0, no stdout, no traceback.

# Acceptance criteria

AC-01 (uninstrumented exit), AC-02 (write project not global), AC-08 (payload only at full), AC-11 (fail-silent), AC-12 (stage null stamping), AC-16 (capture-time identity record), AC-21 (working-directory pinning). Gate: tests compile and fail before implementation.

# Model

Sonnet — multi-scenario subprocess router with cwd-pinning and fail-silent seams.

# Wave

4
