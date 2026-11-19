"""A clean review and green suite cannot replace independent fix/test evidence."""
import hashlib
import json
import subprocess
import sys

import pytest
from fbk.workflow import investigations, remediation_verification as remediation, review_rounds as rounds
from fbk.workflow.store import WorkflowError, digest


def deliver(root, record, member, result):
    path = root / '.fbk' / (member + '.json')
    path.write_text(json.dumps({'schema':'review-contribution-v1', 'round_id':record['id'],
        'contract_id':record['contract_id'], 'contributor':member, 'status':'complete',
        'result':result, 'result_digest':digest(result)}))
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


@pytest.fixture
def setup(tmp_path):
    (tmp_path/'app.py').write_text('def square(n): return n\n')
    (tmp_path/'test_app.py').write_text('from app import square\nassert square(2) == 4\nprint("square assertion passed")\n')
    first = rounds.begin(tmp_path,['detector','challenger'],'Check square',{})
    deliver(tmp_path,first,'detector',[{'id':'F1','status':'verified','evidence':'square returns its input'}])
    deliver(tmp_path,first,'challenger',[])
    return tmp_path, first


def declaration(root, first):
    return remediation.declare(root,first['id'],{'id':'square-fix',
        'finding':{'contributor':'detector','index':0}, 'behavior':'square returns n squared',
        'requirements':['square arithmetic contract'], 'scope':['app.py','test_app.py'],
        'siblings':['app.py']})


def followup(root,first):
    (root/'app.py').write_text('def square(n): return n*n\n')
    post = rounds.begin(root,['detector','challenger'],'Review square correction',{},previous=first['id'])
    deliver(root,post,'detector',[])
    deliver(root,post,'challenger',[])
    return post


def worker(argv,cwd,timeout,prompt=None):
    assert argv[0]=='claude' and '-p' in argv and '--resume' not in argv
    assignment=json.loads((cwd/'investigation-assignment.json').read_text())
    assert assignment['purpose']=='independent-verification'
    command=[sys.executable,'-B','test_app.py']
    fixed=subprocess.run(command,cwd=cwd,capture_output=True,text=True)
    (cwd/'fixed.log').write_text(fixed.stdout+fixed.stderr)
    (cwd/'app.py').write_text('def square(n): return n\n')
    (cwd/'defective-app.py').write_text((cwd/'app.py').read_text())
    defect=subprocess.run(command,cwd=cwd,capture_output=True,text=True)
    (cwd/'defect.log').write_text(defect.stdout+defect.stderr)
    report={'schema':'remediation-verification-v1','contract_id':assignment['contract_id'],
        'remediation_id':'square-fix','status':'verified',
        'behavior':{'evidence':{'path':'fixed.log','quote':'square assertion passed'},'assessment':'square computes the expected result'},
        'regression':{'fixed':{'argv':command,'exit_code':fixed.returncode,'evidence':{'path':'fixed.log','quote':'square assertion passed'}},
            'defect':{'argv':command,'exit_code':defect.returncode,'evidence':{'path':'defect.log','quote':'AssertionError'}},
            'defect_source':'defective-app.py','rejected_behavior':'Returning the original input violates the square assertion',
            'exception':None},
        'siblings':[{'path':'app.py','status':'fixed','reason':'The only square implementation now multiplies its input'}],
        'limitations':'One public arithmetic example; the follow-up review covers adjacent behavior'}
    (cwd/'verification.json').write_text(json.dumps(report))
    return {'exit_code':0,'seconds':1,'stdout':json.dumps({'subtype':'success','result':'Recorded verification'}),'stderr':''}


def test_material_fix_requires_independent_evidence_after_green_review(setup,monkeypatch):
    root,first=setup
    declaration(root,first)
    assert rounds.require_complete(root,first['id'])['remediation_allowed']
    post=followup(root,first)
    with pytest.raises(WorkflowError,match='verification'):
        rounds.require_complete(root,post['id'])
    monkeypatch.setattr(investigations,'run_command',worker)
    result=remediation.verify(root,post['id'],'square-fix')
    assert result['status']=='verified'
    assert rounds.require_complete(root,post['id'])['remediation_allowed']
    assert (root/'app.py').read_text()=='def square(n): return n*n\n'
    assert rounds.load_round(root,post['id'])['budget']['spent_seconds']==1


def test_undeclared_actual_changes_need_reviewed_accounting(setup):
    root,first=setup
    post=followup(root,first)
    status=rounds.status(root,post['id'])
    assert status['unaccounted_changes']==['app.py']
    with pytest.raises(WorkflowError,match='unaccounted'):
        rounds.require_complete(root,post['id'])


def test_nonmaterial_change_is_explicitly_accounted_by_fresh_contributor(setup):
    root,first=setup
    (root/'app.py').write_text('# explanatory comment\ndef square(n): return n\n')
    post=rounds.begin(root,['detector','challenger'],'Review comment',{},previous=first['id'])
    deliver(root,post,'detector',[])
    deliver(root,post,'challenger',{'change_accounting':[{'path':'app.py','classification':'nonmaterial','reason':'Only explanatory comment added; behavior unchanged'}]})
    assert rounds.require_complete(root,post['id'])['remediation_allowed']


@pytest.mark.parametrize('problem',['missing','vacuous','sibling','stale'])
def test_invalid_verifier_result_does_not_complete_round(setup,monkeypatch,problem):
    root,first=setup
    declaration(root,first)
    post=followup(root,first)
    def invalid(argv,cwd,timeout,prompt=None):
        result=worker(argv,cwd,timeout,prompt)
        path=cwd/'verification.json'
        if problem=='missing':path.unlink()
        else:
            data=json.loads(path.read_text())
            if problem=='vacuous':data['regression']['defect']['exit_code']=0
            if problem=='sibling':data['siblings']=[]
            if problem=='stale':data['contract_id']='old-revision'
            path.write_text(json.dumps(data))
        return result
    monkeypatch.setattr(investigations,'run_command',invalid)
    with pytest.raises(WorkflowError):remediation.verify(root,post['id'],'square-fix')
    with pytest.raises(WorkflowError):rounds.require_complete(root,post['id'])


def rejecting(argv,cwd,timeout,prompt=None):
    """An honest rejection: the fixed check still fails, so no red/green proof exists."""
    result=worker(argv,cwd,timeout,prompt)
    path=cwd/'verification.json'
    data=json.loads(path.read_text())
    data['status']='rejected'
    data['behavior']['assessment']='square still returns its input for negative numbers'
    data['regression']['fixed']['exit_code']=1
    data['regression']['rejected_behavior']='Negative inputs are not squared'
    data['siblings']=[]
    path.write_text(json.dumps(data))
    return result


def test_rejected_verifier_report_is_recorded_as_the_verdict(setup,monkeypatch):
    root,first=setup
    declaration(root,first)
    post=followup(root,first)
    monkeypatch.setattr(investigations,'run_command',rejecting)
    with pytest.raises(WorkflowError,match='square-fix not accepted: independent verifier returned rejected: Negative inputs are not squared'):
        remediation.verify(root,post['id'],'square-fix')
    record=rounds.load_round(root,post['id'])
    item=record['remediations']['square-fix']
    assert item['status']=='rejected'
    assert item['verification']['status']=='rejected'
    assert item['verification']['rejected_behavior']=='Negative inputs are not squared'
    assert [f['path'].rsplit('/',1)[-1] for f in item['verification']['evidence_files']]==['fixed.log','verification.json']
    assert 'independent-remediation-rejected' in [e['type'] for e in record['events']]
    entry=record['investigations']['verify-square-fix']
    assert entry['resolution']['conclusion'].startswith('Independent verifier rejected the remediation: Negative inputs')
    assert (root/'app.py').read_text()=='def square(n): return n*n\n'
    with pytest.raises(WorkflowError,match='verification'):
        rounds.require_complete(root,post['id'])


@pytest.mark.parametrize('field',['assessment','rejected_behavior','limitations','evidence'])
def test_malformed_rejected_report_still_raises_as_invalid(setup,monkeypatch,field):
    root,first=setup
    declaration(root,first)
    post=followup(root,first)
    def malformed(argv,cwd,timeout,prompt=None):
        result=rejecting(argv,cwd,timeout,prompt)
        path=cwd/'verification.json'
        data=json.loads(path.read_text())
        if field=='assessment':data['behavior']['assessment']=''
        if field=='rejected_behavior':data['regression']['rejected_behavior']=''
        if field=='limitations':data['limitations']=''
        if field=='evidence':data['behavior']['evidence']['quote']='never logged'
        path.write_text(json.dumps(data))
        return result
    monkeypatch.setattr(investigations,'run_command',malformed)
    with pytest.raises(WorkflowError,match='needs an assessment, the rejected behavior, limitations and attributed behavior evidence|evidence quotation is unavailable'):
        remediation.verify(root,post['id'],'square-fix')
    item=rounds.load_round(root,post['id'])['remediations']['square-fix']
    assert item['status']!='rejected' and 'verification' not in item


def test_evidence_tampering_invalidates_independent_verification(setup,monkeypatch):
    root,first=setup
    declaration(root,first)
    post=followup(root,first)
    monkeypatch.setattr(investigations,'run_command',worker)
    result=remediation.verify(root,post['id'],'square-fix')
    path=root/result['evidence_files'][0]['path']
    path.write_text('overwritten')
    with pytest.raises(WorkflowError,match='verification'):
        rounds.require_complete(root,post['id'])


def test_new_followup_cannot_erase_unaccounted_changes(setup):
    root,first=setup
    post=followup(root,first)
    again=rounds.begin(root,['detector','challenger'],'Retry transport',{},previous=post['id'])
    deliver(root,again,'detector',[])
    deliver(root,again,'challenger',[])
    assert rounds.status(root,again['id'])['unaccounted_changes']==['app.py']
    with pytest.raises(WorkflowError,match='unaccounted'):
        rounds.require_complete(root,again['id'])
