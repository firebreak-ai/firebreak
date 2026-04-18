import pytest
from pathlib import Path


@pytest.fixture
def project_root():
    """Return the path to the assets/fbk-scripts directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def set_log_dir(tmp_path, monkeypatch):
    """Set LOG_DIR env var to a tmp_path subdirectory via monkeypatch."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setenv("LOG_DIR", str(log_dir))
    return log_dir


@pytest.fixture
def set_state_dir(tmp_path, monkeypatch):
    """Set STATE_DIR env var to a tmp_path subdirectory via monkeypatch."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    monkeypatch.setenv("STATE_DIR", str(state_dir))
    return state_dir


@pytest.fixture
def valid_spec_text():
    """Return a minimal valid feature spec string with all required sections."""
    return """# Feature Specification

## Problem
Describes the issue or gap being addressed.

## Goals
- Primary objective of the feature

## User-facing behavior
Describes how end users interact with the feature.

## Technical approach
Details the implementation strategy.

## Testing strategy
- AC-01: Test criterion 1
- AC-02: Test criterion 2

## Documentation impact
Expected changes to user documentation.

## Acceptance criteria
- AC-01: Feature works as specified
- AC-02: Feature passes all test criteria

## Dependencies
None

## Open questions
None
"""


@pytest.fixture
def valid_sighting():
    """Return a dict with all required pipeline sighting fields."""
    return {
        "id": "sighting-001",
        "title": "Test sighting",
        "location": "test/location",
        "type": "issue",
        "severity": "medium",
        "mechanism": "detection mechanism",
        "consequence": "potential impact",
        "evidence": "supporting evidence"
    }
