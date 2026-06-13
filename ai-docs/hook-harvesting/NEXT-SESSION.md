# Next-session runbook: capture-run verification

> **STATUS UPDATE 2026-06-10 (later same day): steps 1–4 COMPLETE.** Tim merged the hook config; the router is live and verified (27+ events captured). Reference doc updated with verified payload tables — 9 event types confirmed, with several doc divergences documented (`tool_response` vs `tool_output`, no size fields, undocumented `effort` and `last_assistant_message` fields, PostToolUseFailure fires on nonzero Bash exit). Remaining: step 5 quirks stand; step 6 (Firebreak brief → `/fbk-intent`) still pending; unobserved events (Stop, PreCompact, Notification, PermissionRequest, TaskCompleted, CwdChanged) will accumulate in `.fbk-capture/events.jsonl` during normal use — check back after a few sessions.

**Written:** 2026-06-10, end of the harness-observability build session.
**For:** Tim + a fresh Claude session in `/opt/code`.
**Goal:** Activate the universal hook router, capture one session of real hook traffic, verify the field-level claims in `harness-observability-reference.md`, and update that doc from observed reality.

## State as of handoff

| Artifact | Status |
|---|---|
| `harness-observability-reference.md` | Written. Hook field tables are doc-derived, **flagged unverified**. |
| `hooks/hook_router.py` | Written, untested live (hooks weren't active this session). Appends full event payloads to `.fbk-capture/events.jsonl`; stage-stamps from `.claude/automation/state/` when present; fail-silent; never writes stdout. |
| `hooks/settings-hooks-snippet.json` | Inert. Claude was **denied** writing `.claude/settings.json` directly (auto-mode self-modification gate). **Human step required — see step 1.** |
| `transcript_harvest.py` | Written and **tested against real transcripts** (multi-session, subagents, JSON mode all verified). |
| `firebreak-instrumentation-brief.md` | Intent seed for the Firebreak-side work. Carry into the Firebreak project; not actionable from this sandbox (fbk-scripts is mounted read-only here). |

## Steps

1. **(Tim, manual)** Copy the `hooks` object from `hooks/settings-hooks-snippet.json` into `/opt/code/.claude/settings.json` (create the file with that content if absent). Start a fresh Claude session in `/opt/code` — hooks load at session start.
2. **(Fresh session)** Generate varied activity: a few Bash/Read/Edit/Write calls, at least one failing command (PostToolUseFailure), spawn a subagent (SubagentStart/Stop), and ideally trigger a permission prompt.
3. Inspect `.fbk-capture/events.jsonl`:
   - Which registered events actually fired? Which never appeared? (Registered set: see snippet — 15 events. Events the docs call "SDK-only" may still fire in the CLI; `TaskCompleted` demonstrably does in Firebreak.)
   - For each observed event, diff actual payload fields against the tables in `harness-observability-reference.md`. Update the doc; remove the "unverified" flag per verified section, and record any settings-validation warnings about unknown event names.
4. Cross-check the router against the harvester: `python3 transcript_harvest.py --project ~/.claude/projects/-opt-code` on the capture session — hook executions visible in the transcript (`system` records) should correspond to router appends.
5. Known data quirks already observed (from harvester testing on real transcripts, 2026-06-10):
   - Subagent transcript records carry `isSidechain: true`, so subagent turns appear under `sidechain_turns`, not `turns`.
   - `durationMs` on hook-execution `system` records read 0 in observed data — verify whether it populates for command hooks.
   - `usage.iterations[]` exists inside assistant usage (per-iteration token splits) — unexplored, possibly useful.
   - No `cost_usd` field in observed transcripts (docs claimed one); harvester deliberately reports tokens only.
6. **(Later, Firebreak project)** Take `firebreak-instrumentation-brief.md` into the Firebreak dev environment and run it through `/fbk-intent`.

## Orientation pointers for the fresh session

- Read `harness-observability-reference.md` first — it is the distilled context from the prior session (the why, the metrics map, the Firebreak plumbing audit).
- Memory index has pointers: harness-observability reference, workflows-deterministic-runner correction.
- The capture file may get large (PreToolUse+PostToolUse on every call, payloads truncated at 20k chars/field). Delete `.fbk-capture/` between runs if you want a clean sample.
