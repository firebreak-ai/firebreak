"""Unit tests for fbk.state module - state machine enforcement."""

import pytest
import json
from fbk.state import (
    create_state,
    transition_state,
    load_state,
    VALID_TRANSITIONS,
)

# Working stages: those whose VALID_TRANSITIONS entry contains PARKED.
# Derived from the live map so the test stays aligned with any future additions.
_WORKING_STAGES = {
    stage for stage, targets in VALID_TRANSITIONS.items() if "PARKED" in targets
}


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


# ---------------------------------------------------------------------------
# Injector wiring tests
#
# These tests verify that transition_state calls inject_stage_metrics with the
# right predicate: fires when prev state is a working stage AND new state is
# not PARKED; does not fire otherwise.  Injection is fail-silent.
#
# The wiring inside transition_state does not exist yet (added by task-36).
# Until then these tests fail red — they collect cleanly and report failures,
# not import/collection errors.  If fbk.capture.retro_injector is absent the
# whole class is skipped.
# ---------------------------------------------------------------------------

# Skip the class if the injector module is not installed yet.
_retro_injector = pytest.importorskip(
    "fbk.capture.retro_injector",
    reason="fbk.capture.retro_injector not available; skipping wiring tests",
)

_INJECTOR_TARGET = "fbk.capture.retro_injector.inject_stage_metrics"


class TestInjectorWiring:
    """Verify the guarded inject_stage_metrics call wired into transition_state."""

    @pytest.fixture
    def record_calls(self, monkeypatch):
        """Monkeypatch the injector and return the call-record list.

        Patches fbk.capture.retro_injector.inject_stage_metrics so that each
        invocation appends (spec, completed_stage) to the returned list.
        state.py will call the function through the module reference, so this
        binding is the correct patch target.
        """
        calls = []
        monkeypatch.setattr(
            _INJECTOR_TARGET,
            lambda spec, completed_stage: calls.append((spec, completed_stage)),
        )
        return calls

    @pytest.fixture
    def raising_injector(self, monkeypatch):
        """Monkeypatch the injector to raise RuntimeError on every call."""
        def _raise(spec, completed_stage):
            raise RuntimeError("injector failure")

        monkeypatch.setattr(_INJECTOR_TARGET, _raise)

    def test_injection_fires_on_working_stage_to_checkpoint(
        self, set_state_dir, record_calls
    ):
        """Injector called exactly once with the completed working stage on a
        working-stage → checkpoint transition; not called on QUEUED → working-stage."""
        create_state("s")
        # QUEUED → VALIDATING: prev is QUEUED (not a working stage) — no fire
        transition_state("s", "VALIDATING")
        assert record_calls == [], "injector should not fire when leaving QUEUED"

        # VALIDATING → VALIDATED: prev is VALIDATING (working stage) → fires
        transition_state("s", "VALIDATED")
        assert len(record_calls) == 1, "injector should fire exactly once"
        assert record_calls[0] == ("s", "VALIDATING"), (
            "injector should receive (spec, prev_working_stage)"
        )

    def test_injection_does_not_fire_on_park(self, set_state_dir, record_calls):
        """Working-stage → PARKED does not fire the injector.

        This is the park-exclusion: keying on prev state alone would inject a
        'completed' block on every park, which is wrong.
        """
        create_state("s")
        transition_state("s", "VALIDATING")
        # VALIDATING → PARKED: prev is a working stage BUT new state is PARKED
        transition_state("s", "PARKED", reason="failure")
        assert record_calls == [], (
            "injector must not fire when transitioning to PARKED"
        )

    def test_injection_does_not_fire_leaving_queued_or_checkpoint_or_ready(
        self, set_state_dir, record_calls
    ):
        """Only one injector call: on the working-stage completion (VALIDATING→VALIDATED).

        Leaving QUEUED (→VALIDATING) and leaving a checkpoint (VALIDATED→REVIEWING)
        must not produce additional calls.
        """
        create_state("s")
        # QUEUED → VALIDATING: prev QUEUED — no fire
        transition_state("s", "VALIDATING")
        # VALIDATING → VALIDATED: prev VALIDATING (working) → fires once
        transition_state("s", "VALIDATED")
        # VALIDATED → REVIEWING: prev VALIDATED (checkpoint, not a working stage) — no fire
        transition_state("s", "REVIEWING")

        assert len(record_calls) == 1, (
            "only the working-stage completion should fire the injector"
        )
        assert record_calls[0] == ("s", "VALIDATING"), (
            "injector should receive the completed working stage, not the checkpoint"
        )

    def test_injection_does_not_fire_on_ready_resume(
        self, set_state_dir, record_calls
    ):
        """PARKED→READY and READY→working-stage do not fire the injector.

        PARKED and READY are not working stages, so resuming from a park must not
        inject a metrics block.
        """
        create_state("s")
        transition_state("s", "VALIDATING")
        transition_state("s", "PARKED", reason="test failure")
        # PARKED → READY: prev PARKED — no fire
        transition_state("s", "READY")
        # READY → VALIDATING: prev READY — no fire
        transition_state("s", "VALIDATING")

        assert record_calls == [], (
            "injector must not fire when resuming through READY"
        )

    def test_failed_injection_does_not_block_transition(
        self, set_state_dir, raising_injector
    ):
        """A raising injector is swallowed; the transition still returns 0 and
        the saved state advances to the new state."""
        create_state("s")
        transition_state("s", "VALIDATING")
        # VALIDATING → VALIDATED triggers the injector, which raises
        result = transition_state("s", "VALIDATED")
        assert result == 0, "transition must succeed even when injector raises"
        state = load_state("s")
        assert state["current_state"] == "VALIDATED", (
            "saved state must reflect the completed transition"
        )

    def test_injection_additive_existing_transitions_unchanged(
        self, set_state_dir, record_calls
    ):
        """With the injector patched to a no-op, the same multi-step transition
        that test_multi_step_transition covers produces the same final state —
        confirming injection is additive and does not alter transition behavior."""
        create_state("s")
        result1 = transition_state("s", "VALIDATING")
        assert result1 == 0
        result2 = transition_state("s", "VALIDATED")
        assert result2 == 0
        state = load_state("s")
        assert state["current_state"] == "VALIDATED"
