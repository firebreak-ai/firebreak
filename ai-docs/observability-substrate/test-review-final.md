Verdict: accepted

## Rationale

The two previously-blocking gaps are now covered by real tests with genuine catching power. The full suite runs 520 tests; all pass. No Tier 1 violations exist in the in-scope test files. The acceptance criteria coverage is sufficient to gate this release.

---

## Previously-blocking findings — now resolved

### Finding A — Harvest refusing to overwrite an unreadable existing record

**Status: resolved.**

`tests/test_harvest_idempotent.py :: TestUnreadableExistingRecordRefused :: test_corrupt_existing_record_is_not_overwritten`

The test writes a valid record on the first harvest, overwrites the file with known corrupt bytes, advances the mocked clock to a different value, then calls `harvest()` again. It asserts two things: `second.error` is truthy, and the file on disk still contains the exact corrupt bytes written by the test.

Catching power verified by reasoning: if the `except (OSError, json.JSONDecodeError)` refusal block (harvest.py lines 610–618) were removed so that harvest fell through to re-derive and write a fresh record, `second.error` would be `None` (first assertion fails) and the file on disk would contain valid JSON, not `corrupt_bytes` (second assertion fails). The test would go red on either assertion. The test is not vacuous.

The test avoids `chmod 0o000` in favour of writing unparseable bytes, which is a sound choice — it makes the failure mode deterministic across Linux and CI environments where root-owned test processes can read through permission bits.

### Finding B — Unreadable transcript forces `truncated` completeness

**Status: resolved.**

`tests/test_harvest_completeness.py :: TestUnreadableTranscriptForcesTruncated :: test_unreadable_transcript_yields_truncated`

The test creates a two-agent run where both agents have journal results (normally sufficient for `clean-complete`), then removes one agent's transcript file from disk before calling `harvest()`. It asserts `result.completeness == "truncated"`.

Catching power verified by reasoning: if the `all_transcripts_readable` condition (harvest.py lines 680–685) were removed so that completeness depended only on `all_have_results`, both agents have results, so `clean-complete` would be returned and the assertion would fail. The test would go red. The test is not vacuous.

Transcript path consistency confirmed: `make_workflow_run` writes transcript files as `agent-{agent_id}.jsonl`; with `agent_id="agent-beta"` the path is `agent-agent-beta.jsonl`. The test removes exactly that path. No fixture mismatch.

---

## Tier 1 evaluation (full suite)

**Criterion 1 (silent failure detection): PASS.** No test asserts only the absence of failure. Both new tests pair error/no-overwrite assertions with positive checks.

**Criterion 2 (stale failure annotations): PASS.** No `xfail`, `expectedFailure`, or equivalent annotations in any in-scope test file.

**Criterion 3 (empty gate tests): PASS.** Both new tests contain multiple assertion calls.

**Criterion 4 (advisory assertions): PASS.** No behavioral check result is logged or printed without a corresponding assertion.

---

## Remaining advisory items (non-blocking)

### Finding C — No test for PostToolUse with a non-Workflow tool name being a no-op

**Status: unchanged, advisory.**

No test passes a `PostToolUse` payload with `tool_name="Bash"` and asserts no record is written. A non-Workflow PostToolUse containing a workflow directory path is implausible in production, but the correctness gate is unanchored. This should be addressed before the next minor release.

### Finding D — Schema version not asserted in harvest output

**Status: unchanged, advisory.**

`TestSchemaVersionPresence` in `test_record_extensibility.py` reads a hand-written fixture file and asserts `schema_version == "1.0"`. It does not call `harvest()`. A change to `_assemble_record` that emits the wrong version or omits the key would not be caught by this test. The integration tests that read written records would catch a missing key only incidentally. A targeted assertion on `schema_version` in a record produced by `harvest()` would close this gap cleanly.

---

## AC coverage summary

| Behavior | Covered | Notes |
|---|---|---|
| Shape vocabulary | Yes | `test_shapes.py` — specific membership and None-identity checks |
| Attribution parse | Yes | `test_harvest_attribution.py` + forgery integration test |
| Roster join, round-trip | Yes | `test_harvest_join.py`, `test_harvest_roundtrip.py` |
| Completeness — missing result | Yes | `TestTruncatedRun` |
| Completeness — unreadable transcript | Yes | `TestUnreadableTranscriptForcesTruncated` (new) |
| Idempotency — readable record no-op | Yes | `TestFinalizedNoOpPreservesHarvestedAt`, `TestFinalizedNoOpPreservesAttributedContent` |
| Idempotency — unreadable record refusal | Yes | `TestUnreadableExistingRecordRefused` (new) |
| Finalization triggers | Partial | Workflow + SessionStart covered; non-Workflow gate untested (advisory) |
| Reader rendering / determinism | Yes | `test_run_retro.py` |
| Dispatcher registration | Yes | `test_dispatcher.py` |
| Schema version / extensibility | Partial | Version only asserted in fixture, not harvest output (advisory) |
| End-to-end conformance | Deferred | Manual UV; no automated test per spec |
| Token accessor | Yes | `test_token_accessor.py` |
| Redaction parity | Yes | `test_harvest_redaction.py` |
| Confinement / temp names | Yes | `test_harvest_confinement.py` |
