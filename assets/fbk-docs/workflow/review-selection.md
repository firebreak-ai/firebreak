Use for managed review selection and council execution for intent, design, spec and breakdown.

## Choosing a review

Design routing and review mode are separate choices. Intent, design, spec and
breakdown can each use one reviewer or a council. Design and spec record a choice
before close. For intent and breakdown no recorded choice means one reviewer, so
record a council there only when the work calls for one. Skipping design does not
remove the council option at spec. A council at one phase does not require one at
the next.

Once the work is understood, recommend a review plan briefly. Follow the human's
existing preference or a saved project default. Ask only when no preference covers
the choice or a material change warrants reconsideration. One reviewer suits a
coherent focused concern. Recommend council when consequential concerns interact
or compete, or a focused review exposes unresolved disagreement. These are
engineering heuristics, not claims that research has established the best mode.

Record each applicable phase's choice before closing it:

```
fbk.py review-plan <unit> --phase design --mode council --members architect builder --reason "<applicable preference and rationale>"
fbk.py review-plan <unit> --phase spec --mode single --reason "<applicable preference and rationale>"
```

A council is the builder plus one or two of architect, guardian, security,
advocate and analyst. The builder prices each proposal's cost and offers cheaper
alternatives, so every council includes it. Choose the others for the concerns the
work raises; each member's role and what it looks for in each phase are in
`fbk-docs/review/council/<member>.md` under the Firebreak installation.
Task count and design scope do not mechanically determine mode.

To save an ongoing project preference, use `review-default --phase spec --mode
single --reason "<human's preference>"` (or council with `--members`). Defaults
are stored in `.fbk/config.json` under `review_defaults`. They apply to new units
and unresolved choices at phase entry; existing selections remain unchanged.
The same commands let the agent record an existing human preference without
asking again. A reason records the decision; it does not authenticate consent.

`status` and entry hooks show the saved plan or a pending choice. Hooks supply
context; the lead agent asks any needed question. `phase-close` refuses to start
a design or spec review without a recorded choice. A running close must finish or
be recovered before changing that choice. Changing an accepted phase's plan
requires reopening. Mode or membership changes invalidate review reuse and
revision-bound approvals while retaining consumed review attempts. Confirming
the same choice is idempotent. Reopening retains the plan, so there is no routine
repeat question. Previously accepted records keep their evidence until reopened.

## How a council runs

`fbk.py phase-close` supplies instructions and starts fresh, read-only headless
Claude sessions. The lead does not spawn acceptance reviewers or write their
verdicts. These sessions use Claude Code authentication and appear as subprocesses,
not teammates in the authoring session. A single selection launches one reviewer
even if the project has an optional external reader configured. Council uses the
selected perspectives on the configured native model; model diversity is not
implied by role diversity.

A council round is a short discussion the runtime runs, each step a fresh
read-only session:

1. Openings: each member reads the work alone and proposes at most eight
   corrections; none is a valid outcome.
2. Turns: each member speaks once, in an order that rotates each round. A turn may
   contest, concede, withdraw its own proposal, or put forward a replacement for
   listed proposals. It cannot add an unrelated new proposal.
3. Closing stances: every member supports or contests every proposal on the list.
4. The count: a proposal a majority supports stands with any dissent attached, and
   one a majority contests drops. A tied suggestion stands with both sides
   recorded. A tied blocker goes to a second round and stands as a suggestion if
   still tied. A standing replacement removes what it replaces.
5. The final session writes each standing proposal as a finding with the severity
   the count gave it, plus what the members agreed on and why each dropped
   proposal dropped.

Only the work, the proposals and the discussion pass between sessions, never the
authoring transcript. `current-findings` shows each council finding's dissent,
whether its count tied, and any finding it is an alternative to; sort each one with
that in view. Status and the `close-attempt` event record each step as `ran`,
`skipped`, `failed`, `incomplete` or `not-reached`.

Reviewers assess current original sources, applicable human decisions, and relevant
execution evidence. Previous rounds' findings, classifications, refutations, and
reopen narratives are not supplied to reviewers. The coordinator uses durable
review history to manage repairs and explain repeated concerns; a focused follow-up
should identify the current source or behavior to examine. Proposals and discussion
from the current round remain available to its later steps.

Source inspection validation lists every missing required path and tells the reader
to inspect any unread originals before reporting those paths truthfully. It checks
the completeness of the declaration, not proof of actual reading. Unavailable
evidence belongs in an incomplete context report.

A three-member round uses ten sessions: three openings, three turns, three stances
and a final session. A second round adds one session per member. `review_timeout` applies to each subprocess, not the whole
council attempt. Each native session has the configured time limit (default 1200
seconds, stated to the reviewer in its prompt) and `reviewer_max_turns` ceiling
(default 100); both are safety nets against a hung or looping session, and the
council's steps are fixed. A failed or incomplete session fails the close with
completed step results retained. It never
downgrades to single review. The attempt consumes one persisted phase review round;
there is no internal repair loop or mandatory self-evaluation. A further attempt
uses the existing phase budget and the same saved review plan.

A required session that reaches its turn ceiling or its time limit is an ordinary
failed attempt: the round records the failure with the configured limits, elapsed
seconds, host-reported turns, and captured output, and another close attempt may
run while phase rounds remain. In a council a timed-out session fails the round
like any other. The review round limit is the repetition control.
The one clock that still pauses for human help is the managed round clock
(`review_round_timeout`), which bounds a whole review round including its
investigations; when it runs out, close attempts are blocked, the retained
diagnostics name the exhausted round clock, and the human authorizes a retry
through `extend-review`. Changing settings alone does not clear that pause. Other
failed reviews still consume the phase's ordinary round budget, which also
escalates when exhausted.

Before any round is recorded or reviewer launched, `phase-close` scans the unit's
own artifacts under `.fbk/<unit>/` (the phase files the close is accepting, never
code, tests, or context sources) for characters a reader cannot see: raw control
characters other than tab, newline, and carriage return; DEL; the Unicode line
boundaries U+0085, U+2028, and U+2029; and bytes that are not valid UTF-8. A hit
fails the close with one line per character (`path:line:column U+XXXX NAME`), spends
no review round, and asks the author to write the character as an escape or remove
it and close again. Binary-looking or very large files are recorded as skipped rather
than clean. The scan's outcome is kept on the `close-attempt` event so the audit
trail shows it ran.

While a close runs, `status <unit>` exposes each council step under
`close_in_progress.stages`, with start/finish timestamps and its current state.
Completed peers are reported as they finish. The retrospective retains
`council-stage` events after the attempt ends; stage reporting does not establish
that a model inspected sources correctly.

After a failed attempt, a retry reuses finished opening reads only when the phase
revision, generation, complete source snapshot, required files, reader
instructions, selection, and review settings match; the discussion always starts
over from them. Reused openings point to their earlier attempt and add no new
usage or execution time; original paid results remain in history. Changed inputs
require fresh openings, and retries still consume the phase budget.

Failed stages retain bounded host stdout/stderr excerpts, timing, exit status and
truncation counts when available. Retrieve the failed round or council-stage event
through the retrospective to diagnose a structured-output failure or timeout.
Exhausting the phase budget requires human review before another attempt; it is
not a direction to keep revising the artifact.

Reviewers see original phase artifacts and declared original source context, not
arbitrary files under `.fbk/`. A scratch review summary can exist on disk while
remaining outside that snapshot. Carry chosen behavior into governing artifacts
and sourced decisions; cite those originals rather than a scratch account of a
previous review. Consult `accepted_reviews` during authoring for historical advice.

Council consultation can help the human develop an approach before closure. It
is advisory authorship support and cannot supply its own independent acceptance.
The standalone `/fbk-council` consultation guide is separate from the managed
review execution; `/fbk-spec-review` routes a managed spec to its saved review plan.

## Targeted implementation review

Managed implementation review receives the installed AI failure-mode checklist,
security and structural targets, detection audits, and shared test-integrity audit
as embedded methodology. These are the same catalogs used by standalone code review;
they do not become project requirements or snapshot source dependencies. The review
records their content hashes, and changed guidance changes its execution identity.
Missing installed guides stop review with a repair instruction before a model call.
Earlier phases retain their phase-specific objectives.

Apply every applicable target and enumerate the relevant sites. For each code
finding, establish the exact mechanism, realistic trigger, and caller impact;
for structural risks, establish the concrete coupling and plausible maintenance
change. Pattern matches direct inspection; they do not automatically qualify as
findings. These criteria fit the existing phase finding fields and add no review
stage or prior-review history.
