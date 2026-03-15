#!/usr/bin/env python3
"""Config loader — merges layered configuration and performs cold-start detection."""

import argparse
import glob
import json
import os
import sys

import yaml

DEFAULTS = {
    "token_budget": None,
    "max_concurrent_agents": 1,
    "replan_cap": 2,
    "model": "sonnet",
}


def load_yaml(file_path):
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path) as f:
            result = yaml.safe_load(f)
            return result if isinstance(result, dict) else {}
    except yaml.YAMLError as e:
        print(f"Error: failed to parse {file_path}: {e}", file=sys.stderr)
        sys.exit(1)


def parse_frontmatter(spec_path):
    if not spec_path or not os.path.exists(spec_path):
        return {}
    with open(spec_path) as f:
        lines = f.readlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}
    frontmatter = "".join(lines[1:end])
    try:
        result = yaml.safe_load(frontmatter)
        return result if isinstance(result, dict) else {}
    except yaml.YAMLError:
        return {}


def merge_configs(*dicts):
    result = {}
    for d in dicts:
        for key, value in d.items():
            if (
                isinstance(value, dict)
                and key in result
                and isinstance(result[key], dict)
            ):
                result[key] = merge_configs(result[key], value)
            else:
                result[key] = value
    return result


def load_config(project_root, spec_path=None):
    project_config = load_yaml(
        os.path.join(project_root, ".claude", "automation", "config.yml")
    )
    spec_config = parse_frontmatter(spec_path)
    merged = merge_configs(DEFAULTS, project_config, spec_config)
    print(json.dumps(merged, indent=2))


def load_verify(project_root):
    path = os.path.join(project_root, ".claude", "automation", "verify.yml")
    data = load_yaml(path)
    print(json.dumps(data, indent=2))


def cold_start_check(project_root):
    # Check test runner
    test_files = [
        "package.json", "Cargo.toml", "go.mod", "pytest.ini", "pyproject.toml"
    ]
    has_test_runner = any(
        os.path.exists(os.path.join(project_root, f)) for f in test_files
    )
    if not has_test_runner:
        makefile = os.path.join(project_root, "Makefile")
        if os.path.exists(makefile):
            with open(makefile) as f:
                if "test:" in f.read():
                    has_test_runner = True
    if not has_test_runner:
        print(
            f"Warning: No test runner detected in {project_root}", file=sys.stderr
        )

    # Check linting config
    has_lint = bool(glob.glob(os.path.join(project_root, ".eslintrc*")))
    if not has_lint:
        if os.path.exists(os.path.join(project_root, ".golangci.yml")):
            has_lint = True
    if not has_lint:
        pyproject = os.path.join(project_root, "pyproject.toml")
        if os.path.exists(pyproject):
            with open(pyproject) as f:
                content = f.read()
                if "ruff" in content or "flake8" in content:
                    has_lint = True
    if not has_lint:
        print(
            f"Warning: No linting configuration detected in {project_root}",
            file=sys.stderr,
        )

    # Check CLAUDE.md
    if not os.path.exists(os.path.join(project_root, "CLAUDE.md")):
        print(
            f"Warning: No CLAUDE.md detected in {project_root}", file=sys.stderr
        )


def main():
    parser = argparse.ArgumentParser(description="Config loader")
    sub = parser.add_subparsers(dest="command")

    p_load = sub.add_parser("load")
    p_load.add_argument("project_root")
    p_load.add_argument("spec_path", nargs="?", default=None)

    p_verify = sub.add_parser("load-verify")
    p_verify.add_argument("project_root")

    p_cold = sub.add_parser("cold-start-check")
    p_cold.add_argument("project_root")

    args = parser.parse_args()

    if args.command == "load":
        load_config(args.project_root, args.spec_path)
    elif args.command == "load-verify":
        load_verify(args.project_root)
    elif args.command == "cold-start-check":
        cold_start_check(args.project_root)
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
