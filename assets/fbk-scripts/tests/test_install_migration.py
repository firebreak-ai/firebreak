"""Upgrade removes owned settings while preserving operator customizations."""

import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("merge_settings", Path(__file__).parents[3] / "installer/merge-settings.py")
merge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(merge)


def test_upgrade_replaces_owned_hooks_and_keeps_mixed_group_additions():
    old_hook = {"type": "command", "command": "python3 retired-hook.py"}
    user_hook = {"type": "command", "command": "python3 user-hook.py"}
    old_group = {"matcher": "Write", "hooks": [old_hook]}
    new_group = {"hooks": [{"type": "command", "command": "python3 workflow-hook.py"}]}
    previous = {"hooks_added": {"PreToolUse": [old_group]}, "env_added": {"OLD_SETTING": "on"}}
    existing = {"hooks": {"PreToolUse": [{**old_group, "hooks": [old_hook, user_hook]}]},
                "env": {"OLD_SETTING": "on", "USER_SETTING": "keep"}, "permissions": {"allow": ["Read"]}}
    incoming = {"hooks": {"PreToolUse": [new_group]}}
    merged, owned = merge.merge_settings(existing, incoming, previous)
    assert merged["hooks"]["PreToolUse"] == [{**old_group, "hooks": [user_hook]}, new_group]
    assert merged["env"] == {"USER_SETTING": "keep"}
    assert merged["permissions"] == existing["permissions"]
    again, again_owned = merge.merge_settings(merged, incoming, owned)
    assert again == merged
    assert again_owned == owned


def test_operator_modified_settings_are_preserved():
    old = {"hooks": [{"command": "old"}]}
    changed = {"hooks": [{"command": "operator version"}]}
    existing = {"hooks": {"Stop": [changed]}, "env": {"SETTING": "custom"}}
    previous = {"hooks_added": {"Stop": [old]}, "env_added": {"SETTING": "default"}}
    result, _ = merge.merge_settings(existing, {}, previous)
    assert result == existing
