# Grilling log — intent: deterministic metrics plane (hook harvesting)

Interview record for the intent phase. Seed: `firebreak-instrumentation-brief.md`.
Each decision below was reflected back to the operator and confirmed.

---

### v1-scope-router-in-or-out
- Question: The brief contradicts itself — the non-goal section says no new Claude-level hooks in v1, but the global-install and capture-level sections describe shipping a globally-armed hook router. Which is v1: Python-layer instrumentation only, or Python layer plus the hook router?
- Recommendation: Python-layer only for v1; defer the router to a fast-follow, because it carries the privacy, retention, and capture-level complexity and the core acceptance-sketch metrics are derivable from the state engine and audit log without it.
- Answer: Include the hook router in v1.
- Confirmed: Yes — v1 ships both the Python-layer instrumentation (dispatcher-chokepoint event logging, TaskCompleted result persistence, code-review round counts, the report command, schema discipline) and the globally-armed, per-project-gated Claude-level hook router with configurable capture levels. The privacy gating, retention policy, and capture-level taxonomy are therefore all in scope.

### report-invocation-timing
- Question: When does the report command run in the SDL — retrospective stage only, or also runnable mid-pipeline?
- Recommendation: Runnable ad-hoc at any point AND auto-injected into the retrospective from code, since the prototype already runs standalone and auto-injection keeps the agent interpreting rather than recording facts.
- Answer: Anytime plus auto-inject at retro.
- Confirmed: Yes — the report is runnable ad-hoc at any pipeline point for spot checks, and is auto-injected into the retrospective from code so the agent interprets the table instead of recording the numbers.

### token-cost-harvest-scope
- Question: Is post-hoc token/cost harvesting (the transcript harvester) part of v1 or a later increment?
- Recommendation: In v1 — it is built and tested, tokens-per-stage is named in the acceptance sketch, and it is post-hoc Python that joins to stages via state timestamps with no new hooks.
- Answer: In v1.
- Confirmed: Yes — post-hoc token/cost harvesting ships in v1, run at retrospective time and joined to stages via state-engine timestamps.

### capture-level-taxonomy
- Question: Ship three capture levels (off / standard / full), with the shipped default deferred to an empirical observation during development?
- Recommendation: Ship three levels; do not pre-split standard; defer the default until observation shows which signals the report and improve loop consume.
- Answer: Ship three levels, but commit the shipped default now rather than deferring it.
- Confirmed: Yes — three levels (off; standard = lifecycle, failures, subagent results, chokepoint events; full = every event with payloads). The shipped default is committed in this phase rather than decided later.

### shipped-default-capture-level
- Question: With the default committed now, which level is on by default inside a Firebreak-managed project (uninstrumented projects stay off regardless)?
- Recommendation: standard — the lean profile gives a working metrics plane out of the box at ~9% of full's volume with no prompt or tool-payload capture; the operator opts up to full when debugging.
- Answer: standard.
- Confirmed: Yes — standard is the shipped default in Firebreak-managed projects; full is a deliberate opt-up; off is available everywhere.

### retention-rotation-policy
- Question: The capture file grows per project. What is v1's retention/rotation policy?
- Recommendation: No automatic rotation in v1; the capture directory is gitignored and pruned by the operator or a cross-project sweep; revisit only if volume bites.
- Answer: Ship a size/age cap in v1.
- Confirmed: Yes — the events file self-prunes via an automatic size or age cap in v1, so it does not grow unbounded without operator action. The exact threshold and mechanism are a design-phase detail.

### privacy-consent-model
- Question: Confirm the consent model — globally armed, per-project gated; capture lands project-local in a gitignored directory, never in the global config dir; full-only captures prompt text; only in instrumented projects.
- Recommendation: Confirm as a standing constraint and record it in the decisions log and architecture overview.
- Answer: Confirm as standing constraint.
- Confirmed: Yes — the router is installed globally but exits immediately unless the project is Firebreak-managed or carries an explicit capture marker; capture always writes to the project's gitignored capture directory and never to the global config directory; prompt text is recorded only at full capture and only in instrumented projects. This is a governing constraint for the feature.

---

## Leans recorded for the design phase (not re-grilled at intent)

These design-level questions from the brief were given a recommended direction and deferred to `/fbk-design` rather than resolved here:

- **Single queryable event stream with a shared envelope.** Lean: one events stream with a shared envelope schema and event-type vocabulary across the router and the dispatcher chokepoint, so the report joins both. Path/store reconciliation (the existing per-spec audit log vs. the project-local capture file) is a design decision.
- **Gate results as a summarized envelope.** Lean: capture a summarized result envelope rather than verbatim gate finding lists, which can be long.
- **Stage stamp written at log time.** Resolved by the experiment — stamping `{spec, stage}` at hook-fire time worked end-to-end and is unambiguous under interleaving. Design confirms the one fail-silent state-file read.
- **Code-review round logging in the gate.** Lean: round counts are logged from the deterministic code-review gate (which sees the JSON artifacts), not from agent-mediated skill instructions.
- **Capture setting is project-local.** Lean: the capture level and enable marker live project-local and sandbox-writable; whether that is a standalone marker file or a key in Firebreak's project config surface is a design choice.
- **Remove the experiment's router registration.** When the global install ships, any project-level router registration from the capture experiment must be removed, or the global and project hooks both fire and events duplicate.
