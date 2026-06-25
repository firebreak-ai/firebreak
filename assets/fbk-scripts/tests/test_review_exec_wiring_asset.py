"""Structural asset tests for the executable-pipeline wiring in each finding-mode review skill.

Asserts that each skill's markdown documents the required pipeline command steps
in order, anchored on the literal command-step tokens, and contains the
cited-source injection instruction positioned correctly relative to the
normalize step and the challenger spawn.

Covers:
- AC-08: normalize step sits between the validation/filter pass and the
  challenger spawn, so the challenger receives normalized findings.
- AC-09: each finding-mode skill contains the by-position rejoin step
  (``pipeline rejoin --verdicts``), asserted present and ordered.
- AC-10: post-challenge ``pipeline validate --lens`` and
  ``pipeline validate-verdicts`` replace the prose verdict-field check.
- AC-11: code-review's run and post-challenge validate pass ``code-lens.md``.
- AC-14: cited-source injection is positioned after the normalize step and
  before the challenger's verification instructions (inside the challenger
  spawn, between the normalized findings and the verification instructions).

Stated limitation: these tests prove the documented command sequence is present
and ordered, not that the running skill executes it correctly.  UV-3 (operator
manual end-to-end run) is the correctness gate; task-08 (chained-integration
test) narrows the gap by exercising the real command composition.  This test
pins the skill wiring.

All tests are RED before the Wave 1 implementation tasks land the pipeline
wiring in the four skill files.  The skills currently lack the ``--lens`` /
``normalize`` / ``validate-verdicts`` / ``rejoin`` step tokens, so the
ordered-marker assertions fail.  Failing here proves the tests catch the
absence of the wiring.
"""

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Asset paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parents[3]

_CODE_REVIEW_SKILL = _REPO_ROOT / "assets" / "skills" / "fbk-code-review" / "SKILL.md"
_TEST_REVIEW_SKILL = _REPO_ROOT / "assets" / "skills" / "fbk-test-review" / "SKILL.md"
_COHERENCE_REVIEW_SKILL = _REPO_ROOT / "assets" / "skills" / "fbk-coherence-review" / "SKILL.md"
_TASK_REVIEW_SKILL = _REPO_ROOT / "assets" / "skills" / "fbk-task-review" / "SKILL.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read(path: Path) -> str:
    """Return the text of an asset file.

    Raises FileNotFoundError (red-phase failure) when the asset does not exist.
    """
    return path.read_text(encoding="utf-8")


def _ordered(text: str, tokens: list[str]) -> None:
    """Assert that each token in ``tokens`` appears in the text in sequential order.

    Searches for each token starting from the character position just after the
    previous token's match end (cursor-based, not first-occurrence).  Sequential
    search is required because the converted skills legitimately contain the same
    ``pipeline validate --lens <type>-lens.md`` token twice — once for the
    detection-round validate and once for the post-challenge re-validation — and a
    first-occurrence helper would match both occurrences to the same early index and
    either wrongly fail a correct skill or wrongly pass an incorrect one.

    Raises AssertionError naming the first token that is missing or out of order.
    """
    cursor = 0
    prev_token = None
    prev_pos = -1

    for token in tokens:
        pos = text.find(token, cursor)
        if pos == -1:
            if prev_token is None:
                raise AssertionError(
                    f"Required step token not found: {token!r} "
                    f"(first token in the ordered sequence)"
                )
            raise AssertionError(
                f"Required step token not found: {token!r} "
                f"(expected after {prev_token!r} at offset {prev_pos}; "
                f"searched from offset {cursor})"
            )
        if pos <= prev_pos and prev_token is not None:
            raise AssertionError(
                f"Step token out of order: {token!r} at offset {pos} "
                f"must appear strictly after {prev_token!r} at offset {prev_pos}"
            )
        prev_token = token
        prev_pos = pos
        cursor = pos + len(token)


# ---------------------------------------------------------------------------
# Code-review wiring (AC-11)
# ---------------------------------------------------------------------------


class TestCodeReviewPipelineWiring:
    """fbk-code-review/SKILL.md documents the five executable pipeline steps in order (AC-10, AC-11).

    Required ordered steps (anchored command-step tokens):
      1. ``pipeline run`` carrying ``--lens`` nearby
      2. ``pipeline normalize``
      3. ``pipeline validate-verdicts``
      4. ``pipeline rejoin``
      5. post-challenge ``pipeline validate`` carrying ``--lens``

    RED before the implementation task adds ``--lens``, ``normalize``,
    ``validate-verdicts``, and ``rejoin`` to fbk-code-review/SKILL.md.
    """

    def test_pipeline_run_carries_lens_flag(self):
        """``pipeline run`` is followed by ``--lens`` within 120 characters (AC-11).

        120 characters is enough to span a typical single-line command step
        including the preset and severity arguments.  This anchors on the
        command-step token rather than on body vocabulary.
        """
        text = _read(_CODE_REVIEW_SKILL)

        run_pos = text.find("pipeline run")
        assert run_pos != -1, (
            "fbk-code-review/SKILL.md must contain the token 'pipeline run' "
            "to document the detection-round command step"
        )

        window = text[run_pos : run_pos + 120]
        assert "--lens" in window, (
            f"'pipeline run' at offset {run_pos} must be followed by '--lens' "
            f"within 120 characters to document the lens argument on the "
            f"detection-round run step (AC-11); "
            f"window: {window!r}"
        )

    def test_pipeline_steps_ordered_after_run(self):
        """``normalize``, ``validate-verdicts``, ``rejoin``, and post-challenge ``validate --lens`` appear in order after ``pipeline run`` (AC-08, AC-09, AC-10).

        Ordering is verified by the sequential cursor-based ``_ordered`` helper
        rather than first-occurrence, so the post-challenge ``validate --lens``
        matches the second occurrence (after the challenger has returned) rather
        than the detection-round occurrence.
        """
        text = _read(_CODE_REVIEW_SKILL)

        # Anchor the ordered check starting from just after the ``pipeline run``
        # detection step so that ``pipeline validate --lens`` (last token) is
        # checked for the post-challenge occurrence, not the detection-round one.
        run_pos = text.find("pipeline run")
        assert run_pos != -1, (
            "fbk-code-review/SKILL.md must contain 'pipeline run' "
            "as the anchor for the ordered step check"
        )

        # Slice the text from just after ``pipeline run`` for the remaining steps.
        remaining = text[run_pos + len("pipeline run"):]

        _ordered(
            remaining,
            [
                "pipeline normalize",
                "pipeline validate-verdicts",
                "pipeline rejoin",
                "pipeline validate",
                "--lens",
            ],
        )

    def test_validate_verdicts_step_wires_stdin_from_verdicts_file(self):
        """The validate-verdicts command in fbk-code-review/SKILL.md pipes the verdicts file to stdin.

        ``cmd_validate_verdicts`` reads only from stdin; a bare command with no stdin
        redirection silently reads nothing.  This test asserts that the ``validate-verdicts``
        invocation is followed by ``< <verdicts-file>`` within 120 characters, proving
        the verdicts temp file is piped in.

        This is the gap that let F-05 reach a green test suite: the ordered-step test
        confirmed the command was present but did not assert stdin wiring.
        """
        text = _read(_CODE_REVIEW_SKILL)

        vv_pos = text.find("pipeline validate-verdicts")
        assert vv_pos != -1, (
            "fbk-code-review/SKILL.md must contain 'pipeline validate-verdicts' "
            "to document the verdict-validation step"
        )

        window = text[vv_pos : vv_pos + 120]
        assert "< <verdicts-file>" in window, (
            f"'pipeline validate-verdicts' at offset {vv_pos} must be followed by "
            f"'< <verdicts-file>' within 120 characters to wire the verdicts temp file "
            f"to stdin (cmd_validate_verdicts reads stdin only); "
            f"window: {window!r}"
        )


# ---------------------------------------------------------------------------
# Converted-skill wiring (AC-08, AC-09, AC-10)
# ---------------------------------------------------------------------------


class TestTestReviewPipelineWiring:
    """fbk-test-review/SKILL.md documents the six executable pipeline steps in order (AC-08, AC-09, AC-10).

    Required ordered steps (anchored on command-step tokens with ``test-lens.md``):
      1. ``pipeline validate --lens test-lens.md``
      2. ``pipeline severity-filter``
      3. ``pipeline normalize``
      4. ``pipeline validate-verdicts``
      5. ``pipeline rejoin --verdicts``
      6. ``pipeline validate --lens test-lens.md``  (post-challenge, second occurrence)

    The ``_ordered`` helper uses sequential cursor search so that the second
    occurrence of ``pipeline validate --lens test-lens.md`` (post-challenge) is
    matched at a position strictly after the first occurrence (detection-round).

    RED before the implementation task converts fbk-test-review/SKILL.md to the
    composable pipeline.
    """

    _LENS = "test-lens.md"

    def test_pipeline_steps_ordered(self):
        """The six pipeline step tokens appear in order in fbk-test-review/SKILL.md."""
        text = _read(_TEST_REVIEW_SKILL)
        lens = self._LENS

        _ordered(
            text,
            [
                f"pipeline validate --lens {lens}",
                "pipeline severity-filter",
                "pipeline normalize",
                "pipeline validate-verdicts",
                "pipeline rejoin --verdicts",
                f"pipeline validate --lens {lens}",
            ],
        )

    def test_validate_verdicts_step_wires_stdin_from_verdicts_file(self):
        """The validate-verdicts command in fbk-test-review/SKILL.md pipes the verdicts file to stdin.

        ``cmd_validate_verdicts`` reads only from stdin; a bare command silently reads
        nothing.  This asserts the command is followed by ``< <verdicts-file>`` within
        120 characters, proving the verdicts temp file is piped in.
        """
        text = _read(_TEST_REVIEW_SKILL)

        vv_pos = text.find("pipeline validate-verdicts")
        assert vv_pos != -1, (
            "fbk-test-review/SKILL.md must contain 'pipeline validate-verdicts'"
        )

        window = text[vv_pos : vv_pos + 120]
        assert "< <verdicts-file>" in window, (
            f"'pipeline validate-verdicts' at offset {vv_pos} must be followed by "
            f"'< <verdicts-file>' within 120 characters; window: {window!r}"
        )


class TestCoherenceReviewPipelineWiring:
    """fbk-coherence-review/SKILL.md documents the six executable pipeline steps in order (AC-08, AC-09, AC-10).

    Required ordered steps (anchored on command-step tokens with ``coherence-lens.md``):
      1. ``pipeline validate --lens coherence-lens.md``
      2. ``pipeline severity-filter``
      3. ``pipeline normalize``
      4. ``pipeline validate-verdicts``
      5. ``pipeline rejoin --verdicts``
      6. ``pipeline validate --lens coherence-lens.md``  (post-challenge, second occurrence)

    RED before the implementation task converts fbk-coherence-review/SKILL.md to the
    composable pipeline.
    """

    _LENS = "coherence-lens.md"

    def test_pipeline_steps_ordered(self):
        """The six pipeline step tokens appear in order in fbk-coherence-review/SKILL.md."""
        text = _read(_COHERENCE_REVIEW_SKILL)
        lens = self._LENS

        _ordered(
            text,
            [
                f"pipeline validate --lens {lens}",
                "pipeline severity-filter",
                "pipeline normalize",
                "pipeline validate-verdicts",
                "pipeline rejoin --verdicts",
                f"pipeline validate --lens {lens}",
            ],
        )

    def test_validate_verdicts_step_wires_stdin_from_verdicts_file(self):
        """The validate-verdicts command in fbk-coherence-review/SKILL.md pipes the verdicts file to stdin.

        ``cmd_validate_verdicts`` reads only from stdin; a bare command silently reads
        nothing.  This asserts the command is followed by ``< <verdicts-file>`` within
        120 characters, proving the verdicts temp file is piped in.
        """
        text = _read(_COHERENCE_REVIEW_SKILL)

        vv_pos = text.find("pipeline validate-verdicts")
        assert vv_pos != -1, (
            "fbk-coherence-review/SKILL.md must contain 'pipeline validate-verdicts'"
        )

        window = text[vv_pos : vv_pos + 120]
        assert "< <verdicts-file>" in window, (
            f"'pipeline validate-verdicts' at offset {vv_pos} must be followed by "
            f"'< <verdicts-file>' within 120 characters; window: {window!r}"
        )


class TestTaskReviewPipelineWiring:
    """fbk-task-review/SKILL.md documents the six executable pipeline steps in order (AC-08, AC-09, AC-10).

    Required ordered steps (anchored on command-step tokens with ``task-lens.md``):
      1. ``pipeline validate --lens task-lens.md``
      2. ``pipeline severity-filter``
      3. ``pipeline normalize``
      4. ``pipeline validate-verdicts``
      5. ``pipeline rejoin --verdicts``
      6. ``pipeline validate --lens task-lens.md``  (post-challenge, second occurrence)

    RED before the implementation task converts fbk-task-review/SKILL.md to the
    composable pipeline.
    """

    _LENS = "task-lens.md"

    def test_pipeline_steps_ordered(self):
        """The six pipeline step tokens appear in order in fbk-task-review/SKILL.md."""
        text = _read(_TASK_REVIEW_SKILL)
        lens = self._LENS

        _ordered(
            text,
            [
                f"pipeline validate --lens {lens}",
                "pipeline severity-filter",
                "pipeline normalize",
                "pipeline validate-verdicts",
                "pipeline rejoin --verdicts",
                f"pipeline validate --lens {lens}",
            ],
        )

    def test_validate_verdicts_step_wires_stdin_from_verdicts_file(self):
        """The validate-verdicts command in fbk-task-review/SKILL.md pipes the verdicts file to stdin.

        ``cmd_validate_verdicts`` reads only from stdin; a bare command silently reads
        nothing.  This asserts the command is followed by ``< <verdicts-file>`` within
        120 characters, proving the verdicts temp file is piped in.
        """
        text = _read(_TASK_REVIEW_SKILL)

        vv_pos = text.find("pipeline validate-verdicts")
        assert vv_pos != -1, (
            "fbk-task-review/SKILL.md must contain 'pipeline validate-verdicts'"
        )

        window = text[vv_pos : vv_pos + 120]
        assert "< <verdicts-file>" in window, (
            f"'pipeline validate-verdicts' at offset {vv_pos} must be followed by "
            f"'< <verdicts-file>' within 120 characters; window: {window!r}"
        )


# ---------------------------------------------------------------------------
# Cited-source injection positioning (AC-14) — all four skills
# ---------------------------------------------------------------------------


class TestCitedSourceInjectionPositioning:
    """Each finding-mode skill documents the cited-source injection instruction positioned inside the challenger spawn (AC-14).

    Three conditions must hold in every skill:

    1. ``source_of_truth_ref`` is present.
    2. An inject/collect instruction co-occurs near ``source_of_truth_ref``
       (within a 500-character window), proving the field name is paired with
       an actionable injection instruction.
    3. The ``source_of_truth_ref`` field appears at an index strictly AFTER the
       ``pipeline normalize`` step and strictly BEFORE the challenger's
       verification-instruction marker.

    The upper bound is anchored on the challenger's verification instructions
    (the instruction text handed to the challenger spawn), NOT on
    ``pipeline validate-verdicts``.  ``pipeline validate-verdicts`` runs after
    the challenger returns — it is too loose a bound to prove in-spawn placement.
    The verification-instruction marker used here is the text that identifies
    the block of instructions sent to the challenger spawn (e.g.
    ``verification instructions``).

    All four tests are RED before the implementation tasks add the normalize step
    and the cited-source injection instruction to the skills.
    """

    # Marker for the challenger's verification instructions block — the text
    # handed to the challenger spawn.  This is the upper bound that proves
    # the cited-source instruction is inside the challenger spawn, positioned
    # between the normalized findings and the verification block.
    _VERIFICATION_MARKER = "verification instructions"

    def _assert_cited_source_injection(self, path: Path, skill_label: str) -> None:
        """Assert the three cited-source injection conditions hold for the skill at ``path``."""
        text = _read(path)

        # Condition 1: source_of_truth_ref is present.
        assert "source_of_truth_ref" in text, (
            f"{skill_label} must contain 'source_of_truth_ref' to document "
            "the cited-source injection contract (AC-14)"
        )

        # Condition 2: inject/collect co-occurs near source_of_truth_ref.
        sot_pos = text.find("source_of_truth_ref")
        window_start = max(0, sot_pos - 500)
        window_end = min(len(text), sot_pos + len("source_of_truth_ref") + 500)
        region = text[window_start:window_end]
        has_injection_instruction = bool(
            re.search(r"\b(inject|collect)\b", region, re.IGNORECASE)
        )
        assert has_injection_instruction, (
            f"{skill_label} must co-locate 'source_of_truth_ref' with an "
            "inject/collect instruction within 500 characters (AC-14); "
            f"region around 'source_of_truth_ref': {region!r}"
        )

        # Condition 3: source_of_truth_ref falls strictly between the normalize
        # step and the challenger's verification-instruction marker.

        # Lower bound: pipeline normalize step.
        normalize_pos = text.find("pipeline normalize")
        assert normalize_pos != -1, (
            f"{skill_label} must contain 'pipeline normalize' as the lower-bound "
            "anchor for the cited-source injection position check (AC-08, AC-14)"
        )

        # Upper bound: challenger verification instructions marker.
        verif_pos = text.find(self._VERIFICATION_MARKER)
        assert verif_pos != -1, (
            f"{skill_label} must contain the text {self._VERIFICATION_MARKER!r} "
            "as the upper-bound anchor proving the cited-source instruction is "
            "positioned inside the challenger spawn (before the verification "
            "instructions block); this text identifies where the challenger spawn "
            "instructions begin (AC-14)"
        )

        assert normalize_pos < verif_pos, (
            f"In {skill_label}, 'pipeline normalize' (offset {normalize_pos}) must "
            f"appear before {self._VERIFICATION_MARKER!r} "
            f"(offset {verif_pos}); the bounds are inverted"
        )

        # sot_pos is the first occurrence of source_of_truth_ref; verify it
        # falls inside the [normalize_pos, verif_pos) window.
        assert normalize_pos < sot_pos < verif_pos, (
            f"In {skill_label}, 'source_of_truth_ref' (offset {sot_pos}) must "
            f"appear strictly after 'pipeline normalize' (offset {normalize_pos}) "
            f"and strictly before the verification-instruction marker "
            f"{self._VERIFICATION_MARKER!r} (offset {verif_pos}); "
            "this proves the cited-source injection is positioned inside the "
            "challenger spawn, between the normalized findings and the "
            "verification instructions (AC-14)"
        )

    def test_code_review_cited_source_injection_positioned(self):
        """fbk-code-review/SKILL.md documents cited-source injection after normalize and before verification instructions."""
        self._assert_cited_source_injection(_CODE_REVIEW_SKILL, "fbk-code-review/SKILL.md")

    def test_test_review_cited_source_injection_positioned(self):
        """fbk-test-review/SKILL.md documents cited-source injection after normalize and before verification instructions."""
        self._assert_cited_source_injection(_TEST_REVIEW_SKILL, "fbk-test-review/SKILL.md")

    def test_coherence_review_cited_source_injection_positioned(self):
        """fbk-coherence-review/SKILL.md documents cited-source injection after normalize and before verification instructions."""
        self._assert_cited_source_injection(_COHERENCE_REVIEW_SKILL, "fbk-coherence-review/SKILL.md")

    def test_task_review_cited_source_injection_positioned(self):
        """fbk-task-review/SKILL.md documents cited-source injection after normalize and before verification instructions."""
        self._assert_cited_source_injection(_TASK_REVIEW_SKILL, "fbk-task-review/SKILL.md")
