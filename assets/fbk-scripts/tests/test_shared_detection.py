"""Structural single-source-of-truth tests for the test-integrity audit.

Asserts that after the Wave 1 migration (task-28):

- The test-integrity audit lives exclusively in ``shared-detection.md``.
- The audit section heading is no longer present in the donor file
  ``detection-audits.md`` (the migration was a move, not a copy).
- Both ``code-lens.md`` and ``test-lens.md`` reference the audit by name
  (the filename token ``shared-detection``) and do not re-embed its body.
- No lens file contains ``AUDIT_HEADING`` as inline body content — each
  references the audit by name, none duplicates it verbatim.

Covers AC-14 (single-source-of-truth for the test-integrity audit; no shared
block duplicated across lenses).
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Repo layout
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parents[3]

_SDL_WORKFLOW = _REPO_ROOT / "assets" / "fbk-docs" / "fbk-sdl-workflow"
_REVIEW_LENSES = _REPO_ROOT / "assets" / "fbk-docs" / "fbk-review-lenses"

_DETECTION_AUDITS_MD = _SDL_WORKFLOW / "detection-audits.md"
_SHARED_DETECTION_MD = _REVIEW_LENSES / "shared-detection.md"
_CODE_LENS_MD = _REVIEW_LENSES / "code-lens.md"
_TEST_LENS_MD = _REVIEW_LENSES / "test-lens.md"

# The seven lens files.  Each ends in ``-lens.md``; ``shared-detection.md``,
# ``review-loop.md``, and ``lens-format.md`` are infrastructure, not lenses.
_LENS_FILES = [
    _REVIEW_LENSES / "code-lens.md",
    _REVIEW_LENSES / "coherence-lens.md",
    _REVIEW_LENSES / "doc-reconcile-lens.md",
    _REVIEW_LENSES / "fresh-eyes-lens.md",
    _REVIEW_LENSES / "quality-lens.md",
    _REVIEW_LENSES / "task-lens.md",
    _REVIEW_LENSES / "test-lens.md",
]

# ---------------------------------------------------------------------------
# Structural anchors
#
# AUDIT_HEADING: the exact section heading of the test-integrity audit in
#   ``shared-detection.md``.  The implementing agent moves the section under
#   this heading verbatim; we pin it here so the test is coupling-free with
#   respect to body prose but catches any renaming of the heading.
#
# RETAINED_HEADING: a section heading that must stay in ``detection-audits.md``
#   after the migration.  Together with the AUDIT_HEADING absence check this
#   proves the migration was a targeted move, not a wholesale deletion of the
#   donor file.
# ---------------------------------------------------------------------------

AUDIT_HEADING = "## Test-integrity audit"
RETAINED_HEADING = "## Consistency audit"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read(path: Path) -> str:
    """Return file text.  Raises FileNotFoundError on red-phase when absent."""
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAuditPresentInSharedDetection:
    """The test-integrity audit now lives in ``shared-detection.md``."""

    def test_audit_present_in_shared_detection(self):
        """shared-detection.md exists and contains the test-integrity audit heading."""
        text = _read(_SHARED_DETECTION_MD)
        assert AUDIT_HEADING in text, (
            f"shared-detection.md must contain the heading {AUDIT_HEADING!r}; "
            "either the file is missing the section or the heading text changed"
        )


class TestAuditAbsentFromDetectionAudits:
    """The test-integrity audit heading no longer appears in the donor file."""

    def test_audit_absent_from_detection_audits(self):
        """detection-audits.md does not contain AUDIT_HEADING after migration."""
        text = _read(_DETECTION_AUDITS_MD)
        assert AUDIT_HEADING not in text, (
            f"detection-audits.md still contains {AUDIT_HEADING!r}; "
            "the test-integrity audit section must be removed from the donor "
            "file — it now lives exclusively in shared-detection.md"
        )

    def test_retained_audit_still_present_in_detection_audits(self):
        """detection-audits.md still contains a retained audit heading (proves a move, not deletion)."""
        text = _read(_DETECTION_AUDITS_MD)
        assert RETAINED_HEADING in text, (
            f"detection-audits.md must still contain {RETAINED_HEADING!r}; "
            "if it is missing the donor file was deleted or over-trimmed rather "
            "than surgically migrating only the test-integrity audit"
        )


class TestCodeLensReferencesAuditByName:
    """code-lens.md references the test-integrity audit by filename, not re-embedded body."""

    def test_code_lens_references_audit_by_name(self):
        """code-lens.md contains the token 'shared-detection' (filename reference)."""
        text = _read(_CODE_LENS_MD)
        assert "shared-detection" in text, (
            "code-lens.md must reference the test-integrity audit by filename "
            "('shared-detection') rather than re-embedding or omitting it"
        )

    def test_code_lens_does_not_embed_audit_heading(self):
        """code-lens.md does not contain the full AUDIT_HEADING inline (it references, not re-embeds)."""
        text = _read(_CODE_LENS_MD)
        assert AUDIT_HEADING not in text, (
            f"code-lens.md must not contain {AUDIT_HEADING!r} as inline body content; "
            "the lens should reference shared-detection.md by name, not re-embed the section"
        )


class TestTestLensReferencesAuditByName:
    """test-lens.md references the test-integrity audit by filename, not re-embedded body."""

    def test_test_lens_references_audit_by_name(self):
        """test-lens.md contains the token 'shared-detection' (filename reference)."""
        text = _read(_TEST_LENS_MD)
        assert "shared-detection" in text, (
            "test-lens.md must reference the test-integrity audit by filename "
            "('shared-detection') rather than re-embedding or omitting it"
        )

    def test_test_lens_does_not_embed_audit_heading(self):
        """test-lens.md does not contain the full AUDIT_HEADING inline (it references, not re-embeds)."""
        text = _read(_TEST_LENS_MD)
        assert AUDIT_HEADING not in text, (
            f"test-lens.md must not contain {AUDIT_HEADING!r} as inline body content; "
            "the lens should reference shared-detection.md by name, not re-embed the section"
        )


class TestNoSharedBlockDuplicatedAcrossLenses:
    """No lens file re-embeds the test-integrity audit heading inline."""

    def test_no_shared_block_duplicated_across_lenses(self):
        """The count of lens files whose body contains AUDIT_HEADING is zero.

        Each lens references the audit by name via 'shared-detection'; none
        duplicates the section heading (and therefore the body) verbatim.
        """
        lenses_with_embedded_heading = [
            lens.name
            for lens in _LENS_FILES
            if lens.exists() and AUDIT_HEADING in _read(lens)
        ]
        assert len(lenses_with_embedded_heading) == 0, (
            f"The following lens files contain {AUDIT_HEADING!r} as inline content "
            f"(expected 0): {lenses_with_embedded_heading}. "
            "Each lens must reference the audit from shared-detection.md by name, "
            "not re-embed it."
        )
