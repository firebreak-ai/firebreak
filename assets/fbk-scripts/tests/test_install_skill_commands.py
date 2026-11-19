"""Installed skill commands must work without another Firebreak installation.

These are executable documentation checks, not simulated model reviews. Extract
the command the skill actually supplies, fill its documented parameters, and
exercise the installed dispatcher and lens with a small reviewer response.
"""

import json
import os
from pathlib import Path
import re
import shlex
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module", params=["project", "global"])
def installed_skill_environment(request, tmp_path_factory):
    sandbox = tmp_path_factory.mktemp(f"skill-{request.param}")
    home = sandbox / "home"
    project = sandbox / "review project"
    home.mkdir()
    project.mkdir()
    target = (project if request.param == "project" else home) / ".claude"
    env = {**os.environ, "HOME": str(home), "CLAUDE_PROJECT_DIR": str(project)}
    # Share only the package cache; HOME and all installed assets stay isolated.
    env.setdefault("UV_CACHE_DIR", str(Path.home() / ".cache/uv"))
    env.pop("PYTHONPATH", None)
    env.pop("VIRTUAL_ENV", None)
    result = subprocess.run(
        ["bash", str(ROOT / "installer/install.sh"), "--source", str(ROOT / "assets"),
         "--target", str(target)],
        cwd=project, env=env, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, f"Install failed:\n{result.stdout}\n{result.stderr}"
    assert (target / "fbk-scripts/fbk.py").is_file()
    if request.param == "project":
        assert not (home / ".claude").exists(), "Project-only test has a global install"
    return target, project, env


def skill_command(target, skill, operation):
    text = (target / "skills" / skill / "SKILL.md").read_text()
    # Skills use both fenced shell examples and inline executable commands.
    snippets = re.findall(r"```[^\n]*\n(.*?)```|`([^`\n]+)`", text, re.DOTALL)
    commands = [fenced or inline for fenced, inline in snippets
                if "fbk.py" in (fenced or inline) and operation in (fenced or inline)]
    assert commands, f"No executable {operation!r} example found in {skill}"
    return commands[0].strip()


@pytest.mark.parametrize("skill,operation,finding_type", [
    ("fbk-code-review", "pipeline run", "behavioral"),
    ("fbk-cross-model-review", "cross-review --check-opt-in", None),
])
def test_installed_standalone_skill_command(installed_skill_environment, skill,
                                           operation, finding_type):
    target, project, env = installed_skill_environment
    command = skill_command(target, skill, operation)
    for parameter, value in {"<root>": str(project), "<preset>": "behavioral-only",
                             "<threshold>": "minor"}.items():
        command = command.replace(parameter, shlex.quote(value))
    finding = {
        "title": "Missing rejection of an invalid request",
        "location": {"file": "handler.py", "start_line": 12},
        "type": finding_type,
        "severity": "major",
        "mechanism": "The invalid request reaches the handler without validation.",
        "consequence": "The caller receives success for an invalid request.",
        "evidence": "An invalid request returns success in the reproduction.",
    }
    result = subprocess.run(
        ["bash", "-o", "pipefail", "-c", command],
        cwd=project, env=env, input=json.dumps([finding]) if finding_type else "",
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, (
        f"{skill} command failed in {project}:\n{command}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    output = json.loads(result.stdout)
    if finding_type:
        assert len(output) == 1, f"Installed pipeline lost a valid finding: {output}"
        assert output[0]["title"] == finding["title"]
        assert output[0]["type"] == finding_type
    else:
        # The clean project has not opted in. This exercises startup without
        # credentials, external model calls, or an existing workflow directory.
        assert output["status"] == "skipped", output


def test_installed_test_review_binds_lens_without_code_domain_filter(installed_skill_environment):
    target, project, env = installed_skill_environment
    instructions = project / ".fbk/runtime/test-review-instructions.txt"
    instructions.parent.mkdir(parents=True, exist_ok=True)
    instructions.write_text("Inspect tests against spec; retain coverage evidence.")
    (project / "spec.md").write_text("The result must equal two.")
    command = skill_command(target, "fbk-test-review", "review-round begin")
    command = command.replace("<governing-project-paths>", "spec.md")
    result = subprocess.run(
        ["bash", "-o", "pipefail", "-c", command], cwd=project, env=env,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["code_review"]["preset"] is None
    assert "untested-behavior" in output["code_review"]["lens_text"]
    assert output["required_files"] == ["spec.md"]
