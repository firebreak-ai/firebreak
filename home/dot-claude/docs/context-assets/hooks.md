Write every hook so a reviewer can determine exactly what it executes by reading the settings file entry alone.
Keep each hook to a single concern with a narrow matcher. A hook that fires on every tool use wastes execution time and may interfere with agent flow.

## Configuration Structure

Define hooks in a `"hooks"` object within `.claude/settings.json` or `.claude/settings.local.json`.

```json
{
  "hooks": {
    "<EventName>": [
      {
        "matcher": "<regex>",
        "hooks": [
          {
            "type": "command",
            "command": "<shell command>"
          }
        ]
      }
    ]
  }
}
```

Use `.claude/settings.json` for hooks the team shares (committed to the repo). Use `.claude/settings.local.json` for personal or machine-specific hooks (gitignored). User-global hooks go in `~/.claude/settings.json` — these fire in every project for that user, so apply the Necessity Test strictly: only include hooks that are correct across all projects.

## Hook Events

Select the event that matches when the hook should fire.

| Event | When it fires | Can block? |
|-------|--------------|------------|
| `PreToolUse` | Before a tool call executes | Yes — deny or escalate to user |
| `PostToolUse` | After a tool call succeeds | No — tool already ran |
| `PostToolUseFailure` | After a tool call fails | No |
| `UserPromptSubmit` | When user submits a prompt | Yes |
| `SessionStart` | When a session begins or resumes | No |
| `Stop` | When the agent finishes responding | Yes — can force continuation |
| `SubagentStart` / `SubagentStop` | When a subagent spawns / finishes | No / Yes |
| `Notification` | When a notification is sent | No |
| `PreCompact` | Before context compaction | No |
| `SessionEnd` | When a session terminates | No |
| `ConfigChange` | When a config file changes mid-session | Yes |
| `WorktreeCreate` / `WorktreeRemove` | Worktree lifecycle | Yes / No |
| `TeammateIdle` / `TaskCompleted` | Team coordination events | Yes (exit code 2 only) |

Use `PreToolUse` for validation and gating (block before the action happens). Use `PostToolUse` for checks, logging, and enforcement after the fact.

## Matcher Patterns

The `matcher` field is a regex matched against the tool name (for tool events) or an event-specific field. Omit `matcher` or use `"*"` to match all occurrences.

Scope matchers as narrowly as possible:
- `"Bash"` — fires only on shell commands.
- `"Edit|Write"` — fires on file modifications.
- `"mcp__memory__.*"` — fires on all tools from a specific MCP server.

Some events (`UserPromptSubmit`, `Stop`, `WorktreeCreate`, `WorktreeRemove`, `TeammateIdle`, `TaskCompleted`) ignore the matcher field and always fire.

## Exit Codes

Exit code 0: success. Claude Code parses stdout for optional JSON output (decision control, context injection). The tool call proceeds unless JSON specifies otherwise.

Exit code 2: blocking error. Claude Code ignores stdout; stderr is fed back as the error message. For `PreToolUse`, this blocks the tool call. For non-blockable events (`PostToolUse`, `SessionStart`), stderr is shown but execution continues.

Any other exit code: non-blocking error. stderr is shown in verbose mode only; execution continues.

Choose one signaling approach per hook: either exit codes alone, or exit 0 with structured JSON. Claude Code only processes JSON on exit 0.

## Command Design

Keep hook commands fast — they execute synchronously and block the agent until they complete (unless `"async": true`).

Use deterministic checks (linters, validators, format checkers, file-existence tests) instead of instructional enforcement. A `PostToolUse` hook running `eslint` on edited files enforces style more reliably than a rule saying "always lint after editing."

Extract logic to a script file when it exceeds a single clear command. Store hook scripts in `.claude/hooks/` and reference them with `"$CLAUDE_PROJECT_DIR"/.claude/hooks/<script>`.

Read JSON input from stdin using `jq` or equivalent. The input includes `tool_name`, `tool_input`, `session_id`, `cwd`, and other context fields specific to the event.

Set `"async": true` for side-effect-only hooks (logging, notifications) that do not need to block the agent.

Set `"timeout"` to limit long-running hooks. Default is 600 seconds for command hooks.

## Decision Control

For `PreToolUse`, return JSON with `hookSpecificOutput` to allow, deny, or escalate:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Blocked by project policy"
  }
}
```

`permissionDecision` accepts `"allow"`, `"deny"`, or `"ask"` (escalate to the user).

For `PostToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStop`, and `ConfigChange`, use top-level `decision` and `reason`:

```json
{
  "decision": "block",
  "reason": "Tests must pass before proceeding"
}
```

To halt the agent entirely from any event, return `{ "continue": false, "stopReason": "reason" }`.

## Security and Auditability

Pin hook commands to specific scripts or binaries with explicit paths. Construct commands from static strings only — e.g., `"$CLAUDE_PROJECT_DIR"/.claude/hooks/validate.sh` instead of inline shell pipelines.

## Scoping

Apply one hook to one concern. Split a hook that validates TypeScript types and also enforces commit message format into two separate hooks.

Scope each hook to the narrowest matching event and matcher. A lint check after file edits belongs on `PostToolUse` with matcher `"Edit|Write"`, not on `Stop` where it fires once per turn regardless of whether files changed.

Use separate matcher groups when the same event needs different handlers for different tools. Two entries under `PreToolUse` — one for `"Bash"`, one for `"Write"` — are clearer than one entry with `"Bash|Write"` running a script that branches internally on tool name.

## Handler Types

`"type": "command"` runs a shell command. Use for deterministic checks, linting, file validation, and logging.

`"type": "prompt"` sends a prompt to a Claude model for single-turn yes/no evaluation. Use when the decision requires judgment rather than a deterministic rule. Include `$ARGUMENTS` as a placeholder for the hook input JSON.

`"type": "agent"` spawns a subagent with tool access (Read, Grep, Glob) to verify conditions before returning a decision. Use when verification requires reading multiple files or searching the codebase.

Use `"command"` when a deterministic check is possible. Use `"prompt"` or `"agent"` only when deterministic logic cannot express the validation.
