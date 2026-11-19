"""Every assigned managed reader must finish; source drift must be diagnosable."""
import pytest
from fbk.workflow import review, store
from tests import test_workflow_lifecycle as scenarios

project = scenarios.project


def test_configured_second_reader_failure_cannot_be_clean_review(tmp_path, monkeypatch):
    record = {'events':[], 'parent':None, 'review_plans':{}}
    monkeypatch.setattr(review, 'claude_review', lambda *a, **k: {
        'review':{'summary':'native clean','findings':[]}})
    monkeypatch.setattr(review, 'run_command', lambda *a, **k: {
        'exit_code':1, 'stdout':'', 'stderr':'worker failed'})
    result = review._review_sources(tmp_path, 'feature', 'intent', [], [],
                                   {'second_reader':['reviewer'], '_review_available_files':{}}, record)
    assert result.get('error')
    assert result['second_reader_failure']


def test_managed_drift_retains_paths_and_both_revisions(project, monkeypatch):
    def reviewer(root, *args):
        (project / 'src/app.py').write_text('external change\n')
        return {'shape':'single','readers':[],
                'review':{'summary':'snapshot clean','findings':[]}}
    monkeypatch.setattr(review, '_review_sources', reviewer)
    result = review.review(project, 'feature', 'intent', ['.fbk/feature/prd.md'], [])
    drift = result.get('source_drift')
    assert drift and 'src/app.py' in drift['paths']
    assert drift['detected_at'] and drift['original_revision'] != drift['current_revision']
    events = store.load(project,'feature')['events']
    assert any(e['event'] == 'review-source-drift' for e in events)


def test_completed_peer_is_durable_before_council_returns(project):
    from fbk.workflow import close
    record = store.load(project, 'feature')
    work = record['phases']['intent']
    work['pending'] = {'id':'interrupted','session':'test'}
    work['rounds'] = [{'operation':'interrupted','result':{'readers':[]}}]
    store.save(project,record)
    progress = review._council_progress(project,'feature','intent','interrupted')
    progress('contract','started',reader_context='contract-hash')
    response = {'review':{'summary':'complete peer','findings':[]},'seconds':3}
    progress('opening','completed','guardian',response=response)
    interrupted = store.load(project,'feature')
    durable = interrupted['phases']['intent']['rounds'][-1]['result']
    assert durable['reader_context'] == 'contract-hash'
    assert durable['readers'][0]['review'] == response['review']
    assert durable['readers'][0]['member'] == 'guardian'
    close.recover(project, interrupted, 'intent', interrupted.get('owner') or 'test', 'Old process stopped')
    recovered = store.load(project,'feature')['phases']['intent']['rounds'][-1]
    assert recovered['error']
    assert recovered['result']['readers'] == durable['readers']
