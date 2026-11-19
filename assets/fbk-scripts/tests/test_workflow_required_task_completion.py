"""Accepted focused checks cannot be skipped by omitting task assignments."""

import sys

import pytest

from fbk.workflow import close, engine, handoff, review, store
from .test_workflow_lifecycle import (
    clean_review, mutate, observe_phase, prepare_implementation, project as workflow_project,
)

from .refactor_plan import complete_refactor_tasks, with_refactor

project = workflow_project


def prepare(root):
    unit = root / '.fbk/feature'
    (unit / 'spec.md').write_text(
        '# Cancellation contract\n\n## Requirements\n\n### Cancel once\n\n'
        'Cancellation releases its resource exactly once and writes an audit record to src/audit.txt. '
        'Serves [Release on cancel](prd.md#release-on-cancel).\n'
    )
    (root / 'tests/audit_check.py').write_text(
        "from pathlib import Path\n"
        "assert Path('src/audit.txt').read_text() == 'cancelled', 'wrong cancellation audit'\n"
    )
    # An existing empty audit makes initial failure an assertion, not setup/import failure.
    (root / 'src/audit.txt').write_text('')
    release = [sys.executable, 'tests/check.py']
    audit = [sys.executable, 'tests/audit_check.py']
    tasks = [task for task in store.read_json(unit / 'tasks.json') if not task.get('refactor')]
    tasks[0].update(
        files=['tests/check.py', 'tests/audit_check.py'],
        check_expectations=[{'argv': command, 'exit_code': 1} for command in (release, audit)],
    )
    tasks[1].update(files=['src/app.py'], depends_on=['prepare-tests'])
    tasks.append({
        'id': 'audit', 'stage': 'implementation',
        'description': 'Write the required cancellation audit record.',
        'files': ['src/audit.txt'], 'depends_on': ['cancel'],
        'acceptance_refs': ['.fbk/feature/prd.md', '.fbk/feature/spec.md', '.fbk/feature/spec.md#cancel-once'],
        'verification': 'Cancellation leaves the required audit record; an empty record fails.',
        'check_expectations': [{'argv': audit, 'exit_code': 0}],
    })
    store.atomic_json(unit / 'tasks.json', with_refactor(tasks))
    results = [review.run_command(command, root, 10) for command in (release, audit)]
    assert all(result['exit_code'] == 1 and 'AssertionError' in result['stderr'] for result in results)
    # Plan-only breakdown; the test task runs in implement and the checkpoint locks.
    prepare_implementation(root)
    assert store.load(root, 'feature')['task_runs']['prepare-tests']['status'] == 'completed'
    return release, audit


def complete(root, task, path, content, command):
    mutate(root, handoff.start_task, 's', task, task + '-worker')
    (root / path).write_text(content)
    result = handoff.complete_task(
        root, 'feature', 's', task, changed_files=[path],
        checks=[{'argv': command, 'exit_code': 0, 'evidence': 'The accepted behavior assertion passes.'}], unresolved=[],
        outcome='The accepted task behavior is implemented.',
    )
    assert result['status'] == 'completed'


@pytest.mark.parametrize('complete_first_task', [False, True], ids=['all-unstarted', 'partially-unstarted'])
def test_close_rejects_unstarted_implementation_tasks_even_when_unit_check_passes(project, complete_first_task):
    release, audit = prepare(project)
    if complete_first_task:
        complete(project, 'cancel', 'src/app.py', 'release()', release)
    else:
        (project / 'src/app.py').write_text('release()')
    assert review.run_command(release, project, 10)['exit_code'] == 0
    assert review.run_command(audit, project, 10)['exit_code'] == 1
    with pytest.raises(store.WorkflowError, match='[Tt]ask|[Aa]ssign') as refused:
        close.close_phase(project, 'feature', 'implement', 's', reviewer=clean_review)
    # The planned refactor task is unstarted too; the refusal must still name the audit task.
    assert 'audit' in str(refused.value)
    assert store.load(project, 'feature')['phases']['implement']['evidence'] is None


def test_close_accepts_completed_tasks_with_runtime_verified_focused_checks(project):
    release, audit = prepare(project)
    complete(project, 'cancel', 'src/app.py', 'release()', release)
    complete(project, 'audit', 'src/audit.txt', 'cancelled', audit)
    complete_refactor_tasks(project)
    result = close.close_phase(project, 'feature', 'implement', 's', reviewer=clean_review)
    assert result['status'] == 'retrospective-required'
    observe_phase(project, 'implement')
    assert engine.status_report(project, store.load(project, 'feature'))['status'] == 'closed'
    runs = store.load(project, 'feature')['task_runs']
    for task in ('cancel', 'audit'):
        assert runs[task]['status'] == 'completed'
        assert runs[task]['return']['verified_checks'][0]['exit_code'] == 0
