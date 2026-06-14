"""Unit tests for fbk.capture.active_stage.resolve_active_stage and the
shared non-active-state constant.

Tests cover:
- resolve_active_stage returns (None, None) for every non-active state
  (checkpoint, idle, and terminal states).
- resolve_active_stage returns (spec_name, stage) for every working stage.
- state.NON_ACTIVE_STATES equals the pinned eleven-member frozenset.
- active_stage and report both expose the same NON_ACTIVE_STATES object by
  identity (guards against two drifting copies passing a value-equality check).
- The old local TERMINAL_STATES name is absent from active_stage after the fix.
"""

import os
import pytest

# Red phase: the fix that introduces NON_ACTIVE_STATES in fbk.state and wires
# both consumers to import it has not landed yet.
try:
    from fbk.capture import active_stage
    _ACTIVE_STAGE_AVAILABLE = True
except ImportError:
    _ACTIVE_STAGE_AVAILABLE = False

from tests import capture_fixtures

pytestmark = pytest.mark.skipif(
    not _ACTIVE_STAGE_AVAILABLE,
    reason="fbk.capture.active_stage module not yet implemented",
)

# ---------------------------------------------------------------------------
# Pinned state lists — do NOT derive from the production constant.
# A wrong constant must not steer the test.
# ---------------------------------------------------------------------------

# Every state that is not a working stage: checkpoint states, idle states, and
# the terminal state. A run in any of these states has no active working stage.
_NON_ACTIVE_STATES = [
    "COMPLETED",
    "PARKED",
    "QUEUED",
    "READY",
    "VALIDATED",
    "REVIEWED",
    "BROKEN_DOWN",
    "TASKS_READY",
    "TESTS_WRITTEN",
    "TESTS_READY",
    "IMPLEMENTED",
]

# The states where active work is happening — the run can be parked from these.
_WORKING_STAGES = [
    "VALIDATING",
    "REVIEWING",
    "BREAKING_DOWN",
    "TASK_REVIEWING",
    "TESTING",
    "TEST_REVIEWING",
    "IMPLEMENTING",
    "VERIFYING",
]


# ---------------------------------------------------------------------------
# Resolver: non-active states return (None, None)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state_name", _NON_ACTIVE_STATES)
def test_resolver_returns_no_stage_for_non_active_states(tmp_path, state_name):
    """resolve_active_stage returns (None, None) for every non-active state.

    Non-active states include the terminal state (COMPLETED), the parked /
    resume states (PARKED, READY), and every checkpoint between working stages.
    A run in any of these states has no active working stage to attribute events
    to.
    """
    state_dir = os.path.join(str(tmp_path), ".claude", "automation", "state")
    state = capture_fixtures.build_state(
        "demo-spec",
        {state_name: "2026-01-01T00:00:00+00:00"},
        current_state=state_name,
    )
    capture_fixtures.write_state(state_dir, state)

    result = active_stage.resolve_active_stage(str(tmp_path))

    assert result == (None, None), (
        f"expected (None, None) for non-active state {state_name!r}, got {result!r}"
    )


# ---------------------------------------------------------------------------
# Resolver: working stages return (spec_name, stage)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("stage_name", _WORKING_STAGES)
def test_resolver_returns_stage_for_each_working_stage(tmp_path, stage_name):
    """resolve_active_stage returns the spec and stage for each working stage.

    A run in a working stage is actively in progress; events fired during this
    period must be attributed to the spec and stage the resolver reads from the
    state file.
    """
    state_dir = os.path.join(str(tmp_path), ".claude", "automation", "state")
    state = capture_fixtures.build_state(
        "demo-spec",
        {stage_name: "2026-01-01T00:00:00+00:00"},
        current_state=stage_name,
    )
    capture_fixtures.write_state(state_dir, state)

    result = active_stage.resolve_active_stage(str(tmp_path))

    assert result == ("demo-spec", stage_name), (
        f"expected ('demo-spec', {stage_name!r}) for working stage, got {result!r}"
    )


# ---------------------------------------------------------------------------
# Identity guard: one shared NON_ACTIVE_STATES object across both consumers
# ---------------------------------------------------------------------------


def test_non_active_set_is_one_object_consumed_by_identity():
    """NON_ACTIVE_STATES is defined once in fbk.state and consumed by both
    active_stage and report via the same object (identity, not value-equality).

    Value-equality alone passes when two drifting copies happen to agree.
    Identity failure means one of the consumers has its own separate literal
    and the two sets can drift without a test catching it.
    """
    import fbk.state as state_module
    import fbk.report as report

    # The constant must equal the pinned eleven-member set.
    assert state_module.NON_ACTIVE_STATES == frozenset({
        "COMPLETED",
        "PARKED",
        "QUEUED",
        "READY",
        "VALIDATED",
        "REVIEWED",
        "BROKEN_DOWN",
        "TASKS_READY",
        "TESTS_WRITTEN",
        "TESTS_READY",
        "IMPLEMENTED",
    }), (
        f"state.NON_ACTIVE_STATES does not match the pinned set; "
        f"got {state_module.NON_ACTIVE_STATES!r}"
    )

    # Both consumers must hold the same object, not independent copies.
    assert active_stage.NON_ACTIVE_STATES is state_module.NON_ACTIVE_STATES, (
        "active_stage.NON_ACTIVE_STATES is not the same object as state.NON_ACTIVE_STATES; "
        "the module has its own copy and the two sets can drift"
    )
    assert report.NON_ACTIVE_STATES is state_module.NON_ACTIVE_STATES, (
        "report.NON_ACTIVE_STATES is not the same object as state.NON_ACTIVE_STATES; "
        "the module has its own copy and the two sets can drift"
    )

    # The old local name must be gone — its removal is the fix.
    with pytest.raises(AttributeError):
        active_stage.TERMINAL_STATES  # noqa: B018
