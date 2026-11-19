"""Request contract checked by a real, optional development JSON Schema validator.

Run with: uv run --no-project --with pytest --with pyyaml --with jsonschema \
    python -m pytest tests/test_workflow_investigation_schema.py
(from assets/fbk-scripts). The normal suite reports a skip without jsonschema.
"""

from copy import deepcopy

import pytest

from fbk.workflow import investigations, managed_investigations, store

jsonschema = pytest.importorskip("jsonschema", reason="schema agreement needs jsonschema; see module invocation")

DIRECT = {"id": "check", "question": "Which version runs?", "requirements": ["spec.md"],
          "mode": "direct", "argv": ["python3", "--version"]}
DELEGATED = {"id": "experiment", "question": "Can the behavior be reproduced?",
             "requirements": ["spec.md"], "mode": "delegated", "prompt": "Reproduce the behavior."}
EXTERNAL = {"target": "test-service", "effects": ["read"]}
GRANT = {**EXTERNAL, "source": {"path": "permission.md", "quote": "Read test-service."}}


def changed(base=DIRECT, **updates):
    return {**deepcopy(base), **updates}


def omitted(base, field):
    result = deepcopy(base)
    del result[field]
    return result


@pytest.fixture(scope="module")
def validator():
    jsonschema.Draft202012Validator.check_schema(managed_investigations.REQUEST_SCHEMA)
    return jsonschema.Draft202012Validator(managed_investigations.REQUEST_SCHEMA)


@pytest.mark.parametrize("declaration", [
    DIRECT, DELEGATED,
    changed(argv=["printf", " "]),
    changed(prompt="", exploratory=False, modifies_code=False),
    changed(DELEGATED, exploratory=True, modifies_code=True),
    changed(DELEGATED, argv=None),
    changed(external=None, authorization=None),
    changed(external=EXTERNAL),  # A prior durable grant can authorize a later attempt.
    changed(external=EXTERNAL, authorization=GRANT),
    changed(authorization=GRANT),
    changed(id="x" * 67),
])
def test_valid_requests_agree(validator, declaration):
    validator.validate(declaration)
    investigations.validate_request(declaration, managed=True)


@pytest.mark.parametrize("declaration", [
    None, [],
    omitted(DIRECT, "id"), changed(id=""), changed(id="x" * 68), changed(id="a/b"),
    omitted(DIRECT, "question"), changed(question=""), changed(question=" \n\t"),
    changed(requirements=[]), changed(requirements=[""]), changed(requirements=[" \t"]),
    changed(requirements="spec.md"), changed(requirements=[1]),
    omitted(DIRECT, "mode"), changed(mode="unknown"),
    omitted(DIRECT, "argv"), changed(argv=None), changed(argv=[]), changed(argv=[""]),
    changed(argv=[1]), changed(argv="python3"),
    omitted(DELEGATED, "prompt"), changed(DELEGATED, prompt=" \t"),
    changed(DELEGATED, argv=["python3"]),
    changed(prompt=7), changed(prompt=None),
    changed(exploratory=True), changed(modifies_code=True),
    changed(exploratory=1), changed(DELEGATED, modifies_code="true"),
    changed(unexpected=True),
    changed(external={}), changed(external="test-service"),
    changed(external={**EXTERNAL, "target": " \t"}),
    changed(external={**EXTERNAL, "effects": []}),
    changed(external={**EXTERNAL, "effects": [" "]}),
    changed(external={**EXTERNAL, "unexpected": True}),
    changed(authorization={}), changed(authorization=EXTERNAL),
    changed(authorization={**GRANT, "effects": []}),
    changed(authorization={**GRANT, "target": " "}),
    changed(authorization={**GRANT, "unexpected": True}),
    changed(authorization={**GRANT, "source": {}}),
    changed(authorization={**GRANT, "source": {"path": "permission.md", "quote": " "}}),
    changed(authorization={**GRANT, "source": {"path": "", "quote": "Read test-service."}}),
    changed(authorization={**GRANT, "source": {**GRANT["source"], "unexpected": True}}),
])
def test_invalid_requests_agree(validator, declaration):
    assert not validator.is_valid(declaration)
    with pytest.raises(investigations.InvestigationRequestError):
        investigations.validate_request(declaration, managed=True)


def test_structural_validity_does_not_authorize_external_effects(validator, tmp_path):
    request = changed(external=EXTERNAL, authorization=GRANT)
    validator.validate(request)
    investigations.validate_request(request, managed=True)
    with pytest.raises(store.WorkflowError, match="verifiable source quotation"):
        investigations._authorization(tmp_path, {"authorizations": []}, request)

    (tmp_path / "permission.md").write_text(GRANT["source"]["quote"])
    request["external"] = {**EXTERNAL, "effects": ["write"]}
    validator.validate(request)
    investigations.validate_request(request, managed=True)
    with pytest.raises(store.WorkflowError, match="does not cover target and effects"):
        investigations._authorization(tmp_path, {"authorizations": []}, request)
