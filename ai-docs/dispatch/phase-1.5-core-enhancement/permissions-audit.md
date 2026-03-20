# Permissions Friction Audit

## Source material

- `home/dot-claude/settings.json` — current hook configuration
- `home/dot-claude/settings.local.json` — does not exist
- Skills: `/spec`, `/spec-review`, `/breakdown`, `/implement`
- Agent: `test-reviewer`
- Hooks: `spec-gate.sh`, `review-gate.sh`, `breakdown-gate.sh`, `task-reviewer-gate.sh`, `task-completed.sh`

## Allowlist state

`settings.json` contains one entry: the `TaskCompleted` hook command. There are no `permissions`, `allowedTools`, or `allowlist` keys. The effective allowlist is empty.

Consequence: every tool call that Claude Code routes through the permissions layer generates a user-visible prompt unless the user has previously approved that exact call pattern in their session. Auto-approved vs. user-approved calls are indistinguishable in agent output, so prompt frequency can only be predicted from static analysis of the tool call patterns in each stage.

---

## Predicted prompt map

The table below lists every tool call pattern identified from static analysis. "Covered" means a matching allowlist rule exists in `settings.json`. Since the allowlist is empty, every row is "No".

Reason codes used in the final column:
- **NO-ALLOWLIST** — No `allowedTools` / `permissions` block in `settings.json` at all.
- **SHELL-GLOB** — The command path contains a variable or wildcard; even if an allowlist rule existed, it would require a glob pattern that is not present.
- **SHELL-EVAL** — The command is constructed at runtime via variable expansion; a static rule cannot pre-match it.

### Stage 1 — Spec (`/spec`)

| Tool | Command / Path | Covered by allowlist rule | If no — why not |
|------|---------------|--------------------------|-----------------|
| Write / Edit | `ai-docs/$ARGUMENTS/$ARGUMENTS-spec.md` (create or iterate) | No | NO-ALLOWLIST |
| Write / Edit | `ai-docs/$ARGUMENTS/$ARGUMENTS-overview.md` (project-level scope) | No | NO-ALLOWLIST |
| Bash | `"$HOME"/.claude/hooks/sdl-workflow/spec-gate.sh <spec-path>` | No | NO-ALLOWLIST; SHELL-GLOB (spec-path varies) |

### Stage 1 gate — `spec-gate.sh`

| Tool | Command / Path | Covered by allowlist rule | If no — why not |
|------|---------------|--------------------------|-----------------|
| Bash (awk, grep) | In-process awk/grep on spec file via shell substitution | No | NO-ALLOWLIST; SHELL-EVAL (content read inline) |
| Bash (python3 inline) | `python3 - "$SPEC" <<'PYEOF'` injection-detection script | No | NO-ALLOWLIST; SHELL-EVAL (heredoc inline script) |
| Bash (python3 audit-logger) | `python3 "$LOGGER" log "$SPEC_NAME" gate_result ...` | No | NO-ALLOWLIST; SHELL-GLOB (SPEC_NAME varies) |

### Stage 2 — Spec Review (`/spec-review`)

| Tool | Command / Path | Covered by allowlist rule | If no — why not |
|------|---------------|--------------------------|-----------------|
| Read | `ai-docs/<feature>/<feature>-spec.md` | No | NO-ALLOWLIST |
| Read | `home/dot-claude/docs/sdl-workflow/review-perspectives.md` | No | NO-ALLOWLIST |
| Bash | `"$HOME"/.claude/hooks/sdl-workflow/spec-gate.sh ai-docs/<feature>/<feature>-spec.md` (prior-stage gate) | No | NO-ALLOWLIST; SHELL-GLOB |
| Write | `ai-docs/<feature>/<feature>-review.md` | No | NO-ALLOWLIST |
| Bash | `"$HOME"/.claude/hooks/sdl-workflow/review-gate.sh <review> <perspectives> [<threat-model>]` | No | NO-ALLOWLIST; SHELL-GLOB |
| Agent (task) | `test-reviewer` invoked as Agent Teams teammate (checkpoint 1) | No | NO-ALLOWLIST (agent spawning requires permission) |
| Read | `home/dot-claude/docs/sdl-workflow/threat-modeling.md` (conditional) | No | NO-ALLOWLIST |
| Write | `ai-docs/<feature>/<feature>-threat-model.md` (conditional) | No | NO-ALLOWLIST |

### Stage 2 gate — `review-gate.sh`

| Tool | Command / Path | Covered by allowlist rule | If no — why not |
|------|---------------|--------------------------|-----------------|
| Bash (grep, awk) | In-process grep/awk on review file and (optional) threat model | No | NO-ALLOWLIST; SHELL-EVAL |

### Stage 3 — Breakdown (`/breakdown`)

| Tool | Command / Path | Covered by allowlist rule | If no — why not |
|------|---------------|--------------------------|-----------------|
| Read | `ai-docs/$FEATURE/$FEATURE-spec.md` | No | NO-ALLOWLIST |
| Read | `ai-docs/$FEATURE/$FEATURE-review.md` | No | NO-ALLOWLIST |
| Read | `ai-docs/$FEATURE/$FEATURE-threat-model.md` (optional) | No | NO-ALLOWLIST |
| Read | `home/dot-claude/docs/sdl-workflow/task-compilation.md` | No | NO-ALLOWLIST |
| Read | `home/dot-claude/docs/brownfield-breakdown.md` | No | NO-ALLOWLIST |
| Bash | `"$HOME"/.claude/hooks/sdl-workflow/review-gate.sh ...` (prior-stage gate) | No | NO-ALLOWLIST; SHELL-GLOB |
| Agent (task) | Test task agent spawned as Agent Teams teammate | No | NO-ALLOWLIST |
| Agent (task) | Implementation task agent spawned as Agent Teams teammate | No | NO-ALLOWLIST |
| Write (multiple) | `ai-docs/$FEATURE/$FEATURE-tasks/task-NN-test-<behavior>.md` per test task | No | NO-ALLOWLIST; SHELL-GLOB (NN and behavior vary) |
| Write (multiple) | `ai-docs/$FEATURE/$FEATURE-tasks/task-NN-impl-<behavior>.md` per impl task | No | NO-ALLOWLIST; SHELL-GLOB |
| Write | `ai-docs/$FEATURE/$FEATURE-tasks/task.json` | No | NO-ALLOWLIST |
| Bash | `"$HOME"/.claude/hooks/sdl-workflow/task-reviewer-gate.sh <spec> <tasks-dir>` | No | NO-ALLOWLIST; SHELL-GLOB |
| Agent (task) | `test-reviewer` invoked as Agent Teams teammate (checkpoint 2) | No | NO-ALLOWLIST |
| Bash | `"$HOME"/.claude/hooks/sdl-workflow/breakdown-gate.sh <spec> <tasks-dir>` | No | NO-ALLOWLIST; SHELL-GLOB |

### Stage 3 gate — `task-reviewer-gate.sh`

| Tool | Command / Path | Covered by allowlist rule | If no — why not |
|------|---------------|--------------------------|-----------------|
| Bash (python3 inline) | `python3 - "$SPEC" "$TASKS_DIR" "$TASK_JSON" <<'PYEOF'` validation script | No | NO-ALLOWLIST; SHELL-EVAL |
| Bash (python3 inline) | Per-task file content read via `python3 -c "import json,sys; ..."` in loop | No | NO-ALLOWLIST; SHELL-EVAL; fires once per task file |
| Bash (python3 audit-logger) | `python3 "$LOGGER" log ...` | No | NO-ALLOWLIST; SHELL-GLOB |

### Stage 3 gate — `breakdown-gate.sh`

| Tool | Command / Path | Covered by allowlist rule | If no — why not |
|------|---------------|--------------------------|-----------------|
| Bash (python3 inline) | `python3 -c "import sys,json; ..."` per task file (in loop) | No | NO-ALLOWLIST; SHELL-EVAL; fires once per task file |
| Bash (python3 inline) | `python3 - "$SPEC" "$TASKS/task.json" "$TASK_CONTENT" <<'PYEOF'` full DAG/AC check | No | NO-ALLOWLIST; SHELL-EVAL |

### Stage 4 — Implement (`/implement`)

| Tool | Command / Path | Covered by allowlist rule | If no — why not |
|------|---------------|--------------------------|-----------------|
| Read | `ai-docs/$FEATURE/$FEATURE-tasks/task.json` | No | NO-ALLOWLIST |
| Read | `home/dot-claude/docs/sdl-workflow/implementation-guide.md` | No | NO-ALLOWLIST |
| Read | `home/dot-claude/docs/sdl-workflow/task-compilation.md` | No | NO-ALLOWLIST |
| Bash | `"$HOME"/.claude/hooks/sdl-workflow/breakdown-gate.sh ...` (stage 3 gate re-run) | No | NO-ALLOWLIST; SHELL-GLOB |
| Bash | `cat ~/.claude/settings.json` (TeamCompleted hook presence check) | No | NO-ALLOWLIST |
| Edit | `ai-docs/$FEATURE/$FEATURE-tasks/task.json` (status updates per task, per wave) | No | NO-ALLOWLIST; fires N times where N = task count |
| Agent (task, per wave) | Native tasks spawned for test tasks (wave-scoped) | No | NO-ALLOWLIST; fires wave-width times per wave |
| Agent (task, per wave) | Native tasks spawned for impl tasks (wave-scoped) | No | NO-ALLOWLIST; fires wave-width times per wave |
| Bash | Test runner (`npm test` / `cargo test` / `go test ./...` / etc.) — per-wave verification | No | NO-ALLOWLIST; SHELL-EVAL (command determined at runtime) |
| Bash | Lint runner (`npx eslint .` / `ruff check .` / etc.) — per-wave verification | No | NO-ALLOWLIST; SHELL-EVAL |
| Write | `ai-docs/$FEATURE/$FEATURE-review.md` (re-plan failure append) | No | NO-ALLOWLIST |
| Write | `ai-docs/$FEATURE/$FEATURE-retrospective.md` | No | NO-ALLOWLIST |

### TaskCompleted hook — `task-completed.sh`

This hook fires on every `TaskCompleted` event and is already registered in `settings.json`. Its internal Bash commands (test runner and lint runner detection and execution) run inside the hook process — they do not themselves generate Claude Code permission prompts. However, the hook registration itself means the hook binary executes for every completed task.

| Tool | Command / Path | Covered by allowlist rule | If no — why not |
|------|---------------|--------------------------|-----------------|
| Bash (hook — registered) | `"$HOME"/.claude/hooks/sdl-workflow/task-completed.sh` | Yes — TaskCompleted hook entry exists | Registered via hooks block |
| Bash (internal, test runner) | `npm test` / `cargo test` / `go test ./...` / `python -m pytest` / `make test` | n/a — runs inside hook process | Not a Claude Code tool call |
| Bash (internal, lint runner) | `npx eslint .` / `ruff check .` / `flake8 .` / `cargo clippy` / `golangci-lint run` | n/a — runs inside hook process | Not a Claude Code tool call |

---

## Highest-frequency prompt sources

Ranked by expected prompt count per full pipeline run (spec through retrospective), assuming one feature, 6 tasks across 2 waves:

1. **`task.json` Edit calls (Stage 4)** — Status is written to `task.json` twice per task (set to `in_progress`, then set to `complete`) plus one write per re-plan. For 6 tasks this is approximately 12 Edit calls, each requiring a prompt. This is the single highest-friction source.

2. **Gate Bash calls** — Every gate script invocation generates a Bash prompt. The full pipeline fires: `spec-gate.sh` (once at spec, once at spec-review), `review-gate.sh` (once at spec-review, once at breakdown), `task-reviewer-gate.sh` (once), `breakdown-gate.sh` (once at breakdown, once at implement). That is 7 gate Bash calls minimum, each with a variable argument that prevents simple command-level matching.

3. **Agent spawn calls (breakdown)** — The breakdown stage spawns three agents: test task agent, implementation task agent, and `test-reviewer` at checkpoint 2. Each spawn is a distinct permission event.

4. **Agent spawn calls (spec-review)** — Spawns `test-reviewer` at checkpoint 1 plus one agent per council perspective (minimum one). Two to four spawns per run.

5. **Per-task agent spawn calls (implement)** — Each wave spawns one native task per test task and one per implementation task. At 6 tasks across 2 waves with wave width 3, this is 6 spawns minimum, each a separate permission event.

6. **Write calls for task files (breakdown)** — One Write per task file. For 6 tasks: 6 Write calls, each to a path containing a variable numeric suffix that cannot be pre-matched without a glob allowlist rule.

7. **Per-wave verification Bash calls (implement)** — Test runner and lint runner are invoked once per wave. At 2 waves: 4 Bash calls. The exact command is determined at runtime (SHELL-EVAL), so these cannot be covered by a static allowlist rule.

8. **Doc reads (spec-review, breakdown, implement)** — Each stage reads one or two doc files from `home/dot-claude/docs/sdl-workflow/`. These are Read calls; 4–5 per run.

---

## Candidates for helper-script encapsulation

The following tool call patterns are currently raw Bash executed by the agent directly. Wrapping them in sanitized scripts would allow a single allowlist entry to cover each pattern.

### 1. Per-wave verification (test + lint)

**Current pattern**: The agent constructs the test and lint commands at runtime by examining project files, then runs `eval "$TEST_CMD"` and `eval "$LINT_CMD"`. This is SHELL-EVAL and cannot be statically allowed.

**Proposed script**: `run-wave-verify.sh <project-root>` — replicates the detection logic from `task-completed.sh`, runs both commands, and exits non-zero on failure. A single allowlist entry for `"$HOME"/.claude/hooks/sdl-workflow/run-wave-verify.sh *` would cover all per-wave verification calls regardless of project type.

### 2. `task.json` status updates

**Current pattern**: The agent issues Edit or Write calls directly to `ai-docs/$FEATURE/$FEATURE-tasks/task.json` on every status transition (`not_started` → `in_progress` → `complete`). These are the highest-frequency prompt source.

**Proposed script**: `update-task-status.sh <task-json-path> <task-id> <new-status> [summary]` — makes the targeted JSON mutation via `python3 -c "..."` inline and writes the result back atomically. A single allowlist entry for the script path would cover all status update calls. The agent issues one Bash call instead of one Edit call per transition.

### 3. Retrospective and review-append writes

**Current pattern**: The agent writes `ai-docs/$FEATURE/$FEATURE-retrospective.md` and appends re-plan failure notes to `ai-docs/$FEATURE/$FEATURE-review.md` via direct Write/Edit calls with variable paths.

**Proposed script**: `write-artifact.sh <artifact-type> <feature-name> <content-file>` — accepts `retrospective` or `review-append` as artifact-type and writes to the canonically derived path. A single allowlist entry covers the script path.

### 4. Council session management (spec-review)

**Current pattern**: The `/spec-review` skill invokes `/council` which presumably spawns sub-agents with per-perspective framing. If council session setup involves direct Bash calls (creating temp context files, writing perspective prompts), each is a separate prompt.

**Proposed script**: `council-session.sh <feature-name> <perspectives-csv>` — sets up the council context directory, writes perspective framing files, and emits a JSON manifest the skill can read. Reduces N Bash calls (one per perspective setup step) to one.

---

## PreToolUse hook design

### Purpose

Log every tool call that Claude Code routes through the permission layer during a pipeline run. The log provides empirical data to validate the predicted prompt map above, reveals which calls generate actual user-facing prompts vs. silent auto-approvals, and identifies patterns suitable for allowlist rules.

### Hook configuration for `settings.json`

Add a `PreToolUse` hook entry alongside the existing `TaskCompleted` entry:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$HOME\"/.claude/hooks/sdl-workflow/pretooluse-logger.sh"
          }
        ]
      }
    ],
    "TaskCompleted": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$HOME\"/.claude/hooks/sdl-workflow/task-completed.sh"
          }
        ]
      }
    ]
  }
}
```

The hook applies to all tool calls (no `tool_name` filter). This is intentional: the audit goal is to observe the full tool call volume including Read, Write, Edit, and Bash.

### Hook script: `pretooluse-logger.sh`

The script receives the PreToolUse event payload on stdin as JSON. It appends one log line per call to a session log file. It always exits 0 to avoid blocking any tool call.

```bash
#!/usr/bin/env bash
# pretooluse-logger.sh — PreToolUse audit logger for permissions friction analysis
# Exits 0 always (observer only — does not block tool calls).
set -uo pipefail

INPUT=$(cat)

LOG_DIR="${LOG_DIR:-.claude/automation/logs}"
SESSION_LOG="$LOG_DIR/pretooluse-$(date -u +%Y%m%d).jsonl"

mkdir -p "$LOG_DIR"

# Extract fields from the PreToolUse payload
TOOL_NAME=$(printf '%s' "$INPUT"  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "")
TOOL_INPUT=$(printf '%s' "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d.get('tool_input',{})))" 2>/dev/null || echo "{}")
SESSION_ID=$(printf '%s' "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null || echo "")

# Derive a target path from the tool_input (best-effort across tool types)
TARGET=$(printf '%s' "$TOOL_INPUT" | python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
# Bash tool: command field
if 'command' in d:
    cmd = d['command']
    print(cmd[:200])
# Read/Write/Edit: file_path field
elif 'file_path' in d:
    print(d['file_path'])
# Glob/Grep: path + pattern
elif 'pattern' in d:
    print(d.get('path','') + ' :: ' + d.get('pattern',''))
else:
    print('')
" 2>/dev/null || echo "")

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

printf '%s\n' "{\"ts\":\"$TIMESTAMP\",\"session\":\"$SESSION_ID\",\"tool\":\"$TOOL_NAME\",\"target\":$(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$TARGET" 2>/dev/null || echo "\"\""),\"input\":$TOOL_INPUT}" >> "$SESSION_LOG"

exit 0
```

### Log format

Each line is a JSON object (JSONL / newline-delimited JSON):

```
{
  "ts":      "<ISO-8601 UTC timestamp>",
  "session": "<session_id from PreToolUse payload>",
  "tool":    "<tool_name: Bash | Read | Write | Edit | Glob | Grep | Agent | ...>",
  "target":  "<derived target: command string, file path, or pattern>",
  "input":   { <full tool_input object> }
}
```

The `target` field is a human-readable summary derived from `tool_input` — it is the key field for pattern-matching against predicted prompt map entries. The full `input` is preserved for cases where the summary is ambiguous.

### Log file location

`$LOG_DIR/pretooluse-YYYYMMDD.jsonl`, where `LOG_DIR` defaults to `.claude/automation/logs`. One file per UTC day; multiple pipeline runs on the same day append to the same file.

### Using the log for validation

To validate the predicted prompt map after a run:

1. Filter the log for the session ID of interest.
2. Group by `tool` and `target` prefix.
3. Compare observed call counts against the frequency estimates in the "Highest-frequency prompt sources" section above.
4. Any `tool`/`target` pair that appears in the log but not in the predicted prompt map is a gap in the static analysis.
5. The log does not distinguish auto-approved from user-prompted calls. A second pass correlating log entries with actual user-visible prompt events (from the session transcript) would be needed to close that gap — that analysis is out of scope for this audit.

### What the hook does not capture

- Calls made inside hook processes (e.g., commands run inside `task-completed.sh`) — those run in the OS shell, not through Claude Code's tool dispatch.
- Tool calls made before the session reaches pipeline stages (e.g., initial file reads at skill entry) if the hook is not yet active at that point.

---

## Summary of mitigations deferred

Per AC-12, mitigations are identified but not implemented. The following actions are deferred to a subsequent task:

| Mitigation | Predicted friction reduction |
|------------|------------------------------|
| Add `allowedTools` / `permissions` block to `settings.json` with rules for hook script paths | Eliminates all gate Bash prompts (7 per run) |
| Implement `run-wave-verify.sh` helper and add allowlist rule | Eliminates per-wave test/lint Bash prompts (4 per run at 2 waves) |
| Implement `update-task-status.sh` helper and add allowlist rule | Eliminates highest-frequency prompt source (12+ Edit prompts per run) |
| Add allowlist glob rule for `ai-docs/**/*.md` Write/Edit | Eliminates spec, review, task file, and retrospective Write prompts |
| Implement `pretooluse-logger.sh` hook | Empirical validation of this prompt map (no friction reduction by itself) |
