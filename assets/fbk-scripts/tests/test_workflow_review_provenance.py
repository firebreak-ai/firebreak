"""Imported findings are useful evidence, never proof a budgeted reviewer ran."""
import json
import pytest
from fbk.workflow import review_execution as managed, review, review_contributors as contributors, review_rounds as rounds
from fbk.workflow.store import WorkflowError,digest


def envelope(root,record,result):
    path=root/'.fbk/import.json'
    path.write_text(json.dumps({'schema':'review-contribution-v1','round_id':record['id'],
        'contract_id':record['contract_id'],'contributor':'reader','status':'complete',
        'result':result,'result_digest':digest(result)}))
    return path


@pytest.mark.parametrize('active',[False,True])
def test_imported_result_never_completes_even_during_active_session(tmp_path,active):
    (tmp_path/'app.py').write_text('answer=42\n')
    record=rounds.begin(tmp_path,['reader'],'Review answer',{})
    execution=managed.activate_round(tmp_path,record['id']) if active else None
    try:
        result=rounds.submit(tmp_path,record['id'],envelope(tmp_path,record,[]))
        assert result['contributors']['reader']['status']!='complete'
        assert result['supporting_results']
    finally:
        if execution:execution.finish()
    with pytest.raises(WorkflowError,match='incomplete'):
        rounds.require_complete(tmp_path,record['id'])


def test_runtime_completion_records_bound_provenance_and_rejects_tampering(tmp_path,monkeypatch):
    (tmp_path/'app.py').write_text('answer=42\n')
    record=rounds.begin(tmp_path,['reader'],'Review answer',{})
    monkeypatch.setattr(review,'_claude_session',lambda *a,**k:{'review':{'result':[]},'seconds':1})
    result=contributors.run(tmp_path,record['id'],['reader'])
    provenance=result['contributors']['reader']['provenance']
    assert provenance['contract_id']==record['contract_id']
    assert provenance['snapshot_digest']==digest(record['snapshot_files'])
    assert provenance['execution_id'] and provenance['response_path']
    assert rounds.require_complete(tmp_path,record['id'])['remediation_allowed']
    (tmp_path/provenance['response_path']).write_text('{}')
    with pytest.raises(WorkflowError,match='incomplete'):
        rounds.require_complete(tmp_path,record['id'])


def test_imported_clean_result_cannot_replace_failed_runtime_reader(tmp_path,monkeypatch):
    (tmp_path/'app.py').write_text('answer=42\n')
    record=rounds.begin(tmp_path,['reader'],'Review answer',{})
    def failed(*a,**k):raise WorkflowError('Reader crashed')
    monkeypatch.setattr(review,'_claude_session',failed)
    contributors.run(tmp_path,record['id'],['reader'])
    result=rounds.submit(tmp_path,record['id'],envelope(tmp_path,record,[]))
    assert result['contributors']['reader']['status']=='failed'
    with pytest.raises(WorkflowError,match='incomplete'):
        rounds.require_complete(tmp_path,record['id'])
