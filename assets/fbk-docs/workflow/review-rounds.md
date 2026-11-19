# Durable standalone review rounds

[Begin and execute](#begin-and-execute) · [Code-review artifacts](#code-review-artifacts) · [Imported evidence](#imported-evidence) · [Completion and recovery](#completion-and-recovery)

Use `review-round` for standalone review. Managed acceptance uses `phase-close`;
standalone completion never changes it. Resolve `firebreak_dir` as described in
the calling skill. Run commands from the reviewed project root.

## Begin and execute

Save complete instructions under `.fbk/runtime/`: each contributor's role, intent,
lens, governing references, required checks and output contract. Workers do not
inherit the calling skill. Keep the human report under `.fbk/runtime/reports/`
so report updates do not change the reviewed source snapshot. Discover check
commands before beginning; execute them only after the round exists, through the
Detector's investigation requests and evidence-bearing continuation. Declare every
contributor before launch:

```bash
python3 "$firebreak_dir/fbk-scripts/fbk.py" review-round begin --root "$PWD" \
  --instructions .fbk/runtime/code-review-instructions.txt \
  --contributors detector challenger --required README.md \
  --code-review detector challenger \
  --lens "$firebreak_dir/fbk-docs/fbk-review-lenses/code-lens.md" \
  --preset behavioral-only --min-severity minor
python3 "$firebreak_dir/fbk-scripts/fbk.py" review-round run --round ID --contributors detector
python3 "$firebreak_dir/fbk-scripts/fbk.py" review-round run --round ID --contributors challenger
```

Use the returned round ID. The code-review binding identifies roles explicitly and
captures the lens, preset, threshold and pipeline identity in the contract. Omit
those code-review options for generic review rounds. Independent contributors may share a batch; dependent
contributors run after their inputs are complete. Use distinct names for parallel
slices. The returned contract, source manifest and `snapshot_path` identify the
immutable review source. Review that snapshot, not the advancing checkout.
`--required PATH` includes governing artifacts otherwise excluded from discovery;
do not silently truncate or omit sources. When edits are already authorized,
record their concrete file scope with repeatable `--scope PATH` at `begin`.
This records permission already given; late registration cannot expand it.

`run` creates contributor workspaces, captures full JSON responses and publishes
result envelopes with runtime execution receipts. Read the returned result paths;
agent messages are retrieval hints, not the sole findings record. Do not construct
or edit those envelopes yourself. Transport completeness does not establish finding
semantics: apply the calling skill's validation and challenge pipeline. Even with
zero candidates, every declared contributor must return its complete inspection
result.

For a test review, use the test lens with `--lens-only` to omit the code-domain
preset. Its Detector returns `{findings, coverage}` as specified by that lens.
The runtime validates the coverage shape and retains it in the Detector result;
only the findings enter normalization and challenge. This validates an inspection
record's structure, not the truth or completeness of coverage claims.

## Code-review artifacts

For a bound code review, `run` applies the existing pipeline between the roles:
validate/filter Detector sightings, retain full kept records, and give the
Challenger only normalized candidates and the immutable cited sources. It then
validates verdicts, rejoins them with the kept records and validates merged
classifications. The Challenger never receives raw Detector framing or imported
claims as a shortcut around that neutral handoff.

Read the Challenger's `result_path` for the complete merged finding array, including
unresolved findings. Use its zero-based indices for remediation declarations; do
not replace it with a filtered report array. Its `provenance.response_path` retains
execution evidence whose `pipeline` object contains `native_response`, `kept`,
`normalized`, `confirmed`, `diagnostics` and `detector_artifact_digest`. Use those records for
pipeline warnings, report filtering and traceability. Convert the confirmed array
with `pipeline to-markdown` for presentation; retain unresolved findings separately.
Native verdicts and original sightings remain available without manual republishing.

## Imported evidence

`review-round submit --round ID --result PATH` imports supporting evidence only.
It cannot complete a contributor, even during an active launch. A runtime-launched
reviewer must independently assess the import. The runtime checks imported and completed peer artifacts before supplying them
to consumers. The bound Challenger receives only the neutral handoff described
above. Manually importing an artifact does not give it execution provenance.

For an external adapter, `PATH` is a complete JSON envelope:

```json
{
  "schema": "review-contribution-v1",
  "round_id": "ROUND_ID",
  "contract_id": "CONTRACT_ID",
  "contributor": "detector",
  "status": "complete",
  "result": [],
  "result_digest": "SHA256_OF_CANONICAL_RESULT"
}
```

Compute the digest from UTF-8 `json.dumps(result, sort_keys=True,
separators=(',', ':'), ensure_ascii=False)`. Publish atomically, retain the full
artifact, and grant external writers access only to their result file. The
`status` field describes the imported response; it does not satisfy the round gate.

## Completion and recovery

Run `review-round require-complete --round ID` before remediation and before
reporting post-fix closure. A nonzero exit means stop. Missing, failed, invalid,
stale or manually imported contributions cannot authorize completion. Neither can
unresolved investigations, pending verification, unaccounted changes, active
execution or exhausted budgets.

| Situation | Action |
| --- | --- |
| Interrupted or uncertain progress | Inspect `review-round status --round ID`. Use `fail --round ID --contributor NAME --reason TEXT` to record a failed worker. |
| Same sources, instructions and configuration | Use `resume --round ID --instructions PATH`; run only returned `missing` contributors. Completed results and consumed budget are retained. |
| Interrupted execution reservation | After confirming old processes stopped, use `recover --round ID --reason TEXT`. Recovery refuses while recorded process groups still run. |
| Exhausted budget | Stop and ask the human for help. Only explicitly authorized `extend --round ID --reason TEXT --rounds N` adds budget. Abandonment does not fabricate missing results. |
| Changed source during review | Retain findings as historical evidence and report the persisted `unexpected-source-change` diagnostic: paths, original/current revision and detection time. Review current sources before fixing or claiming acceptance. |
| Authorized remediation or changed contract | Begin a current snapshot round with `--previous ID`, preserving cumulative budget and prior references. The predecessor cannot accept further work. |

A batch charges shared active wall time once across parallel workers and records
aggregate worker execution/usage separately. Idle time between batches is excluded.
`review_round_timeout` sets the full active allowance (default 9999 seconds);
per-session turn/time limits still apply and their breach is an ordinary failed
attempt. Clearing context,
relaunching a worker or beginning a follow-up does not replenish the budget.

Interruption cancels tracked command groups before execution becomes idle. If
termination is unconfirmed, the round stays active with its remaining reservation
charged and process groups recorded. Unknown interrupted work consumes that
reservation; a recovered controller's late result cannot refund its successor.

Use `investigations.md` for bounded probes and `remediation-verification.md` for
material-fix registration, independent verification and late registration recovery.
Carry unresolved findings into follow-ups and justify their scope from affected
behavior and related paths, expanding beyond changed lines when necessary.

These are cooperative CLI gates. They detect source/result tampering and require
runtime provenance for completion; they do not control unrelated host tools or
external edits. Tool permissions and external effects remain the host's responsibility.
