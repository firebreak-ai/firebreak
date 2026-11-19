#!/usr/bin/env python3
"""Merge firebreak settings entries into an existing settings.json."""

import argparse
import json
import os
import sys



def load_json(file_path):
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, "r") as f:
            content = f.read().strip()
        if not content:
            return {}
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Error: Malformed JSON in {file_path}: {e}", file=sys.stderr)
        sys.exit(1)


def merge_hooks(existing_hooks, new_hooks):
    merged = {k: list(v) for k, v in existing_hooks.items()}
    hooks_added = {}

    for event, new_groups in new_hooks.items():
        if event not in merged:
            merged[event] = list(new_groups)
            hooks_added[event] = list(new_groups)
        else:
            existing_canonical = {json.dumps(g, sort_keys=True) for g in merged[event]}
            added_groups = []
            for group in new_groups:
                canonical = json.dumps(group, sort_keys=True)
                if canonical not in existing_canonical:
                    merged[event].append(group)
                    existing_canonical.add(canonical)
                    added_groups.append(group)
            if added_groups:
                hooks_added[event] = added_groups

    return merged, hooks_added


def remove_owned_settings(existing, previous):
    """Remove unchanged installer-owned entries before merging the next release.

    Compare individual hooks within matching groups so operator additions survive.
    Modified settings are left in the operator's ownership.
    """
    result = dict(existing)
    hooks = {}
    for event, groups in existing.get("hooks", {}).items():
        owned = previous.get("hooks_added", {}).get(event, [])
        kept_groups = []
        for group in groups:
            metadata = {k: v for k, v in group.items() if k != "hooks"}
            owned_hooks = [h for old in owned
                           if {k: v for k, v in old.items() if k != "hooks"} == metadata
                           for h in old.get("hooks", [])]
            kept = [h for h in group.get("hooks", []) if h not in owned_hooks]
            if kept or not group.get("hooks"):
                kept_groups.append({**group, "hooks": kept})
        if kept_groups:
            hooks[event] = kept_groups
    result["hooks"] = hooks
    result["env"] = {k: v for k, v in existing.get("env", {}).items()
                     if k not in previous.get("env_added", {})
                     or previous["env_added"][k] != v}
    return result


def merge_env(existing_env, new_env):
    merged = dict(existing_env)
    env_added = {}

    for key, value in new_env.items():
        if key not in merged:
            merged[key] = value
            env_added[key] = value

    return merged, env_added


def merge_settings(existing, new_entries, previous=None):
    if previous:
        existing = remove_owned_settings(existing, previous)
    existing_hooks = existing.get("hooks", {})

    merged_hooks, hooks_added = merge_hooks(
        existing_hooks, new_entries.get("hooks", {})
    )
    merged_env, env_added = merge_env(
        existing.get("env", {}), new_entries.get("env", {})
    )

    result = dict(existing)
    if merged_hooks:
        result["hooks"] = merged_hooks
    if merged_env:
        result["env"] = merged_env

    manifest = {"hooks_added": hooks_added, "env_added": env_added}
    return result, manifest


def main():
    parser = argparse.ArgumentParser(
        description="Merge firebreak settings entries into an existing settings.json."
    )
    parser.add_argument("existing_path", help="Path to existing settings.json")
    parser.add_argument("new_entries_path", help="Path to firebreak settings JSON")
    args = parser.parse_args()

    if not os.path.exists(args.new_entries_path):
        print(f"Error: new entries file not found: {args.new_entries_path}", file=sys.stderr)
        sys.exit(1)

    existing = load_json(args.existing_path)
    new_entries = load_json(args.new_entries_path)

    previous_path = os.path.join(os.path.dirname(args.existing_path), ".firebreak-manifest.json")
    previous = load_json(previous_path).get("settings_entries", {})
    merged, manifest = merge_settings(existing, new_entries, previous)

    print(json.dumps(merged, indent=2))
    print("---MANIFEST---")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
