# Fresh-eyes review — intent: deterministic metrics plane (hook harvesting)

Artifacts reviewed: `prd.md`, `behavior-inventory.yaml`. Date: 2026-06-10.
Cold adversarial read by an isolated reviewer. Two prior rounds surfaced Critical observations (provenance auditability, missing-transcript handling, and missing capture sources for parks and rework); those were addressed in the PRD and verified clear on this pass. The observations below are the reduced report after dedup against the intent grilling log.

## Critical

None.

## Substantive

**Challenger kill rate definition uses ambiguous denominator.** The code-review round logging section defines the kill rate as "total issues raised across all rounds, minus the issues confirmed, over total issues raised." A single issue raised in round one, challenged, re-raised in round two, then confirmed could contribute either 2 or 1 to "total issues raised." The PRD does not say whether the denominator is distinct issues or cumulative raise events. Design-deferred (the PRD already flags the roll-up as a presentation detail for design).

**"Issues confirmed" equated with "survived to the final quiet round" may exclude true positives from earlier rounds.** If the review gate stops re-raising previously-confirmed issues once they are acknowledged and queued for remediation, those issues would not appear in the final round and would read as "killed" rather than "confirmed." Whether the gate operates that way is not addressed.

**The report's "gate attempts and first-pass rate" row has two sources, and the conflict resolution is not stated.** Gate attempts are recorded by the chokepoint recorder; parks and rework are state-derived. When a gate fails and is re-attempted after a park (stage re-entry), whether that attempt counts toward the gate's first-pass denominator or is excluded is unspecified.

**Token harvester's intra-session stage attribution is undefined.** The harvester joins transcript tokens to stages via state-engine timestamps, but a single session transcript does not record stage transitions. For a session that spans a stage boundary (e.g., began in implementation, ended in verification), the rule for attributing tokens within that session is not defined.

## Minor

**Capture level "off" versus the per-project capture gate composition.** Both cause the router to exit for an uninstrumented project, but the PRD does not state how they compose when a Firebreak-managed project sets its level to "off" — e.g., whether the router still reads the state engine before exiting.

**Provenance marker format is deferred, but the "automated check" success criterion depends on it.** The success metric asserts an automated check can confirm the marker; an automated check needs a stable, parseable marker format, which is called a design detail without flagging the dependency.

**The inventory's mutual-coverage header claim has no drift check.** The schema drift-check concept is not applied to the behavior inventory itself, so an identifier added to one file and not the other goes uncaught.

**"Parks per stage with a recorded reason" does not define an acceptable reason value.** The PRD does not say what form a park reason takes (free text, enum, code) or whether a null reason satisfies the criterion.
