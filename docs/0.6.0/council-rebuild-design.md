# Council rebuild: a mediated discussion instead of parallel reads plus confirmers

Branch `fix/review-inflation`, item 6. Decided with the operator on 2026-10-31.

## Why

The 0.5.x council was a conversation. Members read the document, argued with one another, proposed alternatives and converged on what to change. It was slow but it worked. The 0.6.0 rewrite kept the members but lost the conversation: two or three readers now work alone, then one challenge session and one assessor session grade their candidates. In the review-finding-triage design rounds those two stages supported 48 of 49 candidates. Every member's perspective added findings and nothing removed any, so the council inflated scope. Each role had also shrunk to one sentence, and the member meant to price complexity was optional.

## The shape

The runtime is the mediator. Every step is a fresh, read-only session that sees the original sources, never the authoring conversation, as acceptance reviewers do today.

1. **Opening reads, in parallel.** Each member reads the document alone and states its concerns, each with a proposed correction and whether it blocks this phase. At most eight per member, as today.
2. **Discussion, one round, rotating order.** Members speak one after another, the first speaker changing each council round. Each sees every opening and every earlier turn. A turn may contest a proposal (with its reason), concede, withdraw its own, or put forward a replacement: a new proposal, owned by its author, that names the proposals it replaces. Refining a proposal is a replacement that names it. Every new proposal says whether it blocks this phase. A new proposal that names none is left off the list and recorded as dropped, so the turn still counts. A turn adds at most three new proposals and has a short comment of about 300 words at most.
3. **Closing stances, in parallel.** Each member gives support or contest on every proposal on the list. A contest gives its reason, and that reason may name a cheaper alternative; it travels with the proposal as dissent if the proposal stands.
4. **Count rule (runtime, not a session).** A proposal a majority supports stands, with any dissent attached. One a majority contests is dropped. A tied suggestion stands, with both sides recorded. A replacement removes the proposals it names only if it stands itself, so in a chain a dropped replacement's claim goes with it. Two standing replacements of the same proposal both stand, marked as alternatives for the author to sort together. A member's stance on its own proposal counts like any other; withdrawal during discussion is how a member takes one back. A withdrawn proposal is gone.
5. **Second round, only for a tied blocking proposal.** The members give a stance on those proposals only, in a rotating turn each, with a short comment. A blocking proposal still tied afterward stands as a suggestion, with both sides recorded.
6. **Final session.** It writes each standing proposal as a finding (title, location, evidence, remedy, severity), plus the consensus points, the dissent, and what was dropped and why. It cannot add, revive or drop a proposal, or change a severity the count rule set.

The review result keeps today's shape, a summary and findings, so close and item 4's hold read it unchanged. Consensus, dissent and dropped proposals go in a separate discussion record beside it. The council's finding limit becomes three members times eight openings plus three new proposals per turn, 33, so the final list always fits.

If any session fails or returns invalid output, that council round fails and spends its review round, as today. A retry reuses the finished opening reads and starts the discussion over from them. The shared round clock and per-session limits stay.

The findings then follow the normal path: the author sorts each one as fix, escalate or refute (item 1), and a pass with suggestions holds for that sort (item 4).

A three-member council round uses ten sessions: three openings, three turns, three closing stances and one final session. Today it uses two to five. A second round adds one session per member.

## Members and personas

- The Builder is in every council. The review plan picks one or two more from architect, guardian, security, advocate and analyst.
- Each member's persona is a markdown file, `assets/fbk-docs/review/council/<member>.md`, loaded and fingerprinted by the runtime like the phase briefs. It starts from the 0.5.x persona (identity, quality bars, the defaults it resists, its authority) with every line kept only if it prevents an observed mistake, plus one short focus section for each of intent, design, spec and breakdown. Tool lists, model pins and web research are dropped: members are read-only.
- The Builder's and the Advocate's watchdog authority becomes a stance duty: they contest a proposal whose remedy adds cost or scope nobody priced, and propose the cheaper alternative, as a replacement in their turn or as the reason for a closing contest.
- `assets/fbk-docs/review/council/council-brief.md` holds the instructions every council session shares: what an opening, a turn, a closing stance and the final session each produce. Openings and turns also get the full shared reviewer brief (`reviewer-brief.md`). Closing stances and the second round get only its evidence and excess rules, kept in their own section of that file so neither copy drifts. The final session gets only the council brief.
- Council consultation, the skill's authoring-time mode, reads the same persona files instead of keeping its own table of responsibilities.

## Phases

The council is available, never required, for intent, design, spec and breakdown. For intent and breakdown, no recorded review plan means a single reviewer, so the option adds no question to a unit. Design and spec keep today's rule that a plan is recorded before close. The test checkpoint and implementation keep their single reviewer.

## What goes away

- The challenge stage, which only the council used, and the council's use of the assessor stage, with their council prompts in `council.py` and the `challenge` field in status and close events. Status reports the council's steps instead. The optional external second reader for single-reviewer phases keeps its assessor stage and its `adjudication` field.
- The `FOCUS` table in `council.py`.
- The consultation guide's responsibility table.

## What stays

- Fresh read-only sessions, source snapshots, the context declaration and required-file rules, and the rules block rendered from the constraint registry. The registry gains the new council session kinds. Its rule that an unresolved blocker cannot be downgraded stays as it is: after the rebuild only the external second reader's assessor uses it, and the council's tied-blocker rule is a rule of its own, stated to closing stances.
- Per-session time and turn limits from the project settings.
- One review round per council round against the phase budget.

## Watch item

Recorded on the adversarial-council card in the firebreak wiki: two-member councils tying often and demoting real blockers to suggestions, members contesting by reflex, and a majority dropping a correct finding only one member saw. Judge on the first units that use the council.

## Build order

1. Persona files, drafted for the operator's line-by-line review, and the council brief.
2. Runtime: the six steps, the proposal list with replacements, the count rule, and the final session's result shape. Tests for each step, the count rule's cases, the dropping of an unanchored proposal, and the second round.
3. Review plan: phases extended to intent and breakdown, Builder required.
4. Guides, the consultation reference, status fields, and a decision-log entry.
