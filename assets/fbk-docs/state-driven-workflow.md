# Firebreak 0.6.0 workflow

Load for a new development unit or a unit under `.fbk/`.

## Purpose and authority

Deliver the behavior the human wants in code that is easy to change: easy to fix bugs in, to add features to, and to understand, both the code and the tests. Tests also require maintenance. Write the smallest set of acceptance tests that proves the intended functionality works and catches bugs, so a later change rewrites no tests and touches as few as possible. Each test should fail only when the behavior it proves breaks; a test that cannot fail, or that fails on a correct change, adds upkeep without proving anything. Keep settled decisions. Ask the human about a choice only when it changes what the unit delivers or what it costs and no human decision or governing source settles it; make the rest, including private implementation details, yourself. The human's current authorization and corrections set the scope. User-stated preferences become requirements through the user's decision; models cannot promote their own preferences into authority.

Write each rule once, where it is enforced. Write a rule only where a careful reader could choose otherwise and the difference would matter to a user or caller; when existing code, tests or project conventions already hold a rule, point to them instead of restating it. One test may cover several requirements, and one parameterized test may cover a requirement's examples. Describe what the human decided in their terms. Add nothing the human did not ask for. A guard against input no described use produces, an extra case, or a detail the request leaves open, such as a message's wording, an output format or how an unusual input is treated, is an addition unless an existing caller depends on it. Leave such a detail unspecified, so tests check only what the request fixes and any reasonable answer passes; list each one worth asking about for the human, with its cost and a recommendation to leave it out.

The requirements document owns user behavior. The design owns architectural constraints and shared contracts. The spec owns acceptance examples, edge cases, scope, and verification strategy. Task files describe work distribution. A task cannot quietly revise a requirement. When implementation reveals a wrong assumption, explain its consequence, revise the relevant artifact with the human's authorization, and revalidate downstream work.

## Runtime

Resolve the Firebreak installation as the phase skill describes. Invoke its dispatcher with:

```
uv run --project <installation>/fbk-scripts python <installation>/fbk-scripts/fbk.py <command>
```

Use the resolved absolute installation path, not a shell variable carried over from another tool call. Commands discover the repository root from the current directory; `--root <absolute-root>` makes it explicit. Pass the explicit `--session` value provided by the phase skill on every command. Claude expands its session placeholder; it is not assumed to export a shell environment variable. Outside Claude use `--session <name>` consistently (or set `FBK_SESSION_ID`). `doctor` reports runtime and host availability.

Initialize a project once with `workflow-init`, then create a unit. Unit names have no spaces; use hyphens instead:

```
fbk.py unit-init <unit> --kind feature --parent <parent-unit>
fbk.py phase-enter intent <unit>
```

Omit `--parent` only for a root unit. Confirm whether work is a project or feature: projects define the parent contract and end at spec; features deliver code and continue through implementation. Use `--design off` for a feature that preserves the existing architecture and shared contracts; state that reason briefly. Honor an explicit human preference for design. Ask only when the choice changes a consequential architectural commitment. A project always includes design. If an existing unit is named, run `status <unit>` and resume it.

Direct slash-command and agent Skill entry use hooks. Explicit `phase-enter` is an idempotent confirmation and a fallback for hosts without direct-expansion hooks. Creating a new intent unit may require initialization before the hook can bind it.

## Load the current work only

Run `continuation <unit>` when resuming a unit or after a context clear or compaction. It supplies current authority, pending work, findings, and source references. Read any explicitly omitted relevant detail through its named command before acting.

| Current work | Read under `fbk-docs/workflow/` |
| --- | --- |
| Intent authoring | `intent.md` |
| Design authoring | `design.md` |
| Spec authoring | `spec.md` |
| Task breakdown: test tasks and implementation tasks | `breakdown.md` |
| Implementation: test tasks, the test checkpoint, then code | `implementation.md` |
| Recording a human decision or correction | `decisions.md` |
| Worker launch/return or a planned context reset | `handoffs.md` |
| Routine reference or settled-intent correction | `repairs.md` |
| Reopening, pausing for the operator's answer, interrupted work, exhausted review budget | `recovery.md` |
| Review choice or council execution | `review-selection.md` |
| Configuration or historical audit | `settings.md` |
| Appending phase observations or examining retrospective evidence | `retrospective.md` |
| Proposing or evaluating a process improvement | `improvement.md` |

## Close and feedback

Maintain the retrospective throughout the run: read `workflow/retrospective.md` and append your own observations during every phase, after failed attempts, and after acceptance. Clean phases need observations too. The runtime initializes the durable ledger and exposes pending phase entries in `status` and `continuation`. Record them before advancing or declaring completion. This is normal model work and requires no separate user request or approval.

After any before-closing check in the phase guide, close with `phase-close <phase> <unit>`. The runtime verifies structure, implementation checks where applicable, source freshness, worker evidence and test integrity, then runs fresh independent read-only review. It reserves and revalidates the input revision before accepting. A review that passes with suggestions holds the phase: sort them as described below, then close again. That close accepts on the same review without another round and lists the files you changed since as unreviewed changes in its output and in `status`. A decision governing the phase recorded after that review needs a fresh review.

Before recommending a next phase or giving a command for a fresh session, verify `continuation <unit>` exposes the required sources and any chosen follow-ups; use `workflow/handoffs.md` for durable handoff preparation. Then run `status <unit>` after the last decision or artifact change. Use its current readiness and next action for the handoff. A successful close describes acceptance at that moment; later changes can require reopening the phase.

Read current findings with `current-findings <unit>`, using its `--phase` and `--index` pointers for omitted entries.

Before changing anything, sort every finding as fix, escalate or refute: blockers and suggestions alike, in passing and failing rounds. Severity decides whether the phase can close with the finding open; the sort decides whether you may act alone. The line is scope and blast radius, because changes the operator never agreed to are how a small unit grows large.

- **Fix** when the remedy only corrects what the accepted documents and decisions already state, and you are sure it is right. Name the rule the finding breaks, fix every place it applies, and check that the reviewer's remedy reaches each place. To correct an already accepted document, read `workflow/repairs.md`.
- **Escalate** when the remedy would add a rule or behavior no accepted document states, touch the critical path, add a function or module, change an interface (inputs, outputs, printed text, exit codes, errors), or change a file outside the unit's scope. Also escalate when you are unsure which remedy is right.
- **Refute** when you can show the failure cannot happen, or that the accepted documents require the behavior. A wrong citation alone is not a refutation.

Ask the operator about escalations one at a time, after checking that no recorded decision already answers them. For each, say in plain words what is wrong, what the fix would change, and what you recommend; name the finding by what it says, not by its number or digest. The operator answers fix now, defer (naming an owner) or decline (giving a reason). Record an answer that adds scope as a decision (`workflow/decisions.md`). A blocker the operator declines or defers closes only with their `close-over-findings` approval.

When you report the close, list each fix and refutation in one plain sentence, with the document or evidence behind it.

`workflow-report <unit>` gives current work. Use `workflow-report <unit> --history` only when investigating earlier events or attempts. Prior verdicts are audit material; source artifacts and attributable decisions govern the work.

Native reviewers run in fresh source snapshots with host customizations disabled and file tools restricted to that snapshot. Required source omissions or incomplete structured results fail review. Original candidates remain separately auditable after final findings are corrected. This is an engineering aid: model source-inspection claims are not proof of correctness, and authoring hooks do not confine arbitrary shell access.
