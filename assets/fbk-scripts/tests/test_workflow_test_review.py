"""Test-specific detection retains coverage and executes without source edits."""
import sys
from pathlib import Path

import pytest
from fbk.workflow import review, review_contributors, review_rounds
from fbk.workflow.store import read_json

LENS = Path(__file__).resolve().parents[2] / 'fbk-docs/fbk-review-lenses/test-lens.md'


def begin(root, bound=True):
    (root / 'app.py').write_text('def value(): return 2\n')
    (root / 'spec.md').write_text('Return two.\n')
    return review_rounds.begin(
        root, ['detector', 'challenger'] if bound else ['scan'],
        'Inspect current sources, request a focused check if useful.', {},
        required=['spec.md'], code_review={
            'detector': 'detector', 'challenger': 'challenger',
            'lens': str(LENS), 'preset': None, 'min_severity': 'minor',
        } if bound else None,
    )


def detection():
    return {'findings': [{
        'title': 'Missing result assertion',
        'location': {'file': 'app.py', 'start_line': 1},
        'type': 'untested-behavior', 'severity': 'major',
        'mechanism': 'The required result is never asserted',
        'consequence': 'An incorrect result escapes regression checks',
        'evidence': 'spec.md requires the value two',
        'source_of_truth_ref': 'spec.md',
    }], 'coverage': [{
        'obligation': 'Required result', 'status': 'gap',
        'evidence': 'DETECTOR_ONLY_COVERAGE: no result assertion',
    }]}


@pytest.mark.parametrize('member', ['detector', 'challenger', 'scan'])
def test_every_role_receives_real_probe_evidence_in_separate_copy(tmp_path, monkeypatch, member):
    record = begin(tmp_path, bound=member != 'scan')
    observations = []

    def session(root, prompt, config, **kwargs):
        active = f'Contributor: {member}' in prompt
        if active and 'Investigation evidence' not in prompt:
            return {'investigation': {
                'id': 'test-result', 'question': 'Does the actual value match the contract?',
                'requirements': ['spec.md'], 'mode': 'direct',
                'argv': [sys.executable, '-c',
                         ("from pathlib import Path; from app import value; "
                         "assert value() == 2; Path('app.py').write_text('temporary probe output'); "
                         "print('ACTUAL_TEST_PASSED')")],
            }, 'seconds': 0}
        if active:
            assert 'ACTUAL_TEST_PASSED' in prompt
            assert (root / 'app.py').read_text() == 'def value(): return 2\n'
            observations.append(root)
        if 'Contributor: challenger' in prompt:
            candidates = read_json(root / '_review_inputs/normalized.json')
            assert len(candidates) == 1
            assert candidates[0]['type'] == 'untested-behavior'
            assert 'DETECTOR_ONLY_COVERAGE' not in prompt
            assert not (root / '_review_inputs/detector.json').exists()
            result = [{'status': 'verified',
                       'verification_evidence': 'Source inspection establishes the missing assertion'}]
        else:
            result = detection() if member != 'scan' else {'report': 'Inspected source and ran focused check.'}
        return {'review': {'result': result}, 'seconds': 0}

    monkeypatch.setattr(review, '_claude_session', session)
    for contributor in (['detector', 'challenger'] if member != 'scan' else ['scan']):
        result = review_contributors.run(tmp_path, record['id'], [contributor])
        assert result['contributors'][contributor]['status'] == 'complete', result
    review_rounds.require_complete(tmp_path, record['id'])
    assert len(observations) == 1
    assert (tmp_path / 'app.py').read_text() == 'def value(): return 2\n'
    assert (tmp_path / record['snapshot_path'] / 'app.py').read_text() == 'def value(): return 2\n'
    if member != 'scan':
        row = result['contributors']['detector']
        assert read_json(tmp_path / row['result_path'])['result']['coverage'] == detection()['coverage']


@pytest.mark.parametrize('output', [[], {'findings': [], 'coverage': []},
    {'findings': [], 'coverage': [{'obligation': 'Result', 'status': 'pass', 'evidence': 'Read tests'}]},
    {'findings': {}, 'coverage': detection()['coverage']}])
def test_missing_or_malformed_coverage_cannot_complete_detection(tmp_path, monkeypatch, output):
    record = begin(tmp_path)
    monkeypatch.setattr(review, '_claude_session', lambda *a, **kw:
                        {'review': {'result': output}, 'seconds': 0})
    result = review_contributors.run(tmp_path, record['id'], ['detector'])
    assert result['contributors']['detector']['status'] == 'failed'
    assert 'Test detector' in str(result['contributors']['detector'])
