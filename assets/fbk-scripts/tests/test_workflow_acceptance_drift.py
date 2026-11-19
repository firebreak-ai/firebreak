"""Post-close observations preserve acceptance and distinguish scope from evidence."""

import copy

from fbk.workflow import close, engine, handoff, store
from .test_workflow_lifecycle import clean_review, prepare_implementation, project, complete_declared_implementation_task, observe_phase


def accepted_project(project):
    scope_path = project / '.fbk/feature/scope.json'
    scope = store.read_json(scope_path)
    scope['tests'] = ['tests/check.py']
    store.atomic_json(scope_path, scope)
    (project / 'tests/test_preexisting.py').write_text('def test_old(): pass\n')
    prepare_implementation(project)
    (project / 'src/app.py').write_text('release()')
    complete_declared_implementation_task(project)
    close.close_phase(project, 'feature', 'implement', 's', reviewer=clean_review)
    observe_phase(project, 'implement')
    return store.load(project, 'feature')


def test_post_close_changes_are_explained_without_rewriting_acceptance(project):
    record = accepted_project(project)
    before = copy.deepcopy(record)
    (project / 'src/app.py').write_text('release()\n# reviewed later\n')
    (project / 'tests/check.py').write_text('assert True\n')
    (project / 'tests/test_regression.py').write_text('def test_regression(): assert False\n')
    (project / 'notes.txt').write_text('unrelated\n')
    report = engine.status_report(project, record)
    drift = report['acceptance_drift']
    changes = {row['path']: row for row in drift['changes']}
    assert report['status'] == 'stale'
    assert changes['src/app.py']['kind'] == 'modified'
    assert changes['tests/check.py']['kind'] == 'modified'
    assert 'notes.txt' not in changes
    assert drift['outside_scope_test_candidates'] == ['tests/test_regression.py']
    assert drift['inventory_baseline_known'] is True
    assert handoff.continuation(project, record)['acceptance_drift'] == drift
    assert record == before
    assert store.load(project, 'feature') == before


def test_deleted_and_new_scoped_files_are_distinct_from_unscoped_candidates(project):
    record = accepted_project(project)
    (project / 'src/app.py').unlink()
    (project / 'src/new.py').write_text('pass\n')
    drift = engine.status_report(project, record)['acceptance_drift']
    assert {(r['path'], r['kind']) for r in drift['changes']} == {
        ('src/app.py', 'deleted'), ('src/new.py', 'added')
    }
    assert drift['outside_scope_test_candidates'] == []


def test_historical_acceptance_reports_candidates_without_claiming_they_are_new(project):
    record = accepted_project(project)
    record['phases']['implement']['evidence'].pop('drift_baseline')
    drift = engine.status_report(project, record)['acceptance_drift']
    assert drift['inventory_baseline_known'] is False
    assert drift['outside_scope_test_candidates'] == ['tests/test_preexisting.py']
    assert drift['changes'] == []
    assert engine.status_report(project, record)['status'] == 'closed'


def test_discovery_excludes_caches_and_does_not_follow_external_symlinks(project, tmp_path_factory):
    record = accepted_project(project)
    external = tmp_path_factory.mktemp('outside') / 'test_secret.py'
    external.write_text('secret = 42\n')
    (project / 'tests/test_external.py').symlink_to(external)
    cache = project / 'tests/__pycache__'
    cache.mkdir()
    (cache / 'test_noise.py').write_text('pass\n')
    assert engine.status_report(project, record)['acceptance_drift']['outside_scope_test_candidates'] == []


def test_bounded_handoff_keeps_drift_warning_and_retrieval_when_paths_do_not_fit(project):
    record = accepted_project(project)
    for index in range(120):
        (project / f'src/addition_{index}.py').write_text('pass\n')
    packet = handoff.continuation(project, record, max_chars=1200)
    assert packet['acceptance_drift']['change_count'] == 120
    assert packet['acceptance_drift']['retrieve'] == 'status feature'
