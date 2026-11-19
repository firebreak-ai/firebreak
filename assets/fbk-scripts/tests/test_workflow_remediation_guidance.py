"""The isolated managed reviewer receives remediation methodology from its installation."""
import json
import posixpath
from pathlib import Path

import pytest

from fbk.workflow import review, store
from tests.test_workflow_lifecycle import project as project
from tests.test_workflow_review import native


@pytest.mark.parametrize('layout', ['project/.claude', 'home/.claude'])
def test_installed_remediation_reference_reaches_isolated_reviewer(project, tmp_path_factory, monkeypatch, layout):
    canonical = Path(review.__file__).resolve().parents[3] / 'fbk-docs'
    expected = (canonical / 'review/remediation-verification.md').read_text()
    installation = tmp_path_factory.mktemp('installed-guidance') / layout
    module = installation / 'fbk-scripts/fbk/workflow/review.py'
    module.parent.mkdir(parents=True)
    for source in Path(review.__file__).parent.glob('*.py'):
        (module.parent / source.name).write_text(source.read_text())
    for relative in (*review.DETECTION_GUIDES, *review.REVIEW_BRIEFS):
        target = installation / 'fbk-docs' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((canonical / relative).read_text())
    lookalike = project / 'fbk-docs/review/remediation-verification.md'
    lookalike.parent.mkdir(parents=True)
    lookalike.write_text('PROJECT_LOOKALIKE')
    monkeypatch.setattr(review, '__file__', str(module))
    launches = []

    def session(root, prompt, config, **kwargs):
        assert root != project
        packet = json.loads(prompt.splitlines()[-1])
        supplied = packet['implementation_detection']
        # Resolve the callers' actual relative references within the delivered collection.
        for caller in ['review/detection-audits.md', 'fbk-review-lenses/shared-detection.md']:
            references = [item for item in supplied[caller].split('`')[1::2]
                          if item.endswith('remediation-verification.md')]
            assert len(references) == 1
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(caller), references[0]))
            assert supplied[resolved] == expected
        assert 'PROJECT_LOOKALIKE' not in prompt
        assert 'review/code-review-guide.md' not in supplied
        assert not (root / '.claude/fbk-docs/review/remediation-verification.md').exists()
        launches.append(root)
        return native()

    monkeypatch.setattr(review, '_claude_session', session)
    result = review.review(project, 'feature', 'implement', ['.fbk/feature/spec.md'], [])
    assert len(launches) == 1
    assert result['detection_guidance']['review/remediation-verification.md'] == store.digest(expected)
    assert 'review/remediation-verification.md' not in result['snapshot_files']


@pytest.mark.parametrize('layout', ['project/.claude', 'home/.claude'])
def test_fresh_verifier_receives_current_installed_methodology(tmp_path, tmp_path_factory, monkeypatch, layout):
    from fbk.workflow import investigations, remediation_verification as remediation, review_rounds as rounds
    from tests.test_workflow_remediation_verification import deliver, declaration, followup, worker

    canonical = Path(review.__file__).resolve().parents[3] / 'fbk-docs/review/remediation-verification.md'
    installation = tmp_path_factory.mktemp('verifier-installation') / layout
    module = installation / 'fbk-scripts/fbk/workflow/review.py'
    module.parent.mkdir(parents=True)
    module.touch()
    installed = installation / 'fbk-docs/review/remediation-verification.md'
    installed.parent.mkdir(parents=True)
    installed.write_text(canonical.read_text())
    monkeypatch.setattr(review, '__file__', str(module))
    original = review.remediation_guidance()
    # A later invocation must read updated installation content, not a cached copy.
    updated = canonical.read_text() + '\nInstalled methodology revision for this delivery test.\n'
    installed.write_text(updated)
    root = tmp_path
    (root / 'app.py').write_text('def square(n): return n\n')
    (root / 'test_app.py').write_text('from app import square\nassert square(2) == 4\nprint("square assertion passed")\n')
    lookalike = root / 'fbk-docs/review/remediation-verification.md'
    lookalike.parent.mkdir(parents=True)
    lookalike.write_text('PROJECT_LOOKALIKE')
    first = rounds.begin(root, ['detector', 'challenger'], 'Check square', {})
    deliver(root, first, 'detector', [{'status': 'verified', 'evidence': 'square returns its input'}])
    deliver(root, first, 'challenger', [])
    declaration(root, first)
    post = followup(root, first)
    captured = []

    def fresh_worker(argv, cwd, timeout, prompt=None):
        assert cwd != root
        supplied = json.loads(prompt.split('Supplied remediation methodology:\n', 1)[1].splitlines()[0])
        assert supplied == {'review/remediation-verification.md': updated}
        assert supplied != original
        assert 'PROJECT_LOOKALIKE' not in prompt
        captured.append(supplied)
        return worker(argv, cwd, timeout, prompt)

    monkeypatch.setattr(investigations, 'run_command', fresh_worker)
    result = remediation.verify(root, post['id'], 'square-fix')
    assert result['status'] == 'verified'
    assert len(captured) == 1
    assert (root / 'app.py').read_text() == 'def square(n): return n*n\n'
