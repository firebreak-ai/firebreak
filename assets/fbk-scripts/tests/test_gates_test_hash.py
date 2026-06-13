"""Tests for fbk.gates.test_hash manifest creation and modification detection."""

import json
from pathlib import Path
from fbk.gates.test_hash import compute_hashes, create_manifest, verify_manifest


class TestComputeHashesAndCreateManifest:
    """Tests for hash computation and manifest creation with per-entry object schema."""

    def test_first_run_creates_manifest_with_per_entry_objects(self, tmp_path):
        """First run creates manifest where each file entry is an object with sha256, slice, test-discipline."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_alpha.py").write_text("# test alpha\n")
        (test_dir / "test_beta.py").write_text("# test beta\n")

        manifest_path = tmp_path / "test-hashes.json"
        create_manifest(tmp_path, manifest_path)

        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text())
        files = manifest.get("files", {})
        assert len(files) == 2

        for path, value in files.items():
            assert isinstance(value, dict), f"Entry for {path} is not a dict"
            assert "sha256" in value, f"Entry for {path} missing 'sha256'"
            assert "slice" in value, f"Entry for {path} missing 'slice'"
            assert "test-discipline" in value, f"Entry for {path} missing 'test-discipline'"
            assert len(value["sha256"]) == 64, f"sha256 for {path} is not 64 chars"
            assert all(c in "0123456789abcdef" for c in value["sha256"]), f"sha256 for {path} is not hex"

    def test_no_change_verification_returns_empty_list(self, tmp_path):
        """Verification with no changes returns an empty list."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_one.py").write_text("# test one\n")

        manifest_path = tmp_path / "test-hashes.json"
        create_manifest(tmp_path, manifest_path)

        result = verify_manifest(tmp_path, manifest_path)
        assert result == []

    def test_modified_file_returns_modified_discrepancy(self, tmp_path):
        """Verification returns a discrepancy with kind 'modified' for a changed file.

        Also verifies that the return value is a list of dicts each carrying 'kind' and 'path',
        and that 'kind' is drawn from the allowed set {'modified', 'unexpected', 'missing'}.
        """
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_file.py").write_text("# original content\n")

        manifest_path = tmp_path / "test-hashes.json"
        create_manifest(tmp_path, manifest_path)

        (test_dir / "test_file.py").write_text("# modified content\n")

        result = verify_manifest(tmp_path, manifest_path)
        assert isinstance(result, list)
        assert len(result) > 0

        allowed_kinds = {"modified", "unexpected", "missing"}
        for item in result:
            assert isinstance(item, dict), f"Item is not a dict: {item}"
            assert "kind" in item, f"Item missing 'kind': {item}"
            assert "path" in item, f"Item missing 'path': {item}"
            assert item["kind"] in allowed_kinds, f"Unexpected kind value: {item['kind']}"

        assert any(item["kind"] == "modified" for item in result)

    def test_deleted_file_returns_missing_discrepancy(self, tmp_path):
        """Verification returns a discrepancy with kind 'missing' for a deleted file."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_to_delete.py").write_text("# will be deleted\n")

        manifest_path = tmp_path / "test-hashes.json"
        create_manifest(tmp_path, manifest_path)

        (test_dir / "test_to_delete.py").unlink()

        result = verify_manifest(tmp_path, manifest_path)
        assert any(item["kind"] == "missing" for item in result)

    def test_empty_directory_verify_returns_empty_list(self, tmp_path):
        """Empty directory produces a manifest and verifies clean."""
        manifest_path = tmp_path / "test-hashes.json"
        create_manifest(tmp_path, manifest_path)

        result = verify_manifest(tmp_path, manifest_path)
        assert result == []


class TestListDrivenLockMode:
    """Tests for create_manifest locked_files parameter."""

    def test_locked_pre_existing_file_appears_in_manifest(self, tmp_path):
        """A pre-existing file passed via locked_files appears in the manifest with the required keys."""
        existing_dir = tmp_path / "existing_tests"
        existing_dir.mkdir()
        locked_file = existing_dir / "test_existing.py"
        locked_file.write_text("# existing locked test\n")

        manifest_path = tmp_path / "test-hashes.json"
        create_manifest(tmp_path, manifest_path, locked_files=[str(locked_file)])

        manifest = json.loads(manifest_path.read_text())
        files = manifest.get("files", {})

        # At least one entry should correspond to the locked file
        matching = [k for k in files if "test_existing.py" in k]
        assert len(matching) == 1, f"Expected entry for test_existing.py, got keys: {list(files.keys())}"

        entry = files[matching[0]]
        assert "sha256" in entry
        assert "slice" in entry
        assert "test-discipline" in entry

    def test_locked_file_tamper_detected(self, tmp_path):
        """Modifying a locked pre-existing file is detected as a 'modified' discrepancy."""
        existing_dir = tmp_path / "existing_tests"
        existing_dir.mkdir()
        locked_file = existing_dir / "test_existing.py"
        locked_file.write_text("# original locked content\n")

        manifest_path = tmp_path / "test-hashes.json"
        create_manifest(tmp_path, manifest_path, locked_files=[str(locked_file)])

        locked_file.write_text("# tampered locked content\n")

        result = verify_manifest(tmp_path, manifest_path)
        assert any(item["kind"] == "modified" for item in result)


class TestShadowTestDetection:
    """Tests for unlisted-file detection scoped to locked directories."""

    def test_unlisted_file_in_locked_scope_flagged_as_shadow(self, tmp_path):
        """An unlisted test file inside a locked directory is flagged as 'unexpected'."""
        locked_dir = tmp_path / "locked_tests"
        locked_dir.mkdir()
        locked_file = locked_dir / "test_locked.py"
        locked_file.write_text("# locked test\n")

        manifest_path = tmp_path / "test-hashes.json"
        create_manifest(tmp_path, manifest_path, locked_files=[str(locked_file)])

        shadow_file = locked_dir / "test_shadow.py"
        shadow_file.write_text("# shadow test\n")

        result = verify_manifest(tmp_path, manifest_path)
        unexpected = [item for item in result if item["kind"] == "unexpected"]
        assert len(unexpected) > 0
        assert any("test_shadow.py" in item["path"] for item in unexpected)

    def test_unlisted_file_outside_locked_scope_not_flagged(self, tmp_path):
        """An unlisted test file outside any locked directory is NOT flagged as unexpected."""
        locked_dir = tmp_path / "locked_tests"
        locked_dir.mkdir()
        locked_file = locked_dir / "test_locked.py"
        locked_file.write_text("# locked test\n")

        manifest_path = tmp_path / "test-hashes.json"
        create_manifest(tmp_path, manifest_path, locked_files=[str(locked_file)])

        other_dir = tmp_path / "other_tests"
        other_dir.mkdir()
        (other_dir / "test_unrelated.py").write_text("# unrelated test outside scope\n")

        result = verify_manifest(tmp_path, manifest_path)
        unexpected = [item for item in result if item["kind"] == "unexpected"]
        assert len(unexpected) == 0, (
            f"Expected no unexpected items for file outside locked scope, got: {unexpected}"
        )

