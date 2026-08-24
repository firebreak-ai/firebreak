"""Tests for fbk.gates.breakdown validation logic."""

import json
import pytest
from fbk.gates.breakdown import validate_breakdown


# Minimal test-lock manifest JSON used as the pre-lock-verdict signal in slice-aware tests.
MANIFEST_ENTRY = {"test-hashes.json": '{"files": {}, "computed_at": "2026-01-01T00:00:00Z"}'}


def make_minimal_spec(acs):
    ac_lines = "\n".join(f"- {ac}: Requirement" for ac in acs)
    return f"## Acceptance criteria\n{ac_lines}\n"


def make_cross_cutting_manifest(ac="AC-01"):
    return {
        "category": "feature",
        "tasks": [{
            "id": "task-01",
            "title": "Test cross-cutting AC",
            "file": "task-01.md",
            "type": "test",
            "wave_id": 1,
            "dependencies": [],
            "covers": [ac],
            "model": "Haiku",
            "status": "not_started",
            "slice_shape": "cross-cutting"
        }]
    }


def make_contract_preserving_manifest(ac="AC-01"):
    return {
        "category": "feature",
        "tasks": [{
            "id": "task-01",
            "title": "Impl contract-preserving change",
            "file": "task-01.md",
            "type": "implementation",
            "wave_id": 1,
            "dependencies": [],
            "covers": [ac],
            "model": "Haiku",
            "status": "not_started",
            "slice_shape": "contract-preserving"
        }]
    }


class TestBreakdownGateValidation:
    """Tests for breakdown gate validation."""

    def test_uncovered_ac_detected(self):
        """AC in spec not covered by any task produces 'AC coverage' failure."""
        spec = """## Acceptance criteria
- AC-01: First requirement
- AC-02: Second requirement
"""
        manifest = {
            "category": "feature",
            "tasks": [
                {
                    "id": "task-01",
                    "title": "Test AC-01",
                    "file": "task-01-test-ac01.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-02",
                    "title": "Implement AC-01",
                    "file": "task-02-impl-ac01.md",
                    "type": "implementation",
                    "wave_id": 2,
                    "dependencies": ["task-01"],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                }
            ]
        }
        tfiles = {
            "task-01-test-ac01.md": "## Files to create\n- `test.py`",
            "task-02-impl-ac01.md": "## Files to create\n- `impl.py`"
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "fail"
        assert any("AC coverage" in f for f in result["failures"])

    def test_circular_dependency_detected(self):
        """Circular dependency (task-01 -> task-02 -> task-01) produces 'cycle' failure."""
        spec = """## Acceptance criteria
- AC-01: Requirement 1
"""
        manifest = {
            "category": "feature",
            "tasks": [
                {
                    "id": "task-01",
                    "title": "Test AC-01",
                    "file": "task-01.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": ["task-02"],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-02",
                    "title": "Implement AC-01",
                    "file": "task-02.md",
                    "type": "implementation",
                    "wave_id": 1,
                    "dependencies": ["task-01"],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                }
            ]
        }
        tfiles = {
            "task-01.md": "## Files to create\n- `test.py`",
            "task-02.md": "## Files to create\n- `impl.py`"
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "fail"
        assert any("cycle" in f.lower() for f in result["failures"])

    def test_wave_ordering_violation_detected(self):
        """Dependency in later wave than dependent produces 'Wave ordering' failure."""
        spec = """## Acceptance criteria
- AC-01: Requirement 1
"""
        manifest = {
            "category": "feature",
            "tasks": [
                {
                    "id": "task-01",
                    "title": "Test AC-01",
                    "file": "task-01.md",
                    "type": "test",
                    "wave_id": 2,
                    "dependencies": ["task-02"],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-02",
                    "title": "Implement AC-01",
                    "file": "task-02.md",
                    "type": "implementation",
                    "wave_id": 3,
                    "dependencies": [],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                }
            ]
        }
        tfiles = {
            "task-01.md": "## Files to create\n- `test.py`",
            "task-02.md": "## Files to create\n- `impl.py`"
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "fail"
        assert any("Wave ordering" in f for f in result["failures"])

    def test_file_conflict_detected(self):
        """Two tasks in same wave touching same file produces 'File conflict' failure."""
        spec = """## Acceptance criteria
- AC-01: Requirement 1
- AC-02: Requirement 2
"""
        manifest = {
            "category": "feature",
            "tasks": [
                {
                    "id": "task-01",
                    "title": "Test AC-01",
                    "file": "task-01.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-02",
                    "title": "Test AC-02",
                    "file": "task-02.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-02"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-03",
                    "title": "Implement AC-01",
                    "file": "task-03.md",
                    "type": "implementation",
                    "wave_id": 2,
                    "dependencies": ["task-01"],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-04",
                    "title": "Implement AC-02",
                    "file": "task-04.md",
                    "type": "implementation",
                    "wave_id": 2,
                    "dependencies": ["task-02"],
                    "covers": ["AC-02"],
                    "model": "Haiku",
                    "status": "pending"
                }
            ]
        }
        tfiles = {
            "task-01.md": "## Files to create\n- `test.py`",
            "task-02.md": "## Files to create\n- `test2.py`",
            "task-03.md": "## Files to create\n- `impl.py`\n- `shared.py`",
            "task-04.md": "## Files to create\n- `shared.py`"
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "fail"
        assert any("File conflict" in f for f in result["failures"])

    def test_test_ordering_violation_detected(self):
        """Implementation task before test task in same wave produces 'Test ordering' failure."""
        spec = """## Acceptance criteria
- AC-01: Requirement 1
"""
        manifest = {
            "category": "feature",
            "tasks": [
                {
                    "id": "task-01",
                    "title": "Implement AC-01",
                    "file": "task-01.md",
                    "type": "implementation",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-02",
                    "title": "Test AC-01",
                    "file": "task-02.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                }
            ]
        }
        tfiles = {
            "task-01.md": "## Files to create\n- `impl.py`",
            "task-02.md": "## Files to create\n- `test.py`"
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "fail"
        assert any("Test ordering" in f for f in result["failures"])

    def test_valid_breakdown_passes(self):
        """Valid breakdown with all ACs covered, no cycles, correct ordering, test-before-impl passes."""
        spec = """## Acceptance criteria
- AC-01: First requirement
- AC-02: Second requirement
"""
        manifest = {
            "category": "feature",
            "tasks": [
                {
                    "id": "task-01",
                    "title": "Test AC-01",
                    "file": "task-01.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-02",
                    "title": "Test AC-02",
                    "file": "task-02.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-02"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-03",
                    "title": "Implement AC-01",
                    "file": "task-03.md",
                    "type": "implementation",
                    "wave_id": 2,
                    "dependencies": ["task-01"],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-04",
                    "title": "Implement AC-02",
                    "file": "task-04.md",
                    "type": "implementation",
                    "wave_id": 2,
                    "dependencies": ["task-02"],
                    "covers": ["AC-02"],
                    "model": "Haiku",
                    "status": "pending"
                }
            ]
        }
        tfiles = {
            "task-01.md": "## Files to create\n- `test1.py`",
            "task-02.md": "## Files to create\n- `test2.py`",
            "task-03.md": "## Files to create\n- `impl1.py`",
            "task-04.md": "## Files to create\n- `impl2.py`"
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "pass"
        assert len(result.get("failures", [])) == 0

    def test_prose_mention_of_ac_heading_is_not_parsed_as_the_section(self):
        """A mid-line prose mention of the AC heading must not be read as the section.

        The AC-section regex is anchored to the start of a line. Without that
        anchor, the inline "## Acceptance criteria" below is matched first and the
        decoy id in that prose (AC-99) is read as the requirement set — masking the
        real AC-01/AC-02 section, which no task covers AC-99, so coverage fails.
        With the anchor, only the real heading is parsed and the breakdown passes.
        """
        spec = """## Overview
This spec discusses the ## Acceptance criteria AC-99 only in passing.

## Acceptance criteria
- AC-01: First requirement
- AC-02: Second requirement
"""
        manifest = {
            "category": "feature",
            "tasks": [
                {
                    "id": "task-01",
                    "title": "Test AC-01",
                    "file": "task-01.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-02",
                    "title": "Test AC-02",
                    "file": "task-02.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-02"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-03",
                    "title": "Implement AC-01",
                    "file": "task-03.md",
                    "type": "implementation",
                    "wave_id": 2,
                    "dependencies": ["task-01"],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-04",
                    "title": "Implement AC-02",
                    "file": "task-04.md",
                    "type": "implementation",
                    "wave_id": 2,
                    "dependencies": ["task-02"],
                    "covers": ["AC-02"],
                    "model": "Haiku",
                    "status": "pending"
                }
            ]
        }
        tfiles = {
            "task-01.md": "## Files to create\n- `test1.py`",
            "task-02.md": "## Files to create\n- `test2.py`",
            "task-03.md": "## Files to create\n- `impl1.py`",
            "task-04.md": "## Files to create\n- `impl2.py`"
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "pass"
        assert len(result.get("failures", [])) == 0


class TestSliceShapeAwareness:
    """Tests for slice-shape-aware breakdown gate checks (AC-05)."""

    def test_cross_cutting_test_only_slice_passes(self):
        """Cross-cutting slice with test-only task passes — no impl task required for AC."""
        spec = make_minimal_spec(["AC-01"])
        manifest = make_cross_cutting_manifest("AC-01")
        tfiles = {
            "task-01.md": "## Files to create\n- `test_ac01.py`",
            **MANIFEST_ENTRY
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "pass"

    def test_contract_preserving_impl_without_new_test_passes(self):
        """Contract-preserving impl task with no new test task passes — locks existing tests."""
        spec = make_minimal_spec(["AC-01"])
        manifest = make_contract_preserving_manifest("AC-01")
        tfiles = {
            "task-01.md": (
                "## Files to create\n- `impl.py`\n\n"
                "Locks existing tests; no new test task needed (contract-preserving slice)."
            ),
            **MANIFEST_ENTRY
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "pass"

    def test_contract_evolving_missing_retired_tests_list_fails(self):
        """Contract-evolving slice without retired_tests list fails."""
        spec = make_minimal_spec(["AC-01"])
        manifest = {
            "category": "feature",
            "tasks": [
                {
                    "id": "task-01",
                    "title": "Test AC-01",
                    "file": "task-01-test.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "not_started",
                    "slice_shape": "contract-evolving"
                },
                {
                    "id": "task-02",
                    "title": "Impl contract-evolving AC-01",
                    "file": "task-02-impl.md",
                    "type": "implementation",
                    "wave_id": 2,
                    "dependencies": ["task-01"],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "not_started",
                    "slice_shape": "contract-evolving"
                }
            ]
        }
        tfiles = {
            "task-01-test.md": "## Files to create\n- `test_ac01.py`",
            "task-02-impl.md": "## Files to create\n- `impl.py`",
            **MANIFEST_ENTRY
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "fail"
        assert any(
            "retired" in f.lower() or "contract-evolving" in f.lower()
            for f in result["failures"]
        )

    def test_contract_evolving_with_retired_tests_passes(self):
        """Contract-evolving slice with retired_tests list present passes.

        The fixture carries both a test task and an impl task because a contract-evolving
        slice always carries test work: the contract is the edge of the function, so
        changing it adds an optional argument, adds a required one, or removes one, and
        every such change either breaks an existing test or needs a new one. This fixture
        was previously impl-only and passed, which recorded that gap as intended behavior.
        """
        spec = make_minimal_spec(["AC-01"])
        retired = [{"file": "test_old.py", "rationale": "API changed"}]
        manifest = {
            "category": "testing-infrastructure",
            "tasks": [
                {
                    "id": "task-01",
                    "title": "Test evolved contract AC-01",
                    "file": "task-01.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "not_started",
                    "slice_shape": "contract-evolving",
                    "retired_tests": retired
                },
                {
                    "id": "task-02",
                    "title": "Impl contract-evolving AC-01",
                    "file": "task-02.md",
                    "type": "implementation",
                    "wave_id": 2,
                    "dependencies": ["task-01"],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "not_started",
                    "slice_shape": "contract-evolving",
                    "retired_tests": retired
                }
            ]
        }
        tfiles = {
            "task-01.md": "## Files to create\n- `test_evolved.py`",
            "task-02.md": "## Files to create\n- `impl.py`",
            **MANIFEST_ENTRY
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "pass", result.get("failures")

    def test_cross_cutting_with_impl_task_fails(self):
        """Cross-cutting slice that also includes an impl task fails — cross-cutting forbids impl tasks."""
        spec = make_minimal_spec(["AC-01"])
        manifest = {
            "category": "feature",
            "tasks": [
                {
                    "id": "task-01",
                    "title": "Test cross-cutting AC",
                    "file": "task-01-test.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "not_started",
                    "slice_shape": "cross-cutting"
                },
                {
                    "id": "task-02",
                    "title": "Impl cross-cutting AC",
                    "file": "task-02-impl.md",
                    "type": "implementation",
                    "wave_id": 2,
                    "dependencies": ["task-01"],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "not_started",
                    "slice_shape": "cross-cutting"
                }
            ]
        }
        tfiles = {
            "task-01-test.md": "## Files to create\n- `test_ac01.py`",
            "task-02-impl.md": "## Files to create\n- `impl.py`",
            **MANIFEST_ENTRY
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "fail"
        assert any(
            "cross-cutting" in f.lower() and "impl" in f.lower()
            for f in result["failures"]
        )

    def test_slices_breakdown_missing_test_lock_manifest_fails(self):
        """Slices-bearing breakdown with no test-hashes.json fails — pre-lock verdict not accepted."""
        spec = make_minimal_spec(["AC-01"])
        manifest = make_cross_cutting_manifest("AC-01")
        tfiles = {
            "task-01.md": "## Files to create\n- `test_ac01.py`"
            # no MANIFEST_ENTRY — intentionally absent
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "fail"
        assert any(
            "test-lock manifest" in f.lower()
            or "test-hashes.json" in f.lower()
            or "pre-lock" in f.lower()
            for f in result["failures"]
        )


class TestBounceBackMarkerDetection:
    """Tests for bounce-back marker detection in task file bodies (AC-06)."""

    def test_unresolved_bounce_back_in_task_file_fails(self):
        """Task file containing an unresolved BOUNCE-BACK marker causes gate failure."""
        spec = """## Acceptance criteria
- AC-01: Requirement 1
"""
        manifest = {
            "category": "feature",
            "tasks": [
                {
                    "id": "task-01",
                    "title": "Test AC-01",
                    "file": "task-01.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-02",
                    "title": "Implement AC-01",
                    "file": "task-02.md",
                    "type": "implementation",
                    "wave_id": 2,
                    "dependencies": ["task-01"],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                }
            ]
        }
        tfiles = {
            "task-01.md": "## Files to create\n- `test.py`",
            "task-02.md": (
                "## Files to create\n- `impl.py`\n\n"
                "<!-- BOUNCE-BACK: spec section X is under-specified -->"
            )
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "fail"
        assert any(
            "bounce" in f.lower() or "BOUNCE-BACK" in f
            for f in result["failures"]
        )

    def test_no_bounce_back_marker_passes(self):
        """Valid breakdown with no BOUNCE-BACK markers passes."""
        spec = """## Acceptance criteria
- AC-01: Requirement 1
"""
        manifest = {
            "category": "feature",
            "tasks": [
                {
                    "id": "task-01",
                    "title": "Test AC-01",
                    "file": "task-01.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-02",
                    "title": "Implement AC-01",
                    "file": "task-02.md",
                    "type": "implementation",
                    "wave_id": 2,
                    "dependencies": ["task-01"],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                }
            ]
        }
        tfiles = {
            "task-01.md": "## Files to create\n- `test.py`",
            "task-02.md": "## Files to create\n- `impl.py`"
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "pass"




class TestShapedCoverageInvariants:
    """Shape-aware coverage checks.

    When every task covering an AC carries a slice_shape, the gate replaces its generic
    has_test/has_impl checks with shape-specific ones. Only the cross-cutting invariant was
    ever written, so new-contract, contract-evolving, and contract-preserving ACs were
    checked for neither a test task nor an implementation task. These tests pin the
    per-shape work-unit structure each slice-shape document declares.
    """

    @staticmethod
    def _task(tid, ttype, ac, shape, **extra):
        task = {
            "id": tid,
            "title": f"{ttype} {ac}",
            "file": f"{tid}.md",
            "type": ttype,
            "wave_id": 1 if ttype == "test" else 2,
            "dependencies": [],
            "covers": [ac],
            "model": "Haiku",
            "status": "not_started",
            "slice_shape": shape,
        }
        task.update(extra)
        return task

    @staticmethod
    def _tfiles(*tids):
        return {f"{t}.md": "## Files to create\n- `f.py`" for t in tids} | MANIFEST_ENTRY

    def test_new_contract_without_impl_task_fails(self):
        """new-contract produces a test task AND an impl task — a test task alone is incomplete."""
        spec = make_minimal_spec(["AC-01"])
        manifest = {"category": "feature", "tasks": [
            self._task("task-01", "test", "AC-01", "new-contract"),
        ]}
        result = validate_breakdown(spec, manifest, self._tfiles("task-01"))
        assert result["result"] == "fail"
        assert any(
            "new-contract" in f and "AC-01" in f and "implementation" in f.lower()
            for f in result["failures"]
        ), result["failures"]

    def test_new_contract_without_test_task_fails(self):
        """new-contract introduces behavior that does not exist yet — it requires a red test."""
        spec = make_minimal_spec(["AC-01"])
        manifest = {"category": "feature", "tasks": [
            self._task("task-01", "implementation", "AC-01", "new-contract"),
        ]}
        result = validate_breakdown(spec, manifest, self._tfiles("task-01"))
        assert result["result"] == "fail"
        assert any(
            "new-contract" in f and "AC-01" in f and "test" in f.lower()
            for f in result["failures"]
        ), result["failures"]

    def test_new_contract_with_test_and_impl_passes(self):
        """The complete new-contract pairing passes."""
        spec = make_minimal_spec(["AC-01"])
        manifest = {"category": "feature", "tasks": [
            self._task("task-01", "test", "AC-01", "new-contract"),
            self._task("task-02", "implementation", "AC-01", "new-contract"),
        ]}
        result = validate_breakdown(spec, manifest, self._tfiles("task-01", "task-02"))
        assert result["result"] == "pass", result.get("failures")

    def test_contract_evolving_without_impl_task_fails(self):
        """contract-evolving produces new test tasks AND an impl task."""
        spec = make_minimal_spec(["AC-01"])
        manifest = {"category": "feature", "tasks": [
            self._task("task-01", "test", "AC-01", "contract-evolving",
                       retired_tests=[{"file": "test_old.py", "rationale": "API changed"}]),
        ]}
        result = validate_breakdown(spec, manifest, self._tfiles("task-01"))
        assert result["result"] == "fail"
        assert any(
            "contract-evolving" in f and "AC-01" in f and "implementation" in f.lower()
            for f in result["failures"]
        ), result["failures"]

    def test_contract_evolving_without_test_task_fails(self):
        """contract-evolving always carries test work.

        The contract is the edge of the function: changing it adds an optional argument,
        adds a required one, or removes one. Every such change either breaks an existing
        test or needs a new one, so a contract-evolving slice with no test task is retiring
        coverage without replacing it.
        """
        spec = make_minimal_spec(["AC-01"])
        manifest = {"category": "feature", "tasks": [
            self._task("task-01", "implementation", "AC-01", "contract-evolving",
                       retired_tests=[{"file": "test_old.py", "rationale": "API changed"}]),
        ]}
        result = validate_breakdown(spec, manifest, self._tfiles("task-01"))
        assert result["result"] == "fail"
        assert any(
            "contract-evolving" in f and "AC-01" in f and "test" in f.lower()
            for f in result["failures"]
        ), result["failures"]

    def test_contract_preserving_without_impl_task_fails(self):
        """contract-preserving produces an impl task only — a test task alone cannot satisfy it."""
        spec = make_minimal_spec(["AC-01"])
        manifest = {"category": "feature", "tasks": [
            self._task("task-01", "test", "AC-01", "contract-preserving"),
        ]}
        result = validate_breakdown(spec, manifest, self._tfiles("task-01"))
        assert result["result"] == "fail"
        assert any(
            "contract-preserving" in f and "AC-01" in f and "implementation" in f.lower()
            for f in result["failures"]
        ), result["failures"]

    def test_corrective_category_exempt_from_impl_requirement(self):
        """The corrective-category exemption from the impl requirement survives the shaped path."""
        spec = make_minimal_spec(["AC-01"])
        manifest = {"category": "corrective", "tasks": [
            self._task("task-01", "test", "AC-01", "new-contract"),
        ]}
        result = validate_breakdown(spec, manifest, self._tfiles("task-01"))
        assert result["result"] == "pass", result.get("failures")
