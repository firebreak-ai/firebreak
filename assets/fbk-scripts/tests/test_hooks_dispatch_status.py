"""Tests for fbk.hooks.dispatch_status output formatting."""

import pytest
import json
from fbk.hooks.dispatch_status import format_status


class TestDispatchStatusFormatting:
    """Tests for dispatch_status formatting function."""

    def test_queued_state_formatted_correctly(self):
        """Test queued state shows spec name, QUEUED, and timestamp."""
        state = {
            "spec_name": "queued-spec",
            "current_state": "QUEUED",
            "stage_timestamps": {"QUEUED": "2026-03-14T10:00:00+00:00"},
            "agent_ids": [],
            "verification_results": {},
            "error_history": [],
            "parked_info": {}
        }
        output = format_status(state)
        assert "queued-spec" in output
        assert "QUEUED" in output
        assert "2026-03-14" in output

    def test_reviewing_state_shows_history(self):
        """Test reviewing state contains REVIEWING and prior stages."""
        state = {
            "spec_name": "reviewing-spec",
            "current_state": "REVIEWING",
            "stage_timestamps": {
                "QUEUED": "2026-03-14T10:00:00+00:00",
                "VALIDATING": "2026-03-14T10:05:00+00:00",
                "VALIDATED": "2026-03-14T10:10:00+00:00",
                "REVIEWING": "2026-03-14T10:15:00+00:00"
            },
            "agent_ids": [],
            "verification_results": {},
            "error_history": [],
            "parked_info": {}
        }
        output = format_status(state)
        assert "REVIEWING" in output
        assert "QUEUED" in output
        assert "VALIDATING" in output
        assert "VALIDATED" in output

    def test_parked_state_shows_failure_details(self):
        """Test parked state contains PARKED, failed stage, and reason."""
        state = {
            "spec_name": "parked-spec",
            "current_state": "PARKED",
            "stage_timestamps": {
                "QUEUED": "2026-03-14T10:00:00+00:00",
                "VALIDATING": "2026-03-14T10:05:00+00:00",
                "PARKED": "2026-03-14T10:08:00+00:00"
            },
            "agent_ids": [],
            "verification_results": {},
            "error_history": [
                {
                    "stage": "VALIDATING",
                    "error": "spec validation failed: missing required section: Testing strategy",
                    "timestamp": "2026-03-14T10:08:00+00:00"
                }
            ],
            "parked_info": {
                "failed_stage": "VALIDATING",
                "reason": "missing required section: Testing strategy"
            }
        }
        output = format_status(state)
        assert "PARKED" in output
        assert "VALIDATING" in output
        assert "missing required section" in output

    def test_completed_state_formatted(self):
        """Test completed state contains COMPLETED."""
        state = {
            "spec_name": "completed-spec",
            "current_state": "COMPLETED",
            "stage_timestamps": {
                "QUEUED": "2026-03-14T10:00:00+00:00",
                "VALIDATING": "2026-03-14T10:05:00+00:00",
                "VALIDATED": "2026-03-14T10:10:00+00:00",
                "REVIEWING": "2026-03-14T10:15:00+00:00",
                "REVIEWED": "2026-03-14T10:20:00+00:00",
                "BREAKING_DOWN": "2026-03-14T10:25:00+00:00",
                "BROKEN_DOWN": "2026-03-14T10:30:00+00:00",
                "TASK_REVIEWING": "2026-03-14T10:35:00+00:00",
                "TASKS_READY": "2026-03-14T10:40:00+00:00",
                "TESTING": "2026-03-14T10:45:00+00:00",
                "TESTS_WRITTEN": "2026-03-14T10:50:00+00:00",
                "TEST_REVIEWING": "2026-03-14T10:55:00+00:00",
                "TESTS_READY": "2026-03-14T11:00:00+00:00",
                "IMPLEMENTING": "2026-03-14T11:05:00+00:00",
                "IMPLEMENTED": "2026-03-14T11:10:00+00:00",
                "VERIFYING": "2026-03-14T11:15:00+00:00",
                "COMPLETED": "2026-03-14T11:20:00+00:00"
            },
            "agent_ids": [],
            "verification_results": {},
            "error_history": [],
            "parked_info": {}
        }
        output = format_status(state)
        assert "COMPLETED" in output

    def test_output_contains_spec_name_and_state(self):
        """Test output includes both the spec name and the current state in readable form."""
        state = {
            "spec_name": "queued-spec",
            "current_state": "QUEUED",
            "stage_timestamps": {"QUEUED": "2026-03-14T10:00:00+00:00"},
            "agent_ids": [],
            "verification_results": {},
            "error_history": [],
            "parked_info": {}
        }
        output = format_status(state)
        assert "queued-spec" in output, "Output should contain the spec name"
        assert "QUEUED" in output, "Output should contain the current state"

    def test_error_history_displayed_for_parked_spec(self):
        """Test error history is displayed for parked spec."""
        state = {
            "spec_name": "parked-spec",
            "current_state": "PARKED",
            "stage_timestamps": {
                "QUEUED": "2026-03-14T10:00:00+00:00",
                "VALIDATING": "2026-03-14T10:05:00+00:00",
                "PARKED": "2026-03-14T10:08:00+00:00"
            },
            "agent_ids": [],
            "verification_results": {},
            "error_history": [
                {
                    "stage": "VALIDATING",
                    "error": "spec validation failed: missing required section: Testing strategy",
                    "timestamp": "2026-03-14T10:08:00+00:00"
                }
            ],
            "parked_info": {
                "failed_stage": "VALIDATING",
                "reason": "missing required section: Testing strategy"
            }
        }
        output = format_status(state)
        assert "spec validation failed" in output
