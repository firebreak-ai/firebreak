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

Produces `assets/fbk-scripts/fbk/precheck.py`, the capability-entry prerequisite probe that, given a phase and a project root, returns a structured non-blocking result naming any missing upstream artifact and the upstream phase that produces it.

## 2. Context

Capability-entry: each SDL phase is independently invocable, and a phase invoked without its upstream artifacts must name the specific missing artifact and the upstream phase to run — and must NOT hard-block (never call `sys.exit`). This is the mechanical helper the phase skills' mid-pipeline-entry step calls; it reports, the skill offers to run the upstream phase.

The function signature is pinned (must match exactly what task-06's test imports):

```python
def check_prerequisites(phase: str, feature_dir: str) -> dict
```

Here `feature_dir` is the **project root** (the test passes `str(tmp_path)`), and the function looks under `<feature_dir>/ai-docs/sample/...` — but the feature name is not a separate argument. Read the task-06 test carefully: its `feature_dir` fixture creates `tmp_path / "ai-docs" / "sample"` and passes `tmp_path` (the project root) as the second argument, with the feature name `"sample"`. The function must therefore derive the single feature directory under `<project-root>/ai-docs/` — the test only ever has one feature dir named `sample`. Implement it to scan `<feature_dir>/ai-docs/` for the (single) feature subdirectory and check artifacts inside it. If multiple subdirectories exist, pick the one being probed is out of scope for the test — handle the single-subdirectory case the test exercises; if `ai-docs/` has exactly one subdirectory, use it.

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

The four upstream-missing cases the probe handles (each names the artifact and upstream phase):
1. `phase == "design"` → requires `prd.md` present in the feature dir; if absent → missing `{"artifact": "prd.md", "upstream_phase": "intent"}`.
2. `phase == "spec"` → requires `design-manifest.md`; if absent → missing `{"artifact": "design-manifest.md", "upstream_phase": "design"}`.
3. `phase == "breakdown"` → requires `<feature>-spec.md` (the file ending in `-spec.md`); if absent → missing `{"artifact": "<feature>-spec.md", "upstream_phase": "spec"}`. The test asserts the missing artifact name ends with `-spec.md` and uses the actual feature name (`sample-spec.md`).
4. `phase == "code-review"` → requires an `implementation/` directory under the feature dir; if absent → missing `{"artifact": "implementation/", "upstream_phase": "implement"}`.

When the required artifact for the requested phase is present, `ready` is `True` and `missing` is `[]`. For a phase not in the four mapped cases, return `ready: True` with empty missing (no prerequisite known).

Existing patterns: this is a pure helper module like the gate check functions — `pathlib.Path` for filesystem checks (the test uses real `tmp_path` dirs, no mocks). It does NOT need an argparse `main()` for the test, but add a minimal `main()` + argparse front for consistency with the gate modules (it is not registered in COMMAND_MAP — it is called from skills indirectly or used as a library). The non-blocking invariant is load-bearing: the test monkeypatches `sys.exit` to raise and asserts it is never called.

## 3. Instructions

1. Create `assets/fbk-scripts/fbk/precheck.py` with a module docstring and the function `def check_prerequisites(phase: str, feature_dir: str) -> dict:` exactly.

2. In the function, resolve the feature directory: `root = Path(feature_dir)`, then find the single subdirectory under `root / "ai-docs"` (e.g., iterate `(root / "ai-docs").iterdir()` for the first directory). Derive the feature name from that subdirectory's name. If `ai-docs/` does not exist or has no subdirectory, treat all artifacts as missing for the mapped phase.

3. Implement the four phase→prerequisite mappings exactly as listed in Context. For each, build `missing` with a dict `{"artifact": <name>, "upstream_phase": <phase>}` when the artifact is absent. For the `breakdown` case, the artifact name is `f"{feature_name}-spec.md"`. For `code-review`, check `is_dir()` on `<feature>/implementation`. Return `{"phase": phase, "ready": len(missing) == 0, "missing": missing}`.

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
