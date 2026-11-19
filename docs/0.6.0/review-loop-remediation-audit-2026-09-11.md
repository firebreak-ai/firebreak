# Necessity and correctness audit, 2026-09-11

Verdict: the batch addresses several established defects, but does not merit a
blanket correctness or effectiveness claim. There is one reproduced regression,
one incomplete protocol repair, and several prompt interventions whose benefit
remains unmeasured. This audit includes the coordinator's runtime work as well as
the two agents' changes. Production code and trial artifacts were not edited.

## Evidence comparison

The integrated issue map and scoped evidence packets under
`test-results/live-install/analysis-2026-09-11/` distinguish original events from
reconstructed explanations. In particular, the retained breakdown inspection
failure was within its raised time/turn limits; the two stale-task close failures
followed successful test preparation. Treating either as insufficient budget or
omitted preparation would have produced the wrong fix.

| Observation | Intervention | Assessment |
| --- | --- | --- |
| No contemporaneous breakdown retrospective; user explicitly requires phase accounts | Mandatory acceptance-linked observations and pending-phase guidance | Necessary. The new gate detects all five missing acceptance-linked phase accounts in the retained final trial state. Existing reconstructed observations remain valuable but do not meet this new accounting contract. Boundary enforcement does not prove contemporaneous recording throughout a long phase. |
| Two implementation slash commands produced no conversation after expansion denial | Return recovery context while retaining actual phase-entry checks | Directly justified. State-preservation regressions support runtime behavior. The actual host's conversation behavior still needs a live smoke check. |
| `tests-prepared` followed by stale-assignment close rejection twice | Task-specific blockers in capture/progress/close | Directly justified and narrowly targeted. It corrects readiness advice without claiming that preparation refreshes old assignment provenance. It does not remove all legitimate handoff refresh work. |
| Investigation declarations failed target/effects validation | Tightened schema, prevalidation, one bounded correction | Necessary repair, incomplete implementation: schema and runtime still disagree on other request shapes. One correction is a conservative policy choice, not a measured optimum. |
| Required decision-source inspection declarations missing | Exact missing paths and one truthful correction | Justified. Missing declarations do not prove missing reading. Correction asks for actual reads; it does not fabricate the list. Fresh continuation can repeat costly review work, so usefulness under the remaining clock is unmeasured. |
| Author introduced strict normalization and promoted examples into exact obligations | Proportional authoring guidance | Evidence-linked hypothesis. Original instructions did not demonstrably force those choices; the new wording cannot yet be called a proven prevention. It appropriately preserves explicit accepted decisions. |
| Interior tilde fixture could not detect leading-tilde expansion; reviewer remedy could not reach cleanup | Distinguishing examples and reachable-remedy guidance | Strongly justified engineering correction. Unlike another instruction to name plausible bugs, it targets the actual fixture distinction. We have not measured whether agents follow it. |
| Prerequisite checked by plain Python while consumer used pytest | Check via actual consumer runner/configuration | Directly justified and proportionate; no universal import-path policy added. |
| Same task-reference concern remained a suggestion, later became blocker | Bounded prior dispositions and materiality guidance | Reasonable experiment. Stronger evidence in the later finding means arbitrary severity inflation was not established. Sharing history with every reader may anchor otherwise independent discovery. |
| Passing intent reviews led to explicitly authorized reopenings | Preserve suggestion gate semantics | Correct restraint. Those rounds were not forced by blockers; neither a new suggestion ledger nor automatic refusal to reopen was justified. |
| Genuine timeout and max-turn failures | Preserve budgets; do not generically retry them | Sensible boundary, not a demonstrated solution to those failures. This batch has not established adequate budgets or reduced the work that caused exhaustion. |

## Concrete findings

### Existing files whose planned contents will change are rejected too early

`task_graph.py:74` immediately resolves anchors/lines whenever the file exists.
Only a completely absent file receives the ordered-producer exception. A valid
plan can therefore fail: a producer owns `guide.md` and will add `# New contract`;
a dependent consumer references `guide.md#new-contract`; today the file contains
only `# Existing contract`. The new validator rejects this graph before its
producer can execute. Replacing the file contents with the producer's intended
heading makes the identical graph pass.

This was reproduced in a temporary directory. The check should distinguish the
current input from an ordered producer's future output even when the path already
exists. Consumer launch should still require the actual anchor/line. The existing
regression covers an absent future file but misses this existing-file case.

### Investigation schema alignment is unfinished

`managed_investigations.py:11` still permits `authorization: {}`, empty
`requirements`, and a direct request without `argv`. The runtime rejects all
three. The first has no schema constraints beyond object type; the second lacks
`minItems`; the third lacks mode-dependent requirements. Corresponding runtime
rejections were executed. These are schema-contract inspection findings; no
third-party JSON Schema validator was available in this environment.

Tightening `external` fixes the known malformed shape, but the framework can still
invite invalid output and spend its correction on preventable declaration errors.
The tests exercise rejected dictionaries and correction mechanics, not schema /
runtime agreement. Complete the schema's supported structural constraints and
check representative valid and invalid requests against both layers. Authorization
provenance and runtime policy remain separate checks.

## Limits of traceability and review continuity

Both the final task plan and the retained breakdown-round-1 plan pass the new
structural validator. The latter is the plan whose implementation assignment
omitted relevant path/operation test references. Thus the new checks validate
references that are declared; they do not detect that a relevant reference was
never declared. That omission requires semantic judgment unless an upstream phase
provides an authoritative relationship the runtime can compare. Adding a second
agent-maintained coverage list would not itself solve this problem.

Replaying continuity on the trial state truncated immediately before breakdown
round 4 preserves round 3's task-reference concern as a suggestion, along with its
other findings. That confirms the packet supplies relevant historical context.
It does not prove fewer needless rounds or preserved detection of new defects.
The implementation places this context before every reader's initial discovery;
the investigation had proposed evaluating decision-stage continuity separately.
That broader choice needs comparison against a fresh-discovery reader followed by
history-aware disposition. It is a behavioral risk, not a reproduced missed defect.

## Disposition

Keep the retrospective, recovery, precise diagnostic, and honest readiness changes.
Correct the future-anchor false rejection and finish schema alignment. Retain
upstream guidance, materiality, and continuity as separately attributable
interventions pending a small controlled evaluation. The earlier large passing
test counts establish substantial regression coverage, not prompt effectiveness.

Use the original brief and a contrasting small task, with known consequential
defects and harmless representation differences. Compare introduced unnecessary
requirements, defects preserved or caught, remedy effectiveness, infrastructure
failures, usage and human escalation. Evaluate upstream authoring and review
continuity separately so a reduction in rounds can be attributed rather than
assumed. No new review phase or blanket mutation-testing requirement follows from
this audit.

## Subsequent corrections and user decision

The user rejected prior-review history as default reviewer context because it can
pollute fresh assessment. The history-packet builder and prompt injection have
been removed. Reviewers retain current governing decisions, original sources and
relevant execution evidence; the coordinator retains durable prior reviews.
Current-round candidates/challenges and same-revision execution recovery remain
separate from injecting conclusions from earlier completed review rounds.

Both implementation findings above are corrected: producer-owned future contents
can now resolve at consumer launch even when the file already exists, and managed
request schemas now express mode-specific fields and authorization structure.
The respective agents reported 76 and 96 focused tests passing. Schema tests use
a real JSON Schema validator in an ephemeral uv environment with no repository
dependency changes; native host acceptance of the richer schema remains untested.

The prepared benchmark at `benchmark/review-judgment/` has nine provisional cases.
Its default is now `no-history` at every reviewer stage. Optional historical-context
conditions are experimental comparisons only, with the same current evidence and
stage prompts. No-history judgments are not required to explain historical repairs
or previous classifications. No live model calls have been made.

Integration validation after these changes: from `assets/fbk-scripts`,
`uv run --no-project --with pytest --with pyyaml --with jsonschema python -m pytest tests -q`
reported **606 passed, one unchanged pre-existing declaration test failure**.
`python3 -B -m unittest discover -s benchmark/review-judgment/tests -q` reported
**6 passed**. Focused prompt isolation, managed review/council and protocol recovery
checks passed **46 tests**; scoped Ruff checks passed.
