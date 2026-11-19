Use for routine corrections supported by already settled intent. Apply a bounded correction under existing sourced authorization and validate its evidence.
Changes to desired behavior, scope, tests, or competing authoritative decisions use the normal rework/approval path in `recovery.md`.

## Standing authority

Capture the human's existing repair authorization in an immutable source file as described in `decisions.md`. Record only the classes it actually covers:

```json
{"classes": ["reference", "contradiction"], "source": {"path": ".fbk/cancellation/decisions/repair-authority.md", "quote": "Correct mechanical references and contradictions where my intent is already clear without asking again."}}
```

Run `repair-policy <unit> --request <policy-file>`. An empty classes array revokes the policy. A repair policy authorizes these bounded operations; it does not authorize implementation, test unlocks, changed requirements, or accepting unresolved findings.

## Mechanical reference repair

Write a request and run `repair <unit> --request <request-file>`:

```json
{"kind": "reference", "path": ".fbk/cancellation/spec.md", "before": "[Cancellation](#old-cancellation)", "after": "[Cancellation](#cancellation)"}
```

The deterministic proof requires an actual Markdown link outside code, a broken old fragment, the same local target and label, and exactly one matching simple heading. Other reference formats require ordinary rework until a suitable deterministic validator exists. The size of a patch does not establish semantic equivalence.

Previously current acceptance can be preserved only when this proof succeeds and every other accepted input and supporting source remains current. The journal records the exact patch and before/after hashes. Original review evidence remains attributable alongside the mechanical repair record.

## Contradiction against settled intent

Record the applicable sourced decision first, then submit a narrow prose replacement:

```json
{"kind": "contradiction", "path": ".fbk/cancellation/spec.md", "before": "Retry release after failure.", "after": "Propagate the failure without retrying release.", "decision_id": "release-once"}
```

A fresh read-only checker examines the source and proposed replacement. It must establish fidelity to the already settled decision. It answers `equivalent`, `rejected` (changed intent or unsupported inference) or `insufficient_context` (evidence missing). Only `equivalent` applies the repair. The other two are honest verdicts, not failures: the file is left untouched and the command reports "Repair not applied: verifier returned <verdict>: <the verifier's evidence>" so the operator knows why. This is model evidence, so the affected phases lose acceptance and must be reviewed again. Review attempts remain recorded. The policy avoids another human question for an already authorized correction; it does not convert a model's equivalence claim into preserved semantic acceptance.

Routine repairs target requirement/design/spec prose or declared documentation. Code and locked tests retain their existing scope and approval controls. Retrieve missing existing sources automatically; ask only when authority or desired behavior remains unresolved.

## Interrupted repair

The runtime records pending repair and invalidates affected acceptance before changing the file. Other phase operations pause until the journal is resolved. Run `recover-repair <unit> --reason "<what was interrupted>"`. Recovery completes only the recorded patch against unchanged authority and source evidence; unexpected edits or changed sources abandon the repair while leaving acceptance invalid. It never overwrites an unknown newer edit.
