"""Spec close launches a trimming session; tests run it as one that cuts nothing unless a
test installs its own."""

import pytest
from fbk.workflow import spec_trim


@pytest.fixture(autouse=True)
def trim_cuts_nothing(monkeypatch):
    monkeypatch.setattr(spec_trim, "launch", lambda root, unit, rows, config: [])
