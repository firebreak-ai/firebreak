"""Runtime code review preserves neutral challenge and actionable verified records."""
import json
from pathlib import Path

import pytest
from fbk.workflow import review, review_contributors, review_rounds, remediation_verification
from fbk.workflow.store import WorkflowError, read_json

LENS = Path(__file__).resolve().parents[2] / 'fbk-docs/fbk-review-lenses/code-lens.md'


def sighting(**changes):
    return {'title':'Incorrect square result', 'location':{'file':'app.py','start_line':1},
        'type':'behavioral','severity':'major','mechanism':'Returns the input unchanged',
        'consequence':'The square contract is violated','evidence':'square(2) returns 2',
        'source_of_truth_ref':'spec.md#square','remediation':'SPOILER multiply the input', **changes}


def begin(root):
    (root/'app.py').write_text('def square(n): return n\n')
    (root/'spec.md').write_text('# square\nReturn the mathematical square.\n')
    return review_rounds.begin(root,['finder','skeptic'],'Check square against spec',{},
        required=['spec.md'], code_review={'detector':'finder','challenger':'skeptic',
        'lens':str(LENS),'preset':'behavioral-only','min_severity':'minor'})


def test_runtime_neutral_handoff_rejoins_full_records_for_material_declaration(tmp_path,monkeypatch):
    record=begin(tmp_path)
    def session(root,prompt,config,**kwargs):
        if 'Contributor: finder' in prompt:
            return {'review':{'result':[sighting(),sighting(type='structural',severity='minor')]},'seconds':1}
        handoff=read_json(root/'_review_inputs/normalized.json')
        assert len(handoff)==1
        assert set(handoff[0])=={'mechanism','consequence','evidence','type','severity','source_of_truth_ref'}
        assert not (root/'_review_inputs/finder.json').exists()
        assert 'SPOILER' not in prompt
        assert 'spec.md' in config['_review_required_files']
        assert (root/'spec.md').read_text().startswith('# square')
        return {'review':{'result':[{'status':'verified','verification_evidence':'Executed square(2), observed incorrect 2'}]},'seconds':1}
    monkeypatch.setattr(review,'_claude_session',session)
    review_contributors.run(tmp_path,record['id'],['finder'])
    result=review_contributors.run(tmp_path,record['id'],['skeptic'])
    assert result['remediation_allowed']
    row=result['contributors']['skeptic']
    merged=read_json(tmp_path/row['result_path'])['result']
    assert merged[0]['mechanism']==sighting()['mechanism']
    assert merged[0]['status']=='verified'
    response=read_json(tmp_path/row['provenance']['response_path'])
    assert response['pipeline']['native_response']['review']['result'][0]['status']=='verified'
    assert response['pipeline']['normalized'][0]=={key:response['pipeline']['normalized'][0][key] for key in handoff_keys()}
    declaration=remediation_verification.declare(tmp_path,record['id'],{
        'id':'square-fix','finding':{'contributor':'skeptic','index':0},
        'behavior':'Return mathematical square','requirements':['spec.md#square'],
        'scope':['app.py'],'siblings':['app.py']})
    assert declaration['finding']=={'contributor':'skeptic','index':0}
    assert declaration['finding_evidence']['mechanism']==sighting()['mechanism']
    assert declaration['finding_evidence']['status']=='verified'


def handoff_keys():
    return ['mechanism','consequence','evidence','type','severity','source_of_truth_ref']


@pytest.mark.parametrize('verdicts', [[],[{'status':'verified'}],
    [{'status':'verified','verification_evidence':'Executed the square check','reclassified_from':{'type':'behavioral'},'type':'structural','severity':'critical'}]])
def test_bad_challenger_output_cannot_become_empty_success(tmp_path,monkeypatch,verdicts):
    record=begin(tmp_path)
    monkeypatch.setattr(review,'_claude_session',lambda root,prompt,*a,**k:
        {'review':{'result':[sighting()] if 'Contributor: finder' in prompt else verdicts},'seconds':1})
    review_contributors.run(tmp_path,record['id'],['finder'])
    result=review_contributors.run(tmp_path,record['id'],['skeptic'])
    assert result['contributors']['skeptic']['status']=='failed'
    with pytest.raises(WorkflowError):review_rounds.require_complete(tmp_path,record['id'])


def test_invalid_detection_is_not_clean_review_and_challenger_requires_completed_input(tmp_path,monkeypatch):
    record=begin(tmp_path)
    monkeypatch.setattr(review,'_claude_session',lambda *a,**k: {'review':{'result':[{}]},'seconds':1})
    with pytest.raises(WorkflowError,match='detector'):review_contributors.run(tmp_path,record['id'],['skeptic'])
    review_contributors.run(tmp_path,record['id'],['finder'])
    result=review_contributors.run(tmp_path,record['id'],['skeptic'])
    assert result['contributors']['skeptic']['status']=='failed'


def test_unresolvable_verdict_preserved_and_contract_binds_pipeline_assignment(tmp_path,monkeypatch):
    record=begin(tmp_path)
    monkeypatch.setattr(review,'_claude_session',lambda root,prompt,*a,**k:
        {'review':{'result':[sighting()] if 'Contributor: finder' in prompt else [{'status':'unresolvable'}]},'seconds':1})
    review_contributors.run(tmp_path,record['id'],['finder'])
    result=review_contributors.run(tmp_path,record['id'],['skeptic'])
    row=result['contributors']['skeptic']
    assert read_json(tmp_path/row['result_path'])['result'][0]['status']=='unresolvable'
    assert result['code_review']['detector']=='finder'
    record=review_rounds.load_round(tmp_path,record['id'])
    record['code_review']['preset']='all'
    review_rounds.save_round(tmp_path,record)
    with pytest.raises(WorkflowError,match='contract'):review_rounds.resume(tmp_path,record['id'],'Check square against spec',{})
