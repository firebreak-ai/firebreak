<!-- Adapted from EXACT Coding's Predictive TDD v1.2 refactor phase (MIT) — https://github.com/marcoemrich/agentic_coding_lab/tree/main/research/workflow-dev/export/2026-10-29-exact-coding-ptdd-v1.2 -->

Improve the structure of the code under review without changing what it does. The tests and the rules you are given define what it does: every test passes before you start and after every change you keep. Change only production code; the tests stay as they are, since their passing is what shows the behavior is unchanged.

## Review in this order

Judge the code against the four rules of simple design, in priority order:

1. It passes the tests.
2. It reveals its intention: names use the rules' own terms, and each unit's purpose is clear from its name.
3. It contains no duplication, including the same knowledge written twice in different forms.
4. It has the fewest elements the first three allow.

Linters and smell detectors are evidence for this review, not a replacement for it.

## Responsibilities

For each unit (function, class or module) under review:

- State its responsibility as one sentence in the rules' terms. A sentence such as "processes data" or "handles the request" is too broad to show what belongs together.
- Name the policies it owns: rules that could change for different business reasons or at the request of different people.
- Ask: if one of those policies changed while another stayed fixed, would this unit change for both reasons? If so, the line between them is a candidate boundary.
- Keep domain decisions apart from orchestration and from adapters such as parsing, storage, transport and presentation.
- Keep knowledge that changes together in one place. A split earns its place by separating policies.

A well-named unit that isolates an independently changing policy reveals intent, so rule 2 keeps it even though rule 4 counts it as an element. Apply rule 4 once the boundaries are clear.

## Boundary trial

When the review finds a believable boundary, try the strongest candidate as a real change; reasoning about it is not the attempt. Use the smallest move that makes the boundary visible: extract a policy calculation, or a predicate stating when a rule applies, under a name from the rules; separate orchestration or adapter code from a domain decision; or bring duplicated knowledge together under the concept that owns it. Keep the trial when the policy becomes easier to find and change and every test passes; otherwise undo all of it. An undone trial still counts as the attempt.

When no believable boundary exists, name the rules that make the unit one decision.

## Making changes

Make one change at a time and run the tests after each. A refactor keeps behavior as it is, so a failing test means the change altered it: undo that change. When no change improves the code by the four rules, leave it as it is.

## What to return

For each unit under review:

- its responsibility sentence and the policies it owns;
- the boundary candidate it tried, or "none" with the rules that make it one decision;
- the trial's outcome, kept or undone, and why;
- each other change kept, with the rule of simple design it serves.

Then give the final test result. When nothing changed, return the review above all the same, so the record shows the review took place.
