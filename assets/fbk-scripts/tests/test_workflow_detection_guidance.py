"""Managed code review receives shipped targets without adding project authority."""
import json
from pathlib import Path

import pytest

from fbk.workflow import review, store
from tests.test_workflow_lifecycle import project as project
from tests.test_workflow_review import native


def test_implementation_reviewer_receives_catalogs_inside_isolated_prompt(project, monkeypatch):
    guides = review.implementation_guidance()
    captured = []
    def session(root, prompt, config, **kwargs):
        assert root != project
        packet = json.loads(prompt.splitlines()[-1])
        captured.append(packet)
        assert packet['implementation_detection'] == guides
        assert not set(guides) & set(config['_review_required_files'])
        assert not (root / 'fbk-docs').exists()
        return native()
    monkeypatch.setattr(review, '_claude_session', session)
    result = review.review(project, 'feature', 'implement', ['.fbk/feature/spec.md'], [])
    assert len(captured) == 1
    assert result['detection_guidance'] == {name: store.digest(text) for name, text in guides.items()}
    assert not set(guides) & set(result['snapshot_files'])


def test_guidance_changes_get_new_execution_identity(project, monkeypatch):
    monkeypatch.setattr(review, '_claude_session', lambda *a, **k: native())
    monkeypatch.setattr(review, 'implementation_guidance', lambda: {'targets.md': 'Trace caller one.'})
    first = review.review(project, 'feature', 'implement', ['.fbk/feature/spec.md'], [])
    monkeypatch.setattr(review, 'implementation_guidance', lambda: {'targets.md': 'Trace caller two.'})
    second = review.review(project, 'feature', 'implement', ['.fbk/feature/spec.md'], [])
    assert first['snapshot_files'] == second['snapshot_files']
    assert first['investigation_round'] != second['investigation_round']
    assert first['detection_guidance'] != second['detection_guidance']


@pytest.mark.parametrize("phase", ["intent", "design", "spec"])
def test_upstream_review_does_not_load_detection_catalogs(project, monkeypatch, phase):
    monkeypatch.setattr(review, 'implementation_guidance', lambda: pytest.fail('Code targets loaded upstream'))
    monkeypatch.setattr(review, 'test_guidance', lambda: pytest.fail('Test criteria loaded upstream'))
    def session(root, prompt, config, **kwargs):
        packet = json.loads(prompt.splitlines()[-1])
        assert 'implementation_detection' not in packet
        assert 'test_detection' not in packet
        assert 'For test review, apply the current stage' not in prompt
        return native()
    monkeypatch.setattr(review, '_claude_session', session)
    result = review.review(project, 'feature', phase, ['.fbk/feature/spec.md'], [])
    assert 'detection_guidance' not in result


@pytest.mark.parametrize('empty', [False, True])
def test_missing_or_empty_installed_guidance_fails_before_review(project, monkeypatch, empty):
    original = Path.read_text
    launches = []
    def read(path, *args, **kwargs):
        if path.as_posix().endswith('fbk-docs/review/ai-failure-modes.md'):
            if empty:
                return ''
            raise FileNotFoundError(path)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', read)
    monkeypatch.setattr(review, '_claude_session', lambda *a, **k: launches.append(1))
    with pytest.raises(store.WorkflowError, match='guidance.*(unavailable|empty)'):
        review.review(project, 'feature', 'implement', ['.fbk/feature/spec.md'], [])
    assert launches == []


@pytest.mark.parametrize('phase', ['breakdown', 'implement'])
def test_test_criteria_use_shared_source_and_managed_result_contract(project, monkeypatch, phase):
    canonical = Path(review.__file__).resolve().parents[3] / 'fbk-docs/review/test-integrity.md'
    # A project lookalike cannot replace installed review methodology.
    lookalike = project / 'fbk-docs/review/test-integrity.md'
    lookalike.parent.mkdir(parents=True)
    lookalike.write_text('PROJECT_LOOKALIKE_NOT_METHODOLOGY')
    captured = []

    def session(root, prompt, config, **kwargs):
        packet = json.loads(prompt.splitlines()[-1])
        key = 'test_detection' if phase == 'breakdown' else 'implementation_detection'
        assert packet[key]['review/test-integrity.md'] == canonical.read_text()
        assert 'PROJECT_LOOKALIKE_NOT_METHODOLOGY' not in prompt
        assert '"coverage": [...]' not in prompt
        assert 'lens-matrix' not in packet[key]['review/test-integrity.md']
        assert 'existing summary' in prompt
        assert 'missing_context with incomplete context status' in prompt
        assert 'planned, source-inspected and executed evidence' in prompt
        if phase == 'breakdown':
            assert set(packet[key]) == {'review/test-integrity.md'}
            # Breakdown reviews the plan: its targets are the tasks, not tests that do not exist yet.
            assert 'tests/check.py' not in json.dumps(packet['required_files'])
        # The actual reader receives the existing managed schema, not a test lens envelope.
        assert 'coverage' not in json.dumps(kwargs['schema'])
        captured.append(packet)
        return native()

    monkeypatch.setattr(review, '_claude_session', session)
    result = review.review(project, 'feature', phase, ['.fbk/feature/spec.md'], [])
    assert len(captured) == 1
    assert result['detection_guidance']['review/test-integrity.md'] == store.digest(canonical.read_text())
    assert set(result['review']) == {'summary', 'findings'}


def test_breakdown_guidance_changes_invalidate_execution_identity(project, monkeypatch):
    monkeypatch.setattr(review, '_claude_session', lambda *a, **k: native())
    monkeypatch.setattr(review, 'test_guidance', lambda: {'test-integrity.md': 'Inspect expected failures.'})
    first = review.review(project, 'feature', 'breakdown', ['.fbk/feature/spec.md'], [])
    monkeypatch.setattr(review, 'test_guidance', lambda: {'test-integrity.md': 'Inspect stale expected failures.'})
    second = review.review(project, 'feature', 'breakdown', ['.fbk/feature/spec.md'], [])
    assert first['snapshot_files'] == second['snapshot_files']
    assert first['investigation_round'] != second['investigation_round']
    assert first['detection_guidance'] != second['detection_guidance']


@pytest.mark.parametrize('phase', ['breakdown', 'implement'])
@pytest.mark.parametrize('empty', [False, True])
def test_unavailable_shared_test_criteria_fail_before_launch(project, monkeypatch, phase, empty):
    original = Path.read_text
    launches = []

    def read(path, *args, **kwargs):
        if path.as_posix().endswith('fbk-docs/review/test-integrity.md'):
            if empty:
                return '  \n'
            raise FileNotFoundError(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', read)
    monkeypatch.setattr(review, '_claude_session', lambda *a, **k: launches.append(1))
    with pytest.raises(store.WorkflowError, match='guidance.*(unavailable|empty)'):
        review.review(project, 'feature', phase, ['.fbk/feature/spec.md'], [])
    assert launches == []
