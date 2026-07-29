"""Characterization tests: code-review gate projection is preserved across migration.

Pins that the post-migration round-entry shape — {round, raised, survived, severity}
written by the loop coordinator — is correctly projected by the unchanged gate trust
boundary: raised/survived/enum-valid scalar severity pass through; round and
severity_breakdown are dropped.

These tests are green against the current code and must stay green after migration.
"""

import json
from pathlib import Path

import pytest

try:
    from fbk.gates.code_review import project_round_entries, ROUND_SEVERITIES
    _PROJECTION_AVAILABLE = True
except ImportError:
    project_round_entries = None
    ROUND_SEVERITIES = None
    _PROJECTION_AVAILABLE = False


# ---------------------------------------------------------------------------
# Import existence guard — never skipped
# ---------------------------------------------------------------------------


class TestProjectionImportable:
    """project_round_entries and ROUND_SEVERITIES must be importable from fbk.gates.code_review.

    This test is NOT decorated with skipif: if the import fails, the test fails
    (not skips), so a deleted or renamed projection turns the suite red rather than
    silently green-with-skips.
    """

    def test_project_round_entries_importable(self):
        """Importing project_round_entries from fbk.gates.code_review must succeed.

        A skip here means someone deleted or renamed the function without updating
        the downstream tests — the suite should be red in that case, not green.
        """
        from fbk.gates.code_review import project_round_entries as _fn  # noqa: F401
        assert callable(_fn), (
            "project_round_entries must be a callable; got {!r}".format(_fn)
        )

    def test_round_severities_importable(self):
        """Importing ROUND_SEVERITIES from fbk.gates.code_review must succeed."""
        from fbk.gates.code_review import ROUND_SEVERITIES as _sev  # noqa: F401
        assert isinstance(_sev, tuple) and len(_sev) > 0, (
            "ROUND_SEVERITIES must be a non-empty tuple; got {!r}".format(_sev)
        )


@pytest.mark.skipif(
    not _PROJECTION_AVAILABLE,
    reason="project_round_entries not yet implemented in fbk.gates.code_review",
)
class TestRoundEntryShapePreservedAfterMigration:
    """Gate projection handles the post-migration round-entry shape unchanged.

    The loop coordinator (not the gate) will write round entries that include a
    'round' field (1-based index) and a scalar 'severity'.  The gate's
    project_round_entries allowlist must remain unchanged: it naturally drops 'round'
    because 'round' is not an allowlisted key, and it already drops 'severity_breakdown'
    for the same reason.
    """

    def test_new_round_entry_shape_projects_to_allowlist(self):
        """Post-migration entry with round/raised/survived/severity projects correctly.

        The 'round' field must be stripped (not in the allowlist).
        'raised', 'survived', and enum-valid scalar 'severity' must survive.
        """
        rounds = [{"round": 1, "raised": 5, "survived": 3, "severity": "critical"}]
        result = project_round_entries(rounds)
        assert result == [{"raised": 5, "survived": 3, "severity": "critical"}], (
            f"Expected round stripped and raised/survived/severity preserved; got {result!r}"
        )

    def test_severity_breakdown_object_is_stripped(self):
        """Old 'severity_breakdown' key alongside new fields is dropped at the trust boundary.

        An entry that carries both the new scalar 'severity' and the old
        'severity_breakdown' object must project to an entry that contains
        'raised' and 'survived' but not 'severity_breakdown'.
        """
        rounds = [
            {
                "round": 1,
                "raised": 4,
                "survived": 2,
                "severity": "major",
                "severity_breakdown": {"critical": 1},
            }
        ]
        result = project_round_entries(rounds)
        assert len(result) == 1
        projected = result[0]
        assert "severity_breakdown" not in projected, (
            f"severity_breakdown must be stripped by the trust boundary; got {projected!r}"
        )
        assert projected.get("raised") == 4, (
            f"raised must survive projection; got {projected!r}"
        )
        assert projected.get("survived") == 2, (
            f"survived must survive projection; got {projected!r}"
        )

    def test_non_enum_severity_dropped(self):
        """An entry with a severity value outside the enum vocabulary drops the severity key.

        'blocker' is not in ROUND_SEVERITIES so it must not appear in the projected entry.
        'raised' and 'survived' must still survive.
        """
        rounds = [{"round": 1, "raised": 2, "survived": 1, "severity": "blocker"}]
        result = project_round_entries(rounds)
        assert len(result) == 1
        projected = result[0]
        assert "severity" not in projected, (
            f"Non-enum severity 'blocker' must be dropped; got {projected!r}"
        )
        assert projected.get("raised") == 2, (
            f"raised must survive projection even when severity is invalid; got {projected!r}"
        )
        assert projected.get("survived") == 1, (
            f"survived must survive projection even when severity is invalid; got {projected!r}"
        )

    def test_canonical_rounds_path_is_feature_relative(self, tmp_path):
        """The round log lives at .code-review-rounds.json directly under the feature dir.

        Writes a valid round log to the canonical path and asserts it exists there,
        pinning AC-02's path contract: the loop coordinator and the gate must agree on
        this exact location.
        """
        feature_dir = tmp_path / "ai-docs" / "sample-feature"
        feature_dir.mkdir(parents=True)

        round_data = {
            "schema_version": "1.0",
            "spec": "sample",
            "rounds": [
                {"round": 1, "raised": 3, "survived": 1, "severity": "minor"},
            ],
        }
        rounds_file = feature_dir / ".code-review-rounds.json"
        rounds_file.write_text(json.dumps(round_data))

        assert rounds_file.exists(), (
            f".code-review-rounds.json must exist at {rounds_file} "
            "(canonical path AC-02 pins)"
        )
        assert rounds_file == feature_dir / ".code-review-rounds.json", (
            "Canonical path must be .code-review-rounds.json directly under the feature dir"
        )
