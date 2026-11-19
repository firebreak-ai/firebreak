# Independent remediation verification

Register material fixes before editing, using a completed current review round.
This records the existing user-authorized scope; it does not request routine new
approval or grant permission for new behavior, broader architecture, or external effects.

```bash
python3 "$firebreak_dir/fbk-scripts/fbk.py" remediation declare \
  --round ROUND_ID --request .fbk/runtime/fix-declaration.json
```

Declaration example (paths are concrete repository-relative files):

```json
{
  "id": "resource-release",
  "finding": {"contributor": "challenger", "index": 0},
  "behavior": "Cancellation releases the allocated resource exactly once",
  "requirements": ["spec.md#cancellation"],
  "scope": ["src/worker.py", "tests/test_worker.py"],
  "siblings": ["src/worker.py"]
}
```

The finding reference is a zero-based index into a completed contributor's result
array (or its `findings` array), with `status: verified` or `confirmed`. Preserve
verified findings in that artifact; registering a remediator's unreviewed claim is
not sufficient. Record all known relevant sibling paths, including outside-scope
sites that need an explicit disposition.

Apply the authorized fix. Begin its fresh review with `review-round begin
--previous ROUND_ID`; justify affected behavior and related paths in its instructions.
The runtime carries the declaration and consumed investigation budget forward,
compares actual snapshots, and creates a pending verification obligation. It does
not require a post-fix passing check before the fix can be written.

Run the independent verification:

```bash
python3 "$firebreak_dir/fbk-scripts/fbk.py" remediation verify \
  --round POST_FIX_ROUND_ID --id resource-release
```

Firebreak launches a fresh verifier through the bounded investigation executor in
a disposable source copy. Its assignment includes the accepted behavior, verified
finding, authorized scope and sibling obligations. When verifying the material fix,
read `../review/remediation-verification.md` for behavioral and regression evidence.
Preserve execution logs and defective source for the runtime's verification record.

The runtime requires the verifier's complete `verification.json`: revision and fix
identities, behavioral assessment, fixed/defective commands and exit codes, exact
log evidence, defective-source artifact, sibling dispositions and limitations.
It checks artifact integrity, quotations, completeness and freshness. The fresh
verifier judges semantic sufficiency; hashes or green execution alone cannot do so.
The remediator cannot submit its own report through this command as independent
verification. Retries use the existing investigation budget and human escalation.

The verifier may also answer `rejected`. That is a verdict, not a malformed report:
the runtime still requires the assessment, the `rejected_behavior` text, limitations
and an attributed behavior-evidence quotation, but not the red/green exit codes,
defective source or sibling accounting, since nothing is being accepted. The
remediation is recorded with status `rejected` and the verifier's `rejected_behavior`
text, the command reports "not accepted: independent verifier returned rejected:
<rejected_behavior>", and the round still cannot complete until a fix is verified.
A report missing the structural fields is rejected as invalid, as before.

A post-fix review cannot pass `review-round require-complete` while declared material
fixes lack valid independent verification. Changed paths outside their declared
scope also require explicit reviewed accounting. A completed fresh contributor may
return an object with `findings` (its normal array) and `change_accounting`, for example:

```json
{
  "findings": [],
  "change_accounting": [
    {"path": "README.md", "classification": "nonmaterial", "reason": "Corrected a spelling error; no promised behavior changed"}
  ]
}
```

Feed the `findings` array through the normal finding/verdict pipeline. Accounting is
a review judgment, not the remediator's permission to label a functional change
nonmaterial. Unaccounted changes block completion; omitting a material declaration
does not silently bypass verification. If review identifies an undeclared material
fix, recover the missed registration against the original snapshot before completion.

For this recovery, the original `review-round begin` must have captured the existing
authorized file scope with `--scope PATH` options. Save the declaration fields above
plus `original_round` (the pre-fix ancestor round) and a concrete `reason` explaining
the missed registration, then run:

```bash
python3 "$firebreak_dir/fbk-scripts/fbk.py" remediation register-late \
  --round POST_FIX_ROUND_ID --request .fbk/runtime/late-fix-declaration.json
```

The runtime verifies the original finding, intact pre-fix snapshot, round ancestry,
actual changes and scope containment. It flags the missed registration durably and
creates the same independent verification obligation. It preserves consumed budgets
and correct implementation; no rollback is required for ceremony. Missing original
scope or a proposed expansion is refused rather than treated as new approval. Resolve
that authorization/evidence gap explicitly with the human; do not label the fix
nonmaterial to bypass it.

These controls govern Firebreak's protocol; arbitrary host tool calls remain subject
to host permissions. Use `review-round run` for ordinary contributors: it charges their shared active wall clock. Investigation and verifier execution is also bounded; arbitrary host-spawned work bypasses those controls. Managed phase
acceptance remains separate and uses `phase-close`.
