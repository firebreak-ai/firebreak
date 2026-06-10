"""Integration tests for installer settings migration.

Covers anchored duplicate-registration removal (AC-19):
- Leftover project-level router registration removed after merge
- Unrelated operator-added hook entry left byte-intact
- Second installer run is idempotent
- Global router registration resolves to the global fbk-scripts path
- .fbk-capture/ is gitignored by the installer
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# The test file lives at assets/fbk-scripts/tests/; parents[3] is the repo root.
_REPO_ROOT = Path(__file__).parents[3]
_INSTALLER_DIR = _REPO_ROOT / "installer"

# Load merge-settings.py by path — its hyphenated name requires spec_from_file_location.
_MERGE_SETTINGS_PATH = _INSTALLER_DIR / "merge-settings.py"
_merge_settings_spec = importlib.util.spec_from_file_location(
    "merge_settings", str(_MERGE_SETTINGS_PATH)
)
merge_settings_mod = importlib.util.module_from_spec(_merge_settings_spec)
_merge_settings_spec.loader.exec_module(merge_settings_mod)

# The old per-project command string the prototype shipped.
_OLD_COMMAND = 'python3 "$CLAUDE_PROJECT_DIR"/hooks/hook_router.py'

# The global command form the new template ships (uses $HOME path, not $CLAUDE_PROJECT_DIR).
_GLOBAL_COMMAND_PREFIX = '"$HOME"/.claude/fbk-scripts'

# Skip all tests in this file if remove_hook_command is not yet implemented.
_remove_hook_command = getattr(merge_settings_mod, "remove_hook_command", None)
_missing_removal = _remove_hook_command is None

pytestmark = pytest.mark.skipif(
    _missing_removal,
    reason="remove_hook_command not yet implemented in merge-settings.py (red phase)",
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def old_router_entry():
    """A hook group carrying the old per-project router command."""
    return {"hooks": [{"type": "command", "command": _OLD_COMMAND, "timeout": 15}]}


@pytest.fixture
def unrelated_entry():
    """An operator-added hook entry with a different command, unrelated to the router."""
    return {"hooks": [{"type": "command", "command": "python3 /usr/local/bin/my-custom-hook.py"}]}


@pytest.fixture
def global_router_entry():
    """The new global router hook group the template ships."""
    return {
        "hooks": [
            {
                "type": "command",
                "command": 'python3 "$HOME"/.claude/fbk-scripts/fbk/capture/hook_router.py',
                "timeout": 15,
            }
        ]
    }


@pytest.fixture
def settings_with_leftover(old_router_entry, unrelated_entry):
    """A settings dict carrying both the old per-project registration and an unrelated entry."""
    return {
        "hooks": {
            "PreToolUse": [old_router_entry, unrelated_entry],
        }
    }


@pytest.fixture
def new_entries_template(global_router_entry):
    """The settings template carrying the global router registration."""
    return {
        "hooks": {
            "PreToolUse": [global_router_entry],
        },
        "gitignore": [".fbk-capture/"],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLeftoverProjectRegistrationRemoved:
    """After merge+removal, the old per-project router command is gone; exactly one global remains."""

    def test_leftover_project_registration_removed(
        self, settings_with_leftover, new_entries_template
    ):
        """Old $CLAUDE_PROJECT_DIR/hooks/hook_router.py entry removed; exactly one global registration remains."""
        merged, _ = merge_settings_mod.merge_settings(
            settings_with_leftover, new_entries_template
        )

        hooks_after = merge_settings_mod.remove_hook_command(
            merged["hooks"], _OLD_COMMAND
        )

        # Collect all command strings across all events.
        all_commands = [
            hook["command"]
            for entries in hooks_after.values()
            for group in entries
            for hook in group.get("hooks", [])
        ]

        # The old per-project path must be absent.
        assert _OLD_COMMAND not in all_commands, (
            "old $CLAUDE_PROJECT_DIR/hooks/hook_router.py entry was not removed"
        )

        # Exactly one router registration (the global one) must remain.
        router_commands = [c for c in all_commands if "hook_router.py" in c]
        assert len(router_commands) == 1, (
            f"expected exactly one router registration, found {len(router_commands)}: {router_commands}"
        )


class TestMergeStripsLeftoverWithoutSeparateRemovalCall:
    """merge_settings itself must strip a leftover router registration.

    These tests drive the real installer entry point (merge_settings) ONLY —
    they do NOT call remove_hook_command separately. They fail if the strip is
    not wired into merge_settings, which is the behavior the installer actually
    runs.
    """

    def test_merge_alone_removes_leftover_project_router(
        self, settings_with_leftover, new_entries_template
    ):
        """A single merge_settings call leaves exactly one router command, the global one."""
        merged, _ = merge_settings_mod.merge_settings(
            settings_with_leftover, new_entries_template
        )

        all_commands = [
            hook["command"]
            for entries in merged["hooks"].values()
            for group in entries
            for hook in group.get("hooks", [])
        ]

        assert _OLD_COMMAND not in all_commands, (
            "merge_settings did not strip the leftover $CLAUDE_PROJECT_DIR router "
            "registration — the migration is not wired into the merge path"
        )

        router_commands = [c for c in all_commands if "hook_router.py" in c]
        assert len(router_commands) == 1, (
            f"expected exactly one router registration after merge_settings alone, "
            f"found {len(router_commands)}: {router_commands}"
        )
        assert "$CLAUDE_PROJECT_DIR" not in router_commands[0]
        assert _GLOBAL_COMMAND_PREFIX in router_commands[0]

    def test_merge_alone_preserves_unrelated_entry(
        self, settings_with_leftover, new_entries_template, unrelated_entry
    ):
        """The strip inside merge_settings leaves unrelated operator hooks intact."""
        merged, _ = merge_settings_mod.merge_settings(
            settings_with_leftover, new_entries_template
        )
        all_groups = [
            group for entries in merged["hooks"].values() for group in entries
        ]
        assert unrelated_entry in all_groups, (
            "merge_settings dropped an unrelated operator hook while stripping the router"
        )

    def test_merge_alone_is_idempotent(
        self, settings_with_leftover, new_entries_template
    ):
        """Feeding merge_settings output back in produces an identical result."""
        once, _ = merge_settings_mod.merge_settings(
            settings_with_leftover, new_entries_template
        )
        twice, _ = merge_settings_mod.merge_settings(once, new_entries_template)
        assert twice == once, (
            "a second merge_settings run changed the result — strip+re-add is not idempotent"
        )


class TestUnrelatedHookLeftByteIntact:
    """An operator-added hook entry unrelated to the router survives the migration unchanged."""

    def test_unrelated_hook_left_byte_intact(
        self, settings_with_leftover, new_entries_template, unrelated_entry
    ):
        """Unrelated operator hook entry is byte-identical to its input after merge+removal."""
        merged, _ = merge_settings_mod.merge_settings(
            settings_with_leftover, new_entries_template
        )

        hooks_after = merge_settings_mod.remove_hook_command(
            merged["hooks"], _OLD_COMMAND
        )

        # Collect all hook groups across all events.
        all_groups = [
            group
            for entries in hooks_after.values()
            for group in entries
        ]

        assert unrelated_entry in all_groups, (
            "unrelated operator hook entry was not preserved byte-intact after migration"
        )


class TestSecondRunIsIdempotent:
    """A second migration run over its own output produces no further change."""

    def test_second_run_is_idempotent(self, settings_with_leftover, new_entries_template):
        """Running merge+removal twice yields the same result as running it once."""
        # First run.
        merged_once, _ = merge_settings_mod.merge_settings(
            settings_with_leftover, new_entries_template
        )
        hooks_once = merge_settings_mod.remove_hook_command(
            merged_once["hooks"], _OLD_COMMAND
        )
        first_result = dict(merged_once)
        first_result["hooks"] = hooks_once

        # Second run: feed the first result back in.
        merged_twice, _ = merge_settings_mod.merge_settings(
            first_result, new_entries_template
        )
        hooks_twice = merge_settings_mod.remove_hook_command(
            merged_twice["hooks"], _OLD_COMMAND
        )
        second_result = dict(merged_twice)
        second_result["hooks"] = hooks_twice

        assert second_result == first_result, (
            "second migration run changed the settings — migration is not idempotent"
        )


class TestGlobalRegistrationResolvesToGlobalPath:
    """The merged router command uses the global $HOME path, not $CLAUDE_PROJECT_DIR."""

    def test_global_registration_resolves_to_global_path(
        self, settings_with_leftover, new_entries_template
    ):
        """Router registration after migration points under $HOME/.claude/fbk-scripts, not per-project."""
        merged, _ = merge_settings_mod.merge_settings(
            settings_with_leftover, new_entries_template
        )
        hooks_after = merge_settings_mod.remove_hook_command(
            merged["hooks"], _OLD_COMMAND
        )

        router_commands = [
            hook["command"]
            for entries in hooks_after.values()
            for group in entries
            for hook in group.get("hooks", [])
            if "hook_router.py" in hook.get("command", "")
        ]

        assert len(router_commands) >= 1, "no router registration found after migration"

        for cmd in router_commands:
            assert "$CLAUDE_PROJECT_DIR" not in cmd, (
                f"router command still uses per-project $CLAUDE_PROJECT_DIR path: {cmd!r}"
            )
            assert _GLOBAL_COMMAND_PREFIX in cmd, (
                f"router command does not point under global fbk-scripts tree: {cmd!r}"
            )


class TestCaptureDirGitignored:
    """The installer's merged output carries a .fbk-capture/ gitignore directive."""

    def test_capture_dir_gitignored(self, settings_with_leftover, new_entries_template):
        """.fbk-capture/ is covered by the gitignore directive the merge template ships."""
        merged, _ = merge_settings_mod.merge_settings(
            settings_with_leftover, new_entries_template
        )

        # The template ships a "gitignore" key that the installer shell consumes.
        gitignore_entries = merged.get("gitignore", [])
        assert ".fbk-capture/" in gitignore_entries, (
            ".fbk-capture/ not found in the merged gitignore entries; "
            "the template must carry this directive so the installer shell can apply it"
        )
