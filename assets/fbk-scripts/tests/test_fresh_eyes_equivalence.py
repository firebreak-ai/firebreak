"""Equivalence tests for the fresh-eyes output contract.

Pins the durable, machine-checkable half of AC-04: a fresh-eyes report that
carries a planted critical observation has the three required headings and trips
the design gate's critical-content check; an empty-critical report does not.

The fixture pair (artifact.md + expected-critical.md) is the captured baseline.
The live re-run of the fresh-eyes preset against the artifact is the
source-of-truth completion gate (operator runs /fbk-fresh-eyes on the fixture
and confirms the planted observation appears) — that is out of scope here.
"""

from pathlib import Path

import pytest

try:
    from fbk.gates.design import _critical_section_has_content
    _GATE_IMPORTABLE = True
except ImportError:
    _critical_section_has_content = None  # type: ignore[assignment]
    _GATE_IMPORTABLE = False

requires_gate = pytest.mark.skipif(
    not _GATE_IMPORTABLE,
    reason="fbk.gates.design._critical_section_has_content not yet importable",
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "fresh_eyes_planted_defect"

# Distinctive token that must appear in the artifact AND the expected observation.
# This token is the behaviour-name the Error Handling section uses to mark
# silently-swallowed errors, making it a precise anchor between the two fixtures.
PLANTED_TOKEN = "swallow_on_transient"

FRESH_EYES_HEADINGS = ("## Critical", "## Substantive", "## Minor")


def _build_report(critical_body: str) -> str:
    """Build a minimal fresh-eyes-shaped report with the three required headings.

    critical_body is the text placed between ## Critical and ## Substantive.
    A trailing newline is included in each section so the scanner logic
    (which reads line by line) behaves identically to real report output.
    """
    return (
        f"## Critical\n\n"
        f"{critical_body}"
        f"## Substantive\n\n"
        f"- One substantive observation.\n\n"
        f"## Minor\n\n"
        f"- One minor observation.\n"
    )


@requires_gate
class TestExpectedObservationTripsGate:
    """The planted-observation report has all three headings and trips the gate."""

    def test_expected_observation_is_dash_prefixed_critical(self):
        """A report carrying the expected planted observation trips the design gate.

        Builds a fresh-eyes-shaped report with the planted critical observation as
        a dash-prefixed line and asserts that _critical_section_has_content returns
        True — confirming the observation is gate-visible.
        """
        expected_obs = FIXTURES_DIR / "expected-critical.md"
        observation_text = expected_obs.read_text()

        report = _build_report(observation_text)

        assert _critical_section_has_content(report) is True, (
            "Expected the planted critical observation to be detected as gate-content "
            f"by _critical_section_has_content. Observation: {observation_text!r}"
        )

    def test_three_headings_present_in_report_with_planted_observation(self):
        """The fresh-eyes-shaped report carrying the planted observation has all three headings."""
        expected_obs = FIXTURES_DIR / "expected-critical.md"
        observation_text = expected_obs.read_text()

        report = _build_report(observation_text)

        for heading in FRESH_EYES_HEADINGS:
            assert heading in report, (
                f"Required heading {heading!r} missing from report. "
                f"Report preview: {report[:200]!r}"
            )


@requires_gate
class TestEmptyCriticalDoesNotTripGate:
    """An empty ## Critical section does not trip the gate (keeps positive non-vacuous)."""

    def test_empty_critical_report_does_not_trip_gate(self):
        """A report with an empty ## Critical section returns False from the gate check.

        Paired with the positive test so the gate check is non-vacuous — a gate that
        always returned True would pass the positive test but fail this one.
        """
        report = _build_report("")  # empty body between ## Critical and ## Substantive

        assert _critical_section_has_content(report) is False, (
            "Expected _critical_section_has_content to return False for an empty "
            f"## Critical section. Report: {report!r}"
        )


class TestPlantedObservationTextIsSpecific:
    """The expected-critical fixture names the specific planted flaw token, not a generic flag."""

    def test_planted_observation_text_is_specific(self):
        """The expected-critical fixture is a non-empty dash-prefixed line naming the planted token.

        Asserts:
        - The file is non-empty.
        - The content starts with '- ' (dash-prefixed), matching the fresh-eyes observation format.
        - The planted token (PLANTED_TOKEN) appears in both the artifact and the expected observation,
          pinning that the expected observation names the specific flaw rather than a generic flag.
        """
        artifact = FIXTURES_DIR / "artifact.md"
        expected_obs = FIXTURES_DIR / "expected-critical.md"

        artifact_text = artifact.read_text()
        observation_text = expected_obs.read_text().strip()

        assert observation_text, "expected-critical.md must not be empty"

        assert observation_text.startswith("- "), (
            f"Expected observation must be a dash-prefixed line (start with '- '). "
            f"Got: {observation_text[:80]!r}"
        )

        assert PLANTED_TOKEN in artifact_text, (
            f"Planted token {PLANTED_TOKEN!r} must appear in artifact.md to confirm "
            f"the flaw is present in the artifact."
        )

        assert PLANTED_TOKEN in observation_text, (
            f"Planted token {PLANTED_TOKEN!r} must appear in expected-critical.md so "
            f"the observation names the specific planted flaw, not a generic flag. "
            f"Observation: {observation_text!r}"
        )
