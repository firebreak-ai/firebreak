"""Unit tests for fbk.state module - state machine enforcement."""

import pytest
import json
from fbk.state import (
    create_state,
    transition_state,
    load_state,
    VALID_TRANSITIONS,
)


class TestCreateState:
    """Test state creation."""

    def test_create_state_produces_queued(self, set_state_dir):
        """create_state should produce a state with current_state == QUEUED."""
        result = create_state("test-spec")
        assert result == 0

        state = load_state("test-spec")
        assert state["current_state"] == "QUEUED"
        assert state["spec_name"] == "test-spec"
        assert "stage_timestamps" in state
        assert "QUEUED" in state["stage_timestamps"]
        assert state["error_history"] == []
        assert state["parked_info"] == {}

    def test_create_state_duplicate_rejected(self, set_state_dir):
        """create_state for existing spec should return 1."""
        # Create first time
        result1 = create_state("duplicate-spec")
        assert result1 == 0

        # Attempt create second time
        result2 = create_state("duplicate-spec")
        assert result2 == 1


class TestValidTransition:
    """Test valid state transitions."""

    def test_queued_to_validating_succeeds(self, set_state_dir):
        """Valid transition QUEUED -> VALIDATING should succeed."""
        create_state("test-spec")

        result = transition_state("test-spec", "VALIDATING")
        assert result == 0

        state = load_state("test-spec")
        assert state["current_state"] == "VALIDATING"
        assert "VALIDATING" in state["stage_timestamps"]

    def test_multi_step_transition(self, set_state_dir):
        """Multiple sequential transitions should work."""
        create_state("test-spec")

        result1 = transition_state("test-spec", "VALIDATING")
        assert result1 == 0

        result2 = transition_state("test-spec", "VALIDATED")
        assert result2 == 0

        state = load_state("test-spec")
        assert state["current_state"] == "VALIDATED"


class TestInvalidTransition:
    """Test invalid state transitions."""

    def test_invalid_transition_rejected(self, set_state_dir):
        """Invalid transition QUEUED -> REVIEWED should return 1."""
        create_state("test-spec")

        result = transition_state("test-spec", "REVIEWED")
        assert result == 1

        # State should be unchanged
        state = load_state("test-spec")
        assert state["current_state"] == "QUEUED"


class TestParkedState:
    """Test PARKED state behavior."""

    def test_parked_stores_failure_info(self, set_state_dir):
        """Transition to PARKED should store failed_stage and error history."""
        create_state("test-spec")
        transition_state("test-spec", "VALIDATING")

        reason = "validation failed"
        result = transition_state("test-spec", "PARKED", reason=reason)
        assert result == 0

        state = load_state("test-spec")
        assert state["current_state"] == "PARKED"
        assert state["parked_info"]["failed_stage"] == "VALIDATING"
        assert state["parked_info"]["reason"] == reason
        assert len(state["error_history"]) == 1
        assert state["error_history"][0]["stage"] == "VALIDATING"
        assert state["error_history"][0]["error"] == reason

    def test_parked_without_reason(self, set_state_dir):
        """Transition to PARKED without reason should store empty string."""
        create_state("test-spec")
        transition_state("test-spec", "VALIDATING")

        result = transition_state("test-spec", "PARKED")
        assert result == 0

        state = load_state("test-spec")
        assert state["parked_info"]["reason"] == ""
        assert state["error_history"][0]["error"] == ""


class TestReadyState:
    """Test READY state behavior and dynamic transitions."""

    def test_ready_resolves_from_parked_info(self, set_state_dir):
        """Transition PARKED -> READY should resolve next valid state from failed_stage."""
        create_state("test-spec")
        transition_state("test-spec", "VALIDATING")
        transition_state("test-spec", "PARKED", reason="validation failed")

        result = transition_state("test-spec", "READY")
        assert result == 0

        state = load_state("test-spec")
        assert state["current_state"] == "READY"
        # parked_info should still contain failed_stage for READY to resolve transitions
        assert state["parked_info"]["failed_stage"] == "VALIDATING"

    def test_ready_clears_parked_info_when_transitioning(self, set_state_dir):
        """Transitioning FROM READY should clear parked_info."""
        create_state("test-spec")
        transition_state("test-spec", "VALIDATING")
        transition_state("test-spec", "PARKED", reason="test failed")
        transition_state("test-spec", "READY")

        # Now transition from READY to the failed_stage (VALIDATING)
        result = transition_state("test-spec", "VALIDATING")
        assert result == 0

        state = load_state("test-spec")
        assert state["parked_info"] == {}


class TestStateValidTransitionsMap:
    """Test VALID_TRANSITIONS map structure."""

    def test_valid_transitions_map_exists(self):
        """VALID_TRANSITIONS should be defined and contain expected states."""
        assert isinstance(VALID_TRANSITIONS, dict)
        assert "QUEUED" in VALID_TRANSITIONS
        assert "PARKED" in VALID_TRANSITIONS
        assert "READY" in VALID_TRANSITIONS
        assert VALID_TRANSITIONS["QUEUED"] == ["VALIDATING"]
        assert "READY" in VALID_TRANSITIONS["PARKED"]
