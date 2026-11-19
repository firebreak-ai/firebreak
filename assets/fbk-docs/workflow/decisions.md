Use when recording settled human intent or a correction. Preserve the original words and their source separately from your interpretation.
Record existing authorization as given.

## Record a decision

Keep each original decision in an immutable source file, for example `.fbk/<unit>/decisions/cancellation-source.md`. Copy the relevant human words exactly, with enough surrounding context to distinguish the decision. A source file can also be an existing authoritative requirement. Use a separate source file for a later correction: appending to a previously cited file changes its hash.

Write a repository-relative request file under `.fbk/runtime/<unit>/` containing:

```json
{
  "id": "release-once",
  "text": "Cancellation releases its resource once, including after a release failure.",
  "phase": "intent",
  "kind": "governs",
  "source": {
    "path": ".fbk/cancellation/decisions/cancellation-source.md",
    "quote": "Cancellation must release its resource exactly once, even if release raises."
  }
}
```

Set `kind` to `governs` when the decision constrains the work product (behavior, scope, contracts, plan rules), or `process` when it records how the work was run (review plans, approvals, dispositions, overrides). Process decisions stay in the record but never reach a reviewer or work agent.

Run `decision-record <unit> --request <request-file>`. The runtime checks that the exact quote occurs once, binds its source contents, and records attribution. The response includes current readiness under `workflow`; follow its `status` and `next` fields before continuing or handing off. Recording a decision after acceptance can make that acceptance stale, even when it confirms behavior already written in the artifact. The record is an audit of the human's instruction, not authentication of consent or proof that your interpretation is correct.

## Disposition an accepted suggestion

A reviewer's suggestion is neither accepted nor rejected until the operator says what happens to it. Record that answer as a decision carrying `dispositions`, one entry per suggestion, naming each by the digest the continuation packet shows under `undispositioned_suggestions`. The decision's `text` and `source` are the operator's disposition words only; the `phase` is the phase you are working in when you record them, and the `kind` is `process`. A disposition record leaves accepted work current, so any other decision the operator gives in the same breath, including a correction of an earlier one, goes in its own record; the runtime refuses a disposition record that also `supersedes`. `fix-now` means the work happens before the current phase closes. It adopts the work, not the remedy: before planning or applying the remedy, check that it catches the defect at every place the finding's scenario touches, including places the finding does not name. Extend it where it falls short, and show the same evidence for it as for your own work. `defer` names the person or unit that owns it later; `decline` needs the operator's reason in the text. A later decision may disposition the same digest again, and the newest recorded one stands.

```json
{
  "id": "spec-suggestions-1",
  "text": "Fix the encoding note now. Defer the second-cancel regression to the test lead. Decline the naming change; the current names match the API.",
  "phase": "breakdown",
  "kind": "process",
  "source": {
    "path": ".fbk/cancellation/decisions/spec-suggestions-1.md",
    "quote": "Fix the encoding note now. Defer the second-cancel regression to the test lead. Decline the naming change; the current names match the API."
  },
  "dispositions": [
    {"finding": "<64-character digest>", "disposition": "fix-now"},
    {"finding": "<64-character digest>", "disposition": "defer", "owner": "test-lead"},
    {"finding": "<64-character digest>", "disposition": "decline"}
  ]
}
```

Record one when the continuation packet lists suggestions under `undispositioned_suggestions`, and before the test checkpoint locks the tests when a listed suggestion's remedy is a test. A phase cannot close while a listed suggestion from an earlier phase has no disposition, and the test checkpoint cannot lock the tests while a listed test-remedy suggestion, or one from its own review, has none. Every one of these refusals names the suggestions as `<phase>#<index> <title>`.

Use a new id and `"supersedes": "<earlier-id>"` for a correction. An id that differs from an active decision's only by a version ending such as `-v2` is refused unless it names that decision in `supersedes`. The phase names the earliest phase governed by the decision. Revisions include every applicable current decision and its source hash, so an applicable correction makes earlier acceptance stale.

## What readers receive

Reviewers and work agents of a phase receive that phase's own governing decisions, plus amendments not yet absorbed, and must read only those decisions' source files. Earlier phases' decisions reach them through the accepted documents, so a phase's review blocks when the phase's document does not state each of its decisions in substance.

To change an earlier phase's accepted document without reopening it, record the decision under the current phase with `"amends": "<earlier phase>"`. The earlier phase must be accepted, and an amendment's kind is `governs`. A decision that supersedes one from an earlier phase amends that phase automatically; an `amends` naming any other phase is refused. An amendment reaches every later phase, and the amended phase if reopened, until that phase is accepted again after the amendment was recorded.

A decision recorded before kinds existed counts as governing for its own phase. To classify one, write `{"id": "<decision id>", "kind": "governs" | "process", "amends": "<phase>", "reason": "<operator's reason>"}` (`amends` optional) and run `decision-annotate <unit> --request <file>`. Each such decision is annotated once; the same rules apply as when recording. When correcting artifacts to match an already settled decision, read `repairs.md` beside this file. A change to the desired behavior uses `recovery.md` instead.

## Sufficient context

Select the applicable decisions and acceptance examples for the receiving task. Keep the source references accessible so the receiver can verify meaning without inheriting the conversation. Record unresolved questions separately from settled decisions. Read the current decision before asking the human to answer an old question again.
