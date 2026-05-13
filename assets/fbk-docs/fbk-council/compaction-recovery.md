# Compaction Recovery

This leaf is loaded only when `recovery-check` returns `recovering: true`, indicating the orchestrator's previous context was discarded by auto-compaction. It contains only the READ side of the recovery protocol — the WRITE side (per-phase phase checkpointing via `fbk.py session-state`) lives inline in the SKILL because it must run on every phase regardless of whether a compaction has occurred. Load this leaf once, execute the recovery steps, then resume the session normally.

## Recovery Protocol

1. Run `python3 "$HOME"/.claude/fbk-scripts/fbk.py session-state recovery-check`
2. If `recovering: true`, adopt the returned `session_id` as this session's `SESSION_ID` (so subsequent logging continues under the existing registered session, not a new one)
3. Skip any phase listed in `completed_phases`; resume from the returned `current_phase`
4. Seed each spawned agent with the `transcript_summary` and `key_decisions` fields from the recovery JSON as prior-session context, so agents do not re-deliberate already-resolved questions
5. Acknowledge recovery in output: "Resumed from checkpoint after context compaction"

## State Persistence

The schema below is the READ-side reference for `~/.claude/council-logs/council-state.json`; the SKILL inline checkpoint instruction populates the same file using the same fields.

```json
{
  "task": "Brief task description",
  "iteration": 3,
  "status": "CONTINUE",
  "completed_phases": ["research", "design"],
  "current_phase": "implementation",
  "key_decisions": ["Use JWT auth", "PostgreSQL for storage"],
  "remaining_work": ["Implement API endpoints", "Write tests"],
  "last_updated": "2026-01-24T07:30:00Z"
}
```

## Session Cleanup

Unregister the council session when the session ends:

```bash
python3 "$HOME"/.claude/fbk-scripts/fbk.py session-manager unregister "$SESSION_ID"
```

When outputting `COUNCIL_COMPLETE`, also clean up state:

```bash
python3 "$HOME"/.claude/fbk-scripts/fbk.py session-state cleanup
python3 "$HOME"/.claude/fbk-scripts/fbk.py session-manager unregister "$SESSION_ID"
```
