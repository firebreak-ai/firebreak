# Task 008: Create hooks.md Leaf

**Output file**: `.claude/docs/context-assets/hooks.md`
**Dependencies**: 001 (must be consistent with index principles)

## Context

This leaf covers authoring guidance for Claude Code hooks (defined in `.claude/settings.json` or `.claude/settings.local.json`). It loads when the agent is writing or modifying hooks.

Read `ai-docs/mvp-000/plan.md` section: "File descriptions > 5-10 > hooks.md"

## Output Specification

Create `.claude/docs/context-assets/hooks.md` covering:

### Critical constraints (first 3 lines)

The most important rules for hook authoring — hooks execute shell commands, so the stakes are higher than other asset types.

### Main guidance

Research current Claude Code hook documentation to confirm accurate technical details before writing. Cover these topics:

1. **Hook structure in settings.json**
   - Confirm the exact JSON schema for defining hooks
   - Hook trigger events: which events are available (e.g., PreToolUse, PostToolUse, etc.)
   - Matcher patterns: how to scope hooks to specific tools or tool patterns
   - Command specification: how the shell command is defined and executed
   - Confirm whether hooks go in `settings.json`, `settings.local.json`, or both (and the distinction)

2. **Trigger event selection**
   - Match the hook to the right event — pre-tool-use for validation/gating, post-tool-use for checks/logging
   - Scope hooks narrowly: a hook that fires on every tool use wastes execution time and may interfere with agent flow
   - Use matcher patterns to restrict which tools trigger the hook

3. **Command design**
   - Keep hook commands simple and fast — they execute synchronously and block the agent
   - Prefer deterministic enforcement (linters, validators, format checkers) over instructional enforcement ("always run tests before committing")
   - Exit codes matter: confirm how Claude Code interprets hook exit codes (pass/fail/block)

4. **Security and auditability**
   - Hooks execute arbitrary shell commands — every hook must be auditable
   - A reviewer should be able to determine exactly what a hook will execute by reading the configuration
   - Avoid dynamically constructed commands from untrusted input
   - Use `settings.local.json` for hooks containing machine-specific paths or developer-specific preferences (not committed to repo)

5. **Scoping**
   - One hook, one concern — same principle as rules
   - A hook that validates TypeScript types should not also enforce commit message format
   - Keep hook logic in the commands it calls, not in complex shell one-liners — extract to a script file if the logic exceeds a single clear command

## Verification Criteria

- [ ] Critical constraints in first 3 lines
- [ ] Covers: settings.json schema, trigger events, command design, security/auditability, scoping
- [ ] JSON schema and event types are accurate per current Claude Code documentation
- [ ] Security section is prominent (hooks are the highest-risk asset type)
- [ ] Positive framing, atomic constraints, no preamble
- [ ] No duplication of index principles (reference them, apply them, but state leaf-specific guidance only)
- [ ] Includes guidance on settings.json vs. settings.local.json distinction
