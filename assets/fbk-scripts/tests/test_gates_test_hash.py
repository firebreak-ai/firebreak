"""Tests for fbk.gates.test_hash manifest creation and modification detection."""

import json
import pytest
from pathlib import Path
from fbk.gates.test_hash import compute_hashes, create_manifest, verify_manifest


class TestComputeHashesAndCreateManifest:
    """Tests for hash computation and manifest creation."""

    def test_first_run_creates_manifest_with_correct_structure(self, tmp_path):
        """First run creates manifest with correct file count and 64-char hex hashes."""
        # Create test files
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_alpha.py").write_text("# test alpha\n")
        (test_dir / "test_beta.py").write_text("# test beta\n")
        (test_dir / "test_gamma.py").write_text("# test gamma\n")

        # Create manifest
        manifest_path = tmp_path / "test-hashes.json"
        create_manifest(tmp_path, manifest_path)

        # Assert manifest exists and has correct structure
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text())

        files = manifest.get("files", {})
        assert len(files) == 3, f"Expected 3 files, got {len(files)}"

        # Check all hashes are 64-char hex strings
        for path, hash_value in files.items():
            assert len(hash_value) == 64, f"Hash for {path} is {len(hash_value)} chars, expected 64"
            assert all(c in "0123456789abcdef" for c in hash_value), f"Hash for {path} is not hex"

    def test_no_change_verification_passes(self, tmp_path):
        """Verification with no changes returns 'pass'."""
        # Create test files
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_one.py").write_text("# test one\n")

        # Create manifest
        manifest_path = tmp_path / "test-hashes.json"
        create_manifest(tmp_path, manifest_path)

        # Verify with no changes
        result = verify_manifest(tmp_path, manifest_path)
        assert result == "pass"

    def test_modified_file_detected(self, tmp_path):
        """Verification detects modified files with MODIFIED error."""
        # Create test files
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_file.py").write_text("# original content\n")

        # Create manifest
        manifest_path = tmp_path / "test-hashes.json"
        create_manifest(tmp_path, manifest_path)

        # Modify file
        (test_dir / "test_file.py").write_text("# modified content\n")

        # Verify detects modification
        result = verify_manifest(tmp_path, manifest_path)
        assert "MODIFIED" in result

    def test_deleted_file_detected(self, tmp_path):
        """Verification detects deleted files with MISSING error."""
        # Create test files
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_to_delete.py").write_text("# will be deleted\n")

        # Create manifest
        manifest_path = tmp_path / "test-hashes.json"
        create_manifest(tmp_path, manifest_path)

        # Delete file
        (test_dir / "test_to_delete.py").unlink()

        # Verify detects deletion
        result = verify_manifest(tmp_path, manifest_path)
        assert "MISSING" in result

    def test_unexpected_new_file_detected(self, tmp_path):
        """Verification detects new unexpected files with UNEXPECTED error."""
        # Create test files
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_original.py").write_text("# original\n")

        # Create manifest
        manifest_path = tmp_path / "test-hashes.json"
        create_manifest(tmp_path, manifest_path)

        # Add new file
        (test_dir / "test_new.py").write_text("# unexpected new file\n")

        # Verify detects new file
        result = verify_manifest(tmp_path, manifest_path)
        assert "UNEXPECTED" in result

    def test_empty_directory_passes_gracefully(self, tmp_path):
        """Empty directory with no test files passes with files: 0."""
        # Create manifest on empty directory
        manifest_path = tmp_path / "test-hashes.json"
        create_manifest(tmp_path, manifest_path)

        # Assert manifest exists and has no files
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text())

        files = manifest.get("files", {})
        assert len(files) == 0, f"Expected 0 files, got {len(files)}"

        # Verify passes
        result = verify_manifest(tmp_path, manifest_path)
        assert result == "pass"
