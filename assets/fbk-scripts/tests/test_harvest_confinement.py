"""Integration tests for fbk.harvest — realpath-confined write and distinct temp names.

Tests cover:
- Confined-write happy path: record lands under the realpath of .fbk-capture/runs/
- Symlink-refusal: a symlinked runs/ redirect is refused (no write, error set)
- Distinct temp names: two different unfinalized runs produce distinct temp names,
  each embedding the process id and a uuid component; no temp residue after harvest

All tests use real filesystem symlinks via tmp_path and real gate_check._real_capture_dir.
No stand-ins for code we own; os.replace is monkeypatched only to observe the temp-name
argument — a collaborator we do not own that would otherwise hide the temp-name value.
"""

import os
import re
import pytest

try:
    from fbk import harvest
    HARVEST_AVAILABLE = True
except ImportError:
    HARVEST_AVAILABLE = False

from tests import capture_fixtures

pytestmark = pytest.mark.skipif(
    not HARVEST_AVAILABLE,
    reason="fbk.harvest module not yet implemented",
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

_CAPTURE_CFG_REL = ".fbk-capture/capture.cfg"
_RUNS_REL = ".fbk-capture/runs"


def _make_instrumented_project(base, name="project"):
    """Build a minimal instrumented project with capture_level=standard under base.

    Returns the project root path.  Creates:
      .fbk-capture/capture.cfg   (capture_level=standard)
      .fbk-capture/runs/         (real directory)
    """
    root = os.path.join(base, name)
    os.makedirs(root, exist_ok=True)

    cfg_path = os.path.join(root, _CAPTURE_CFG_REL)
    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
    with open(cfg_path, "w") as fh:
        fh.write("capture_level=standard\n")

    runs_dir = os.path.join(root, _RUNS_REL)
    os.makedirs(runs_dir, exist_ok=True)

    return root


def _make_workflow_run_unfinalized(projects_root, run_id, project_name="proj"):
    """Build a workflow-run directory without a result line (unfinalized).

    The journal contains only a 'started' entry so the run looks open to harvest.
    Returns the run directory path.
    """
    return capture_fixtures.make_workflow_run(
        projects_root=projects_root,
        run_id=run_id,
        agents=[
            {
                "agent_id": "agent-a",
                "first_message": '<!--fbk-attr {"cardinality": "single", "stance": "collaborative"}-->',
                "turns": [],
                "result": None,  # no result line → unfinalized
            }
        ],
        project_hash=project_name,
        session_uuid="sess-001",
    )


# ---------------------------------------------------------------------------
# Confined-write happy path
# ---------------------------------------------------------------------------


class TestConfinedWriteHappyPath:
    """harvest() writes the run record under the realpath of .fbk-capture/runs/."""

    def test_record_lands_under_realpath_capture_dir(self, tmp_path, monkeypatch):
        """A normal harvest writes exactly one record inside the confined capture dir."""
        projects_root = tmp_path / "projects"
        projects_root.mkdir()
        project_root = _make_instrumented_project(str(tmp_path), name="proj")

        run_id = "run-happy-001"
        _make_workflow_run_unfinalized(str(projects_root), run_id, project_name="proj")

        monkeypatch.setenv("FBK_PROJECTS_ROOT", str(projects_root))

        result = harvest.harvest(run_id, project_root)

        real_capture = os.path.realpath(os.path.join(project_root, ".fbk-capture"))
        expected_record = os.path.join(real_capture, "runs", f"{run_id}.json")

        assert result.error is None, f"Expected no error, got: {result.error!r}"
        assert os.path.isfile(expected_record), (
            f"Record not found at {expected_record}"
        )
        # Verify the record path is inside the realpath capture dir, not redirected.
        assert os.path.realpath(expected_record).startswith(real_capture + os.sep), (
            f"Record path {expected_record!r} escapes realpath capture dir {real_capture!r}"
        )


# ---------------------------------------------------------------------------
# Symlink-refusal
# ---------------------------------------------------------------------------


class TestSymlinkRefusal:
    """harvest() refuses to write when runs/ is a symlink pointing outside the project."""

    def test_symlinked_runs_dir_is_refused(self, tmp_path, monkeypatch):
        """A symlinked runs/ produces no record at the redirect target and sets result.error."""
        projects_root = tmp_path / "projects"
        projects_root.mkdir()
        project_root = _make_instrumented_project(str(tmp_path), name="proj")

        # Create an outside-the-project redirect target directory.
        redirect_target = tmp_path / "outside-redirect"
        redirect_target.mkdir()

        # Replace the real runs/ with a symlink to the outside target.
        runs_dir = os.path.join(project_root, _RUNS_REL)
        os.rmdir(runs_dir)
        os.symlink(str(redirect_target), runs_dir)

        run_id = "run-symlink-001"
        _make_workflow_run_unfinalized(str(projects_root), run_id, project_name="proj")

        monkeypatch.setenv("FBK_PROJECTS_ROOT", str(projects_root))

        result = harvest.harvest(run_id, project_root)

        # Assert the write was refused: no record at the symlink target.
        redirect_contents = list(redirect_target.iterdir())
        assert redirect_contents == [], (
            f"Expected no record written to redirect target, found: {redirect_contents}"
        )
        # Assert error was reported.
        assert result.error, (
            "Expected result.error to be truthy when runs/ is a symlink redirect"
        )


# ---------------------------------------------------------------------------
# Distinct temp names across two different unfinalized runs
# ---------------------------------------------------------------------------


class TestDistinctTempNames:
    """harvest() uses a distinct per-writer temp name for each write."""

    def test_two_runs_produce_distinct_pid_uuid_temp_names_and_no_residue(
        self, tmp_path, monkeypatch
    ):
        """Two different unfinalized runs yield distinct temp names; each embeds pid and a uuid
        component; no temp-named files remain in runs/ after both harvests complete.
        """
        projects_root = tmp_path / "projects"
        projects_root.mkdir()
        project_root = _make_instrumented_project(str(tmp_path), name="proj")

        run_id_a = "run-temp-a"
        run_id_b = "run-temp-b"
        _make_workflow_run_unfinalized(str(projects_root), run_id_a, project_name="proj")
        _make_workflow_run_unfinalized(str(projects_root), run_id_b, project_name="proj")

        monkeypatch.setenv("FBK_PROJECTS_ROOT", str(projects_root))

        # Intercept os.replace in the harvest module to record the source temp paths.
        # os.replace is an OS collaborator we do not own, so intercepting it is appropriate.
        captured_src_paths = []
        original_os_replace = harvest.os.replace  # type: ignore[attr-defined]

        def _capturing_replace(src, dst):
            captured_src_paths.append(src)
            original_os_replace(src, dst)

        monkeypatch.setattr(harvest.os, "replace", _capturing_replace)

        result_a = harvest.harvest(run_id_a, project_root)
        result_b = harvest.harvest(run_id_b, project_root)

        assert result_a.error is None, f"harvest of run A failed: {result_a.error!r}"
        assert result_b.error is None, f"harvest of run B failed: {result_b.error!r}"
        assert len(captured_src_paths) >= 2, (
            f"Expected at least 2 os.replace calls (one per run), got {len(captured_src_paths)}"
        )

        temp_name_a = os.path.basename(captured_src_paths[0])
        temp_name_b = os.path.basename(captured_src_paths[1])

        # The two temp names must be distinct.
        assert temp_name_a != temp_name_b, (
            f"Expected distinct temp names for two runs, both were {temp_name_a!r}"
        )

        pid_str = str(os.getpid())
        # UUID component: 32 hex chars or 8-4-4-4-12 with hyphens.
        uuid_pattern = re.compile(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
            r"|[0-9a-f]{32}",
            re.IGNORECASE,
        )

        assert pid_str in temp_name_a, (
            f"Temp name {temp_name_a!r} does not contain process id {pid_str!r}"
        )
        assert pid_str in temp_name_b, (
            f"Temp name {temp_name_b!r} does not contain process id {pid_str!r}"
        )
        assert uuid_pattern.search(temp_name_a), (
            f"Temp name {temp_name_a!r} does not contain a uuid-shaped component"
        )
        assert uuid_pattern.search(temp_name_b), (
            f"Temp name {temp_name_b!r} does not contain a uuid-shaped component"
        )

        # No temp residue: runs/ should contain only the two finalized .json records.
        runs_dir = os.path.join(project_root, _RUNS_REL)
        runs_contents = set(os.listdir(runs_dir))
        expected_records = {f"{run_id_a}.json", f"{run_id_b}.json"}
        leftover = runs_contents - expected_records
        assert not leftover, (
            f"Temp residue found in runs/: {leftover!r}"
        )
