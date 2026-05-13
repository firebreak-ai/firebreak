# Ralph Integration

This leaf is loaded only when the orchestrator detects Ralph mode: the state file `~/.claude/council-logs/council-state.json` exists with `status: CONTINUE` and `iteration` below `max_iterations`, or you were invoked via explicit `/ralph-loop` invocation. The leaf documents the multi-iteration checkpointing and exit-marker protocol for running `/fbk-council` inside a Ralph Wiggum autonomous loop. If you are reading this without Ralph context you may have been loaded by mistake — verify the state file before continuing.

## What is Ralph Wiggum?

Ralph Wiggum is an official Anthropic Claude Code plugin that creates autonomous iteration loops using a Stop hook. It:
1. Feeds a prompt to Claude
2. Intercepts Claude's exit attempt
3. Re-feeds the SAME prompt
4. Repeats until a completion marker is detected or max iterations reached

The key insight: **the prompt stays static, but Claude sees its previous work in files and git history**.

## How Council + Ralph Works

```
┌─────────────────────────────────────────────────────────┐
│  /ralph-loop "Run council to design and implement X"   │
│              --max-iterations 10                        │
│              --completion-promise "COUNCIL_COMPLETE"    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Iteration 1: Council deliberates on design            │
│  - Writes decisions to ~/.claude/council-logs/council-state.json    │
│  - Outputs: <!-- COUNCIL_STATUS: CONTINUE -->          │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ (Ralph re-feeds prompt)
┌─────────────────────────────────────────────────────────┐
│  Iteration 2: Council reads previous state, continues  │
│  - Sees design is done, moves to implementation        │
│  - Updates state, outputs: <!-- COUNCIL_STATUS: CONTINUE -->
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ (Ralph re-feeds prompt)
┌─────────────────────────────────────────────────────────┐
│  Iteration N: Council completes final validation       │
│  - Cleans up state file                                │
│  - Outputs: <!-- COUNCIL_STATUS: COUNCIL_COMPLETE -->  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
            Ralph detects completion, exits loop
```

## Usage

**Basic invocation:**
```bash
/ralph-loop "Convene the council to design and implement [TASK].
Read ~/.claude/council-logs/council-state.json for previous progress and continue from there.
When complete, output COUNCIL_COMPLETE." \
  --max-iterations 10 \
  --completion-promise "COUNCIL_COMPLETE"
```

**With specific phases:**
```bash
/ralph-loop "Council task: Build authentication system.

Phases:
1. Research existing patterns (council deliberation)
2. Design architecture (council deliberation)
3. Implement core auth (execution)
4. Implement tests (execution)
5. Final review (council deliberation)

Read ~/.claude/council-logs/council-state.json and continue from last completed phase.
Output COUNCIL_COMPLETE when all phases done." \
  --max-iterations 15 \
  --completion-promise "COUNCIL_COMPLETE"
```

## Guardrails (Mandatory)

| Guardrail | Implementation |
|-----------|----------------|
| **Max iterations** | Always use `--max-iterations` (recommended: 10-20) |
| **Escape hatch** | Create `~/.claude/council-logs/council-abort` to stop gracefully |
| **State checkpointing** | Council writes to `~/.claude/council-logs/council-state.json` each iteration |
| **Stuck detection** | If 3+ iterations with no phase progress, pause and alert |

## Escape Hatches

**To stop a running loop gracefully:**
```bash
touch ~/.claude/council-logs/council-abort
```
The council will complete the current phase, clean up, and exit.

**To pause for human review:**
```bash
touch ~/.claude/council-logs/council-pause
```
The council will complete current work and wait for the file to be removed.

**To force immediate stop:**
```bash
# Cancel the Ralph loop directly
/cancel-ralph
```

## State File Format

`~/.claude/council-logs/council-state.json`:
```json
{
  "task": "Build authentication system",
  "iteration": 3,
  "max_iterations": 10,
  "status": "CONTINUE",
  "completed_phases": [
    {"name": "research", "iteration": 1, "summary": "Reviewed OAuth2, JWT patterns"},
    {"name": "design", "iteration": 2, "summary": "Decided on JWT with refresh tokens"}
  ],
  "current_phase": "implementation",
  "key_decisions": [
    "Use JWT with RS256 signing",
    "15-minute access token expiry",
    "Refresh token rotation on each use"
  ],
  "remaining_work": [
    "Implement token generation",
    "Implement token validation middleware",
    "Write integration tests"
  ],
  "files_modified": [
    "src/auth/jwt.ts",
    "src/middleware/auth.ts"
  ],
  "last_updated": "2026-01-24T08:00:00Z"
}
```

## Best Practices

1. **Clear completion criteria**: Define exactly what "done" means in your prompt
2. **Phased approach**: Break complex tasks into named phases
3. **Scope constraints**: Include what's OUT of scope to prevent drift
4. **Checkpoints**: For very long tasks, include "pause after phase X for review"

## When to Use Ralph + Council

**Good for:**
- Multi-phase feature implementation (design → implement → test → review)
- Complex refactoring requiring deliberation at decision points
- Tasks where you want to "sleep on it" and resume tomorrow
- Exploratory work where scope may evolve across iterations

**Not good for:**
- Quick one-off questions
- Tasks requiring constant human judgment
- Time-sensitive work where you can't wait for iterations
- Tasks with unclear success criteria

## Monitoring Progress

Check current state:
```bash
python3 "$HOME"/.claude/fbk-scripts/fbk.py session-state show
```

View iteration history:
```bash
ls -la ~/.claude/council-logs/
```

Quick status (pipes the JSON emitted by `show` through `jq`):
```bash
python3 "$HOME"/.claude/fbk-scripts/fbk.py session-state show \
  | jq -r '"Iteration \(.iteration): \(.current_phase) - \(.status)"'
```
