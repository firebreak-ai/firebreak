"""Structural asset tests for the cross-model-review skill wiring.

These tests are RED until task-05 (SKILL.md) and task-06 (reference doc) are
authored.  They pin the load-bearing wiring facts of AC-10: the skill checks
the opt-in first, names both lenses, calls the runner with the required flags,
and the reference doc exists at the expected path.

Stated limitation: these tests prove the documented wiring is present and
ordered, not that the running skill behaves correctly.  UV-1 through UV-5 are
the behavior gate.  This test pins the skill wiring.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Asset paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parents[3]

_SKILL = _REPO_ROOT / "assets" / "skills" / "fbk-cross-model-review" / "SKILL.md"
_REFERENCE_DOC = (
    _REPO_ROOT
    / "assets"
    / "skills"
    / "fbk-cross-model-review"
    / "references"
    / "cross-model-review-guide.md"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read(path: Path) -> str:
    """Return the text of an asset file.

    Raises FileNotFoundError (red-phase failure) when the asset does not exist.
    """
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Opt-in check ordering
# ---------------------------------------------------------------------------


class TestOptInOrdering:
    """fbk-cross-model-review/SKILL.md documents the opt-in check before the main runner invocation (AC-10).

    The skill must gate on ``cross-review --check-opt-in`` before invoking
    ``cross-review --prompt-file`` so that projects without the opt-in flag are
    rejected at the earliest opportunity.

    RED before task-05 authors SKILL.md.
    """

    def test_opt_in_check_present(self):
        """SKILL.md contains the opt-in check token 'cross-review --check-opt-in'."""
        text = _read(_SKILL)
        assert "cross-review --check-opt-in" in text, (
            "fbk-cross-model-review/SKILL.md must contain the token "
            "'cross-review --check-opt-in' to document the opt-in gate step"
        )

    def test_main_invocation_present(self):
        """SKILL.md contains the main runner invocation token 'cross-review --prompt-file'."""
        text = _read(_SKILL)
        assert "cross-review --prompt-file" in text, (
            "fbk-cross-model-review/SKILL.md must contain the token "
            "'cross-review --prompt-file' to document the main runner invocation"
        )

    def test_opt_in_check_precedes_main_invocation(self):
        """'cross-review --check-opt-in' appears before 'cross-review --prompt-file' in SKILL.md.

        The opt-in gate must be documented before the main runner call so the
        skill instructs the agent to short-circuit before any expensive invocation.
        """
        text = _read(_SKILL)

        opt_in_pos = text.find("cross-review --check-opt-in")
        assert opt_in_pos != -1, (
            "fbk-cross-model-review/SKILL.md must contain 'cross-review --check-opt-in'"
        )

        main_pos = text.find("cross-review --prompt-file")
        assert main_pos != -1, (
            "fbk-cross-model-review/SKILL.md must contain 'cross-review --prompt-file'"
        )

        assert opt_in_pos < main_pos, (
            f"'cross-review --check-opt-in' (offset {opt_in_pos}) must appear "
            f"before 'cross-review --prompt-file' (offset {main_pos}); "
            "the opt-in check must be documented first so the agent gates on it "
            "before invoking the runner"
        )


# ---------------------------------------------------------------------------
# Lens references
# ---------------------------------------------------------------------------


class TestLensReferences:
    """fbk-cross-model-review/SKILL.md names both supported lenses (AC-10).

    The skill must reference both ``fresh-eyes-lens`` and ``code-lens`` so the
    agent knows which lens identifiers to pass to the runner.

    RED before task-05 authors SKILL.md.
    """

    def test_fresh_eyes_lens_referenced(self):
        """SKILL.md contains the substring 'fresh-eyes-lens'."""
        text = _read(_SKILL)
        assert "fresh-eyes-lens" in text, (
            "fbk-cross-model-review/SKILL.md must reference 'fresh-eyes-lens' "
            "to document the available lens for fresh-eyes review mode"
        )

    def test_code_lens_referenced(self):
        """SKILL.md contains the substring 'code-lens'."""
        text = _read(_SKILL)
        assert "code-lens" in text, (
            "fbk-cross-model-review/SKILL.md must reference 'code-lens' "
            "to document the available lens for code review mode"
        )


# ---------------------------------------------------------------------------
# Runner flag wiring
# ---------------------------------------------------------------------------


class TestRunnerFlagWiring:
    """fbk-cross-model-review/SKILL.md documents the required runner flags (AC-10).

    The main ``cross-review`` invocation must carry ``--prompt-file``,
    ``--report-dir``, and ``--project-root`` flags so the agent constructs a
    complete, valid runner call.

    RED before task-05 authors SKILL.md.
    """

    def test_prompt_file_flag_present(self):
        """SKILL.md contains the runner flag '--prompt-file'."""
        text = _read(_SKILL)
        assert "--prompt-file" in text, (
            "fbk-cross-model-review/SKILL.md must contain '--prompt-file' "
            "to document the runner flag that selects the prompt"
        )

    def test_report_dir_flag_present(self):
        """SKILL.md contains the runner flag '--report-dir'."""
        text = _read(_SKILL)
        assert "--report-dir" in text, (
            "fbk-cross-model-review/SKILL.md must contain '--report-dir' "
            "to document the runner flag that sets the output directory"
        )

    def test_project_root_flag_present(self):
        """SKILL.md contains the runner flag '--project-root'."""
        text = _read(_SKILL)
        assert "--project-root" in text, (
            "fbk-cross-model-review/SKILL.md must contain '--project-root' "
            "to document the runner flag that identifies the project under review"
        )


# ---------------------------------------------------------------------------
# Reference doc existence
# ---------------------------------------------------------------------------


class TestReferenceDocExists:
    """The cross-model-review reference doc exists at the expected path and is non-empty (AC-10).

    The reference doc provides operational guidance that SKILL.md delegates to.
    Its absence means the skill lacks the supporting material the agent is
    directed to consult.

    RED before task-06 authors cross-model-review-guide.md.
    """

    def test_reference_doc_is_file(self):
        """cross-model-review-guide.md exists as a file at the expected path."""
        assert _REFERENCE_DOC.is_file(), (
            f"Reference doc not found at {_REFERENCE_DOC}; "
            "task-06 must author this file before the skill is complete"
        )

    def test_reference_doc_is_non_empty(self):
        """cross-model-review-guide.md has content (is not an empty file)."""
        assert _REFERENCE_DOC.is_file(), (
            f"Reference doc not found at {_REFERENCE_DOC}; "
            "cannot check content — file does not exist"
        )
        content = _REFERENCE_DOC.read_text(encoding="utf-8")
        assert len(content.strip()) > 0, (
            f"Reference doc at {_REFERENCE_DOC} is empty; "
            "task-06 must populate it with the cross-model-review guide"
        )


# ---------------------------------------------------------------------------
# Skill ↔ runner status contract
# ---------------------------------------------------------------------------


class TestSkillRunnerStatusContract:
    """SKILL.md must branch on the runner's ACTUAL JSON contract (AC-10, IF-D-02).

    The runner returns ``status`` of ``success`` / ``skipped`` / ``failed`` and
    carries the failure message in the ``cause`` field. A token-presence check
    alone does not catch a skill that branches on an invented status value
    (``ready``) or relays a field the runner never emits (``reason`` / ``error``)
    — that exact seam shipped and was caught only by a cross-model review.
    These tests pin the contract so the seam cannot regress.
    """

    def test_documents_real_status_values(self):
        """SKILL.md branches on success, skipped, and failed."""
        text = _read(_SKILL)
        for status in ("success", "skipped", "failed"):
            assert status in text, (
                f"fbk-cross-model-review/SKILL.md must branch on the runner's "
                f"'{status}' status value"
            )

    def test_no_invented_status_value(self):
        """SKILL.md does not branch on a 'ready' status the runner never returns."""
        text = _read(_SKILL)
        assert '"status": "ready"' not in text and "status: ready" not in text, (
            "fbk-cross-model-review/SKILL.md must not branch on a 'ready' status — "
            "the runner returns 'success' for an opted-in --check-opt-in result"
        )

    def test_failure_relays_cause_field(self):
        """SKILL.md's failed branch relays the 'cause' field, not 'reason'/'error'."""
        text = _read(_SKILL)
        assert "cause" in text, (
            "fbk-cross-model-review/SKILL.md's failed branch must relay the "
            "runner's 'cause' field"
        )
        assert "`reason`" not in text and "`error`" not in text, (
            "fbk-cross-model-review/SKILL.md must relay the 'cause' field — the "
            "runner never emits a 'reason' or 'error' field"
        )


class TestReferenceGuideStatusContract:
    """The reference guide must agree with the runner contract too (AC-10, B-007, IF-D-02).

    The skill-level contract test alone let a guide-level seam omission ship: the
    guide documented only the opt-in command and a generic ``<error message>``
    rather than the real runner invocation and the ``cause`` field. These tests
    pin the guide to the same contract so the two prose assets cannot diverge.
    """

    def test_guide_documents_main_runner_invocation(self):
        """The guide shows the full runner command, not just --check-opt-in."""
        text = _read(_REFERENCE_DOC)
        assert "cross-review --prompt-file" in text, (
            "cross-model-review-guide.md must document the main runner invocation "
            "'cross-review --prompt-file ...', not only the opt-in command"
        )

    def test_guide_relays_cause_field(self):
        """The guide's failure wording names the 'cause' field, not 'reason'/'error'."""
        text = _read(_REFERENCE_DOC)
        assert "cause" in text, (
            "cross-model-review-guide.md must relay the runner's 'cause' field on failure"
        )
        assert "`reason`" not in text and "`error`" not in text, (
            "cross-model-review-guide.md must use the 'cause' field — the runner "
            "never emits 'reason'/'error'"
        )

    def test_guide_documents_real_status_values(self):
        """The guide branches on success, skipped, and failed."""
        text = _read(_REFERENCE_DOC)
        for status in ("success", "skipped", "failed"):
            assert status in text, (
                f"cross-model-review-guide.md must document the runner's '{status}' status"
            )
