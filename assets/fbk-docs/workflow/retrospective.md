Use in every phase to append the model's own observations, and when examining completed or interrupted work. Retrospective recording is required throughout the workflow. Build explanations from recorded evidence and identify uncertainty.

Run `retrospective <unit>` to get a bounded evidence index and capture health. Follow its section and entry references for the relevant phase, attempt, worker, repair, or observation. Read original sources when needed to test an explanation. Keep the unit's request files and temporary analysis exports under `.fbk/runtime/<unit>/`; the durable observation and improvement records live in the unit state.

Append observations as work happens, including failed review attempts before retrying. After each phase is accepted, append a concise account of that phase and its review outcome: what worked, material friction or rework, and lessons or uncertainty supported by the evidence. A clean phase can record a useful successful approach and the absence of observed friction; it does not need an invented problem or improvement proposal. The model authors these entries without asking the human to supply or approve them.

`status`, `continuation`, and this command expose pending phase observations with their exact acceptance `event_id`. Use `observation-record` with `detection_phase` naming that phase and `evidence` containing that event reference. Add original references for any other claims. Acceptance remains recorded, but phase entry and further closure require these observations, and final unit completion stays pending until they are recorded. Reopening and re-closing a phase needs a new entry citing the new acceptance; earlier entries remain immutable. Existing runs expose missing phase observations for backfill from retained evidence, with uncertainty about anything not recorded.

For an oversized historical entry, add `--pointer` to select the exact nested field. For example, select a phase entry, then use `/value/rounds/0/result/review/findings/0` for its first round's first finding. Pointer array indexes start at zero, and a negative index counts from the end, so `/value/rounds/-1` is the phase's latest review round. The command's entry `--index` starts at one. When the selected evidence is still too large, the omission lists the entry's children and, for a phase entry or a list, a `suggested_pointers` list with a `next` command that reaches the rounds and the last round in one step. `--max-chars N` raises or lowers the output bound (2000 to 100000, default 12000) when a whole entry is needed at once.

A section index lists entries oldest-first, so index 1 is the earliest event. Long sections are paged: a truncated page carries a `next` command naming the exact `--offset` that continues it, and its absence means the page is the last. `--offset N` skips the first N entries; `--offset -N` starts N entries before the end, which reaches the latest events of a long unit in one call.

Treat workflow events as recorded actions and outcomes. Treat reviewer judgments, worker checks, question classifications, and agent observations as attributed claims. An emitted context packet is not proof that the receiver read or understood it. Capture counts describe observed events; disabled, capped, missing, or failed capture does not establish zero events. Unit attribution can be unknown when multiple units are active.

Record an observation through `observation-record <unit> --request <file>` using a repository-relative JSON request:

```json
{
  "id": "intent-requested-future-tests",
  "observation": "Intent review requested tests that belong to implementation.",
  "evidence": [{"event_id": "<copy the event reference from retrospective>"}],
  "suspected_cause": "The review objective may not distinguish current prerequisites from later deliverables.",
  "uncertainty": "This attempt alone does not establish whether the prompt or model variability caused the error.",
  "category": "phase-context",
  "detection_phase": "intent"
}
```

Use an existing event reference or a file reference with its content hash; add inclusive `start_line` and `end_line` for a precise file excerpt. Source hashes detect later changes, not truth. Record observations while evidence is available, including a failed attempt before retrying. Use a new observation id for a correction and cite the earlier observation; preserve the original account.

Add `origin_phase` only when evidence supports which earlier phase missed the issue. For an observed human question, optional `human_question` contains `classification`, `reason`, and `decision_refs` naming relevant recorded decisions. Classifications are necessary, unnecessary, already-settled, unresolved, or unknown. Explain the judgment; counts alone do not establish whether asking was warranted. Preserve the question in a cited source when its wording matters. Record these optional fields when the incident warrants them; the phase observation itself is always required.

For improvement analysis, use `/fbk-improve <unit>`. Carry forward the relevant evidence references and open explanations, then load `improvement.md`. An unchanged historical file reference remains useful evidence; a changed or unavailable one requires checking the original source before drawing a conclusion.

For a structural defect discovered after design/spec, clearly identify the late discovery, affected responsibility, concrete maintenance risk, and correction. Trace it to the earliest evidenced missed decision or verification obligation using accepted artifact/event references. Set `origin_phase` to design or spec only when those sources support that attribution; an implementation departure from a sound design is an implementation issue. Missing history warrants uncertainty, not inferred upstream blame. Passing tests do not erase a structural defect.

A local structural correction stays in implementation when it preserves accepted architecture and contracts. Reopen an earlier phase only when the correction changes an accepted architectural decision or contract; use the existing reopening and approval flow. Recording a missed review opportunity does not itself require reopening.
