"""Ordinary standalone readers consume one shared active wall clock."""
import threading

import pytest
from fbk.workflow import review_execution, review, review_contributors as contributors, review_rounds as rounds
from fbk.workflow.store import WorkflowError


def test_parallel_contributors_charge_wall_once_and_resume_only_missing(tmp_path,monkeypatch):
    (tmp_path/'app.py').write_text('answer=42\n')
    record=rounds.begin(tmp_path,['left','right','challenger'],'Each reader checks answer=42',{})
    clock=[0.0]
    monkeypatch.setattr(review_execution.time,'monotonic',lambda:clock[0])
    barrier=threading.Barrier(2)
    calls=[]
    def session(root,prompt,config,**kwargs):
        calls.append(prompt)
        assert root != tmp_path
        assert (root/'app.py').read_text()=='answer=42\n'
        barrier.wait(timeout=5)
        clock[0]=5
        return {'review':{'result':[]},'seconds':5,'usage':{'tokens':10}}
    monkeypatch.setattr(review,'_claude_session',session)
    result=contributors.run(tmp_path,record['id'],['left','right'])
    assert result['budget']['spent_seconds']==5
    assert result['managed_clock']['worker_seconds']==10
    assert result['missing']==['challenger']
    assert len(calls)==2
    clock[0]=1000  # Human/orchestrator idle time must not spend review execution time.
    def final(root,prompt,config,**kwargs):
        clock[0]=1002
        assert 'left' in prompt and 'right' in prompt
        return {'review':{'result':[]},'seconds':2}
    monkeypatch.setattr(review,'_claude_session',final)
    result=contributors.run(tmp_path,record['id'],['challenger'])
    assert result['budget']['spent_seconds']==7
    assert rounds.require_complete(tmp_path,record['id'])['remediation_allowed']
    with pytest.raises(WorkflowError,match='complete'):
        contributors.run(tmp_path,record['id'],['left'])


def test_exhausted_round_cannot_launch_another_contributor(tmp_path,monkeypatch):
    (tmp_path/'app.py').write_text('answer=42\n')
    record=rounds.begin(tmp_path,['reader'],'Review',{})
    record['budget']['spent_seconds']=record['budget']['seconds']
    rounds.save_round(tmp_path,record)
    monkeypatch.setattr(review,'_claude_session',lambda *a,**k:pytest.fail('Launched after exhaustion'))
    with pytest.raises(WorkflowError,match='budget'):
        contributors.run(tmp_path,record['id'],['reader'])
    assert rounds.status(tmp_path,record['id'])['missing']==['reader']


def test_failed_contributor_retains_completed_peer_and_consumed_budget(tmp_path,monkeypatch):
    (tmp_path/'app.py').write_text('answer=42\n')
    record=rounds.begin(tmp_path,['left','right'],'Review',{})
    clock=[0.0]
    monkeypatch.setattr(review_execution.time,'monotonic',lambda:clock[0])
    def session(root,prompt,config,**kwargs):
        clock[0]=2
        if 'Contributor: right' in prompt:raise WorkflowError('reader failed')
        return {'review':{'result':[]},'seconds':2}
    monkeypatch.setattr(review,'_claude_session',session)
    result=contributors.run(tmp_path,record['id'],['left','right'])
    assert result['missing']==['right']
    assert result['budget']['spent_seconds']==2
    assert result['contributors']['right']['status']=='failed'
    with pytest.raises(WorkflowError,match='incomplete'):
        rounds.require_complete(tmp_path,record['id'])


def test_finished_results_cannot_bypass_active_or_exhausted_execution(tmp_path,monkeypatch):
    (tmp_path/'app.py').write_text('answer=42\n')
    record=rounds.begin(tmp_path,['reader'],'Review',{})
    monkeypatch.setattr(review,'_claude_session',lambda *a,**k:{'review':{'result':[]},'seconds':1})
    contributors.run(tmp_path,record['id'],['reader'])
    record=rounds.load_round(tmp_path,record['id'])
    record['managed_clock']['active']=True
    rounds.save_round(tmp_path,record)
    with pytest.raises(WorkflowError,match='execution'):
        rounds.require_complete(tmp_path,record['id'])
    record['managed_clock']['active']=False
    record['budget']['spent_seconds']=record['budget']['seconds']
    rounds.save_round(tmp_path,record)
    with pytest.raises(WorkflowError,match='budget'):
        rounds.require_complete(tmp_path,record['id'])
