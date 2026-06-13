"""Unit tests for fbk.capture.token_harvester — post-hoc stage token attribution.

Tests cover:
- Hard-split stage attribution on transition timestamps (strictly before → earlier stage;
  at-or-after → later stage)
- Missing or unreadable transcripts marked unavailable (never presented as 0)
- Cross-session aggregation: multiple transcript paths sum into one per-stage total set
- Per-stage boundary-adjacent turn count emission
"""

import os
import pytest

try:
    from fbk.capture import token_harvester
    TOKEN_HARVESTER_AVAILABLE = True
except ImportError:
    TOKEN_HARVESTER_AVAILABLE = False

from tests import capture_fixtures

pytestmark = pytest.mark.skipif(
    not TOKEN_HARVESTER_AVAILABLE,
    reason="fbk.capture.token_harvester module not yet implemented",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _transitions_from_timestamps(stage_timestamps):
    """Convert a stage_timestamps dict to the ordered list harvest() expects.

    stage_timestamps maps stage name → ISO-8601 string, in insertion order.
    Each entry becomes {"stage": name, "timestamp": iso_string}.
    """
    return [{"stage": k, "timestamp": v} for k, v in stage_timestamps.items()]


# ---------------------------------------------------------------------------
# Attribution tests
# ---------------------------------------------------------------------------


class TestTurnAttributionByStageBoundary:
    """harvest() attributes each turn to the stage active at its timestamp."""

    def test_turn_before_boundary_attributes_to_earlier_stage(self, tmp_path):
        """A turn strictly before T2 goes to IMPLEMENTING; at-or-after T2 goes to IMPLEMENTED."""
        # Two boundaries: IMPLEMENTING starts at T1, IMPLEMENTED starts at T2.
        stage_timestamps = {
            "IMPLEMENTING": "2026-01-01T00:00:00+00:00",
            "IMPLEMENTED":  "2026-01-01T01:00:00+00:00",
        }
        transitions = _transitions_from_timestamps(stage_timestamps)

        # Turn A: strictly before T2 (at T0:30) → goes to IMPLEMENTING
        # Turn B: at T2 exactly → goes to IMPLEMENTED
        transcript_path = str(tmp_path / "session.jsonl")
        capture_fixtures.write_transcript(
            transcript_path,
            [
                {
                    "timestamp": "2026-01-01T00:30:00+00:00",
                    "model": "claude-sonnet-4-6",
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "tools": [],
                    "sidechain": False,
                },
                {
                    "timestamp": "2026-01-01T01:00:00+00:00",
                    "model": "claude-sonnet-4-6",
                    "input_tokens": 200,
                    "output_tokens": 80,
                    "tools": [],
                    "sidechain": False,
                },
            ],
        )

        result = token_harvester.harvest([transcript_path], transitions)

        # Earlier turn (100/50) lands in IMPLEMENTING
        implementing = result["IMPLEMENTING"]
        assert implementing["tokens_by_type"]["input_tokens"] == 100
        assert implementing["tokens_by_type"]["output_tokens"] == 50
        assert implementing["available"] is True

        # Later turn (200/80) lands in IMPLEMENTED
        implemented = result["IMPLEMENTED"]
        assert implemented["tokens_by_type"]["input_tokens"] == 200
        assert implemented["tokens_by_type"]["output_tokens"] == 80
        assert implemented["available"] is True

    def test_turn_exactly_at_boundary_attributes_to_later_stage(self, tmp_path):
        """A turn whose timestamp equals the boundary T2 goes to IMPLEMENTED (at-or-after rule)."""
        stage_timestamps = {
            "IMPLEMENTING": "2026-01-01T00:00:00+00:00",
            "IMPLEMENTED":  "2026-01-01T01:00:00+00:00",
        }
        transitions = _transitions_from_timestamps(stage_timestamps)

        # One turn whose timestamp equals exactly the IMPLEMENTED boundary.
        transcript_path = str(tmp_path / "boundary_turn.jsonl")
        capture_fixtures.write_transcript(
            transcript_path,
            [
                {
                    "timestamp": "2026-01-01T01:00:00+00:00",
                    "model": "claude-sonnet-4-6",
                    "input_tokens": 300,
                    "output_tokens": 120,
                    "tools": [],
                    "sidechain": False,
                },
            ],
        )

        result = token_harvester.harvest([transcript_path], transitions)

        # The boundary turn goes to IMPLEMENTED, not IMPLEMENTING.
        assert result["IMPLEMENTED"]["tokens_by_type"]["input_tokens"] == 300
        assert result["IMPLEMENTED"]["tokens_by_type"]["output_tokens"] == 120
        # IMPLEMENTING gets nothing.
        assert result["IMPLEMENTING"]["tokens_by_type"].get("input_tokens", 0) == 0


# ---------------------------------------------------------------------------
# Unavailable transcript tests
# ---------------------------------------------------------------------------


class TestUnavailableTranscript:
    """Missing or unreadable transcripts mark affected stages unavailable, never 0."""

    def test_missing_transcript_marks_unavailable_not_zero(self, tmp_path):
        """A path that does not exist marks all stages available=False (rendered as 'unavailable')."""
        stage_timestamps = {
            "IMPLEMENTING": "2026-01-01T00:00:00+00:00",
            "IMPLEMENTED":  "2026-01-01T01:00:00+00:00",
        }
        transitions = _transitions_from_timestamps(stage_timestamps)

        missing_path = capture_fixtures.nonexistent_transcript_path(
            str(tmp_path), "ghost.jsonl"
        )

        result = token_harvester.harvest([missing_path], transitions)

        # Every stage in the result must be flagged unavailable — not zero.
        for stage_name, stage_data in result.items():
            assert stage_data["available"] is False, (
                f"stage {stage_name!r} should be available=False when transcript is missing"
            )
            # The distinction from 0 is load-bearing: token fields must not be 0.
            tokens = stage_data.get("tokens_by_type", {})
            for token_key, token_val in tokens.items():
                assert token_val != 0, (
                    f"stage {stage_name!r} field {token_key!r} must not be 0 when transcript "
                    f"is unavailable — use None or omit, never 0"
                )

    def test_unreadable_transcript_marks_unavailable_not_zero(self, tmp_path):
        """An unreadable (chmod 000) transcript marks affected stages available=False."""
        stage_timestamps = {
            "IMPLEMENTING": "2026-01-01T00:00:00+00:00",
            "IMPLEMENTED":  "2026-01-01T01:00:00+00:00",
        }
        transitions = _transitions_from_timestamps(stage_timestamps)

        unreadable_path = capture_fixtures.write_unreadable_transcript(
            str(tmp_path / "unreadable.jsonl")
        )

        result = token_harvester.harvest([unreadable_path], transitions)

        for stage_name, stage_data in result.items():
            assert stage_data["available"] is False, (
                f"stage {stage_name!r} should be available=False for unreadable transcript"
            )
            tokens = stage_data.get("tokens_by_type", {})
            for token_key, token_val in tokens.items():
                assert token_val != 0, (
                    f"stage {stage_name!r} field {token_key!r} must not be 0 when unreadable"
                )


# ---------------------------------------------------------------------------
# Cross-session aggregation tests
# ---------------------------------------------------------------------------


class TestCrossSessionAggregation:
    """Multiple transcripts for the same cycle sum into one per-stage total."""

    def test_two_transcripts_aggregate_into_one_total_set(self, tmp_path):
        """Turns from two transcripts in the same stage produce a single summed total."""
        stage_timestamps = {
            "IMPLEMENTING": "2026-01-01T00:00:00+00:00",
            "IMPLEMENTED":  "2026-01-01T02:00:00+00:00",
        }
        transitions = _transitions_from_timestamps(stage_timestamps)

        # Transcript A: one turn in IMPLEMENTING (before T2).
        path_a = str(tmp_path / "session_a.jsonl")
        capture_fixtures.write_transcript(
            path_a,
            [
                {
                    "timestamp": "2026-01-01T00:30:00+00:00",
                    "model": "claude-sonnet-4-6",
                    "input_tokens": 100,
                    "output_tokens": 40,
                    "tools": [],
                    "sidechain": False,
                },
            ],
        )

        # Transcript B: one more turn in IMPLEMENTING (before T2), different values.
        path_b = str(tmp_path / "session_b.jsonl")
        capture_fixtures.write_transcript(
            path_b,
            [
                {
                    "timestamp": "2026-01-01T01:00:00+00:00",
                    "model": "claude-sonnet-4-6",
                    "input_tokens": 150,
                    "output_tokens": 60,
                    "tools": [],
                    "sidechain": False,
                },
            ],
        )

        result = token_harvester.harvest([path_a, path_b], transitions)

        # Both turns aggregate into IMPLEMENTING: 100+150=250 input, 40+60=100 output.
        implementing = result["IMPLEMENTING"]
        assert implementing["tokens_by_type"]["input_tokens"] == 250
        assert implementing["tokens_by_type"]["output_tokens"] == 100
        assert implementing["available"] is True

    def test_stage_only_in_unreadable_transcript_stays_unavailable(self, tmp_path):
        """In a mixed cycle, a stage available makes its peer no less unavailable.

        One stage's turns are in a readable transcript; another stage's turns are
        only in an unreadable one.  The readable stage must show real tokens and
        the other must stay unavailable — not read as zero.  (A readable
        transcript must not make every stage look available.)
        """
        stage_timestamps = {
            "IMPLEMENTING": "2026-01-01T00:00:00+00:00",
            "VERIFYING":    "2026-01-01T02:00:00+00:00",
            "DONE":         "2026-01-01T04:00:00+00:00",
        }
        transitions = _transitions_from_timestamps(stage_timestamps)

        # Readable transcript: one turn in IMPLEMENTING only.
        readable = str(tmp_path / "readable.jsonl")
        capture_fixtures.write_transcript(
            readable,
            [
                {
                    "timestamp": "2026-01-01T00:30:00+00:00",
                    "model": "claude-sonnet-4-6",
                    "input_tokens": 120,
                    "output_tokens": 30,
                    "tools": [],
                    "sidechain": False,
                },
            ],
        )

        # Unreadable transcript: would have carried the VERIFYING turn.
        unreadable = capture_fixtures.write_unreadable_transcript(
            str(tmp_path / "unreadable.jsonl")
        )

        result = token_harvester.harvest([readable, unreadable], transitions)

        # IMPLEMENTING got a real readable turn.
        assert result["IMPLEMENTING"]["available"] is True
        assert result["IMPLEMENTING"]["tokens_by_type"]["input_tokens"] == 120

        # VERIFYING had no readable turn — it must be unavailable, not zero.
        verifying = result["VERIFYING"]
        assert verifying["available"] is False, (
            "a stage with no readable turn must stay unavailable even when "
            "another transcript was readable"
        )
        assert verifying["tokens_by_type"] == {}, (
            f"unavailable stage must not present zero token totals: {verifying!r}"
        )


# ---------------------------------------------------------------------------
# Boundary-adjacent turn count tests
# ---------------------------------------------------------------------------


class TestBoundaryAdjacentTurnCount:
    """harvest() emits boundary_adjacent_turns per stage for turns near a boundary."""

    def test_boundary_adjacent_turn_count_emitted(self, tmp_path):
        """Turns within one transition-interval of a boundary are counted as boundary-adjacent."""
        # Three stages with two boundaries: T1=00:00, T2=02:00, T3=04:00.
        # Transition interval = 2 hours.  A turn is boundary-adjacent if it is
        # within 2 hours of any boundary for its stage.
        stage_timestamps = {
            "IMPLEMENTING": "2026-01-01T00:00:00+00:00",
            "REVIEWING":    "2026-01-01T02:00:00+00:00",
            "IMPLEMENTED":  "2026-01-01T04:00:00+00:00",
        }
        transitions = _transitions_from_timestamps(stage_timestamps)

        transcript_path = str(tmp_path / "session.jsonl")
        capture_fixtures.write_transcript(
            transcript_path,
            [
                # IMPLEMENTING turn: at T=00:05 — within 2h of the IMPLEMENTING start boundary.
                {
                    "timestamp": "2026-01-01T00:05:00+00:00",
                    "model": "claude-sonnet-4-6",
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "tools": [],
                    "sidechain": False,
                },
                # IMPLEMENTING turn: at T=01:00 — still within 2h of start or end boundary
                # (start boundary 00:00 is 1h away; end boundary 02:00 is 1h away).
                {
                    "timestamp": "2026-01-01T01:00:00+00:00",
                    "model": "claude-sonnet-4-6",
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "tools": [],
                    "sidechain": False,
                },
                # REVIEWING turn: at T=03:00 — within 2h of either boundary (T2=02:00 is 1h
                # before; T3=04:00 is 1h after). Counts as boundary-adjacent.
                {
                    "timestamp": "2026-01-01T03:00:00+00:00",
                    "model": "claude-sonnet-4-6",
                    "input_tokens": 20,
                    "output_tokens": 8,
                    "tools": [],
                    "sidechain": False,
                },
                # IMPLEMENTED turn: at T=05:00 — within 2h of the IMPLEMENTED start boundary
                # (T3=04:00 is 1h away). There is no later boundary so only the start applies.
                {
                    "timestamp": "2026-01-01T05:00:00+00:00",
                    "model": "claude-sonnet-4-6",
                    "input_tokens": 30,
                    "output_tokens": 10,
                    "tools": [],
                    "sidechain": False,
                },
            ],
        )

        result = token_harvester.harvest([transcript_path], transitions)

        # Field must be present on every stage entry.
        for stage_name in ("IMPLEMENTING", "REVIEWING", "IMPLEMENTED"):
            assert "boundary_adjacent_turns" in result[stage_name], (
                f"stage {stage_name!r} missing boundary_adjacent_turns field"
            )

        # REVIEWING has 1 turn — it's within one interval of both boundaries.
        assert result["REVIEWING"]["boundary_adjacent_turns"] == 1
