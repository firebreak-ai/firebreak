"""Managed reviewers resolve observable questions with durable executable evidence."""
import json
import sys

import pytest
from fbk.workflow import investigations, review, store
from tests.test_workflow_commands import call
from tests.test_workflow_review import at_spec, choose, project


def verdict(config):
    return {'summary': 'Checked the actual environment.', 'findings': [], 'context': {
        'status': 'complete', 'inspected_files': config, 'supporting_files': [], 'missing_context': []}}


def host(data, seconds=1):
    return {'exit_code': 0, 'seconds': seconds, 'stdout': json.dumps({'subtype': 'success', 'structured_output': data}), 'stderr': ''}


def test_council_request_runs_real_probe_then_reviewer_receives_evidence(project, monkeypatch):
    at_spec(project)
    choose(project, 'council', members=['builder', 'guardian'])
    observed = []
    real_command = investigations.run_command
    def reviewer(argv, cwd, timeout, prompt):
        required = sorted(p.relative_to(cwd).as_posix() for p in cwd.rglob('*') if p.is_file())
        if 'Council member: guardian.' in prompt and 'Investigation evidence' not in prompt:
            return host({'investigation': {'id': 'python-version', 'question': 'Which Python version actually executes?',
                'requirements': ['.fbk/feature/spec.md'], 'mode': 'direct',
                'argv': [sys.executable, '-c', "import sys; print('OBSERVED_PYTHON=' + str(sys.version_info.major))"]}})
        if 'Council member: guardian.' in prompt:
            observed.append(prompt)
            assert 'OBSERVED_PYTHON=3' in prompt
        return host(verdict(required))
    monkeypatch.setattr(review, 'run_command', reviewer)
    monkeypatch.setattr(investigations, 'run_command', real_command)
    result = call(project, 'phase-close', 'spec', 'feature')
    assert result['accepted_phase'] == 'spec'
    assert len(observed) == 1
    attempts = list((project / '.fbk/runtime/investigations').rglob('investigation-result.json'))
    assert len(attempts) == 1
    assert 'OBSERVED_PYTHON=3' in store.read_json(attempts[0])['stdout']


def test_repeated_managed_requests_stop_without_unbounded_reviewer_loop(project, monkeypatch):
    """Three attempts exhaust the question; the reader hears so, gets one free repeat, then stops."""
    at_spec(project)
    choose(project, 'single')
    launches = []
    def reviewer(argv, cwd, timeout, prompt):
        launches.append(prompt)
        return host({'investigation': {'id': 'repeat', 'question': 'Does this environment support the behavior?',
            'requirements': ['.fbk/feature/spec.md'], 'mode': 'direct', 'argv': [sys.executable, '-c', 'print(42)']}})
    monkeypatch.setattr(review, 'run_command', reviewer)
    with pytest.raises(store.WorkflowError, match='exhausted investigation .* twice'):
        call(project, 'phase-close', 'spec', 'feature')
    assert len(launches) == 5
    assert all('no further attempts are possible' in prompt for prompt in launches[3:])
    attempts = list((project / '.fbk/runtime/investigations').rglob('investigation-result.json'))
    assert len(attempts) == 3
    # A looping reader is an ordinary failed attempt: no budget event, no pause for a human,
    # and the next close attempt runs the reader again without extend-review.
    current = call(project, 'status', 'feature')[0]
    assert current['status'] != 'human-review-required'
    work = store.load(project, 'feature')['phases']['spec']
    assert not work.get('budget_exhausted')
    assert 'budget_exhausted' not in json.dumps(work['rounds'][-1])
    with pytest.raises(store.WorkflowError, match='twice'):
        call(project, 'phase-close', 'spec', 'feature')
    assert len(launches) == 7
    assert len(list((project / '.fbk/runtime/investigations').rglob('investigation-result.json'))) == 3


def test_shared_clock_counts_parallel_wall_once_and_preserves_retry_budget(tmp_path, monkeypatch):
    from fbk.workflow import managed_investigations as managed, review_execution
    source = tmp_path / 'snapshot'
    source.mkdir()
    (source / 'spec.md').write_text('Contract')
    ticks = [100.0]
    monkeypatch.setattr(review_execution.time, 'monotonic', lambda: ticks[0])
    session = managed.open_round(tmp_path, source, {'review_round_timeout': 20}, 'contract')
    ticks[0] = 105.0
    session.record_worker({'seconds': 5, 'usage': {'input_tokens': 10}})
    session.record_worker({'seconds': 5, 'usage': {'input_tokens': 20}})
    session.finish()
    row = investigations._load(tmp_path, session.round_id)
    assert row['budget']['spent_seconds'] == 5
    assert row['managed_clock']['worker_seconds'] == 10
    assert row['managed_clock']['worker_usage'] == [{'input_tokens': 10}, {'input_tokens': 20}]
    ticks[0] = 205.0
    resumed = managed.open_round(tmp_path, source, {'review_round_timeout': 20}, 'contract')
    assert resumed.remaining() == 15
    ticks[0] = 208.0
    resumed.finish()
    row = investigations._load(tmp_path, session.round_id)
    assert row['budget']['spent_seconds'] == 8


def test_shared_clock_limits_late_reader_and_exhaustion_survives_retry(tmp_path, monkeypatch):
    from fbk.workflow import managed_investigations as managed, review_execution
    source = tmp_path / 'snapshot'
    source.mkdir()
    ticks = [1.0]
    monkeypatch.setattr(review_execution.time, 'monotonic', lambda: ticks[0])
    session = managed.open_round(tmp_path, source, {'review_round_timeout': 10}, 'contract')
    ticks[0] = 9.0
    assert session.remaining() == 2
    ticks[0] = 12.0
    with pytest.raises(store.WorkflowError, match='human'):
        session.remaining()
    session.finish()
    with pytest.raises(store.WorkflowError, match='human'):
        managed.open_round(tmp_path, source, {'review_round_timeout': 10}, 'contract')


def test_explicit_round_extension_preserves_consumed_time(tmp_path, monkeypatch):
    from fbk.workflow import managed_investigations as managed, review_execution
    source = tmp_path / 'snapshot'
    source.mkdir()
    ticks = [1.0]
    monkeypatch.setattr(review_execution.time, 'monotonic', lambda: ticks[0])
    session = managed.open_round(tmp_path, source, {'review_round_timeout': 10}, 'contract')
    ticks[0] = 11.0
    session.finish()
    review_execution.extend_round(tmp_path, session.round_id, 1, 'Human approves one additional review round.')
    resumed = managed.open_round(tmp_path, source, {'review_round_timeout': 10}, 'contract')
    assert resumed.remaining() == 10
    row = investigations._load(tmp_path, session.round_id)
    assert row['budget']['spent_seconds'] == 10
    assert row['managed_clock']['extensions'][0]['reason'].startswith('Human approves')
    resumed.finish()


def test_full_experiment_evidence_is_reachable_inside_reviewer_snapshot(tmp_path):
    from fbk.workflow import managed_investigations as managed
    live = tmp_path / 'live'
    snapshot = tmp_path / 'reader'
    snapshot.mkdir()
    workspace = live / '.fbk/runtime/investigations/r/q/1'
    workspace.mkdir(parents=True)
    output = 'critical observation at beginning\n' + 'x' * 20000
    store.atomic_json(workspace / 'investigation-result.json', {'stdout': output})
    config = {'_review_available_files': {}}
    entry = {'attempts': [{'workspace': str(workspace.relative_to(live))}]}
    relative = managed.expose_evidence(live, snapshot, 'q', entry, config)
    assert (snapshot / relative).is_file()
    manifest = store.read_json(snapshot / relative)
    copied = manifest['files'][0]['path']
    assert copied in config['_review_available_files']
    assert store.read_json(snapshot / copied)['stdout'] == output
    assert manifest['files'][0]['origin'].endswith('investigation-result.json')


def test_managed_wire_schema_is_flat_with_no_union_and_keeps_summary_budget(tmp_path, monkeypatch):
    seen = []
    def command(argv, cwd, timeout, prompt):
        schema = json.loads(argv[argv.index('--json-schema') + 1])
        seen.append(schema)
        return host(verdict([]))
    monkeypatch.setattr(review, 'run_command', command)
    result = review._claude_session(tmp_path, 'Inspect', {'_managed_project_root': str(tmp_path)})
    assert result['review']['findings'] == []
    [schema] = seen
    # The host reports every failing union branch together, which the model never
    # recovered from after one over-long summary. Only the top level may skip unions;
    # the investigation request keeps its nested mode union.
    assert 'response' not in schema['properties']
    assert not any(key in schema for key in ('anyOf', 'oneOf', 'allOf'))
    assert schema['type'] == 'object'
    assert schema['additionalProperties'] is False
    assert schema['required'] == []
    assert set(schema['properties']) == {'summary', 'findings', 'context', 'investigation'}
    assert schema['properties']['summary']['maxLength'] == review.SCHEMA['properties']['summary']['maxLength'] == 1500
    assert schema['properties']['investigation']['required'] == ['id', 'question', 'requirements', 'mode']


def test_managed_response_must_be_investigation_alone_or_complete_review(tmp_path, monkeypatch):
    config = {'_managed_project_root': str(tmp_path)}
    request = {'id': 'check', 'question': 'What is observed?', 'requirements': ['spec.md'], 'mode': 'direct', 'argv': ['python3', '--version']}
    monkeypatch.setattr(review, 'run_command', lambda *a: host({'investigation': request}))
    result = review._claude_session(tmp_path, 'Inspect', config)
    assert result['investigation'] == request
    assert 'review' not in result
    monkeypatch.setattr(review, 'run_command', lambda *a: host(verdict(['spec.md'])))
    result = review._claude_session(tmp_path, 'Inspect', config)
    assert result['review'] == {'summary': 'Checked the actual environment.', 'findings': []}
    assert 'investigation' not in result
    # A validating review sent alongside a re-emitted request is the final review; the request is dropped.
    monkeypatch.setattr(review, 'run_command', lambda *a: host({'investigation': request, **verdict(['spec.md'])}))
    result = review._claude_session(tmp_path, 'Inspect', config)
    assert result['review'] == {'summary': 'Checked the actual environment.', 'findings': []}
    assert 'investigation' not in result
    assert result['ignored_investigation'] == {'id': 'check', 'reason': (
        'response combined a completed review with an investigation request; '
        'the review was accepted and the request was not run')}
    # Mixing only fails the response when the review fields do not validate on their own.
    partial = {'findings': [], 'context': verdict(['spec.md'])['context']}
    monkeypatch.setattr(review, 'run_command', lambda *a: host({'investigation': request, **partial}))
    with pytest.raises(store.WorkflowError, match='invalid review.*mixed an investigation request.*findings'):
        review._claude_session(tmp_path, 'Inspect', config)
    monkeypatch.setattr(review, 'run_command', lambda *a: host({}))
    with pytest.raises(store.WorkflowError, match='invalid review.*empty object.*neither an investigation'):
        review._claude_session(tmp_path, 'Inspect', config)
    monkeypatch.setattr(review, 'run_command', lambda *a: host({'summary': 'Incomplete', 'context': verdict([])['context']}))
    with pytest.raises(store.WorkflowError, match='invalid review'):
        review._claude_session(tmp_path, 'Inspect', config)


def test_mixed_response_with_incomplete_inspection_still_fails_as_mixed(tmp_path, monkeypatch):
    # The review fields are present but the context misses a required path, so the review
    # branch does not validate and the mixing itself is the named failure.
    config = {'_managed_project_root': str(tmp_path), '_review_required_files': ['spec.md']}
    request = {'id': 'check', 'question': 'What is observed?', 'requirements': ['spec.md'], 'mode': 'direct', 'argv': ['python3', '--version']}
    monkeypatch.setattr(review, 'run_command', lambda *a: host({'investigation': request, **verdict([])}))
    with pytest.raises(store.WorkflowError, match='invalid review.*mixed an investigation request') as failure:
        review._claude_session(tmp_path, 'Inspect', config)
    # The missing paths ride on the mixed error so the reader loop re-prompts instead of failing.
    assert failure.value.inspection_missing_paths == ['spec.md']
    assert failure.value.diagnostics['missing_inspection_paths'] == ['spec.md']
    assert 'missing required paths: spec.md' in str(failure.value.__cause__.__cause__)


def test_reader_reprompts_once_for_mixed_response_with_incomplete_inspection(project, monkeypatch):
    at_spec(project)
    choose(project, 'single')
    prompts = []
    request = {'id': 'already-satisfied', 'question': 'Does the executable run?',
               'requirements': ['.fbk/feature/spec.md'], 'mode': 'direct', 'argv': [sys.executable, '--version']}
    def reviewer(argv, cwd, timeout, prompt):
        prompts.append(prompt)
        required = sorted(p.relative_to(cwd).as_posix() for p in cwd.rglob('*') if p.is_file())
        if len(prompts) == 1:
            return host({'investigation': request, **verdict([])})
        assert 'mixed an investigation request' in prompt
        assert '.fbk/feature/spec.md' in prompt
        return host(verdict(required))
    monkeypatch.setattr(review, 'run_command', reviewer)
    monkeypatch.setattr(investigations, 'run_command',
                        lambda *a, **k: pytest.fail('ignored investigation request must not run'))
    result = call(project, 'phase-close', 'spec', 'feature')
    assert result['accepted_phase'] == 'spec'
    assert len(prompts) == 2
    reader = store.load(project, 'feature')['phases']['spec']['rounds'][-1]['result']['readers'][0]
    assert 'ignored_investigation' not in reader
    assert reader['investigations'] == []


def test_reader_accepts_mixed_valid_review_without_running_the_ignored_request(project, monkeypatch):
    at_spec(project)
    choose(project, 'single')
    prompts = []
    def reviewer(argv, cwd, timeout, prompt):
        prompts.append(prompt)
        required = sorted(p.relative_to(cwd).as_posix() for p in cwd.rglob('*') if p.is_file())
        return host({'investigation': {'id': 'already-satisfied', 'question': 'Does the executable run?',
            'requirements': ['.fbk/feature/spec.md'], 'mode': 'direct', 'argv': [sys.executable, '--version']},
            **verdict(required)})
    monkeypatch.setattr(review, 'run_command', reviewer)
    monkeypatch.setattr(investigations, 'run_command',
                        lambda *a, **k: pytest.fail('ignored investigation request must not run'))
    result = call(project, 'phase-close', 'spec', 'feature')
    assert result['accepted_phase'] == 'spec'
    assert len(prompts) == 1
    assert not list((project / '.fbk/runtime/investigations').rglob('investigation-result.json'))
    reader = store.load(project, 'feature')['phases']['spec']['rounds'][-1]['result']['readers'][0]
    assert reader['ignored_investigation']['id'] == 'already-satisfied'
    assert 'the request was not run' in reader['ignored_investigation']['reason']
    assert reader['investigations'] == []


def _rules(config, schema=review.SCHEMA, kind='review'):
    """The sentences the constraint registry renders for a session; the real assemblers
    place this block in the prompt (tests/test_workflow_constraints.py covers that)."""
    from fbk.workflow import constraints
    block = constraints.render(kind, config, schema)
    return {item['id']: item['rule'] for item in constraints.rules(block)}


def test_every_native_session_prompt_states_the_schema_length_budgets(tmp_path):
    summary_limit = review.SCHEMA['properties']['summary']['maxLength']
    item_limits = review.SCHEMA['properties']['findings']['items']['properties']
    for config in ({'_managed_project_root': str(tmp_path)},
                   {'_review_available_files': {}, '_review_required_files': []}):
        budgets = _rules(config)['length-budgets']
        assert f'summary at most {summary_limit} characters' in budgets
        assert f"findings at most {review.SCHEMA['properties']['findings']['maxItems']} items" in budgets
        for field in ('title', 'location', 'evidence', 'remedy'):
            assert f"findings[].{field} at most {item_limits[field]['maxLength']} characters" in budgets
    assert '1500' in review.length_budgets(review.SCHEMA)
    assert review.length_budgets({'type': 'object', 'properties': {'result': {'type': 'object'}}}) == ''


def test_managed_prompt_names_the_properties_a_complete_review_must_carry(tmp_path):
    # The managed wire schema requires nothing at the top level, so the prompt is the
    # only place the reviewer learns which properties make a review complete.
    rules = _rules({'_managed_project_root': str(tmp_path)})
    names = ', '.join([*review.SCHEMA['required'], 'context'])
    assert f'exactly these top-level properties: {names}.' in rules['response-properties']
    assert names == 'summary, findings, context'
    # The sentence tracks the schema in use: a contributor session names its own key.
    contributor = {'type': 'object', 'additionalProperties': False,
                   'properties': {'result': {'type': 'object'}}, 'required': ['result']}
    rules = _rules({'_managed_project_root': str(tmp_path)}, contributor, kind='contributor')
    assert 'exactly these top-level properties: result, context.' in rules['response-properties']


def test_managed_prompt_states_the_authorization_rules_and_refusal(tmp_path):
    rules = _rules({'_managed_project_root': str(tmp_path)})
    assert ('authorization.source.quote is copied verbatim from the file at authorization.source.path'
            in rules['authorization-grant-quote'])
    assert 'authorization.target equals external.target exactly' in rules['authorization-grant-covers']
    assert 'every entry of external.effects appears in authorization.effects' in rules['authorization-grant-covers']
    assert ('A request declaring external with no valid grant is refused and recorded, no command runs, '
            "and the refusal spends one of the investigation's attempts" in rules['authorization-refusal'])


def test_managed_prompt_states_the_mode_argv_coupling(tmp_path):
    rules = _rules({'_managed_project_root': str(tmp_path)})
    assert 'mode=direct requires a nonempty argv and exploratory and modifies_code false' in rules['investigation-mode-direct']
    assert ('mode=delegated requires a nonempty prompt string and must not carry argv (omit it or set it to null)'
            in rules['investigation-mode-delegated'])
    # The stated coupling is the one the request schema enforces.
    from fbk.workflow.managed_investigations import REQUEST_SCHEMA
    direct, delegated = REQUEST_SCHEMA['anyOf']
    assert direct['required'] == ['argv'] and direct['properties']['argv'] == {'type': 'array'}
    assert direct['properties']['exploratory'] == direct['properties']['modifies_code'] == {'enum': [False]}
    assert delegated['required'] == ['prompt'] and delegated['properties']['argv'] == {'type': 'null'}


@pytest.mark.parametrize('config, attempts, seconds', [
    ({}, 3, 600),
    ({'investigation_max_attempts': 5, 'investigation_timeout': 90}, 5, 90),
])
def test_managed_prompt_states_the_configured_investigation_budgets(tmp_path, config, attempts, seconds):
    rules = _rules({'_managed_project_root': str(tmp_path), **config})
    assert (f'each investigation allows at most {attempts} attempts and {seconds} seconds; when either is exhausted '
            'the question is returned as unresolved evidence and you finish the review without it.'
            ) in rules['investigation-budgets']
    # The numbers come from the same reading the investigation record uses.
    assert investigations._positive(config, 'investigation_max_attempts', 3) == attempts
    assert investigations._positive(config, 'investigation_timeout', 600) == seconds


def test_standalone_prompt_carries_no_investigation_protocol(tmp_path, monkeypatch):
    prompts = []
    def command(argv, cwd, timeout, prompt):
        prompts.append(prompt)
        return host(verdict([]))
    monkeypatch.setattr(review, 'run_command', command)
    config = {'_review_available_files': {}, '_review_required_files': []}
    review._claude_session(tmp_path, 'Inspect', config)
    [prompt] = prompts
    assert 'investigation' not in prompt
    assert 'investigation' not in json.dumps(_rules(config))


def test_every_native_session_prompt_states_the_context_list_caps(tmp_path):
    from fbk.workflow.review_context import CONTEXT_SCHEMA
    for config in ({'_managed_project_root': str(tmp_path)},
                   {'_review_available_files': {}, '_review_required_files': []}):
        budgets = _rules(config)['length-budgets']
        for name in ('inspected_files', 'supporting_files', 'missing_context'):
            node = CONTEXT_SCHEMA['properties'][name]
            assert f"context.{name} at most {node['maxItems']} items" in budgets
            assert f"context.{name}[] at most {node['items']['maxLength']} characters" in budgets
        assert 'context.missing_context at most 20 items' in budgets
        # The investigation request carries no size limits, so it adds nothing to the sentence.
        assert 'investigation.' not in review.length_budgets(review.wire_contract(review.SCHEMA, managed=True))


def test_interrupted_continuation_restores_evidence_before_retry_verdict(project, monkeypatch):
    at_spec(project)
    choose(project, 'single')
    prompts = []
    roots = []
    def reviewer(argv, cwd, timeout, prompt):
        prompts.append(prompt)
        roots.append(cwd)
        if len(prompts) == 1:
            return host({'investigation': {'id': 'needed', 'question': 'What does the executable actually report?',
                'requirements': ['.fbk/feature/spec.md'], 'mode': 'direct',
                'argv': [sys.executable, '-c', "print('DURABLE_OBSERVATION=73')"]}})
        if len(prompts) == 2:
            raise store.WorkflowError('Interrupted continuation transport')
        assert 'DURABLE_OBSERVATION=73' in prompt
        manifests = list(cwd.glob('.review-investigations/*/manifest.json'))
        assert manifests
        assert any('DURABLE_OBSERVATION=73' in (cwd / item['path']).read_text()
                   for manifest in manifests for item in store.read_json(manifest)['files'])
        return host(verdict(sorted(p.relative_to(cwd).as_posix() for p in cwd.rglob('*') if p.is_file())))
    monkeypatch.setattr(review, 'run_command', reviewer)
    with pytest.raises(store.WorkflowError, match='Interrupted continuation transport'):
        call(project, 'phase-close', 'spec', 'feature')
    records = [store.read_json(p) for p in (project / '.fbk/runtime/review-rounds').glob('*/round.json')]
    retained = next(r for r in records if r.get('investigations'))
    question = next(iter(retained['investigations'].values()))
    assert not question.get('resolution')
    assert len(question['attempts']) == 1
    result = call(project, 'phase-close', 'spec', 'feature')
    assert result['accepted_phase'] == 'spec'
    current = investigations._load(project, retained['id'])
    question = next(iter(current['investigations'].values()))
    assert question['resolution']['attempts'] == [1]
    assert len(question['attempts']) == 1
    assert current['budget']['spent_seconds'] >= retained['budget']['spent_seconds']
    assert roots[0] != roots[-1]
    assert len(prompts) == 3


def test_clean_managed_verdict_cannot_bypass_an_unanswered_round_question(project, monkeypatch):
    at_spec(project)
    choose(project, 'single')
    def reader(cwd, prompt, config, **kwargs):
        execution = config['_managed_execution']
        investigations.start(project, execution.round_id, {'id': 'unanswered', 'question': 'Is the required external behavior supported?', 'requirements': ['.fbk/feature/spec.md']})
        return {'review': {'summary': 'Looks fine', 'findings': []}, 'seconds': 0}
    monkeypatch.setattr(review, '_claude_session', reader)
    with pytest.raises(store.WorkflowError, match='[Uu]nresolved|[Uu]nanswered'):
        call(project, 'phase-close', 'spec', 'feature')
    assert store.load(project, 'feature')['phases']['spec']['evidence'] is None


def test_retry_preserves_explicit_human_disposition_of_unanswered_question(project, monkeypatch):
    at_spec(project)
    choose(project, 'single')
    calls = []
    def reviewer(argv, cwd, timeout, prompt):
        calls.append(prompt)
        if len(calls) == 1:
            return host({'investigation': {'id': 'external', 'question': 'Can staging answer this question?',
                'requirements': ['.fbk/feature/spec.md'], 'mode': 'direct', 'argv': ['probe'],
                'external': {'target': 'staging', 'effects': ['read']}}})
        if len(calls) == 2:
            assert 'existing explicit authorization' in prompt
            raise store.WorkflowError('Interrupted continuation transport')
        assert 'Human explicitly accepts this unresolved staging uncertainty.' in prompt
        return host(verdict(sorted(p.relative_to(cwd).as_posix() for p in cwd.rglob('*') if p.is_file())))
    monkeypatch.setattr(review, 'run_command', reviewer)
    with pytest.raises(store.WorkflowError, match='Interrupted continuation transport'):
        call(project, 'phase-close', 'spec', 'feature')
    retained = next(store.read_json(p) for p in (project / '.fbk/runtime/review-rounds').glob('*/round.json') if store.read_json(p).get('investigations'))
    identifier = next(iter(retained['investigations']))
    quote = 'Human explicitly accepts this unresolved staging uncertainty.'
    decision = project / '.fbk/runtime/decision.md'
    decision.write_text(quote)
    investigations.resolve(project, retained['id'], identifier, {'disposition': 'stop', 'reason': quote,
        'source': {'path': '.fbk/runtime/decision.md', 'quote': quote}})
    result = call(project, 'phase-close', 'spec', 'feature')
    assert result['accepted_phase'] == 'spec'
    entry = investigations._load(project, retained['id'])['investigations'][identifier]
    assert entry['disposition']['disposition'] == 'stop'
    assert not entry.get('resolution')
    assert [a['status'] for a in entry['attempts']] == ['refused']
    assert len(calls) == 3
