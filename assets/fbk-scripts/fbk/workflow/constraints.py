"""One registry of every rule the runtime enforces on a reviewer session's response.

A rule the reviewer is held to is a rule the reviewer is told, and the telling is
generated from this list rather than hand-maintained in prompt prose. Each entry
names the rule once, says which session kinds it applies to, which validator
rejects a response that breaks it, and how to render its sentence. Sentences whose
numbers come from configuration or a schema are callables that read the same source
the validator reads, so the prompt cannot drift from the check.

Two tests hold the registry to the code: ``tests/test_workflow_constraints.py``
asserts that every applicable entry appears in the prompt each real assembler
builds, and that every rejection site inside a validator names an entry here.

Session kinds are the response contracts the code actually launches:

- ``review``: a single phase reader (``review._review_sources`` with the review schema).
- ``council-member``: an independent council reader (the candidate schema).
- ``adjudication``: the assessor that settles the optional external second reader (assessment schema).
- ``council-turn``: a council member's discussion turn (``council.turn_contract``).
- ``council-stance``: a council member's closing stances, and the second round (``council.stance_contract``).
- ``council-final``: the council's final session (``council.final_contract``).
- ``contributor``: a standalone review-round contributor (the ``result`` schema).
- ``repair-verifier``: the contradiction-repair verifier (the verdict schema).
- ``remediation-verifier``: the delegated fix verifier that writes ``verification.json``.
- ``spec-trim``: the session that trims the spec before its review (``spec_trim.SCHEMA``).

An investigation request is a response of a managed session, not a session of its
own, so its rules carry ``managed=True`` and render in every managed kind.
"""

from dataclasses import dataclass
from typing import Callable, Optional, Union

PREAMBLE = (
    "The runtime enforces every rule below; a response that breaks one is rejected "
    "or recorded as stated."
)
STAGE_PREAMBLE = (
    "This pass returns an assessment object. The runtime enforces every rule below on "
    "this pass, in place of the packet's rules block written for the independent "
    "readers; a response that breaks one is rejected or recorded as stated."
)

KINDS = (
    "review",
    "council-member",
    "adjudication",
    "council-turn",
    "council-stance",
    "council-final",
    "contributor",
    "repair-verifier",
    "remediation-verifier",
    "spec-trim",
)
READERS = frozenset({"review", "council-member", "adjudication",
                     "council-turn", "council-stance", "council-final"})
MANAGED = READERS | {"contributor"}
NATIVE = MANAGED | {"repair-verifier"}


@dataclass(frozen=True)
class Constraint:
    id: str
    applies_to: frozenset
    group: str
    enforced_by: Optional[tuple]
    render: Union[str, Callable]
    managed: bool = False
    note: Optional[str] = None

    def sentence(self, config, schema):
        if isinstance(self.render, str):
            return self.render
        return self.render(config, schema)


def _managed(config):
    return bool(config.get("_managed_project_root"))


def _properties(config, schema):
    names = ", ".join([*schema["required"], "context"])
    return f"The response is one object carrying exactly these top-level properties: {names}."


def _length_budgets(config, schema):
    from .review import length_budgets, wire_contract

    return length_budgets(wire_contract(schema, managed=_managed(config)))


def _investigation_budgets(config, schema):
    from .investigations import _positive

    attempts = _positive(config, "investigation_max_attempts", 3)
    seconds = _positive(config, "investigation_timeout", 600)
    return (
        f"Budgets do not renew: each investigation allows at most {attempts} attempts and "
        f"{seconds} seconds; when either is exhausted the question is returned as unresolved "
        "evidence and you finish the review without it."
    )


def _session_time_limit(config, schema):
    from .review import bounded_number

    timeout = bounded_number(config, "review_timeout", 1200, 86400)
    return (
        f"This session is stopped after {timeout} seconds (the configured review_timeout) and "
        "the attempt is then recorded as failed, so return the complete review within that time; "
        "when the whole round's clock has less time left, this session is stopped at that shorter limit instead."
    )


def _turn_ceiling(config, schema):
    from .investigations import _positive

    turns = _positive(config, "reviewer_max_turns", 100)
    return (
        f"This session has at most {turns} turns (the configured reviewer_max_turns); reaching "
        "the ceiling is recorded as a failed attempt without a verdict."
    )


def _worker_limits(config, schema):
    from .investigations import _positive

    seconds = _positive(config, "investigation_timeout", 600)
    turns = _positive(config, "reviewer_max_turns", 100)
    return (
        f"This verifier session is stopped after at most {seconds} seconds (the configured "
        f"investigation_timeout) or {turns} turns (the configured reviewer_max_turns); an "
        "attempt that reaches either is recorded as failed."
    )


def _trim_limits(config, schema):
    from .investigations import _positive
    from .review import bounded_number

    seconds = bounded_number(config, "review_timeout", 1200, 86400)
    turns = _positive(config, "reviewer_max_turns", 100)
    return (
        f"This session is stopped after {seconds} seconds (the configured review_timeout) or "
        f"{turns} turns (the configured reviewer_max_turns); either ends it without a result. "
        "A session without a result is run once more, and if that fails too the spec goes to "
        "review untrimmed."
    )


def _trim_list(config, schema):
    from .review import length_budgets

    return (
        "removed is a list with one object per item you merged or removed, each with exactly "
        "item and reason as nonempty strings; an empty list means nothing was cut. "
        + length_budgets(schema)
    ).strip()


def _assessment_items(config, schema):
    items = schema["properties"]["assessments"]["items"]["properties"]
    canonical = "finding" in items
    keys = (
        "finding_id, disposition, evidence, and finding, plus an optional duplicate_of"
        if canonical
        else "finding_id, disposition, and evidence"
    )
    return (
        f"Each assessment is an object with exactly {keys}; finding_id names a supplied "
        "candidate id; disposition is supported, refuted, or unresolved; evidence is a "
        "nonempty string."
    )


def _assessing(sentence):
    """A sentence stated only when the schema asks for requirement_assessments: the
    implementation review, and its adjudication, of a unit with review-only requirements."""

    def render(config, schema):
        return sentence if "requirement_assessments" in (schema or {}).get("properties", {}) else ""

    return render


def _entry(id, kinds, group, enforced_by, render, *, managed=False, note=None):
    if isinstance(enforced_by, str):
        enforced_by = (enforced_by,)
    return Constraint(
        id=id,
        applies_to=frozenset(kinds),
        group=group,
        enforced_by=tuple(enforced_by) if enforced_by else None,
        render=render,
        managed=managed,
        note=note,
    )


REGISTRY = (
    # response-shape: what the host schema and the Python validators accept.
    _entry(
        "response-properties",
        NATIVE,
        "response-shape",
        (
            "review.validate_review",
            "council.assessment_contract",
            "council.turn_contract",
            "council.stance_contract",
            "council.final_contract",
            "repair._verify",
            "review_contributors._validate",
        ),
        _properties,
    ),
    _entry(
        "summary-nonempty",
        READERS - {"council-turn", "council-stance"},
        "response-shape",
        ("review.validate_review", "council.assessment_contract", "council.final_contract"),
        "summary is a nonempty string.",
    ),
    _entry(
        "finding-fields",
        {"review", "council-member", "adjudication", "council-turn", "council-final"},
        "response-shape",
        "review.validate_review",
        "Each finding is an object with title, location, evidence, remedy, and severity, "
        "each a nonempty string, and no other property except an optional remedy_kind; "
        "severity is blocker or suggestion.",
    ),
    _entry(
        "remedy-kind",
        {"review", "council-member", "adjudication", "council-turn", "council-final", "contributor"},
        "response-shape",
        "review.validate_review",
        "Each finding may carry remedy_kind, one of artifact, test, code, or documentation; "
        "absent means artifact. Tag a suggestion whose remedy is a new or changed test as "
        "test, because a test remedy must be dispositioned before breakdown accepts the plan "
        "or the test checkpoint locks the suite, and nothing after the lock can add one.",
    ),
    _entry(
        "length-budgets",
        NATIVE,
        "response-shape",
        (
            "review.validate_review",
            "review.validate_single",
            "council.validate_candidates",
            "council.assessment_contract",
            "council.turn_contract",
            "council.final_contract",
            "review_context.validate_context",
        ),
        _length_budgets,
    ),
    _entry(
        "contributor-result",
        {"contributor"},
        "response-shape",
        "review_contributors._validate",
        "result is a JSON object or array holding the complete contribution.",
    ),
    _entry(
        "managed-response-shape",
        MANAGED,
        "response-shape",
        "review._claude_session",
        "Return either an investigation request as an object whose only property is "
        "investigation, or the complete response with no investigation property, never "
        "both; when both are present and the response validates on its own, the response "
        "is taken as final and the request is discarded without running; an empty object "
        "is rejected.",
        managed=True,
    ),
    # context-declaration: the inspection record every native session returns.
    _entry(
        "context-record",
        NATIVE,
        "context-declaration",
        "review_context.validate_context",
        "context is an object with exactly status, inspected_files, supporting_files, and "
        "missing_context; status is complete or incomplete.",
    ),
    _entry(
        "context-status-shape",
        NATIVE,
        "context-declaration",
        "review_context.validate_context",
        "Status complete requires an empty missing_context; status incomplete requires "
        "missing_context to name each missing item; any other combination is rejected as "
        "malformed.",
    ),
    _entry(
        "required-files-declared",
        NATIVE,
        "context-declaration",
        "review_context.validate_context",
        "Every path in required_files, in both its phase_targets and authoritative_context "
        "lists, must appear in the declaration, in inspected_files or in supporting_files; "
        "supporting_files is the subset relied on as governing authority.",
    ),
    _entry(
        "declared-paths-in-snapshot",
        NATIVE,
        "context-declaration",
        "review_context.validate_context",
        "Each declared path is a file path spelled exactly as it appears in required_files "
        "or the snapshot listing: no directories, wildcards, ./ prefixes, or absolute paths.",
    ),
    _entry(
        "incomplete-context-is-a-verdict",
        READERS - {"council-stance"},
        "context-declaration",
        "review_context.incomplete_context",
        "An incomplete declaration is accepted as your verdict: the round then fails on that "
        "missing context with your findings retained for the author, and it is never treated "
        "as a protocol error.",
    ),
    _entry(
        "stance-incomplete-context",
        {"council-stance"},
        "context-declaration",
        "review_context.incomplete_context",
        "An incomplete declaration is accepted as your verdict: the round then fails on that "
        "missing context, and it is never treated as a protocol error.",
    ),
    _entry(
        "contributor-incomplete-context",
        {"contributor"},
        "context-declaration",
        "review_contributors._worker",
        "An incomplete declaration is accepted as your verdict: the contribution is recorded "
        "as failed with the missing items named, never as a protocol error.",
    ),
    _entry(
        "repair-incomplete-context",
        {"repair-verifier"},
        "context-declaration",
        "repair._verify",
        "An incomplete declaration is accepted as your verdict: it becomes an "
        "insufficient_context verdict naming the missing items, and the repair is not applied.",
    ),
    # investigation-request: the shape of a managed session's investigation request.
    _entry(
        "investigation-fields",
        MANAGED,
        "investigation-request",
        "investigations.validate_request",
        "An investigation request is an object carrying only id, question, requirements, "
        "mode, argv, prompt, exploratory, modifies_code, external, and authorization; "
        "unknown fields are rejected.",
        managed=True,
    ),
    _entry(
        "investigation-id",
        MANAGED,
        "investigation-request",
        "investigations.validate_request",
        "id is 1 to 67 letters, digits, underscores, or hyphens (the runtime adds a reader "
        "prefix).",
        managed=True,
    ),
    _entry(
        "investigation-question",
        MANAGED,
        "investigation-request",
        "investigations.validate_request",
        "question is a nonempty string and requirements is a nonempty list of reference "
        "strings.",
        managed=True,
    ),
    _entry(
        "investigation-mode",
        MANAGED,
        "investigation-request",
        "investigations.validate_request",
        "mode is direct or delegated.",
        managed=True,
    ),
    _entry(
        "investigation-mode-direct",
        MANAGED,
        "investigation-request",
        "investigations.validate_request",
        "mode=direct requires a nonempty argv and exploratory and modifies_code false.",
        managed=True,
    ),
    _entry(
        "investigation-mode-delegated",
        MANAGED,
        "investigation-request",
        "investigations.validate_request",
        "mode=delegated requires a nonempty prompt string and must not carry argv (omit it "
        "or set it to null).",
        managed=True,
    ),
    _entry(
        "investigation-flags",
        MANAGED,
        "investigation-request",
        "investigations.validate_request",
        "exploratory and modifies_code, when present, are JSON booleans; an exploratory or "
        "code-changing experiment must be delegated.",
        managed=True,
    ),
    _entry(
        "external-shape",
        MANAGED,
        "investigation-request",
        "investigations.validate_request",
        "external and authorization, when present, are objects with a nonempty target "
        "string and effects as a nonempty list of strings, and authorization also carries "
        "source with nonempty path and quote strings; keep the intended target and effects "
        "rather than removing effects to bypass authorization.",
        managed=True,
    ),
    _entry(
        "investigation-id-reuse",
        MANAGED,
        "investigation-request",
        None,
        "Reuse the same investigation id when retrying a question; a retry under a new id "
        "is not rejected but opens a separate investigation with its own attempt and time "
        "budget, and every investigation shares the round clock.",
        managed=True,
        note="Not enforced: the runtime cannot tell a retry from a new question, so a new "
        "id starts a new entry; the sentence states that consequence instead of a rejection.",
    ),
    # authorization: what makes an external check runnable.
    _entry(
        "authorization-grant-quote",
        MANAGED,
        "authorization",
        "investigations._authorization",
        "An authorization grant is valid only when authorization.source.quote is copied "
        "verbatim from the file at authorization.source.path.",
        managed=True,
    ),
    _entry(
        "authorization-grant-covers",
        MANAGED,
        "authorization",
        "investigations._authorization",
        "A grant covers a request only when authorization.target equals external.target "
        "exactly and every entry of external.effects appears in authorization.effects.",
        managed=True,
    ),
    _entry(
        "authorization-refusal",
        MANAGED,
        "authorization",
        ("investigations._authorization", "investigations._refuse"),
        "A request declaring external with no valid grant is refused and recorded, no "
        "command runs, and the refusal spends one of the investigation's attempts.",
        managed=True,
    ),
    # budgets: per-question limits inside a managed round.
    _entry(
        "investigation-budgets",
        MANAGED,
        "budgets",
        "investigations.run",
        _investigation_budgets,
        managed=True,
    ),
    _entry(
        "exhausted-question-repeat",
        MANAGED,
        "budgets",
        "managed_investigations.run_reader",
        "Requesting an exhausted question again returns the same unresolved evidence once "
        "more; a further request for it stops the session.",
        managed=True,
    ),
    _entry(
        "protocol-correction",
        MANAGED,
        "budgets",
        "managed_investigations._correction",
        "A malformed investigation request or inspection declaration gets one protocol "
        "correction per reader per round; a second such failure stops the session.",
        managed=True,
    ),
    # assessment: the external second reader's assessor.
    _entry(
        "assessment-items",
        {"adjudication"},
        "assessment",
        "council.assessment_contract",
        _assessment_items,
    ),
    _entry(
        "assess-every-candidate-once",
        {"adjudication"},
        "assessment",
        "council.assessment_contract",
        "assessments name every supplied candidate id exactly once; minority findings "
        "cannot disappear.",
    ),
    _entry(
        "refuted-finding-null",
        {"adjudication"},
        "assessment",
        "council.assessment_contract",
        "A refuted candidate carries finding null.",
    ),
    _entry(
        "supported-finding-complete",
        {"adjudication"},
        "assessment",
        "council.assessment_contract",
        "A supported or unresolved candidate that is not a duplicate carries a complete "
        "operative finding obeying the finding rules.",
    ),
    _entry(
        "unresolved-blocker-stays-blocker",
        {"adjudication"},
        "assessment",
        "council.adjudicate",
        "An unresolved candidate reported as a blocker keeps blocker severity in its "
        "operative finding; it cannot be downgraded.",
    ),
    _entry(
        "duplicate-reference",
        {"adjudication"},
        "assessment",
        "council.assessment_contract",
        "duplicate_of names a retained representative candidate directly: never the "
        "assessment's own id, never another duplicate (no chains), with the same disposition "
        "as the representative, and the duplicate's finding is null.",
    ),
    _entry(
        "refuted-duplicate-ignored",
        {"adjudication"},
        "assessment",
        "council.assessment_contract",
        "A refuted assessment's duplicate_of is ignored: a refuted claim has no operative "
        "finding to group, so it needs finding null and its own refuting evidence.",
    ),
    # council: what the mediated council's turns, stances and final session may return.
    _entry(
        "turn-responses",
        {"council-turn"},
        "council",
        "council.turn_contract",
        "Each entry of responses names a listed proposal id, an action of contest, concede, or "
        "withdraw, and a nonempty reason; withdraw applies only to your own proposals and takes "
        "that proposal off the list.",
    ),
    _entry(
        "turn-replacements",
        {"council-turn"},
        "council",
        "council.turn_contract",
        "Each new proposal is a finding plus replaces, the listed proposal ids it replaces; an "
        "id not on the list is rejected. A new proposal that replaces none is left off the list "
        "and recorded as dropped, and the rest of the turn still counts.",
    ),
    _entry(
        "stance-every-proposal",
        {"council-stance"},
        "council",
        "council.stance_contract",
        "stances holds exactly one stance for each listed proposal id, each support or contest "
        "with a reason; a contest's reason is nonempty.",
    ),
    _entry(
        "count-rule",
        {"council-stance"},
        "council",
        None,
        "The runtime counts the stances. A proposal a majority supports stands, with each contest "
        "reason attached as dissent; one a majority contests is dropped. A tied suggestion stands "
        "with both sides recorded. A tied blocker goes to a second round, and one still tied after "
        "it stands as a suggestion. A replacement that stands removes the proposals it replaces.",
        note="Not a rejection: council.count applies the rule to valid stances.",
    ),
    _entry(
        "final-findings-match",
        {"council-final"},
        "council",
        "council.final_contract",
        "findings holds exactly one entry for each listed standing proposal id, with its finding "
        "and its dissent; each finding obeys the finding rules and keeps the severity given for "
        "its proposal; no proposal may be added, revived, or left out.",
    ),
    _entry(
        "final-dropped-match",
        {"council-final"},
        "council",
        "council.final_contract",
        "dropped holds exactly one entry for each listed dropped proposal id, with a nonempty reason.",
    ),
    # requirement-assessment: the implementation review's verdict on each review-only requirement.
    _entry(
        "requirement-assessments-complete",
        {"review", "adjudication"},
        "requirement-assessment",
        ("review.validate_review", "council.assessment_contract"),
        _assessing(
            "requirement_assessments holds exactly one assessment for each requirement listed in "
            "review_only_requirements, naming it by its reference; a missing, repeated, or unlisted "
            "requirement is rejected."
        ),
    ),
    _entry(
        "requirement-assessment-fields",
        {"review", "adjudication"},
        "requirement-assessment",
        ("review.validate_review", "council.assessment_contract"),
        _assessing(
            "Each requirement assessment is an object with exactly requirement, verdict, and "
            "evidence, plus remedy, which a not met verdict requires; verdict is met or not met; "
            "evidence and remedy are nonempty strings."
        ),
    ),
    _entry(
        "requirement-not-met-blocker",
        {"review", "adjudication"},
        "requirement-assessment",
        None,
        _assessing(
            "Each operative not met verdict is recorded as one blocker finding located at the "
            "requirement's reference, carrying the assessment's evidence and remedy; these blockers "
            "are added by the runtime and do not count toward your findings limits. The operative "
            "verdicts are the single reader's; with a second reader, the readers' when they agree on "
            "every verdict and report no findings, and otherwise the adjudication's."
        ),
        note="Not a rejection: review.requirement_blockers records each operative not met verdict "
        "as a blocker finding, and the close then stops over it like any blocker.",
    ),
    # session-limits: the safety nets on one session.
    _entry(
        "session-time-limit",
        NATIVE,
        "session-limits",
        "review.run_command",
        _session_time_limit,
    ),
    _entry(
        "turn-ceiling",
        NATIVE,
        "session-limits",
        "review._claude_session",
        _turn_ceiling,
    ),
    _entry(
        "worker-limits",
        {"remediation-verifier"},
        "session-limits",
        "investigations.run",
        _worker_limits,
    ),
    # verdict: what a verifier's answer does.
    _entry(
        "repair-verdict",
        {"repair-verifier"},
        "verdict",
        "repair._verify",
        "status is equivalent, rejected, or insufficient_context, and evidence is a "
        "nonempty string.",
    ),
    _entry(
        "repair-not-applied",
        {"repair-verifier"},
        "verdict",
        "repair.apply",
        "A rejected or insufficient_context verdict means the repair is not applied and "
        "your evidence is reported to the operator as the reason.",
    ),
    _entry(
        "remediation-report-identity",
        {"remediation-verifier"},
        "verdict",
        "remediation_verification._validate",
        "verification.json is an object with schema remediation-verification-v1, the "
        "supplied contract_id and remediation_id, and status verified or rejected.",
    ),
    _entry(
        "remediation-report-fields",
        {"remediation-verifier"},
        "verdict",
        "remediation_verification._validate",
        "behavior.assessment, regression.rejected_behavior, and limitations are nonempty, "
        "and behavior.evidence names a path and quote.",
    ),
    _entry(
        "remediation-evidence-quote",
        {"remediation-verifier"},
        "verdict",
        "remediation_verification._evidence",
        "Every evidence quote is an exact plain-text excerpt of the named log file, which "
        "must exist inside your workspace.",
    ),
    _entry(
        "remediation-verified-proof",
        {"remediation-verifier"},
        "verdict",
        "remediation_verification._validate",
        "A verified report also needs regression.fixed with exit_code 0 and "
        "regression.defect with exit_code 1, each with a nonempty argv and attributed "
        "evidence; regression.defect_source naming the defective source kept in the "
        "workspace; siblings covering every declared sibling path, each with status fixed, "
        "already-safe, or outside-scope and a reason, with fixed only for paths inside the "
        "declared scope; and, when regression.exception is present, its reason and evidence.",
    ),
    _entry(
        "remediation-rejected-verdict",
        {"remediation-verifier"},
        "verdict",
        "remediation_verification.verify",
        "A rejected report is accepted as your verdict: the remediation is recorded as not "
        "accepted with your rejected_behavior text, and the remediator must fix and "
        "re-verify.",
    ),
    # spec-trim: the session that trims the spec before its review.
    _entry(
        "trim-edit-scope",
        {"spec-trim"},
        "scope",
        None,
        "Only the spec can be edited; the host denies an edit to any other file.",
        note="Enforced by the host's permission rule, which allows Edit only on the spec's path; "
        "no Python validator judges it.",
    ),
    _entry(
        "trim-removed-list",
        {"spec-trim"},
        "response-shape",
        "spec_trim._parse",
        _trim_list,
    ),
    _entry(
        "trim-limits",
        {"spec-trim"},
        "limits",
        "spec_trim._parse",
        _trim_limits,
    ),
    _entry(
        "trim-result-checks",
        {"spec-trim"},
        "checks",
        "spec_trim._check",
        "After this session the spec must still pass its structure and link checks and the "
        "invisible-character scan, so write each escape sequence as an escape. A spec that fails "
        "goes back to its author, and the trim does not run again for this draft.",
    ),
)

BY_ID = {entry.id: entry for entry in REGISTRY}
assert len(BY_ID) == len(REGISTRY), "constraint ids must be unique"


def applicable(kind, config):
    """The entries a session of this kind is held to under this configuration."""
    if kind not in KINDS:
        raise ValueError(f"Unknown session kind: {kind}")
    managed = _managed(config)
    return [
        entry
        for entry in REGISTRY
        if kind in entry.applies_to and (managed or not entry.managed)
    ]


def render(kind, config, schema=None, *, preamble=PREAMBLE):
    """The rules block for one session: a preamble, then groups of {id, rule}."""
    block = {"preamble": preamble}
    for entry in applicable(kind, config):
        sentence = entry.sentence(config, schema)
        if sentence:
            block.setdefault(entry.group, []).append({"id": entry.id, "rule": sentence})
    return block


def stage_block(kind, config, schema):
    """The assessor restates its own rules in place of the packet's."""
    return render(kind, config, schema, preamble=STAGE_PREAMBLE)


def block_text(block):
    """The rules block as the prompt carries it outside the review packet."""
    import json

    return "\nrules:\n" + json.dumps(block, ensure_ascii=False)


def rules(block):
    """Every rendered sentence in a block, for tests and callers that need them flat."""
    return [item for group, items in block.items() if group != "preamble" for item in items]
