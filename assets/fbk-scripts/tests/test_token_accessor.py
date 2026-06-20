"""Unit tests for fbk.capture.token_harvester.transcript_token_totals — per-transcript accessor.

Tests cover:
- Summing all four token fields across a multi-turn transcript
- Exposing the accessor's own availability flag (false for unreadable/missing transcripts)
- All four token fields (input, output, cache_read, cache_creation) genuinely summed with
  non-zero, mutually distinct expected values
"""

import pytest

try:
    from fbk.capture import token_harvester
    TRANSCRIPT_TOKEN_TOTALS_AVAILABLE = hasattr(token_harvester, "transcript_token_totals")
except ImportError:
    TRANSCRIPT_TOKEN_TOTALS_AVAILABLE = False

from tests import capture_fixtures

pytestmark = pytest.mark.skipif(
    not TRANSCRIPT_TOKEN_TOTALS_AVAILABLE,
    reason="fbk.capture.token_harvester.transcript_token_totals function not yet implemented",
)


# ---------------------------------------------------------------------------
# Multi-turn summation test
# ---------------------------------------------------------------------------


class TestTranscriptTokenTotals:
    """transcript_token_totals() sums across all turns and reports availability."""

    def test_readable_multi_turn_transcript_sums_all_four_token_fields(self, tmp_path):
        """Accessor returns available=True and sums all four token fields across turns."""
        # Turn 1: non-zero, distinct values for all four fields.
        # Turn 2: different non-zero, distinct values.
        # Chosen so each field's expected sum is unique:
        #   input_tokens: 10 + 20 = 30
        #   output_tokens: 3 + 7 = 10
        #   cache_read_input_tokens: 100 + 200 = 300
        #   cache_creation_input_tokens: 1000 + 2000 = 3000
        transcript_path = str(tmp_path / "multi_turn.jsonl")
        capture_fixtures.write_transcript(
            transcript_path,
            [
                {
                    "timestamp": "2026-01-01T00:00:00+00:00",
                    "model": "claude-sonnet-4-6",
                    "input_tokens": 10,
                    "output_tokens": 3,
                    "cache_read_input_tokens": 100,
                    "cache_creation_input_tokens": 1000,
                    "tools": [],
                    "sidechain": False,
                },
                {
                    "timestamp": "2026-01-01T00:05:00+00:00",
                    "model": "claude-sonnet-4-6",
                    "input_tokens": 20,
                    "output_tokens": 7,
                    "cache_read_input_tokens": 200,
                    "cache_creation_input_tokens": 2000,
                    "tools": [],
                    "sidechain": False,
                },
            ],
        )

        result = token_harvester.transcript_token_totals(transcript_path)

        # Availability flag must be True for readable transcript.
        assert result["available"] is True

        # All four token fields must be present and sum to expected values.
        tokens = result["tokens"]
        assert tokens["input_tokens"] == 30
        assert tokens["output_tokens"] == 10
        assert tokens["cache_read_input_tokens"] == 300
        assert tokens["cache_creation_input_tokens"] == 3000

        # Tokens dict must have exactly the four expected keys.
        expected_keys = {
            "input_tokens",
            "output_tokens",
            "cache_read_input_tokens",
            "cache_creation_input_tokens",
        }
        assert set(tokens.keys()) == expected_keys

    def test_unreadable_transcript_returns_available_false(self, tmp_path):
        """Accessor returns available=False and empty tokens dict for unreadable transcript."""
        unreadable_path = capture_fixtures.write_unreadable_transcript(
            str(tmp_path / "unreadable.jsonl")
        )

        result = token_harvester.transcript_token_totals(unreadable_path)

        assert result["available"] is False
        assert result["tokens"] == {}

    def test_missing_transcript_returns_available_false(self, tmp_path):
        """Accessor returns available=False for non-existent transcript path."""
        missing_path = capture_fixtures.nonexistent_transcript_path(str(tmp_path), "ghost.jsonl")

        result = token_harvester.transcript_token_totals(missing_path)

        assert result["available"] is False
