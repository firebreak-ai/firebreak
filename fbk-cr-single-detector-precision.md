# Code Review: Single-Detector Precision v0.4.0

**Date**: 2026-04-17
**Type**: Post-implementation review
**Preset**: behavioral-only
**Severity threshold**: minor

## Source of Truth

Feature spec: `ai-docs/0.4.0/single-detector-precision/single-detector-precision-spec.md`

## Scope

Files modified in this implementation:
- `assets/scripts/pipeline.py` — filter pipeline (validate, domain-filter, severity-filter, to-markdown, run)
- `ai-docs/detection-accuracy/martian-benchmark/inject_results.py` — JSON-based inject script
- `assets/agents/fbk-code-review-detector.md` — Detector persona rewrite
- `assets/agents/fbk-code-review-challenger.md` — Challenger persona rewrite
- `assets/config/presets.json` — detection preset configuration
- `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md` — guide update
- `assets/skills/fbk-code-review/SKILL.md` — orchestrator update

## Findings

### F-01: cmd_run silently ignores invalid --min-severity instead of rejecting

- **Location**: `assets/scripts/pipeline.py:259-260`
- **Type**: behavioral | **Severity**: major | **Origin**: introduced
- **Detection source**: spec-ac | **Pattern**: `inconsistent-validation`

**Mechanism**: `cmd_run` at line 260 computes threshold with `SEVERITY_ORDER.get(min_sev, 0)`, defaulting to 0 (info-level) when `min_sev` is not a recognized key. `cmd_severity_filter` at lines 131-134 validates `min_sev` against `VALID_SEVERITIES` and calls `sys.exit(1)` on an unrecognized value. The two code paths treat the same invalid input differently.

**Consequence**: An orchestrator that passes a typo or unsupported severity string (e.g., `blocker`, `high`) to `pipeline.py run` receives exit code 0 and a full, unfiltered sighting list rather than an error.

**Evidence**: `cmd_severity_filter` line 131-134: validates and exits. `cmd_run` line 259-260: no validation, silently falls through with threshold=0. Concrete input: `pipeline.py run --preset behavioral-only --min-severity blocker` — all sightings pass through.

**Verification**: Both code paths confirmed. `cmd_severity_filter` explicitly checks `if min_sev not in VALID_SEVERITIES` and `sys.exit(1)`. `cmd_run` performs no equivalent check.

**Remediation**: Add `VALID_SEVERITIES` membership check before line 260 in `cmd_run`, mirroring lines 131-134 in `cmd_severity_filter`.

### F-02: code-review-guide.md instructs 'uv run pipeline.py' — path fails from project root

- **Location**: `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md:99-103`
- **Type**: behavioral | **Severity**: major | **Origin**: introduced
- **Detection source**: spec-ac | **Pattern**: `path-divergence`

**Mechanism**: Orchestration Protocol steps 3 and 7 in the guide specify `uv run pipeline.py run ...` and `uv run pipeline.py to-markdown`. The script is at `assets/scripts/pipeline.py`. No `pyproject.toml` registers it as a uv script entry point. SKILL.md correctly uses `uv run assets/scripts/pipeline.py`.

**Consequence**: An agent that reads the guide and follows its protocol issues a command that fails with file-not-found on every review run.

**Evidence**: SKILL.md line 83: `uv run assets/scripts/pipeline.py run`. Guide line 99: `uv run pipeline.py run`. No `pyproject.toml` at project root.

**Verification**: Both documents confirmed. SKILL.md uses the correct full path. Guide uses the bare filename. The guide is injected into agents per SKILL.md line 10.

**Remediation**: Update guide lines 99 and 103 to use `uv run assets/scripts/pipeline.py`.

### F-03: Challenger output bypasses pipeline.py validate — matrix enforcement skipped

- **Location**: `assets/skills/fbk-code-review/SKILL.md:85-86`
- **Type**: behavioral | **Severity**: major | **Origin**: introduced
- **Detection source**: spec-ac | **Pattern**: `pipeline-bypass`

**Mechanism**: AC-11 specifies: Detector JSON → `pipeline.py run` → Challenger JSON → validate → filter → `to-markdown`. SKILL.md steps 5-6 perform Challenger output validation manually (prose instructions), without invoking `pipeline.py validate`. Only step 7 invokes `pipeline.py` (for `to-markdown`).

**Consequence**: Challenger reclassifications that produce invalid type-severity combinations (e.g., behavioral+info) are not caught by the machine-validated matrix in `pipeline.py` — they pass through to the review report.

**Evidence**: AC-11 names four post-Challenger stages. SKILL.md steps 5-6 substitute prose instructions for pipeline.py invocations. Adjacent: code-review-guide.md Orchestration Protocol step 5 mirrors the same omission.

**Verification**: AC-11 compared to SKILL.md steps 4-7. The validate and filter stages from AC-11 are not present as pipeline.py invocations for Challenger output.

**Remediation**: After Challenger produces JSON, pipe through `pipeline.py validate` to enforce matrix on reclassified combinations before the status filter.

## Rejections

- **S-04**: inject_results.py `pr_lookup` variable constructed but unused — structurally dead code, not behavioral. Rejected as out-of-scope.

## Retrospective

- **Sightings**: 4 total, 3 verified, 1 rejected (structural, out-of-scope)
- **Verification rounds**: 1 (converged in first round)
- **Finding quality**: 3 behavioral/major findings, all spec-traceable
- **Detection sources**: all spec-ac
- **Patterns identified**: inconsistent-validation, path-divergence, pipeline-bypass
