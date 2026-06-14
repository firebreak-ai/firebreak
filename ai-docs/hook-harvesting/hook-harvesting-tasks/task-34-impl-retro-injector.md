---
id: task-34
type: implementation
wave: 4
covers: [AC-18, AC-11, AC-20]
files_to_create:
  - assets/fbk-scripts/fbk/capture/retro_injector.py
test_tasks: [task-17]
completion_gate: "task-17 tests pass"
dependencies: [task-28]
---

# 1 Objective

Produce the per-stage retrospective injector: it resolves the retrospective path internally from `os.getcwd()` and the spec, appends a provenance-marked metrics block under a `## <STAGE> — metrics` heading (distinct from the agent's plain `## <STAGE>` heading) via the existing `retro.append_section`, produces a second marked block on a reworked stage, and catches EVERY exception so a failed injection never blocks anything.

# 2 Context

After a working stage completes, the state engine calls this injector to write a metrics block for that stage into `ai-docs/<spec>/<spec>-retrospective.md` — the same path the retrospective skill and existing `retro.append_section` callers use, so the machine block and the agent's prose coexist in one file. The block opens with a provenance marker of exactly `<!-- fbk-metrics stage=<STAGE> spec=<SPEC> generated=<ISO-8601> -->` (no trailing space), followed by the stage's metrics body. The heading `<STAGE> — metrics` is distinct from the plain `<STAGE>` heading the skill uses for prose, so neither overwrites the other. A reworked stage that completes again produces a SECOND marked block, distinguished by its provenance timestamp.

The block body comes from `report.stage_summary(spec, stage)` (task-28), which already opens with the provenance marker. To avoid a load cycle (`report` imports `fbk.capture.*`; this injector imports `report`), import `report` with a FUNCTION-LEVEL import inside `inject_stage_metrics`, not at module top.

`retro.append_section(retrospective_path, stage_name, content)` writes `## {stage_name}\n\n{content}\n` — reuse it as-is; do NOT modify it. Passing `stage_name="<STAGE> — metrics"` yields the distinct heading.

# 3 Instructions

1. Create `fbk/capture/retro_injector.py`. Import `os` at module top; do NOT import `report` or `retro` at module top (function-level import avoids the load cycle).
2. Implement `inject_stage_metrics(spec: str, completed_stage: str) -> None`. Wrap the ENTIRE body in `try/except Exception` returning `None` — every exception is caught so a failed injection never blocks the caller (the state transition). Never write to stdout (the injector can run inside the chokepoint's stdout-redirect frame). Completion: an internal failure (unwritable path, raising `append_section`) returns `None` and raises nothing.
3. Resolve the retrospective path internally as `os.path.join(os.getcwd(), "ai-docs", spec, f"{spec}-retrospective.md")` — no path parameter. Completion: with cwd set to a tmp project, the block lands at `<cwd>/ai-docs/<spec>/<spec>-retrospective.md`.
4. Build the block body via a function-level `from fbk import report` then `content = report.stage_summary(spec, completed_stage)`. The body already opens with the provenance marker line `<!-- fbk-metrics stage=<STAGE> spec=<SPEC> generated=<ISO-8601> -->`. Completion: the appended block's first content line matches the provenance-marker structure for the stage/spec.
5. Append via a function-level `from fbk import retro` then `retro.append_section(path, f"{completed_stage} — metrics", content)`. This yields the heading `## <STAGE> — metrics`. Ensure the `ai-docs/<spec>/` directory exists (create it if needed) before appending so a first injection succeeds. Completion: the heading `## <STAGE> — metrics` appears, distinct from any plain `## <STAGE>` prose section, which is preserved byte-intact.
6. Rework: calling the injector twice for the same stage appends TWO marked blocks (append-only via `append_section`), each opened by a provenance marker. Completion: two calls → exactly two `## <STAGE> — metrics` blocks with two marker lines.

# 4 Files to create/modify

- Create `fbk/capture/retro_injector.py`

# 5 Test requirements

Makes task-17 (`tests/test_capture_retro_injector.py`) pass: appends a block under `## <STAGE> — metrics` with a structurally-matched provenance marker; preserves an existing plain `## <STAGE>` prose section while coexisting; two injections → two marked blocks; an internal failure returns None and raises nothing.

# 6 Acceptance criteria

Primary: task-17's tests pass. Covers AC-18 (provenance-marked block under the distinct heading, rework two-block outcome), AC-11 (fail-silent injection), AC-20 (the retrospective's machine-marked metrics blocks half of the end-to-end report+retro outcome).

# 7 Model

Sonnet

# 8 Wave

4
