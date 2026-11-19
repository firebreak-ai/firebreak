"""Experiments consume durable budgets and preserve reproducible evidence."""
import sys
import json

import pytest
from fbk.workflow import investigations, store


@pytest.fixture
def round_root(tmp_path, monkeypatch):
    sources = tmp_path / '.fbk/runtime/review-rounds/r/sources'
    sources.mkdir(parents=True)
    (sources / 'value.txt').write_text('original')
    (tmp_path / 'value.txt').write_text('deliverable')
    record = {'id': 'r', 'contract_id': 'revision', 'snapshot_path': str(sources.relative_to(tmp_path)),
              'budget': {'seconds': 30, 'spent_seconds': 0}, 'investigations': {}}
    path = tmp_path / 'round.json'
    store.atomic_json(path, record)
    monkeypatch.setattr(investigations, '_load', lambda root, rid: store.read_json(path))
    monkeypatch.setattr(investigations, '_save', lambda root, record: store.atomic_json(path, record))
    monkeypatch.setattr(investigations, 'project_config', lambda root: {})
    return tmp_path


def begin(root):
    return investigations.start(root, 'r', {'id': 'problem', 'question': 'Does the write replace the value?',
                                            'requirements': ['spec.md#replace']})


def test_real_assignment_uses_copy_and_keeps_evidence(round_root, monkeypatch):
    real_command = investigations.run_command
    def worker(argv, cwd, timeout, prompt=None):
        assert argv[0] == 'claude' and '-p' in argv
        assert '--resume' not in argv and '--continue' not in argv
        assert 'Does the write replace the value?' in prompt
        result = real_command([sys.executable, '-c', "from pathlib import Path; Path('value.txt').write_text('experiment'); print('observed')"], cwd, timeout)
        return {**result, 'stdout': json.dumps({'subtype': 'success', 'result': result['stdout']})}
    monkeypatch.setattr(investigations, 'run_command', worker)
    begin(round_root)
    result = investigations.run(round_root, 'r', 'problem', {
        'mode': 'delegated', 'modifies_code': True,
        'prompt': 'Run the value replacement experiment.'})
    assert (round_root / 'value.txt').read_text() == 'deliverable'
    assert (round_root / '.fbk/runtime/review-rounds/r/sources/value.txt').read_text() == 'original'
    attempt = result['attempts'][0]
    assert 'observed' in attempt['result']['stdout']
    assert attempt['contract_id'] == 'revision'
    assert (round_root / attempt['workspace'] / 'value.txt').read_text() == 'experiment'
    assert result['spent_seconds'] > 0


def test_budget_survives_repeated_start_and_context_reset(round_root, monkeypatch):
    begin(round_root)
    monkeypatch.setattr(investigations, 'run_command', lambda *args: {'exit_code': 1, 'seconds': 1, 'stdout': 'failed', 'stderr': ''})
    request = {'mode': 'direct', 'argv': ['probe']}
    for _ in range(3):
        investigations.run(round_root, 'r', 'problem', request)
    with pytest.raises(store.WorkflowError, match='already exists'):
        begin(round_root)
    with pytest.raises(store.WorkflowError, match='human'):
        investigations.run(round_root, 'r', 'problem', request)
    current = investigations.status(round_root, 'r', 'problem')
    assert current['human_review']['limit'] == 'attempts'
    assert len(current['attempts']) == 3


def test_enclosing_budget_caps_timeout_and_is_consumed(round_root, monkeypatch):
    begin(round_root)
    seen = []
    def command(argv, cwd, timeout):
        seen.append(timeout)
        return {'exit_code': 0, 'seconds': timeout, 'stdout': '', 'stderr': ''}
    monkeypatch.setattr(investigations, 'run_command', command)
    result = investigations.run(round_root, 'r', 'problem', {'mode': 'direct', 'argv': ['probe']})
    assert seen == [30]
    assert result['human_review']['limit'] == 'review-time'
    with pytest.raises(store.WorkflowError, match='human'):
        investigations.run(round_root, 'r', 'problem', {'mode': 'direct', 'argv': ['probe']})


def test_direct_code_experiment_rejected_before_budget_use(round_root):
    begin(round_root)
    with pytest.raises(store.WorkflowError, match='delegated'):
        investigations.run(round_root, 'r', 'problem', {'mode': 'direct', 'modifies_code': True, 'argv': ['probe']})
    assert investigations.status(round_root, 'r', 'problem')['attempts'] == []


def test_external_authorization_must_cover_exact_effects_and_persists(round_root, monkeypatch):
    # Refusals count as attempts, so leave room for two refusals and two runs.
    monkeypatch.setattr(investigations, 'project_config', lambda root: {'investigation_max_attempts': 5})
    begin(round_root)
    monkeypatch.setattr(investigations, 'run_command', lambda *a: {'exit_code': 0, 'seconds': 1, 'stdout': '', 'stderr': ''})
    request = {'mode': 'direct', 'argv': ['probe'], 'external': {'target': 'staging', 'effects': ['read']}}
    with pytest.raises(investigations.InvestigationRefused, match='authorization'):
        investigations.run(round_root, 'r', 'problem', request)
    refused = investigations.status(round_root, 'r', 'problem')['attempts']
    assert [a['status'] for a in refused] == ['refused'] and 'workspace' not in refused[0]
    (round_root / 'approval.md').write_text('User authorizes reading staging.')
    request['authorization'] = {'target': 'staging', 'effects': ['read'], 'source': {'path': 'approval.md', 'quote': 'User authorizes reading staging.'}}
    investigations.run(round_root, 'r', 'problem', request)
    del request['authorization']
    investigations.run(round_root, 'r', 'problem', request)
    request['external']['effects'] = ['delete']
    with pytest.raises(store.WorkflowError, match='authorization'):
        investigations.run(round_root, 'r', 'problem', request)


@pytest.mark.parametrize('key,value', [('investigation_max_attempts', 0), ('investigation_max_attempts', True), ('investigation_timeout', -1)])
def test_invalid_configuration_rejected(round_root, monkeypatch, key, value):
    monkeypatch.setattr(investigations, 'project_config', lambda root: {key: value})
    with pytest.raises(store.WorkflowError, match=key):
        begin(round_root)


def test_interrupted_assignment_retains_reservation_and_blocks_retry(round_root, monkeypatch):
    begin(round_root)
    def crash(*a):
        raise KeyboardInterrupt()
    monkeypatch.setattr(investigations, 'run_command', crash)
    with pytest.raises(KeyboardInterrupt):
        investigations.run(round_root, 'r', 'problem', {'mode': 'direct', 'argv': ['probe']})
    with pytest.raises(store.WorkflowError, match='human'):
        investigations.run(round_root, 'r', 'problem', {'mode': 'direct', 'argv': ['probe']})
    assert investigations.status(round_root, 'r', 'problem')['attempts'][0]['status'] == 'running'


def test_delegated_worker_receives_question_and_requirements_in_fresh_session(round_root, monkeypatch):
    begin(round_root)
    calls = []
    def worker(argv, cwd, timeout, prompt=None):
        calls.append((argv, cwd, timeout, prompt))
        return {'exit_code': 0, 'seconds': 1, 'stdout': json.dumps({'subtype': 'success', 'result': 'reproduced'}), 'stderr': ''}
    monkeypatch.setattr(investigations, 'run_command', worker)
    investigations.run(round_root, 'r', 'problem', {'mode': 'delegated', 'exploratory': True,
                                                   'prompt': 'Check replacement behavior.'})
    argv, cwd, timeout, prompt = calls[0]
    assert argv[0] == 'claude'
    assert '-p' in argv
    assert '--resume' not in argv and '--continue' not in argv
    assert 'spec.md#replace' in prompt
    assert 'Does the write replace the value?' in prompt
    assert 'Check replacement behavior.' in prompt
    assert 'independent verification' in prompt
    assert cwd != round_root
    assert timeout <= 30


def test_direct_check_executes_without_worker_and_captures_failure(round_root):
    begin(round_root)
    result = investigations.run(round_root, 'r', 'problem', {'mode': 'direct',
        'argv': [sys.executable, '-c', "import sys; print('counterexample'); sys.exit(1)"]})
    attempt = result['attempts'][0]
    assert attempt['status'] == 'failed'
    assert attempt['result']['exit_code'] == 1
    assert 'counterexample' in attempt['result']['stdout']


def test_human_extension_is_sourced_explicit_and_does_not_erase_usage(round_root, monkeypatch):
    begin(round_root)
    monkeypatch.setattr(investigations, 'run_command', lambda *a: {'exit_code': 1, 'seconds': 1, 'stdout': '', 'stderr': ''})
    for _ in range(3):
        investigations.run(round_root, 'r', 'problem', {'mode': 'direct', 'argv': ['probe']})
    with pytest.raises(store.WorkflowError, match='source'):
        investigations.resolve(round_root, 'r', 'problem', {'disposition': 'extend', 'reason': 'Need one more', 'additional_attempts': 1, 'additional_seconds': 10})
    (round_root / 'decision.md').write_text('Human approves one more attempt and ten seconds.')
    entry = investigations.resolve(round_root, 'r', 'problem', {'disposition': 'extend', 'reason': 'Need one more', 'additional_attempts': 1, 'additional_seconds': 10,
        'source': {'path': 'decision.md', 'quote': 'Human approves one more attempt and ten seconds.'}})
    assert entry['spent_seconds'] == 3
    assert len(entry['attempts']) == 3
    assert entry['attempt_limit'] == 4
    assert 'human_review' not in entry
    investigations.run(round_root, 'r', 'problem', {'mode': 'direct', 'argv': ['probe']})
    assert len(investigations.status(round_root, 'r', 'problem')['attempts']) == 4


def test_interrupted_work_requires_explicit_stopped_confirmation(round_root, monkeypatch):
    begin(round_root)
    def crash(*a):
        raise KeyboardInterrupt()
    monkeypatch.setattr(investigations, 'run_command', crash)
    with pytest.raises(KeyboardInterrupt):
        investigations.run(round_root, 'r', 'problem', {'mode': 'direct', 'argv': ['probe']})
    (round_root / 'decision.md').write_text('Human stops investigation and accepts unresolved uncertainty.')
    request = {'disposition': 'stop', 'reason': 'Accept unresolved uncertainty', 'source': {'path': 'decision.md', 'quote': 'Human stops investigation and accepts unresolved uncertainty.'}}
    with pytest.raises(store.WorkflowError, match='stopped'):
        investigations.resolve(round_root, 'r', 'problem', request)
    request['confirm_stopped'] = True
    entry = investigations.resolve(round_root, 'r', 'problem', request)
    assert entry['attempts'][0]['status'] == 'interrupted'
    assert entry['spent_seconds'] == 30
    assert entry['disposition']['reason'] == 'Accept unresolved uncertainty'
    with pytest.raises(store.WorkflowError, match='stopped'):
        investigations.run(round_root, 'r', 'problem', {'mode': 'direct', 'argv': ['probe']})


@pytest.mark.parametrize('action', ['start', 'run', 'resolve'])
def test_superseded_round_cannot_fork_investigation_budget(round_root, action):
    begin(round_root)
    record = investigations._load(round_root, 'r')
    record['superseded_by'] = 'new-round'
    investigations._save(round_root, record)
    (round_root / 'decision.md').write_text('Human stops this investigation.')
    with pytest.raises(store.WorkflowError, match='superseded'):
        if action == 'start':
            investigations.start(round_root, 'r', {'id': 'another', 'question': 'Another?', 'requirements': ['spec.md']})
        elif action == 'run':
            investigations.run(round_root, 'r', 'problem', {'mode': 'direct', 'argv': ['probe']})
        else:
            investigations.resolve(round_root, 'r', 'problem', {'disposition': 'stop', 'reason': 'Done', 'source': {'path': 'decision.md', 'quote': 'Human stops this investigation.'}})


def test_resolution_requires_completed_evidence_and_explicit_conclusion(round_root):
    begin(round_root)
    with pytest.raises(store.WorkflowError, match='evidence'):
        investigations.conclude(round_root, 'r', 'problem', {'conclusion': 'It works', 'attempts': [1]})
    investigations.run(round_root, 'r', 'problem', {'mode': 'direct', 'argv': [sys.executable, '-c', "print('observed violation'); raise SystemExit(1)"]})
    result = investigations.conclude(round_root, 'r', 'problem', {'conclusion': 'The probe demonstrates the violation; nonzero was the observed result.', 'attempts': [1]})
    assert result['resolution']['attempts'] == [1]
    assert 'demonstrates' in result['resolution']['conclusion']


@pytest.mark.parametrize('envelope', [
    {'subtype': 'error_during_execution', 'is_error': True},
    {'subtype': 'error_max_structured_output_retries'},
    {'subtype': 'success', 'is_error': True},
])
def test_failed_native_envelope_cannot_complete_assignment_even_with_zero_exit(round_root, monkeypatch, envelope):
    import json
    begin(round_root)
    monkeypatch.setattr(investigations, 'run_command', lambda *a: {'exit_code': 0, 'seconds': 1, 'stdout': json.dumps(envelope), 'stderr': ''})
    result = investigations.run(round_root, 'r', 'problem', {'mode': 'delegated', 'prompt': 'Check the source.'})
    assert result['attempts'][0]['status'] == 'failed'
    assert result['attempts'][0]['result']['native_completion'] == 'failed'


@pytest.mark.parametrize('stdout,omitted', [
    ('not JSON', 0), ('{}', 0), ('[]', 0), ('null', 0),
    ('{"subtype":"success"}', 0),
    ('{"subtype":"success","result":"complete"}', 12),
])
def test_malformed_or_incomplete_native_transport_cannot_complete_worker(round_root, monkeypatch, stdout, omitted):
    begin(round_root)
    monkeypatch.setattr(investigations, 'run_command', lambda *a: {'exit_code': 0, 'seconds': 1, 'stdout': stdout, 'stdout_omitted_bytes': omitted, 'stderr': ''})
    result = investigations.run(round_root, 'r', 'problem', {'mode': 'delegated', 'prompt': 'Check the source.'})
    assert result['attempts'][0]['status'] == 'failed'
    assert result['attempts'][0]['result']['native_completion'] == 'failed'


def test_worker_turn_ceiling_is_a_failed_attempt_not_immediate_escalation(round_root, monkeypatch):
    """A delegated worker that reaches its turn ceiling fails the attempt; only the attempt limit escalates."""
    begin(round_root)
    envelope = {'subtype': 'error_max_turns', 'is_error': True, 'num_turns': 100}
    monkeypatch.setattr(investigations, 'run_command', lambda *a: {'exit_code': 0, 'seconds': 1, 'stdout': json.dumps(envelope), 'stderr': ''})
    request = {'mode': 'delegated', 'prompt': 'Check the source.'}
    result = investigations.run(round_root, 'r', 'problem', request)
    attempt = result['attempts'][0]
    assert attempt['status'] == 'failed'
    assert attempt['result']['native_completion'] == 'failed'
    assert attempt['result']['native_subtype'] == 'error_max_turns'
    assert 'human_review' not in result
    assert result['attempt_limit'] == 3
    result = investigations.run(round_root, 'r', 'problem', request)
    assert len(result['attempts']) == 2 and 'human_review' not in result
    result = investigations.run(round_root, 'r', 'problem', request)
    assert len(result['attempts']) == 3
    assert result['human_review']['limit'] == 'attempts'
    with pytest.raises(store.WorkflowError, match='human'):
        investigations.run(round_root, 'r', 'problem', request)
