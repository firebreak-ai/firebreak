"""Task completion uses reviewed focused checks, with independent execution."""

import json
import re
import sys

import pytest

from fbk.workflow import close, handoff, review, store
from .test_workflow_implement_stages import plan_refusals
from .test_workflow_lifecycle import (
    accept, clean_review, enter, mutate, prepare_implementation, project as workflow_project,
)

project = workflow_project


def contract(root):
    path = root / '.fbk/feature/tasks.json'
    tasks = json.loads(path.read_text())
    focused = [sys.executable, 'tests/check.py']
    for task in tasks:
        task['check_expectations'] = [{'argv': focused, 'exit_code': 1 if task['stage'] == 'tests' else 0}]
    store.atomic_json(path, tasks)
    return focused


def implement(root):
    command = contract(root)
    prepare_implementation(root)
    packet = mutate(root, handoff.start_task, 's', 'cancel', 'worker')
    assert packet['check_expectations'] == [{'argv': command, 'exit_code': 0}]
    return command


def plan_refusal(root):
    """Plan validation's refusal at breakdown close."""
    accept(root, 'intent')
    accept(root, 'spec')
    enter(root, 'breakdown')
    [message] = plan_refusals(root)
    return message


def finish(root, command, changed=True):
    return mutate(root, handoff.finish_task, 's', 'cancel',
                  changed_files=['src/app.py'] if changed else [],
                  checks=[{'argv': command, 'exit_code': 0, 'evidence': 'Worker reports passing.'}],
                  unresolved=[], outcome='Cancellation releases once.')


def test_every_task_requires_a_concrete_completion_check(project):
    contract(project)
    path = project / '.fbk/feature/tasks.json'
    tasks = json.loads(path.read_text())
    del tasks[1]['check_expectations']
    store.atomic_json(path, tasks)
    message = plan_refusal(project)
    assert message is not None and re.search('[Cc]heck expectations', message), message


def test_focused_green_task_does_not_require_unrelated_work_to_be_green(project):
    focused = contract(project)
    scope_path = project / '.fbk/feature/scope.json'
    scope = json.loads(scope_path.read_text())
    scope['checks'].append([sys.executable, 'tests/integration.py'])
    store.atomic_json(scope_path, scope)
    (project / 'tests/integration.py').write_text("assert False, 'another planned feature remains missing'\n")
    # Focused task checks are not whole-unit gates.
    scope['checks'].remove(focused)
    store.atomic_json(scope_path, scope)
    command = implement(project)
    (project / 'src/app.py').write_text('release()')
    assert finish(project, command)['status'] == 'completed'
    with pytest.raises(store.WorkflowError):
        close.close_phase(project, 'feature', 'implement', 's', reviewer=clean_review)
    assert not store.load(project, 'feature')['phases']['implement']['evidence']


def test_claimed_green_does_not_complete_a_task_whose_accepted_check_fails(project):
    command = implement(project)
    assert review.run_command(command, project, 10)['exit_code'] == 1
    assert finish(project, command, changed=False)['status'] == 'needs-attention'


def test_implementer_cannot_replace_reviewed_check_with_an_easy_pass(project):
    implement(project)
    (project / 'src/app.py').write_text('release()')
    result = finish(project, [sys.executable, '-c', 'pass'])
    assert result['status'] == 'needs-attention'


@pytest.mark.parametrize('expectations', [
    [{'argv': [], 'exit_code': 0}],
    [{'argv': ['python'], 'exit_code': 1}],
    [{'argv': ['python'], 'exit_code': 0}, {'argv': ['python'], 'exit_code': 0}],
])
def test_invalid_or_ambiguous_implementation_checks_are_rejected(project, expectations):
    contract(project)
    path = project / '.fbk/feature/tasks.json'
    tasks = json.loads(path.read_text())
    tasks[1]['check_expectations'] = expectations
    store.atomic_json(path, tasks)
    message = plan_refusal(project)
    assert message is not None and re.search('[Cc]heck expectations', message), message


def public_finish(root, command):
    from .test_workflow_commands import call

    store.atomic_json(root / '.fbk/runtime/task-result.json', {
        'changed_files': ['src/app.py'],
        'checks': [{'argv': command, 'exit_code': 0, 'evidence': 'Worker checked cancellation.'}],
        'unresolved': [], 'outcome': 'Cancellation releases once.',
    })
    return call(root, 'task-finish', 'feature', 'cancel', '--result', '.fbk/runtime/task-result.json')


def test_task_checks_release_lock_and_preserve_concurrent_progress(project, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    command = implement(project)
    (project / 'src/app.py').write_text('release()')
    entered, resume = Event(), Event()
    execute = review.run_command

    def paused(*args, **kwargs):
        entered.set()
        assert resume.wait(5), 'test did not release the paused check'
        return execute(*args, **kwargs)

    monkeypatch.setattr(review, 'run_command', paused)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(public_finish, project, command)
        try:
            assert entered.wait(5), 'task verification never started'
            with store.transaction(project, timeout=0.1):
                record = store.load(project, 'feature')
                store.event(record, 'independent-progress', 's', detail='Another disjoint worker made progress.')
                store.save(project, record)
        finally:
            resume.set()
        assert pending.result(timeout=5)['status'] == 'completed'
    assert any(e['event'] == 'independent-progress' for e in store.load(project, 'feature')['events'])


@pytest.mark.parametrize('change', ['assignment', 'contract', 'input', 'output'])
def test_task_check_result_cannot_commit_after_its_evidence_changes(project, monkeypatch, change):
    command = implement(project)
    (project / 'src/app.py').write_text('release()')
    execute = review.run_command

    def changing(*args, **kwargs):
        result = execute(*args, **kwargs)
        if change == 'assignment':
            with store.transaction(project, timeout=0.1):
                record = store.load(project, 'feature')
                handoff.cancel_task(project, record, 's', 'cancel', 'Restart worker.')
                record = store.load(project, 'feature')
                handoff.start_task(project, record, 's', 'cancel', 'worker')
        elif change == 'contract':
            (project / '.fbk/feature/spec.md').write_text('Changed cancellation contract.')
        elif change == 'input':
            (project / '.fbk/feature/prd.md').write_text('Changed governing intent.')
        else:
            (project / 'src/app.py').write_text('release_twice()')
        return result

    monkeypatch.setattr(review, 'run_command', changing)
    with pytest.raises(store.WorkflowError):
        public_finish(project, command)
    assert store.load(project, 'feature')['task_runs']['cancel']['status'] == 'running'
