"""Task reviewer gate validation logic."""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Set

try:
    import yaml
except ImportError:
    yaml = None


def parse_frontmatter(content: str) -> Dict:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Raw markdown content string

    Returns:
        Dictionary of parsed frontmatter fields, or empty dict if parse fails
    """
    lines = content.split('\n')
    if not lines or lines[0].strip() != '---':
        return {}

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end = i
            break

    if end is None:
        return {}

    fm_text = '\n'.join(lines[1:end])
    if not yaml:
        return {}

    try:
        result = yaml.safe_load(fm_text)
        return result if isinstance(result, dict) else {}
    except yaml.YAMLError:
        return {}


def find_project_root(start: str) -> str:
    """Walk up from start directory to find project root marker.

    Args:
        start: Starting directory path

    Returns:
        Project root path
    """
    current = os.path.abspath(start)
    while current != os.path.dirname(current):
        markers = ['.git', 'go.mod', 'package.json', 'Cargo.toml', 'pyproject.toml', 'Makefile']
        if any(os.path.exists(os.path.join(current, m)) for m in markers):
            return current
        current = os.path.dirname(current)
    return os.path.abspath('.')


def _run_validations(
    tasks: Dict[str, Dict],
    spec_acs: Set[str],
    project_root: Optional[str] = None,
    category: str = "feature"
) -> List[str]:
    """Run all validation checks on parsed task data.

    Args:
        tasks: Dict mapping task filenames to parsed frontmatter dicts
        spec_acs: Set of AC identifiers from the spec (e.g., {'AC-01', 'AC-02'})
        project_root: Root directory for resolving file paths
        category: Task category: 'feature', 'corrective', or 'testing-infrastructure'

    Returns:
        List of failure messages. Empty list indicates all validations pass.
    """
    failures = []

    if not yaml:
        return ["Error: PyYAML required"]

    VALID_CATEGORIES = {"feature", "corrective", "testing-infrastructure"}
    required_fields = ['id', 'type', 'wave', 'covers', 'completion_gate']

    # Validate category
    if category not in VALID_CATEGORIES:
        failures.append(
            f"Unrecognized category '{category}'. Valid categories: {', '.join(sorted(VALID_CATEGORIES))}"
        )

    # Per-task validation
    for fname, fm in tasks.items():
        # Required fields
        for field in required_fields:
            if field not in fm or fm[field] is None:
                failures.append(f"{fname}: missing required field '{field}'")

        # files_to_create or files_to_modify
        ftc = fm.get('files_to_create', []) or []
        ftm = fm.get('files_to_modify', []) or []
        if not ftc and not ftm:
            failures.append(f"{fname}: must have files_to_create or files_to_modify (neither present or both empty)")

        # type validation
        task_type = fm.get('type', '')
        if task_type not in ('test', 'implementation'):
            failures.append(f"{fname}: type must be 'test' or 'implementation', got '{task_type}'")

        # covers validation
        covers = fm.get('covers', []) or []
        if covers:
            for ac in covers:
                if not re.match(r'^AC-\d+$', str(ac)):
                    failures.append(f"{fname}: invalid AC identifier '{ac}' in covers (expected AC-NN)")

        # Implementation tasks need test_tasks
        if task_type == 'implementation':
            tt = fm.get('test_tasks')
            if not tt:
                failures.append(f"{fname}: implementation task missing 'test_tasks'")

        # files_to_modify paths must exist
        if project_root:
            for path in ftm:
                full_path = os.path.join(project_root, path)
                if not os.path.exists(full_path):
                    failures.append(f"{fname}: files_to_modify path does not exist: {path}")

    # Cross-task validation

    # AC coverage
    test_acs = set()
    impl_acs = set()
    for fname, fm in tasks.items():
        covers = fm.get('covers', []) or []
        task_type = fm.get('type', '')
        for ac in covers:
            if task_type == 'test':
                test_acs.add(str(ac))
            elif task_type == 'implementation':
                impl_acs.add(str(ac))

    # Validate AC coverage
    for ac in sorted(spec_acs):
        if category == "feature":
            # Standard: every AC needs both test and implementation coverage
            if ac not in test_acs:
                failures.append(f"AC coverage: {ac} not covered by any test task")
            if ac not in impl_acs:
                failures.append(f"AC coverage: {ac} not covered by any implementation task")
        elif category == "corrective":
            # Corrective: test tasks can cover ACs without paired implementation
            if ac not in test_acs and ac not in impl_acs:
                failures.append(f"AC coverage: {ac} not covered by any test task or implementation task")
        elif category == "testing-infrastructure":
            # Testing infra: test tasks can satisfy ACs directly
            if ac not in test_acs and ac not in impl_acs:
                failures.append(f"AC coverage: {ac} not covered by any test task or implementation task")

    # File scope conflicts within same wave
    wave_files = {}  # wave -> {path: [task_fnames]}
    for fname, fm in tasks.items():
        wave = fm.get('wave', 0)
        if wave not in wave_files:
            wave_files[wave] = {}
        all_paths = (fm.get('files_to_create', []) or []) + (fm.get('files_to_modify', []) or [])
        for path in all_paths:
            if path not in wave_files[wave]:
                wave_files[wave][path] = []
            wave_files[wave][path].append(fname)

    for wave, files in wave_files.items():
        for path, fnames in files.items():
            if len(fnames) > 1:
                failures.append(f"File scope conflict in wave {wave}: {path} claimed by {', '.join(fnames)}")

    # test_tasks reference validation
    all_task_ids = {fm.get('id') for fm in tasks.values() if fm.get('id')}
    for fname, fm in tasks.items():
        if fm.get('type') == 'implementation':
            for ref in (fm.get('test_tasks', []) or []):
                if ref not in all_task_ids:
                    failures.append(f"{fname}: test_tasks reference '{ref}' does not match any task id")

    return failures


def _extract_spec_acs(spec_path: str) -> Set[str]:
    """Extract AC identifiers from the acceptance criteria section of a spec file."""
    with open(spec_path) as f:
        spec_content = f.read()

    spec_acs: Set[str] = set()
    in_ac_section = False
    for line in spec_content.split('\n'):
        if re.match(r'^## [Aa]cceptance [Cc]riteria', line):
            in_ac_section = True
            continue
        if in_ac_section and line.startswith('## '):
            break
        if in_ac_section:
            for m in re.findall(r'AC-\d+', line):
                spec_acs.add(m)
    return spec_acs


def _read_category(tasks_dir: str) -> str:
    """Read category from task.json manifest in tasks_dir."""
    task_json_path = os.path.join(tasks_dir, "task.json")
    if os.path.isfile(task_json_path):
        with open(task_json_path) as f:
            manifest = json.load(f)
        return manifest.get("category", "feature")
    return "feature"


def validate_tasks(
    tasks: Dict[str, Dict],
    spec_acs: Set[str],
    project_root: Optional[str] = None,
    category: str = "feature",
) -> List[str]:
    """Validate parsed task dicts against a set of spec ACs.

    Args:
        tasks: Dict mapping task filenames to parsed frontmatter dicts
        spec_acs: Set of AC identifiers from the spec (e.g., {'AC-01', 'AC-02'})
        project_root: Root directory for resolving files_to_modify paths
        category: Task category: 'feature', 'corrective', or 'testing-infrastructure'

    Returns:
        List of failure messages. Empty list indicates all validations pass.
    """
    return _run_validations(tasks, spec_acs, project_root, category)


def validate_tasks_from_files(
    spec_path: str,
    task_files: Dict[str, str],
    project_root: Optional[str] = None,
    tasks_dir: Optional[str] = None,
) -> Dict:
    """Validate task files and return a structured result dict.

    Args:
        spec_path: Path to the spec markdown file (used to extract ACs)
        task_files: Dict mapping task filenames to raw markdown content strings
        project_root: Root directory for resolving files_to_modify paths.
                      Auto-detected from tasks_dir if not provided.
        tasks_dir: Directory containing task.json (used to read category).
                   Defaults to dirname of spec_path if not provided.

    Returns:
        Dict with keys: gate, result, tasks, acs_covered, waves, failures
    """
    if not yaml:
        return {
            "gate": "task-reviewer",
            "result": "fail",
            "tasks": 0,
            "acs_covered": 0,
            "waves": 0,
            "failures": ["Error: PyYAML required"],
        }

    if tasks_dir is None:
        tasks_dir = os.path.dirname(spec_path)
    if project_root is None:
        project_root = find_project_root(tasks_dir)

    spec_acs = _extract_spec_acs(spec_path)
    category = _read_category(tasks_dir)

    # Parse frontmatter for all task files
    parsed_tasks: Dict[str, Dict] = {}
    for fname, content in task_files.items():
        parsed_tasks[fname] = parse_frontmatter(content)

    failures = _run_validations(parsed_tasks, spec_acs, project_root, category)

    all_covers: Set[str] = set()
    for fm in parsed_tasks.values():
        for ac in (fm.get('covers', []) or []):
            all_covers.add(str(ac))
    acs_covered = len(spec_acs & all_covers)

    max_wave = max(
        (fm.get('wave', 0) for fm in parsed_tasks.values()),
        default=0
    )

    return {
        "gate": "task-reviewer",
        "result": "pass" if not failures else "fail",
        "tasks": len(parsed_tasks),
        "acs_covered": acs_covered,
        "waves": max_wave,
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate task files against a spec."
    )
    parser.add_argument("spec_path", help="Path to the spec markdown file")
    parser.add_argument("tasks_dir", help="Directory containing task-*.md files")
    parser.add_argument(
        "--project-root",
        default=None,
        help="Project root for resolving files_to_modify paths (auto-detected if omitted)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.spec_path):
        print(f"Spec file not found: {args.spec_path}", file=sys.stderr)
        sys.exit(2)
    if not os.path.isdir(args.tasks_dir):
        print(f"Tasks directory not found: {args.tasks_dir}", file=sys.stderr)
        sys.exit(2)

    task_files: Dict[str, str] = {}
    for fname in sorted(os.listdir(args.tasks_dir)):
        if fname.startswith("task-") and fname.endswith(".md"):
            fpath = os.path.join(args.tasks_dir, fname)
            with open(fpath) as f:
                task_files[fname] = f.read()

    result = validate_tasks_from_files(args.spec_path, task_files, args.project_root, args.tasks_dir)

    print(json.dumps(result))

    if result["result"] == "pass":
        try:
            from fbk.audit import log_event
            spec_name = os.path.splitext(os.path.basename(args.spec_path))[0]
            log_event(
                spec_name,
                "gate_result",
                json.dumps({"gate": "task-reviewer", "result": "pass"}),
            )
        except Exception:
            pass
        sys.exit(0)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
