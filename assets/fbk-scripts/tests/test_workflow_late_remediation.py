"""Missed registration preserves correct work without manufacturing edit authority."""
import pytest
from fbk.workflow import investigations, remediation_verification as remediation, review_rounds as rounds
from fbk.workflow.store import WorkflowError
from tests.test_workflow_remediation_verification import deliver, worker


def project(root,scope):
    (root/'app.py').write_text('def square(n): return n\n')
    (root/'test_app.py').write_text('from app import square\nassert square(2) == 4\nprint("square assertion passed")\n')
    original=rounds.begin(root,['detector','challenger'],'Review square',{},scope=scope)
    deliver(root,original,'detector',[{'id':'F1','status':'verified','evidence':'square returns input'}])
    deliver(root,original,'challenger',[])
    (root/'app.py').write_text('def square(n): return n*n\n')
    post=rounds.begin(root,['detector','challenger'],'Review actual changes',{},previous=original['id'])
    deliver(root,post,'detector',[]);deliver(root,post,'challenger',[])
    request={'id':'square-fix','original_round':original['id'],
        'finding':{'contributor':'detector','index':0},'behavior':'square returns n squared',
        'requirements':['square arithmetic contract'],'scope':['app.py','test_app.py'],
        'siblings':['app.py'],'reason':'Original authorized correction missed registration'}
    return original,post,request


def test_late_registration_keeps_correct_code_and_still_requires_independent_verification(tmp_path,monkeypatch):
    original,post,request=project(tmp_path,['app.py','test_app.py'])
    result=remediation.register_late(tmp_path,post['id'],request)
    assert result['status']=='pending'
    assert result['recovery']['original_round']==original['id']
    assert result['recovery']['missed_registration']
    assert (tmp_path/'app.py').read_text()=='def square(n): return n*n\n'
    with pytest.raises(WorkflowError,match='verification'):rounds.require_complete(tmp_path,post['id'])
    monkeypatch.setattr(investigations,'run_command',worker)
    remediation.verify(tmp_path,post['id'],'square-fix')
    assert rounds.require_complete(tmp_path,post['id'])['remediation_allowed']
    events=rounds.load_round(tmp_path,post['id'])['events']
    assert any(e['type']=='missed-remediation-registration' for e in events)
    assert not any('approv' in e['type'] for e in events)


@pytest.mark.parametrize('scope',[[],['app.py']])
def test_late_registration_cannot_expand_or_invent_original_scope(tmp_path,scope):
    original,post,request=project(tmp_path,scope)
    with pytest.raises(WorkflowError,match='scope'):
        remediation.register_late(tmp_path,post['id'],request)
    assert rounds.status(tmp_path,post['id'])['unaccounted_changes']==['app.py']


def test_late_registration_requires_original_finding_and_ancestor(tmp_path):
    original,post,request=project(tmp_path,['app.py','test_app.py'])
    request['finding']['index']=99
    with pytest.raises(WorkflowError,match='finding'):
        remediation.register_late(tmp_path,post['id'],request)
    request['finding']['index']=0
    request['original_round']=post['id']
    with pytest.raises(WorkflowError,match='ancestor'):
        remediation.register_late(tmp_path,post['id'],request)
