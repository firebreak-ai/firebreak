---
id: task-29
type: implementation
wave: 4
covers: [AC-01, AC-02, AC-08, AC-11, AC-12, AC-16, AC-21, AC-15]
files_to_create:
  - assets/fbk-scripts/fbk/capture/hook_router.py
test_tasks: [task-12]
completion_gate: "task-12 tests pass"
dependencies: [task-27, task-24, task-22, task-25]
---

# 1 Objective

Produce the standalone globally-installed hook router: a script Claude's hook runtime fires by absolute path. It reads the hook event from stdin, resolves ONE pinned working directory, gates capture against it, resolves the level, assembles a Claude-level event envelope, filters subagent events by agent identity, stamps the active SDL stage (null when none), writes the event under that same pinned directory via the shared writer, and exits 0 — never writing to stdout, never raising. This is an ORCHESTRATOR task (its own process bootstrap, gating, redaction, and writer wiring): see the Wiring checklist.

# 2 Context

The router runs as its own process by absolute path, NOT through `fbk.py` (routing it through the dispatcher would require the dispatcher to instrument itself before loading). It therefore must replicate `fbk.py`'s `sys.path` bootstrap before importing `fbk.capture.*`. Port the stdin/envelope/stage-stamp shape from the prototype `ai-docs/hook-harvesting/hooks/hook_router.py`, but harden two things the prototype got wrong:
- **Working-directory pinning (AC-21).** The prototype read the stage directory from `payload['cwd']` and the write directory from `$CLAUDE_PROJECT_DIR` — a divergence that lets the gate evaluate one project while the write lands in another. The ported router pins ONE source with explicit precedence: `os.getcwd()` is the authority; `payload['cwd']` and `$CLAUDE_PROJECT_DIR` are not silently trusted over it. It gates that path and writes only under it.
- **Level-gated payloads (AC-08).** At `standard` the router strips tool-call payloads and prompt text; at `full` it records them. This is enforced centrally by the writer's redaction, so the router hands the raw `data` and the resolved level to the writer rather than stripping itself — but it must pass the level the gate resolved.

Stage stamping: read the active SDL run's spec/stage from the state store under the pinned cwd (best-effort, like the prototype's `current_stage`); when no run is active, the event's `spec`/`stage` are null (present, not absent) — the writer enforces null-not-absent, so the router passes `None`. The event is still recorded with no active run.

Subagent filtering: for a `SubagentStop`/`SubagentStart` payload, read the agent identity; the event is still RECORDED carrying its identity (the report excludes unknown identities from counts, not the router). The router may consult `known_agents.is_known_agent` to tag known-ness but must record the event either way.

Event-type mapping: map the payload's `hook_event_name` to the fixed vocabulary — tool-use events → `TOOL_USE`, subagent lifecycle → `SUBAGENT_STOP`, session/prompt lifecycle → `LIFECYCLE`. Source is `"hook_router"`.

# 3 Instructions

## Wiring checklist (orchestrator)

- **Import bootstrap:** at the top, before importing `fbk.capture.*`, replicate `fbk.py`'s `sys.path` setup — insert the fbk-scripts package dir (compute from `os.path.dirname(os.path.realpath(__file__))` walking up to the fbk-scripts root, i.e. the parent of `fbk/`) and glob the venv site-packages (`<fbk-scripts>/.venv/lib/python*/site-packages`) onto `sys.path`, mirroring lines 8–17 of `fbk.py`. Only THEN `from fbk.capture import event_writer, gate_check, known_agents`. This makes imports resolve in production (run by absolute path) and in tests.
- **Interpose:** read stdin once (`json.load(sys.stdin)`, fail-silent to a parse-error marker); resolve the pinned cwd (`os.getcwd()` authority); run the gate against it.
- **Initialize:** resolve the capture level via `gate_check.resolve_capture_level(cwd)`; if `project_is_instrumented(cwd)` is False (or level is `off`), exit 0 immediately writing nothing and no stdout.
- **Write:** assemble the event `data`, map the event type, read spec/stage best-effort, and call `event_writer.write(event_type, "hook_router", data, spec, stage, level, <cwd>/.fbk-capture/events.jsonl)`.
- **Clean up / preserve contract:** the router NEVER writes to stdout and ALWAYS exits 0, even on any failure (wrap everything so nothing propagates). The events path is always `os.path.join(cwd, ".fbk-capture", "events.jsonl")` — same pinned cwd the gate used.

## Steps

1. Create `fbk/capture/hook_router.py` with a `main()` and `if __name__ == "__main__": main()`. Completion: the file runs as a standalone script.
2. Implement the bootstrap as above. Completion: importing `fbk.capture.event_writer` succeeds when the script is run by absolute path.
3. Read stdin payload fail-silently. Resolve `cwd = os.getcwd()` as the authority (do NOT prefer `payload['cwd']` or `$CLAUDE_PROJECT_DIR`). Completion: a payload whose `cwd`/`$CLAUDE_PROJECT_DIR` points at project B still gates and writes under project A (the process cwd).
4. Gate: if not instrumented or level `off`, exit 0, no write, no stdout. Completion: a bare project produces no events file and no stdout.
5. Map `hook_event_name` to the event type; assemble `data` from the payload (tool name/input for tool-use, agent identity for subagent, lifecycle fields otherwise). Read best-effort spec/stage from the state store under the pinned cwd; pass `None`/`None` when no run is active. Completion: with no state file, the written event carries `stage` present and null.
6. Call `event_writer.write(...)` with the resolved level so `standard` strips the payload and `full` keeps it. Completion: at `standard` the `TOOL_USE` event has the tool payload stripped; at `full` (with out-of-tree corroboration) it is present.
7. Subagent path: record a `SubagentStop` event even when the agent identity is empty/unknown, carrying the identity. Completion: an empty-identity `SubagentStop` is written with the empty identity.
8. Exit 0 always; never write stdout; never raise. Completion: an unwritable events path still exits 0 with empty stdout and no traceback.

# 4 Files to create/modify

- Create `fbk/capture/hook_router.py`

# 5 Test requirements

Makes task-12 (`tests/test_capture_hook_router.py`) pass: standard strips payload / full records it; uninstrumented writes nothing and no stdout; empty-identity SubagentStop recorded with its identity; stage null when no run; writes under cwd never the global dir; gate+write follow the pinned cwd when the payload cwd diverges; fail-silent on an unwritable path (exit 0, no stdout, no traceback).

# 6 Acceptance criteria

Primary: task-12's tests pass. Covers AC-01 (uninstrumented exit), AC-02 (writes project not global), AC-08 (payload only at full), AC-11 (fail-silent), AC-12 (stage null stamping), AC-16 (capture-time identity record), AC-21 (working-directory pinning), AC-15 (router events join the chokepoint's in one stream).

# 7 Model

Sonnet

# 8 Wave

4
