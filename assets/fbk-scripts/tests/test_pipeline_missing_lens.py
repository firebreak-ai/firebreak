"""
Tests for load_lens_matrix() loud-failure behavior (AC-06).

An unresolvable lens path must raise a named exception whose message contains
the missing path string. Silent fallback to generic behavior is forbidden.

These cases live in their own file so they do not race task-02's edits to
test_pipeline.py in the same wave.
"""
import pytest

try:
    from fbk.pipeline import load_lens_matrix, LensVocabulary  # type: ignore[import]
    _LOAD_LENS_IMPORTABLE = True
except ImportError:
    _LOAD_LENS_IMPORTABLE = False


@pytest.mark.skipif(
    not _LOAD_LENS_IMPORTABLE,
    reason="load_lens_matrix not yet implemented — red-phase skip",
)
class TestMissingLensLoudFailure:
    """load_lens_matrix() raises a named exception when the lens path does not exist."""

    def test_missing_lens_path_raises_named_error(self, tmp_path):
        """Unresolvable lens path raises an exception whose message names the path."""
        missing_path = tmp_path / "fbk-review-lenses" / "nonexistent-lens.md"

        with pytest.raises(Exception) as exc_info:
            load_lens_matrix(str(missing_path))

        assert "nonexistent-lens.md" in str(exc_info.value), (
            f"Expected exception message to contain 'nonexistent-lens.md', "
            f"got: {exc_info.value!r}"
        )

    def test_missing_lens_does_not_return_default_vocabulary(self, tmp_path):
        """load_lens_matrix on a missing path raises — no silent fallback to a default vocabulary.

        The pytest.raises context enforces that an exception is raised; no LensVocabulary
        is silently returned.  This test documents the no-silent-fallback contract from AC-06.
        """
        missing_path = tmp_path / "fbk-review-lenses" / "nonexistent-lens.md"

        with pytest.raises(Exception):
            load_lens_matrix(str(missing_path))
            # Unreachable: if we reach this line the loader returned a value
            # instead of raising, which violates the no-silent-fallback contract.
            pytest.fail(  # pragma: no cover
                "load_lens_matrix returned without raising — silent fallback is forbidden"
            )
