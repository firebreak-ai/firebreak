---
id: task-23
type: implementation
wave: 1
covers: [AC-12]
files_to_create:
  - assets/fbk-scripts/fbk/precheck.py
test_tasks: [task-06]
dependencies: []
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Produces `assets/fbk-scripts/fbk/precheck.py`, the capability-entry prerequisite probe that, given a phase and a feature directory, returns a structured non-blocking result naming any missing upstream artifact and the upstream phase that produces it.

## 2. Context

Capability-entry: each SDL phase is independently invocable, and a phase invoked without its upstream artifacts must name the specific missing artifact and the upstream phase to run — and must NOT hard-block (never call `sys.exit`). This is the mechanical helper the phase skills' mid-pipeline-entry step calls; it reports, the skill offers to run the upstream phase.

The function signature is pinned (must match exactly what task-06's test imports):

```python
def check_prerequisites(phase: str, feature_dir: str) -> dict
```

Here `feature_dir` is the **actual feature directory**, full stop (e.g. `ai-docs/refactored-sdl/`). The function does NOT scan a project root for "the single subdirectory under `ai-docs/`" — that fragile single-subdir invariant is removed. The feature name is derived directly from the path: `feature_name = Path(feature_dir).name`. Upstream artifacts are looked up directly under `feature_dir/...` per the spec's per-phase prerequisite rules.

The return dict shape (pinned by the test):
```python
{
  "phase": "<requested-phase>",
  "ready": True | False,
  "missing": [  # empty list if ready
    {"artifact": "<artifact-name>", "upstream_phase": "<phase-name>"}
  ]
}
```

The four upstream-missing cases the probe handles (each names the artifact and upstream phase), checked directly under `feature_dir`:
1. `phase == "design"` → requires `prd.md` present in the feature dir; if absent → missing `{"artifact": "prd.md", "upstream_phase": "intent"}`.
2. `phase == "spec"` → requires `design-manifest.md`; if absent → missing `{"artifact": "design-manifest.md", "upstream_phase": "design"}`.
3. `phase == "breakdown"` → requires `<feature>-spec.md` (the file ending in `-spec.md`); if absent → missing `{"artifact": "<feature>-spec.md", "upstream_phase": "spec"}`. The test asserts the missing artifact name ends with `-spec.md` and uses the actual feature name (derived from `Path(feature_dir).name`).
4. `phase == "code-review"` → requires an `implementation/` directory under the feature dir; if absent → missing `{"artifact": "implementation/", "upstream_phase": "implement"}`.

When the required artifact for the requested phase is present, `ready` is `True` and `missing` is `[]`. For a phase not in the four mapped cases, return `ready: True` with empty missing (no prerequisite known).

Existing patterns: this is a pure helper module like the gate check functions — `pathlib.Path` for filesystem checks (the test uses real `tmp_path` dirs, no mocks). It does NOT need an argparse `main()` for the test, but add a minimal `main()` + argparse front for consistency with the gate modules (it is not registered in COMMAND_MAP — it is called from skills indirectly or used as a library). The non-blocking invariant is load-bearing: the test monkeypatches `sys.exit` to raise and asserts it is never called.

## 3. Instructions

1. Create `assets/fbk-scripts/fbk/precheck.py` with a module docstring and the function `def check_prerequisites(phase: str, feature_dir: str) -> dict:` exactly.

2. In the function, resolve the feature directory directly: `feature_path = Path(feature_dir)`. Derive `feature_name = feature_path.name`. Do NOT scan any parent for "the single subdirectory under `ai-docs/`" — `feature_dir` IS the feature directory. If `feature_path` does not exist, treat all artifacts as missing for the mapped phase.

3. Implement the four phase→prerequisite mappings exactly as listed in Context, checking artifacts directly under `feature_path`. For each, build `missing` with a dict `{"artifact": <name>, "upstream_phase": <phase>}` when the artifact is absent. For the `breakdown` case, the artifact name is `f"{feature_name}-spec.md"`. For `code-review`, check `is_dir()` on `feature_path / "implementation"`. Return `{"phase": phase, "ready": len(missing) == 0, "missing": missing}`.

4. Never call `sys.exit` inside `check_prerequisites`. Completion: the function returns a dict in every branch and contains no `sys.exit` call.

5. Add a minimal `main()` with argparse (`phase` and `feature_dir` positional args) that prints `json.dumps(check_prerequisites(...))` and a `if __name__ == "__main__": main()` guard. The `main()` may exit 0 always (non-blocking) — do not exit 2 on missing prerequisites.

6. Run the paired test: from `assets/fbk-scripts`, `python3 -m pytest tests/test_precheck.py -q`. All 10 test methods must pass.

## 4. Files to create/modify

- `assets/fbk-scripts/fbk/precheck.py` (create)

## 5. Test requirements

This task makes `assets/fbk-scripts/tests/test_precheck.py` (task-06) pass: the non-blocking invariant, the four upstream-missing cases (both fail-when-missing and pass-when-present), and the return-structure test. No new tests are written here. Do not edit the test file.

## 6. Acceptance criteria

- AC-12: for each of the four upstream-missing cases, the probe returns a structured dict naming the missing artifact and the upstream phase, without calling `sys.exit`.
- Primary criterion: the task-06 tests pass.

## 7. Model

Sonnet

## 8. Wave

Wave 1
