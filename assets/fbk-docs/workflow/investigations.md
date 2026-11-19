# Investigative checks and experiments

Reviewers and remediators should check actual source, dependencies, documentation
and runtime behavior when evidence is available. Small inspections and focused
checks may run directly. Exploratory debugging, noisy multi-step investigations
and code-changing experiments belong in fresh experimental workers. Give the
worker a concrete question, relevant requirements and source revision; request
reproducible evidence and limitations. A remediator's helper is not independent
verification of that remediator's changes.

## Durable invocation

Start an investigation attached to an existing review round:

```
fbk.py investigation start --root /project --round ROUND --request investigation.json
fbk.py investigation run --root /project --round ROUND --id QUESTION --request assignment.json
fbk.py investigation status --root /project --round ROUND --id QUESTION
```

The start request contains `id`, `question`, and `requirements` (source references).
An assignment contains `mode` (`direct` or `delegated`) and optional booleans
`exploratory` and `modifies_code`. Direct assignments supply `argv` (a command
argument list). Delegated assignments supply `prompt`; Firebreak launches a fresh
noninteractive Claude worker with no resumed session, bounded turns, and the
assignment packet. Arbitrary delegated command lines are rejected. The worker can
read, execute experiments, edit the disposable copy and consult public web sources.
It has no agent-spawning tool. Classification of a check as exploratory still
depends on the caller's honest declaration.

Each assignment receives a separate copy of the round's source snapshot. Its
packet, command output, exit status and execution duration remain under
`.fbk/runtime/investigations/ROUND/QUESTION/ATTEMPT/`. Temporary edits never become
accepted deliverable edits through this command. Include external source versions,
reproduction steps and limitations in the output; retain large evidence in files
inside that workspace. The bounded stdout/stderr capture records omitted bytes.

Project configuration accepts `investigation_max_attempts` (default **3**) and
`investigation_timeout` (default **600** seconds), both positive integers. An
attempt is one bounded assignment, not each command executed inside it. The round's
remaining time further limits execution. Each launch reserves time durably before
execution and records actual usage afterward. Retries and context resets reuse
that record. Exhaustion records `human_review`, including the exhausted limit,
question and evidence locations, and prevents further attempts at that question.
The two per-question limits (attempts and time) are safety nets, not verdicts:
reaching one means the question could not be answered within budget. A managed
reader is told so and finishes its review without the answer, as described below;
only a human disposition can reopen the question. The round's own clock
(`review-time`) is different: exhausting it stops the review and needs a human.
An interrupted assignment retains its reservation; a human must reconcile its
execution before recovery. Creating another question cannot bypass a round-level
escalation; a per-question exhaustion does not block other questions.

## External effects and confinement

Public documentation lookups and isolated local experiments need no additional
approval. Declare authenticated, shared-environment or state-changing checks using
`external: {target, effects}`, with a nonempty target string and a nonempty list
of effect strings. Omit `external` for checks with no such effects. Supply an existing explicit grant as
`authorization: {target, effects, source: {path, quote}}`; the exact quotation must
exist in that project-relative source. Grants persist for matching target/effects,
so subsequent attempts do not ask again. The caller is responsible for ensuring
the source really records human authorization or an applicable standing policy;
a quotation does not authenticate its author.

An external check with no matching grant, or with a grant whose quotation or
coverage does not verify, is refused. The refusal is evidence, not a failure:
the investigation records a `refused` attempt holding the reason, no command runs,
no workspace is created, no time is charged, and the reader's protocol correction
is untouched. The refused attempt still counts toward the attempt limit, so a
reader that keeps asking for the same unauthorized check reaches the ordinary
attempt escalation instead of looping. A managed reader continues with the
refusal in its evidence and either proceeds without that answer or reports the
question as unresolved in its review; the review's conclusion may cite the
refused attempt.

The executable checks declared authorization and enforces process-group timeout,
durable budgets and workspace selection. It is **not an operating-system sandbox**:
arbitrary commands can use absolute paths, credentials or networking. Actual
filesystem and network restrictions require the host sandbox. Do not claim that
copying files enforces these permissions. Child work must stay
inside the enclosing assignment and share its timeout; this interface does not
grant independent child budgets.

## Human disposition

`fbk.py investigation resolve --root /project --round ROUND --id QUESTION
--request decision.json` records the human's explicit disposition. The request
requires `disposition` (`stop` or `extend`), `reason`, and `source: {path, quote}`.
Stopping records the unresolved question and the human's decision; it does not
turn experimental claims into verified findings. Extending requires explicit
positive `additional_attempts` and `additional_seconds`; it preserves consumed
usage and evidence. The enclosing review budget is unchanged unless the human
also authorizes explicit `additional_review_seconds`. Interrupted work additionally
requires `confirm_stopped: true` after confirming its process group is stopped.
Reservations remain charged; this acknowledgement is not automatic process cleanup.

## Closing an investigative question

Running a probe, including a successful probe, does not establish a conclusion.
`investigation conclude --root /project --round ROUND --id QUESTION --request
conclusion.json` records the reviewer's interpretation with `conclusion` and
`attempts` (one-based indices of completed evidence). The conclusion can explain
why an intentionally failing probe demonstrates a defect. An unanswered question
continues to block round completion. A question exhausted on its own attempt or
time limit is closed by the reviewer's conclusion citing its attempts, exactly as
a refused attempt is; its `human_review` record stays for the audit trail. A
round-level escalation (the review clock, or an interrupted assignment) still
requires human disposition; a conclusion cannot clear it.

## Investigations during managed review

Managed native reviewers can return an investigation request instead of guessing
about observable behavior. Firebreak executes the request and starts a fresh
review continuation with the original review instructions and experimental
evidence. Complete artifacts and their origin/hash manifest are copied into the
reviewer's readable snapshot; inline excerpts explicitly identify omissions.
The validated final verdict records the reviewer's interpretation separately
from command success. When a question exhausts its attempts or its time, the
next continuation carries it as unresolved evidence with an `exhausted` note
naming the limit reached and the attempts made, and telling the reader that no
further attempts are possible in this round: proceed without the evidence or
report the question as unresolved in the review. Asking for that question again
returns the same evidence without spending an attempt or a correction; a reader
that asks a third time is looping and is stopped with a diagnostic naming the
question. The review lands with the caveat; nothing pauses for a human.

`review_round_timeout` caps the **whole review's active wall-clock execution**,
including parallel Council readers, investigations and continuations. Parallel
elapsed time counts once. Its default is 9999 seconds, independent of
`review_timeout`, which keeps its own per-session limit (default 1200 seconds)
whose breach is an ordinary failed attempt. Set `review_round_timeout` explicitly
when a shorter whole-round ceiling is wanted. The maximum is 86400 seconds. Transport retries preserve consumed time; human waiting between
invocations does not consume active time. The durable clock records active wall
time, total elapsed time, waiting time, aggregate worker seconds and model usage
separately. Aggregate worker seconds are a cost/work measure, not the wall limit.

The existing operator `extend-review` action adds the configured time for each
explicitly authorized extra round and preserves consumed usage. It does not erase
an investigation's separate exhaustion; dispose of that question explicitly.
An interrupted coordinator requires `recover-close` after stopping its processes;
unknown execution conservatively retains its remaining reservation, so extending
is explicit rather than an accidental budget reset.

A malformed managed investigation request is rejected before an experiment record
or attempt is created. Diagnostics identify the invalid field and expected shape;
the durable record retains a request hash and field names, not command text or
authorization quotations. A missing inspection declaration names the exact source
paths and requires actual inspection before a truthful declaration. A required
path counts as declared when it appears in either `inspected_files` or
`supporting_files`; a supporting source the reader relied on is a source it read.
A declaration naming a path outside the snapshot (a directory, a wildcard, a
`./` prefix, an absolute path, or a file the reader never received) earns the
same single correction: the diagnostic names the exact offending entries and
states that each entry must be a file path spelled exactly as in `required_files`
or the snapshot listing.

Each logical reader has at most one protocol correction per round, shared between
these declaration errors and retained across restarts. The fresh continuation
uses the original instructions and the remaining shared clock; its usage remains
charged. Generic response errors, timeouts, and turn exhaustion do not trigger
this correction. Absent external authorization triggers neither the correction
nor a stop: the refusal is recorded as evidence with its reason, no command runs,
and the reader continues and reports the question as unresolved. A second
declaration failure stops the reader with the original diagnostic and an
exhausted-correction indicator. Any other error while dispatching a reader's
investigation is recorded on the round with the round identifier and a summary
of the reader's earlier responses (count, usage, and the digest of its last
request), so the failure stays diagnosable.
