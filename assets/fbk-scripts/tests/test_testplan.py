"""The test-list trial tool, driven as an agent drives it: through its commands, in a real pytest project."""
import subprocess
import sys
import textwrap

import pytest

TOOL = __file__.replace("tests/test_testplan.py", "testplan.py")
CHECK = f"{sys.executable} -m pytest -q -p no:cacheprovider"

REQUEST = "Add a `double` command. double 2 prints 4. The `greet` command now prints Hello, not Hi.\n"

EXISTING = '''
import pytest
from app import greet, shout

def test_greet_says_hi():
    assert greet() == "Hi"

def test_old_alias():
    assert greet() != ""

def test_shout():
    assert shout("a") == "A"
'''

PLANNED = '''
import pytest
import app

@pytest.mark.planned(action="change", rule="greet prints Hello", source="request: The `greet` command now prints Hello",
                        owner="app.greet", was="greet prints Hi", reason="the request changes the greeting")
def test_greet_says_hi():
    """greet prints Hello."""
    assert app.greet() == "Hi"

@pytest.mark.planned(action="remove", rule="greet prints Hello", source="request: now prints Hello, not Hi",
                        reason="it only repeats the greeting test")
def test_old_alias():
    """greet prints something."""
    assert app.greet() != ""

@pytest.mark.planned(action="protect", rule="shout is unchanged", owner="app.shout")
def test_shout():
    """shout a gives A."""
    assert app.shout("a") == "A"

@pytest.mark.planned(rule="double doubles a number", source="request: double 2 prints 4", owner="app.double",
                        new_owner="nothing in app does arithmetic")
def test_double_two():
    """double 2 gives 4."""

@pytest.mark.planned(rule="double doubles a number", source="answer: 1", owner="app.double")
def test_double_zero():
    """double 0 gives 0."""
'''

BODIES = PLANNED.replace('assert app.greet() == "Hi"', 'assert app.greet() == "Hello"').replace(
    '"""double 2 gives 4."""', '"""double 2 gives 4."""\n    assert app.double(2) == 4').replace(
    '"""double 0 gives 0."""', '"""double 0 gives 0."""\n    assert app.double(0) == 0')


class Project:
    def __init__(self, root):
        self.root = root
        (root / "tests").mkdir()
        self.app('def greet():\n    return "Hi"\n\ndef shout(text):\n    return text.upper()\n')
        self.tests(EXISTING)
        (root / "request.md").write_text(REQUEST)
        (root / "pyproject.toml").write_text('[tool.pytest.ini_options]\npythonpath = ["."]\ntestpaths = ["tests"]\n')

    def app(self, text):
        (self.root / "app.py").write_text(text)

    def tests(self, text):
        (self.root / "tests" / "test_app.py").write_text(textwrap.dedent(text))

    def run(self, *args):
        return subprocess.run([sys.executable, TOOL, "--root", str(self.root), *args], capture_output=True, text=True)

    def ok(self, *args):
        done = self.run(*args)
        assert done.returncode == 0, done.stdout + done.stderr
        return done.stdout

    def refused(self, *args):
        done = self.run(*args)
        assert done.returncode == 1, done.stdout + done.stderr
        return done.stderr

    def planned(self, bodies="author"):
        self.ok("init", "--request", str(self.root / "request.md"), "--bodies", bodies, "--check", CHECK)
        self.ok("answer", "What does double 0 give?", "0")
        self.tests(PLANNED)
        return self

    def approved(self, bodies="author"):
        self.planned(bodies)
        self.ok("approve", "--reason", "looks right")
        return self


@pytest.fixture
def project(tmp_path):
    return Project(tmp_path)


def test_printout_groups_the_plan_by_rule_and_shows_each_kind(project):
    project.planned().ok("park", "A triple command")
    plan = project.ok("plan")
    assert "2 rules; 2 new tests, 1 existing tests to change, 1 to remove, 1 protecting existing behaviour." in plan
    assert "## double doubles a number" in plan and "## Protecting existing behaviour" in plan
    assert "Today it says: greet prints Hi" in plan and "Why: it only repeats the greeting test" in plan
    assert "new; no existing owner fits because: nothing in app does arithmetic" in plan
    assert "From your answer 1" in plan and "What does double 0 give? — **0**" in plan
    assert "- A triple command" in plan


@pytest.mark.parametrize("old, new, complaint", [
    ("request: double 2 prints 4", "request: double 3 prints 6", "not in the request"),
    ("answer: 1", "answer: 7", "names answer 7"),
    (', source="answer: 1"', "", "needs `source`"),
    ('reason="it only repeats the greeting test"', "", "needs `reason`"),
    ('"""double 0 gives 0."""', "pass", "needs a docstring"),
    (', owner="app.shout"', "", "needs `owner`"),
])
def test_a_plan_entry_missing_what_the_operator_must_see_is_refused(project, old, new, complaint):
    project.planned().tests(PLANNED.replace(old, new))
    assert complaint in project.refused("plan")
    assert complaint in project.refused("approve", "--reason", "ok")


def test_planned_tests_stay_off_until_switched_on_and_the_step_gate_holds(project):
    project.approved()
    project.tests(BODIES)
    project.ok("lock")
    assert "Task 1: app.greet" in project.ok("tasks") and "Task 2: app.double" in project.ok("tasks")
    assert "It fails" in project.ok("next", "1")
    assert "must pass" in project.refused("next", "1", "--review", "done")  # greet still says Hi
    project.app('def greet():\n    return "Hello"\n\ndef shout(text):\n    return text.upper()\n')
    assert "--review" in project.refused("next", "1")
    assert "Task 1 is complete" in project.ok("next", "1", "--review", "one line changed; nothing to tidy")
    project.ok("next", "2")
    project.app('def greet():\n    return "Hello"\n\ndef shout(text):\n    return text.upper()\n\ndef double(n):\n    return n * 2\n')
    assert "passes already" in project.ok("next", "2", "--review", "double is one expression")
    project.ok("next", "2", "--review", "covered by the same expression")
    assert "test_old_alias" in project.refused("finish")
    project.tests(BODIES.replace(BODIES[BODIES.index('@pytest.mark.planned(action="remove"'):BODIES.index('@pytest.mark.planned(action="protect"')], ""))
    assert "Finished" in project.ok("finish")
    assert "pytest_collection_modifyitems" not in (project.root / "conftest.py").read_text()
    finished = (project.root / "tests" / "test_app.py").read_text()
    assert "planned" not in finished and finished.count("@pytest.mark.acceptance(rule=") == 4
    assert '@pytest.mark.acceptance(rule="double doubles a number")\ndef test_double_two():' in finished


def test_tests_of_a_finished_plan_stay_on_and_out_of_the_next_plan(project):
    project.approved("implementer")
    project.tests(BODIES)
    project.app('def greet():\n    return "Hello"\n\ndef shout(text):\n    return text.upper()\n\ndef double(n):\n    return n * 2\n')
    project.ok("next", "1")
    project.ok("next", "1", "--review", "tidy")
    project.ok("next", "2")
    project.ok("next", "2", "--review", "tidy")
    project.ok("next", "2", "--review", "tidy")
    project.refused("finish")
    kept = (project.root / "tests" / "test_app.py").read_text()
    start, end = kept.index('@pytest.mark.planned(action="remove"'), kept.index('@pytest.mark.planned(action="protect"')
    project.tests(kept[:start] + kept[end:])
    project.ok("finish")
    project.ok("init", "--request", str(project.root / "request.md"), "--bodies", "implementer", "--check", CHECK)
    assert "0 new tests, 0 existing tests to change" in project.run("plan").stdout
    project.app('def greet():\n    return "Hello"\n\ndef shout(text):\n    return text.upper()\n\ndef double(n):\n    return n\n')
    suite = subprocess.run([*CHECK.split(), "-rs"], cwd=project.root, capture_output=True, text=True)
    assert "1 failed" in suite.stdout and "skipped" not in suite.stdout, suite.stdout


def test_a_locked_test_file_that_changes_stops_the_next_step(project):
    project.approved()
    project.tests(BODIES)
    project.ok("lock")
    project.tests(BODIES.replace("== 4", "== 5"))
    assert "Locked test files changed: tests/test_app.py" in project.refused("next", "1")


def test_a_plan_changed_after_approval_stops_lock_and_steps(project):
    project.approved()
    project.tests(BODIES + '\n@pytest.mark.planned(rule="extra", source="request: double 2 prints 4", owner="app.double")\ndef test_extra():\n    """Unapproved."""\n')
    assert "differs from the one the operator approved" in project.refused("lock")
    assert "differs from the one the operator approved" in project.refused("next", "1")


def test_when_the_implementer_writes_bodies_there_is_no_lock_but_the_plan_still_holds(project):
    project.approved("implementer")
    assert "no lock" in project.refused("lock")
    assert "Write this test's body now" in project.ok("next", "1")
    project.tests(BODIES)
    project.app('def greet():\n    return "Hello"\n\ndef shout(text):\n    return text.upper()\n')
    assert "Task 1 is complete" in project.ok("next", "1", "--review", "tidy")
    project.tests(BODIES.replace("double 0 gives 0", "double 0 gives nothing"))
    assert "differs from the one the operator approved" in project.refused("next", "2")


def test_approval_needs_the_existing_suite_to_pass(project):
    project.planned().app('def greet():\n    return "Hi"\n\ndef shout(text):\n    return text\n')
    assert "must pass with the planned tests switched off" in project.refused("approve", "--reason", "ok")


def test_a_skeleton_test_forms_the_first_task(project):
    project.planned().tests(PLANNED.replace('source="answer: 1", owner="app.double"', 'source="answer: 1", owner="app.double", skeleton=True'))
    tasks = project.ok("tasks")
    assert tasks.index("test_double_zero") < tasks.index("test_greet_says_hi")


LINT = """import pathlib, sys
for path in sorted(pathlib.Path('.').glob('*.py')):
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if 'TODO' in line:
            print(f'{path}:{number}:1: T001 todo left in code')
"""


def test_a_step_that_adds_lint_findings_is_refused_until_they_are_gone(project):
    (project.root / "lint.py").write_text(LINT.replace("'TODO'", "'TO' + 'DO'"))
    project.app('def greet():\n    return "Hi"  # TODO\n\ndef shout(text):\n    return text.upper()\n')
    project.ok("init", "--request", str(project.root / "request.md"), "--bodies", "implementer", "--check", CHECK,
               "--lint", f"{sys.executable} lint.py")
    project.ok("answer", "What does double 0 give?", "0")
    project.tests(PLANNED)
    project.ok("approve", "--reason", "ok")
    project.ok("next", "1")
    project.tests(BODIES)
    project.app('def greet():\n    return "Hello"  # TODO\n\ndef shout(text):\n    return text.upper()  # TODO\n')
    refusal = project.refused("next", "1", "--review", "tidy")
    assert "2 findings against 1 when the plan started" in refusal and "app.py:5:1: T001" in refusal
    project.app('def greet():\n    return "Hello"  # TODO\n\ndef shout(text):\n    return text.upper()\n')
    assert "Task 1 is complete" in project.ok("next", "1", "--review", "tidy")


def test_a_step_is_checked_against_the_tasks_test_files_and_the_task_end_against_the_whole_suite(project):
    (project.root / "tests" / "test_other.py").write_text("import app\n\ndef test_shout_elsewhere():\n    assert app.shout('b') == 'B'\n")
    project.approved("implementer")
    project.tests(BODIES)
    project.ok("next", "2")
    project.app('def greet():\n    return "Hi"\n\ndef shout(text):\n    return text.upper() if text == "a" else text\n\ndef double(n):\n    return n * 2\n')
    assert "Switched on" in project.ok("next", "2", "--review", "tidy")  # the break is outside the task's files
    refusal = project.refused("next", "2", "--review", "tidy")
    assert "The suite must pass before the task ends" in refusal and "test_shout_elsewhere" in refusal


def test_one_session_writes_its_own_test_bodies_and_status_says_so(project):
    assert "--bodies implementer" in project.refused("init", "--request", str(project.root / "request.md"), "--session", "one", "--bodies", "author")
    project.ok("init", "--request", str(project.root / "request.md"), "--session", "one", "--check", CHECK)
    status = project.ok("status")
    assert "this one session, with no subagents" in status and "Bodies written by: the implementer" in status
    assert "Closing tidy-up by: this session" in status


def test_one_session_can_hand_the_closing_tidy_up_to_a_fresh_subagent(project):
    project.ok("init", "--request", str(project.root / "request.md"), "--session", "one", "--tidy", "agent", "--check", CHECK)
    status = project.ok("status")
    assert "Work done by: this one session\n" in status and "Closing tidy-up by: a fresh subagent" in status
