"""Malformed native output cannot discard a blocker through mapping coercion."""

import json

import pytest

from fbk.workflow import review, store


def verdict():
    return {
        'summary': 'The implementation violates the cancellation contract.',
        'findings': [{
            'title': 'Cancellation leaks its resource',
            'location': 'app.py:1',
            'evidence': 'The cancellation path returns without releasing its resource.',
            'remedy': 'Release the resource on the first cancellation.',
            'severity': 'blocker',
        }],
        'context': {
            'status': 'complete', 'inspected_files': ['app.py'],
            'supporting_files': [], 'missing_context': [],
        },
    }


def native(monkeypatch, data, transport):
    # Managed sessions use the same flat object; only the configuration differs.
    envelope = {'subtype': 'success', 'is_error': False}
    if transport == 'result-string':
        envelope['result'] = json.dumps(data)
    else:
        envelope['structured_output'] = data
    monkeypatch.setattr(review, 'run_command', lambda *args: {
        'exit_code': 0, 'seconds': 0.01, 'stdout': json.dumps(envelope), 'stderr': '',
    })
    return {
        '_review_available_files': {'app.py': 'snapshot-hash'},
        '_review_required_files': ['app.py'],
        **({'_managed_project_root': '/isolated-project'} if transport == 'managed-response' else {}),
    }


@pytest.mark.parametrize('transport', ['structured-output', 'result-string', 'managed-response'])
def test_native_key_value_array_cannot_erase_blocker(tmp_path, monkeypatch, transport):
    # This is an array, not an object. dict() would silently discard the first
    # findings value and turn the reported blocker into a clean review.
    pairs = list(verdict().items()) + [['findings', []]]
    config = native(monkeypatch, pairs, transport)
    with pytest.raises(store.WorkflowError, match='object|invalid review'):
        review._claude_session(tmp_path, 'Review cancellation.', config)


@pytest.mark.parametrize('transport', ['structured-output', 'result-string', 'managed-response'])
def test_native_object_preserves_blocker_and_inspection_record(tmp_path, monkeypatch, transport):
    original = verdict()
    config = native(monkeypatch, original, transport)
    result = review._claude_session(tmp_path, 'Review cancellation.', config)
    assert result['review'] == {key: original[key] for key in ('summary', 'findings')}
    assert result['context'] == original['context']
