# Fresh-eyes review — design: deterministic metrics plane (hook harvesting)

Artifacts reviewed: `design/overview.md`, `design/capture-sources.md`, `design/reporting-and-injection.md`, `design/configuration-and-lifecycle.md`, `design/contracts.md`, `design-manifest.md`. Date: 2026-06-10.

Cold adversarial read by an isolated reviewer, checked against the PRD, the behavior inventory, the intent-phase fresh-eyes observations, and the real Firebreak source the design modifies. One round surfaced five Critical observations; all five were resolved in the design before this record was finalized. The resolutions are recorded below the Critical section, which is now empty.

## Critical

None.

## Resolved this pass (were Critical)

- **State transition had no path to the project root.** The injection trigger lives in `transition_state()`, which receives only a spec name and target state. Resolved: the injector resolves the retrospective path internally from `os.getcwd()` — the same project-root assumption the chokepoint recorder and the report prototype already rely on — and `transition_state` passes only the spec name and the previous state. The injector signature dropped its path parameter. Recorded in `reporting-and-injection.md` and contract IF-D-07.

- **The "active working stage" injection predicate was undefined against the real state names.** Resolved by defining the predicate exactly: the eight working stages are the states whose `VALID_TRANSITIONS` entry contains `PARKED` (`VALIDATING`, `REVIEWING`, `BREAKING_DOWN`, `TASK_REVIEWING`, `TESTING`, `TEST_REVIEWING`, `IMPLEMENTING`, `VERIFYING`). Injection fires only when the previous state is one of these. The checkpoint states, `QUEUED`, `PARKED`, and `READY` are named as non-triggering. The implementation reads the set from `VALID_TRANSITIONS` rather than hardcoding it.

- **The READY-to-working resume case would skip injection.** Resolved by the corrected predicate: injection fires on stage *completion* (a working-state-to-checkpoint transition), not on stage entry. A resume (`READY` to `IMPLEMENTING`) correctly injects nothing on entry; the reworked stage's completion (`IMPLEMENTING` to `IMPLEMENTED`) has a working previous state and injects just like a first pass. Rework is covered for free.

- **The chokepoint stdout re-emit mechanism was imprecise.** Gates raise `SystemExit` from inside `main()`, which would short-circuit `with`/`atexit` cleanup. Resolved by specifying the exact mechanism: save real stdout, install a buffer, call `run_fn()` in a `try` catching normal return and `SystemExit`, and in a `finally` restore stdout and flush the buffer to it before writing the event and re-raising with the same code. Recorded in `capture-sources.md` and contract IF-D-04, with the source of `cwd` (`os.getcwd()` in `fbk.py`) named.

- **The verification hook's dispatch path was unstated (reviewer believed it bypassed the chokepoint).** Clarified: the hook is registered as `fbk.py task-completed`, so it is dispatched through the chokepoint like any other command — the chokepoint records the command-level event, and the hook module additionally writes the structured `VERIFICATION_RESULT` event. The two are complementary. Recorded in `capture-sources.md`.

## Substantive

- **Intent-phase deferred items — resolution status.** Kill-rate denominator: resolved (cumulative raises including re-raises), and the secondary "confirmed = survived to final quiet round" ambiguity is now documented as a known limitation with a deferral path. Gate-attempt classification under rework: resolved, with an explicit rule that classification keys on park boundaries, not attempt count (pre-park re-runs are first-try). Intra-session token attribution: resolved, with "turn" now defined as one assistant API response and the boundary rule stated (strictly-before to the earlier stage, at-or-after to the later). Provenance-marker format: resolved (exact marker, stripped match, no trailing space). Park-reason form: resolved (free-text string, empty allowed and rendered as a visible "(no reason recorded)" row).

- **B-009 PRD-vs-design divergence is intentional and now labelled.** The PRD frames auto-injection as happening "when the retrospective phase runs"; the design injects per-stage at the state transition because the operator ruled there is no single retrospective phase. The design now states this is a deliberate, recorded supersession of the PRD's phrasing, not an accidental divergence, and shows it still satisfies the underlying requirement (machine-written, agent-independent, marked).

- **Installer changes (gitignore, duplicate-registration removal) are net-new, correctly.** The reviewer noted these are absent from the current `install.sh`. That is expected — they are changes this feature introduces, not existing behavior. The design frames them as additions; behaviors for the capture-directory gitignore and the duplicate-registration removal both have a design home.

- **Behavior-inventory coverage.** All of B-001 through B-017 have a design home: capture gate, hook router, chokepoint, verification persistence, code-review rounds, token harvester, report, ad-hoc invocation, per-stage injection, three levels, default, common schema, stage stamping, retention, duplicate-registration removal, subagent filtering, and state-derived parks/rework are each addressed across the four capability pages and the contracts.

## Minor

- **Retro heading collision possibility.** If the injector and the skill both called the append function with the same plain stage name, two identically-headed sections would result. Addressed: the injector uses the `<STAGE> — metrics` heading, distinct from the agent's plain `<STAGE>` heading, plus the provenance marker.

- **Drift check vs writer-discard were described as one mechanism.** Now separated into two layers: a build/test-time vocabulary assertion (raises in CI) and the runtime writer discard-and-warn (never raises). Recorded in `capture-sources.md`.

- **Overhead claim now has a basis.** The hot-path "well under a second" is replaced with the prototype's measured ~8ms gated-off path plus a couple of stat calls.

- **Retrospective filename reconciliation remains a flagged spec-time item.** The injector's path convention must be reconciled with the existing `<feature>-retrospective.md` naming before implementation; the design names this explicitly (contract IF-D-09) rather than leaving it implicit. Acceptably deferred to spec, not a design blocker.
