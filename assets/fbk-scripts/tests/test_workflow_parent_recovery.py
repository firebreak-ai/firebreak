"""A parent contract update must leave an in-progress child recoverable."""

import pytest
from fbk.workflow import cli, review, store

from tests import test_workflow_lifecycle as scenarios

project = scenarios.project


def call(root, command, *arguments, session="s"):
    args = cli.parser_for(command).parse_args(
        [*arguments, "--root", str(root), "--session", session]
    )
    return cli.execute(command, args)


def test_suspended_child_can_adopt_updated_parent_and_finish_initial_intent(
    project, monkeypatch
):
    monkeypatch.setattr(review, "review", scenarios.clean_review)
    for phase in ("intent", "spec"):
        call(project, "phase-enter", phase, "feature")
        call(project, "phase-close", phase, "feature")
        scenarios.observe_phase(project, phase)

    call(project, "unit-init", "child", "--parent", "feature", "--design", "off")
    draft = project / ".fbk/child/prd.md"
    draft_text = "Expose cancellation to callers and report whether the task was canceled."
    draft.write_text(draft_text)
    call(project, "phase-enter", "intent", "child", session="child-author")

    # The parent changes in another session while the child's first phase is open.
    reason = "Cancellation must wait for pending I/O before releasing the resource."
    call(project, "approve", "feature", "reopen", "--phase", "spec", "--reason", reason)
    call(project, "phase-close", "spec", "feature", "--reopen", "--reason", reason)
    (project / ".fbk/feature/spec.md").write_text(
        "# Cancellation contract\n\n## Requirements\n\n### Wait for pending I/O\n\n"
        f"{reason} Serves [Release on cancel](prd.md#release-on-cancel).\n"
    )
    call(project, "phase-enter", "spec", "feature")
    call(project, "phase-close", "spec", "feature")
    scenarios.observe_phase(project, "spec")

    # New parent acceptance must not silently authorize the child's existing work.
    assert call(project, "status", "child")[0]["status"] == "stale"
    with pytest.raises(store.WorkflowError):
        call(project, "phase-enter", "intent", "child", session="child-author")
    with pytest.raises(store.WorkflowError):
        call(project, "phase-close", "intent", "child", session="child-author")

    call(
        project,
        "suspend",
        "child",
        "--reason",
        "Review the updated parent contract before continuing.",
        session="child-author",
    )
    # No child phase has been accepted yet: recovery cannot require reopening one.
    call(
        project,
        "acknowledge-parent",
        "child",
        "--reason",
        "The child's cancellation outcome remains compatible with the updated contract.",
        session="next-child-author",
    )
    assert draft.read_text() == draft_text
    call(project, "phase-enter", "intent", "child", session="next-child-author")
    result = call(
        project, "phase-close", "intent", "child", session="next-child-author"
    )
    assert (result["phase"], result["status"]) == ("spec", "ready")
    assert result["accepted_phase"] == "intent"
    status = call(project, "status", "child")[0]
    assert (status["phase"], status["status"]) == ("spec", "ready")
