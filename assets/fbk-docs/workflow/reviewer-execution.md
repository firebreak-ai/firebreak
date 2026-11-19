# Executing checks during review

Every reviewer may use actual tests or focused probes to resolve a material factual
question: researchers, challengers, Council members and scan/document reviewers.
Choose the smallest useful check, using the project's real runner and configuration.
Do not rerun a suite merely for ceremony, investigate preferences, or replace source
inspection with green test output. Read the source first and state what observation
would decide the question.

## Native reviewers

Managed phase reviewers already have the investigation response protocol. Standalone
skills must launch through `review-round run`, not a bare agent spawn, to receive
it. Read `review-rounds.md` and capture the complete role/lens/source/output contract
before launch. For a single scan or document reviewer, omit the code-review binding:

```bash
python3 "$firebreak_dir/fbk-scripts/fbk.py" review-round begin --root "$PWD" \
  --instructions .fbk/runtime/reviewer-instructions.txt \
  --contributors reviewer --required <governing-project-paths>
python3 "$firebreak_dir/fbk-scripts/fbk.py" review-round run --round ID --contributors reviewer
python3 "$firebreak_dir/fbk-scripts/fbk.py" review-round require-complete --round ID
```

Use the returned ID, resolving the installed driver as the calling skill describes.
Workers return their JSON output under `result`, with the required context inspection
record. For prose scans, use `result: {report: "..."}` and render that report only
after checking completeness. This changes transport, not the lens's classifications
or cardinality. Capture full instructions; workers do not inherit a skill or agent
file merely because their role has its name.

Every native reviewer prompt carries a `rules` block stating each rule the runtime
checks against the response: the response properties and length budgets (including the
context record's caps), the context declaration rules, and in managed sessions the
investigation request shape, the authorization rules, and the per-question budgets. The
block is rendered from one registry, worded from the same data each check reads; see
`constraints.md` for the registry, its groups, and how a new rule is added.
Each finding may carry `remedy_kind` (`artifact`, `test`, `code`, or `documentation`;
absent means `artifact`), and a suggestion whose remedy is a new or changed test is
tagged `test` so that, unless the author sorted it before its phase was accepted, it is
dispositioned before the test checkpoint locks the suite, since nothing after the lock can add a test; a council finding keeps its proposal's tag unless the
final session restates a different one.

Every reviewer prompt carries `required_files`: the exact list of paths the runtime
checks the context declaration against. The rule beside it in the `rules` block says to
name each of those paths in the declaration, under `inspected_files` or under
`supporting_files`; supporting files are the subset relied on as governing authority.
A declaration missing any of them is rejected. Council turns, closing stances and the
final session carry the same list and their own `rules` block with the same obligation as an
opening read, even when proposals cite only a few sources.

A deterministic check may reject a malformed claim, never an honest one. A reviewer
that reports `context.status: incomplete` with the missing items named in
`missing_context` has given a verdict, not broken the protocol: the runtime records
that verdict on the round, fails the round with a plain "Review incomplete; missing
context: ..." message, and keeps the reader's summary and findings for the author.
No harness diagnostics, budget marker, or human-review pause follow; the next close
attempt runs the reader again, reusing finished council openings. In a council an
incomplete session stops the round at its step. Only a contradictory
declaration is malformed: `complete` with named gaps, or `incomplete` naming nothing.
In the same spirit, a refuted assessment from the second reader's assessor that also carries `duplicate_of` is
accepted and the reference dropped, since a refuted claim has no operative finding
to group; every other duplicate rule (a direct retained representative, no self
reference, no chains, the same disposition, a null finding) still rejects the pass.

Readers retain Read/Grep/Glob inspection tools. Instead of a final result they may
return this request as the only property of their structured response (never
alongside review fields). If a reader sends both and the review fields validate on
their own, the runtime keeps the review as final, records the discarded request
under `ignored_investigation` on the reader's result, and never runs it; if the
review fields do not validate, the mixed object is rejected as such:

```json
{"investigation": {
  "id": "focused-regression",
  "question": "Does the regression test reject an incorrect result?",
  "requirements": ["spec.md#required-result"],
  "mode": "direct",
  "argv": ["python3", "-m", "pytest", "tests/test_result.py", "-q"]
}}
```

Use actual paths, a stable question ID and the appropriate project command. For
fault injection or temporary test additions use `mode: delegated`, `modifies_code:
true` and a concrete `prompt` instead of `argv`, following `investigations.md`.
The runtime executes in a separate disposable copy of the captured round sources,
then continues the reviewer with original instructions and recorded evidence. It
retains stdout/stderr, exit/timeout status and complete artifact paths. The reviewer
must interpret those observations; process success does not confirm a finding.
All attempts and continuations consume the existing shared round budget. A timeout
or unavailable dependency is a limitation, not a reason to restart a fresh budget.

## Source preservation

Run tests only in the investigation workspace. Keep generated fixtures, caches,
build outputs and experimental edits there. Do not edit the live project, canonical
snapshot or reader's source copy; do not redirect commands to them using absolute
paths, symlinks or configuration. Do not copy experimental changes back into the
reviewed content. Reports belong under `.fbk/runtime/reports/` during the round.
The runtime checks source drift before completion; retain diagnostics if sources
change. Copying is workspace isolation, not an OS security sandbox: host permissions
must constrain arbitrary commands when enforced filesystem/network confinement is
needed. External effects follow the existing authorization rules in `investigations.md`.

## External or read-only adapters

An external reviewer that cannot use the native response protocol should return a
concrete execution request (question, governing reference and direct argv or delegated
experiment). If no round exists, the coordinator first captures the original review assignment
and begins a standalone round as above. The coordinator attaches the request to
that round through
`investigation start` and `investigation run`, then supplies the original current
sources and actual evidence to a fresh review continuation. Record the reviewer's
interpretation with `investigation conclude`. See `investigations.md` for those
request formats. Do not give the external model write access to reviewed content
or claim that an unconnected adapter automatically executes native requests.
External review output remains supporting candidate evidence, not a runtime
contribution receipt or managed acceptance. Keep unavailable checks explicit.
