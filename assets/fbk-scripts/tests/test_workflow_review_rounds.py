"""Standalone review must not confuse partial transport with a completed round."""
import json
import re

import pytest

from fbk.workflow import review_rounds as rounds
from fbk.workflow.store import WorkflowError, digest


def begin(root, **kwargs):
    (root / 'app.py').write_text('answer = 42\n')
    return rounds.begin(root, ['detector', 'challenger'], 'Review behavior', {}, **kwargs)


def deliver(root, record, member, result):
    envelope = {'schema': 'review-contribution-v1', 'round_id': record['id'],
                'contract_id': record['contract_id'], 'contributor': member,
                'status': 'complete', 'result': result, 'result_digest': digest(result)}
    path = root / '.fbk' / f'{member}-result.json'
    path.write_text(json.dumps(envelope))
    # Approved fixture migration: model a reserved runtime result, not a manual import.
    from unittest.mock import patch
    from fbk.workflow import review_execution as managed, review_contributors
    with patch('fbk.workflow.review_execution.time.monotonic', return_value=1000.0):
        execution = managed.activate_round(root, record['id'])
        try:
            review_contributors._reserve(root, record['id'], [member], execution)
            response = {'review': {'result': result}, 'seconds': 0}
            execution.record_worker(response)
            rounds._submit_runtime(root, record['id'], path, execution, response)
        finally:
            execution.finish()
    return rounds.status(root, record['id'])


def test_missing_and_large_results_survive_restart(tmp_path):
    record = begin(tmp_path)
    data = [{'evidence': 'proof ' * 30000}]
    deliver(tmp_path, record, 'detector', data)
    status = rounds.status(tmp_path, record['id'])
    assert not status['remediation_allowed']
    assert status['missing'] == ['challenger']
    with pytest.raises(WorkflowError, match='incomplete'):
        rounds.require_complete(tmp_path, record['id'])
    deliver(tmp_path, record, 'challenger', [])
    done = rounds.require_complete(tmp_path, record['id'])
    artifact = tmp_path / done['contributors']['detector']['result_path']
    assert json.loads(artifact.read_text())['result'] == data
    assert done['remediation_allowed']


def test_truncated_or_incomplete_envelope_never_completes(tmp_path):
    record = begin(tmp_path)
    path = tmp_path / '.fbk' / 'broken.json'
    for content in ['{"schema":', json.dumps({'status': 'complete'}),
                    json.dumps({'schema':'review-contribution-v1','round_id':record['id'],
                                'contract_id':record['contract_id'],'contributor':'detector',
                                'status':'complete','result':[],'result_digest':digest([1])})]:
        path.write_text(content)
        with pytest.raises(WorkflowError):
            rounds.submit(tmp_path, record['id'], path)
        assert rounds.status(tmp_path, record['id'])['missing'] == ['detector','challenger']


def test_recovery_reuses_only_identical_contract_and_retains_budget(tmp_path):
    record = begin(tmp_path)
    deliver(tmp_path, record, 'detector', [])
    record = rounds.load_round(tmp_path, record['id'])
    record['budget']['spent_seconds'] = 42
    rounds.save_round(tmp_path, record)
    resumed = rounds.resume(tmp_path, record['id'], 'Review behavior', {})
    assert resumed['missing'] == ['challenger']
    assert resumed['budget']['spent_seconds'] == 42
    assert resumed['events'][-1]['reused'] == ['detector']
    for instructions, config in [('Changed instructions', {}), ('Review behavior', {'review_timeout':600})]:
        with pytest.raises(WorkflowError, match='contract'):
            rounds.resume(tmp_path, record['id'], instructions, config)
    (tmp_path / 'app.py').write_text('answer = 0\n')
    with pytest.raises(WorkflowError, match='contract'):
        rounds.resume(tmp_path, record['id'], 'Review behavior', {})


def test_drift_retains_historical_findings_and_records_diagnostic(tmp_path):
    record = begin(tmp_path)
    (tmp_path / 'app.py').write_text('answer = 0\n')
    deliver(tmp_path, record, 'detector', [])
    deliver(tmp_path, record, 'challenger', [])
    status = rounds.status(tmp_path, record['id'])
    assert status['status'] == 'complete'
    assert status['historical'] and not status['remediation_allowed']
    drift = status['drift']
    assert drift['paths'] == ['app.py']
    assert drift['detected_at'] and drift['original_revision'] != drift['current_revision']
    assert (tmp_path / record['snapshot_path'] / 'app.py').read_text() == 'answer = 42\n'
    with pytest.raises(WorkflowError, match='historical'):
        rounds.require_complete(tmp_path, record['id'])


def test_failed_late_duplicate_and_tampered_results_cannot_approve(tmp_path):
    record = begin(tmp_path)
    rounds.fail(tmp_path, record['id'], 'detector', 'worker exited')
    assert rounds.status(tmp_path, record['id'])['status'] == 'incomplete'
    deliver(tmp_path, record, 'detector', [])
    deliver(tmp_path, record, 'challenger', [])
    with pytest.raises(WorkflowError, match='already'):
        deliver(tmp_path, record, 'detector', [{'late':True}])
    status = rounds.status(tmp_path, record['id'])
    (tmp_path / status['contributors']['detector']['result_path']).write_text('{}')
    with pytest.raises(WorkflowError, match='result'):
        rounds.require_complete(tmp_path, record['id'])


def test_unresolved_investigation_blocks_remediation_even_with_all_results(tmp_path):
    record = begin(tmp_path)
    deliver(tmp_path, record, 'detector', [])
    deliver(tmp_path, record, 'challenger', [])
    record = rounds.load_round(tmp_path, record['id'])
    # A round-level escalation (the review clock) blocks; a per-question limit would not.
    escalation = {'limit': 'review-time', 'question': 'Is cleanup observable?', 'evidence': []}
    record['investigations']['cleanup'] = {'id': 'cleanup', 'question': escalation['question'],
        'attempts': [], 'resolution': {'conclusion': 'unanswered', 'attempts': []}, 'human_review': escalation}
    record['investigation_human_review'] = escalation
    rounds.save_round(tmp_path, record)
    assert not rounds.status(tmp_path, record['id'])['remediation_allowed']
    with pytest.raises(WorkflowError, match='investigation'):
        rounds.require_complete(tmp_path, record['id'])


def test_followup_changes_snapshot_without_resetting_budget_or_losing_evidence(tmp_path):
    first = begin(tmp_path)
    deliver(tmp_path, first, 'detector', [{'unresolved':'check cleanup'}])
    deliver(tmp_path, first, 'challenger', [])
    record = rounds.load_round(tmp_path, first['id'])
    record['budget']['spent_seconds'] = 71
    rounds.save_round(tmp_path, record)
    (tmp_path / 'app.py').write_text('answer = 43\n')
    following = rounds.begin(tmp_path, ['detector','challenger'], 'Review affected cleanup', {}, previous=first['id'])
    assert following['contract_id'] != first['contract_id']
    assert following['budget']['spent_seconds'] == 71
    assert following['previous_round'] == first['id']
    assert following['prior_results']['detector']['result_path']
    assert rounds.status(tmp_path,first['id'])['superseded_by'] == following['id']


def test_added_snapshot_source_invalidates_completed_round(tmp_path):
    record = begin(tmp_path)
    deliver(tmp_path, record, 'detector', [])
    deliver(tmp_path, record, 'challenger', [])
    (tmp_path / record['snapshot_path'] / 'extra.py').write_text('changed review inputs\n')
    with pytest.raises(WorkflowError, match='snapshot'):
        rounds.require_complete(tmp_path, record['id'])


def test_a_standalone_round_is_named_review_and_its_start_time(tmp_path):
    """A standalone round has no unit, so its folder starts with "review" and the UTC time it
    began, which an operator can match against the report; the digest keeps it unique."""
    record = begin(tmp_path)
    assert re.fullmatch(r"review-\d{8}T\d{6}Z-[a-f0-9]{32}", record["id"])
    assert (tmp_path / ".fbk/runtime/review-rounds" / record["id"] / "round.json").is_file()
    assert rounds.status(tmp_path, record["id"])


@pytest.mark.parametrize("round_id, valid", [
    ("a" * 32, True),
    ("feature-spec-" + "a" * 32, True),
    ("parent-child-test-checkpoint-" + "a" * 32, True),
    ("review-20261025T101500Z-" + "a" * 32, True),
    ("-x-" + "a" * 32, False),
    ("a/b-" + "a" * 32, False),
    ("../" + "a" * 32, False),
    ("feature-spec-" + "a" * 31, False),
    ("feature-spec-" + "A" * 32, False),
    ("x" * 70 + "-" + "a" * 32, False),
])
def test_round_ids_accept_a_readable_prefix_and_the_older_bare_digest(tmp_path, round_id, valid):
    if valid:
        assert rounds.round_dir(tmp_path, round_id).name == round_id
    else:
        with pytest.raises(WorkflowError, match="Invalid review round id"):
            rounds.round_dir(tmp_path, round_id)


@pytest.mark.parametrize("unit, label", [
    ("feature", "feature-test-checkpoint"),
    ("parent/child", "parent-child-test-checkpoint"),
    ("-draft", "draft-test-checkpoint"),
    ("退款", "test-checkpoint"),
    ("u" * 60, "u" * 48 + "-test-checkpoint"),
])
def test_a_managed_round_id_names_its_unit_and_phase_and_is_a_valid_round_id(tmp_path, unit, label):
    from fbk.workflow.managed_investigations import managed_round_id
    round_id = managed_round_id(unit, "test-checkpoint", "identity")
    assert round_id == f"{label}-{digest({'managed-review': 'identity'})[:32]}"
    assert rounds.round_dir(tmp_path, round_id).name == round_id
