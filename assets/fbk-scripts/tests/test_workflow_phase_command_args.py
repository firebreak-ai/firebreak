"""A phase command's first word names the unit; any text after it is the operator's request.

Both hook entries are covered: the operator typing the command (UserPromptExpansion) and the
model invoking the Skill tool (PreToolUse).
"""

from pathlib import Path

import pytest
from fbk.workflow import hooks, store

from tests import test_workflow_lifecycle as scenarios

project = scenarios.project

ASSETS = Path(__file__).resolve().parents[2]
PHASE_SKILLS = ("fbk-intent", "fbk-design", "fbk-spec", "fbk-breakdown", "fbk-implement")

REQUESTS = {
    "plain": "feature count the words in the request text",
    "apostrophe": "feature don't release the resource twice",
    "unbalanced-quote": 'feature keep the "draft wording as is',
}


def typed(root, args, skill="fbk-intent"):
    return hooks.handle(root, {
        "hook_event_name": "UserPromptExpansion", "session_id": "s", "cwd": str(root),
        "command_name": skill, "command_args": args,
    })


def invoked(root, args, skill="fbk-intent"):
    tool_input = {"skill": skill} if args is None else {"skill": skill, "args": args}
    return hooks.handle(root, {
        "hook_event_name": "PreToolUse", "session_id": "s", "cwd": str(root),
        "tool_name": "Skill", "tool_input": tool_input,
    })


def assert_intent_opened(root, result):
    output = result.get("hookSpecificOutput", {})
    assert "decision" not in result, result
    assert output.get("permissionDecision") != "deny", result
    assert store.load(root, "feature")["open_phase"] == "intent", result


@pytest.mark.parametrize("args", REQUESTS.values(), ids=REQUESTS.keys())
def test_typed_command_with_request_opens_phase_for_first_word_unit(project, args):
    """Red: the unit parser requires exactly one shell word, so extra text is refused and an
    unmatched quote surfaces a raw quoting error instead of opening the phase."""
    result = typed(project, args)
    assert_intent_opened(project, result)
    assert "feature, intent is open" in result["hookSpecificOutput"]["additionalContext"]


@pytest.mark.parametrize("args", REQUESTS.values(), ids=REQUESTS.keys())
def test_skill_tool_with_request_opens_phase_for_first_word_unit(project, args):
    """Red: the Skill tool path uses the same one-word parser, so the model invoking the skill
    with the operator's request is denied."""
    assert_intent_opened(project, invoked(project, args))


@pytest.mark.parametrize("entry", [typed, invoked], ids=["typed", "skill-tool"])
def test_runtime_prefix_and_trailing_slash_are_stripped_before_a_request(project, entry):
    """Red: with extra text the parser refuses before it strips the .fbk/ prefix and the
    trailing slash from the unit word."""
    assert_intent_opened(project, entry(project, ".fbk/feature/ write down what it is for"))


@pytest.mark.parametrize("args", ["", "   ", "\t\n", None], ids=["empty", "spaces", "tab-newline", "missing"])
@pytest.mark.parametrize("entry", [typed, invoked], ids=["typed", "skill-tool"])
def test_no_unit_still_gets_name_one_unit_refusal(project, entry, args):
    """Guard: the first-word rule must not turn missing arguments into an index error or a
    phase opened for an empty unit name; the operator still gets the named refusal."""
    result = entry(project, args)
    reason = result.get("reason") or result["hookSpecificOutput"].get("permissionDecisionReason", "")
    assert "Name one unit" in reason
    assert store.load(project, "feature")["open_phase"] is None


@pytest.mark.parametrize("args", ["feature", ".fbk/feature/", "  feature  "])
@pytest.mark.parametrize("entry", [typed, invoked], ids=["typed", "skill-tool"])
def test_single_word_unit_still_opens_phase(project, entry, args):
    """Guard: a command naming only the unit keeps working after the change to first-word
    parsing."""
    assert_intent_opened(project, entry(project, args))


def _frontmatter_and_body(skill):
    text = (ASSETS / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    _, frontmatter, body = text.split("---", 2)
    return frontmatter, body


@pytest.mark.parametrize("skill", PHASE_SKILLS)
def test_phase_skill_argument_hint_names_unit_and_request(skill):
    """Red: the argument hint shows only the unit name, so the operator is not told that a
    request may follow it."""
    frontmatter, _ = _frontmatter_and_body(skill)
    hints = [line for line in frontmatter.splitlines() if line.startswith("argument-hint:")]
    assert hints == ['argument-hint: "<unit-name> [request]"']


@pytest.mark.parametrize("skill", PHASE_SKILLS)
def test_phase_skill_body_says_text_after_unit_is_operator_request(skill):
    """Red: no phase skill tells the model that the text after the unit name is the
    operator's request, so the model may ignore it or treat it as part of the unit."""
    _, body = _frontmatter_and_body(skill)
    lines = [line.lower() for line in body.splitlines()]
    assert any("unit" in line and "request" in line for line in lines), skill
