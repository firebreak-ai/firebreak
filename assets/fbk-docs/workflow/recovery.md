Use when accepted work changes, a review budget is exhausted, or work is interrupted. Preserve existing authorization and recorded review attempts.
When a supported routine repair can resolve the issue, read `repairs.md` beside this file.

## Rework and human handoff

Accepted artifacts are tied to their contents. Editing, adding, or removing an input makes relevant acceptance stale. Reopen the earliest affected phase with a reason and grant:

```
fbk.py approve <unit> reopen --phase spec --reason "<human's words>"
fbk.py phase-close spec <unit> --reopen --reason "<why the contract changed>"
```

Reopening supersedes later acceptance and a later open phase in one transaction; locked tests remain locked. Stop active workers before reopening. A running close must finish or be explicitly recovered before reopening. Reclose the affected phases in order. Parent changes require `acknowledge-parent <unit> --reason "<human's disposition>"` between active phases or after suspending the child. A suspended initial draft can resume after acknowledgment. Changed parent evidence makes accepted child work stale; reopen the earliest accepted phase and revalidate it before continuing.

The phase budget is three review attempts, persisted across fixes and sessions. A completed review of unchanged inputs is reused. The failed attempt that exhausts the budget records `human-review-required`; a single session reaching its time limit or turn ceiling is not such an exhaustion, it fails that attempt and spends one round. Status and continuation then direct the agent to the human, and their `human_review` block points at the phase's review rounds (`retrospective <unit> --section phases --index N --pointer /value/rounds`, with `/value/rounds/-1` for the latest round). Present the failed stages, unresolved candidates, and changes proposed in response, including any expansion of scope. Distinguish incomplete reviews from completed verdicts and agent interpretations from human requirements. Suspend while awaiting the human's judgment, before asking for or starting more rounds. Once a suspend note has been recorded after the exhaustion, that note is the current state: status and continuation quote it, name the human's authorization for another round as the open item, and give the `extend-review` command, so a resuming agent leads with the note instead of presenting the failure a second time. A note recorded before the exhaustion described an earlier state and does not change the guidance. Continue only with `extend-review <phase> <unit> --rounds 1 --reason "<human's authorization>"`, or accept findings from a complete review using `approve <unit> close-over-findings --phase <phase> --reason "<human's words>"` followed by close. Approval cannot turn missing or incomplete review evidence into a verdict. Suggestions do not require either operation.

If the human needs to answer a question or work is paused, use `suspend <unit> --reason "<what is pending>"`. The phase and evidence remain on disk. Resume using the same phase skill or `phase-enter`. If another terminal died while owning it, use `takeover <unit> --reason "<why ownership is changing>"`. Stop an abandoned close process before `recover-close <phase> <unit> --reason "<what happened>"`; its old reservation can no longer commit.

Change design routing only between phases with `route <unit> --design on|off --reason "<why design is needed or unnecessary>"`. Honor the human's explicit architectural decisions. Reopen affected accepted work first.

## Phase entry recovery

When a direct phase slash command encounters an unmet prerequisite, its expansion
returns the reason and a continuation action to the conversation. The requested
phase remains unopened. Read `continuation <unit>`, resolve the named prerequisite,
and use `phase-enter <phase> <unit>` with the current session identity. Existing
operator authorization can be recorded where applicable; the model records its
own required phase observations without asking the user to opt in. Agent-invoked
Skill calls still receive a tool denial, which provides the same prerequisite
reason. Invalid unit/configuration loads remain errors.
