# Task 009: Create agents.md Leaf

**Output file**: `.claude/docs/context-assets/agents.md`
**Dependencies**: 001 (must be consistent with index principles)

## Context

This leaf covers authoring guidance for Claude Code custom agents (`.claude/agents/*.md`). It loads when the agent is writing or modifying an agent definition.

Read `ai-docs/mvp-000/plan.md` section: "File descriptions > 5-10 > agents.md"

## Output Specification

Create `.claude/docs/context-assets/agents.md` covering:

### Critical constraints (first 3 lines)

The most important rules for agent authoring.

### Main guidance

Research current Claude Code agent documentation to confirm accurate technical details before writing. Cover these topics:

1. **Agent definition structure**
   - Confirm the file format and location (`.claude/agents/<name>.md`)
   - Frontmatter options: confirm available fields (e.g., `allowed-tools`, `model`, etc.)
   - Body content: what goes in the agent's instruction body

2. **When to use a custom agent vs. alternatives**
   - Use a custom agent when a task needs a specialized persona, restricted tool set, or distinct behavioral profile
   - Use a skill when you need to load reference knowledge without changing the agent's identity
   - Use a rule when behavior should apply automatically based on file patterns
   - Agents are spawned as subagents — they have their own context and tool access

3. **Capability scoping**
   - Agents inherit the parent session's tool access by default — constrain using `allowed-tools`
   - Minimum required capabilities: start restrictive, expand only when the agent demonstrably needs more access
   - An agent that only analyzes code should not have write or bash access

4. **Instruction design**
   - Agent instructions follow all the same principles as other context assets (the index principles apply)
   - Focus the agent's instructions on what makes it different from the default agent — role, constraints, behavioral boundaries
   - Avoid duplicating general project knowledge that the agent can read from CLAUDE.md or discover from the codebase

5. **Security**
   - Constrain agent definitions to minimum required capabilities using `allowed-tools`
   - A specialized agent with broad tool access is a higher-risk surface for prompt injection or misbehavior
   - Agent files are committed to the repo and can be modified by contributors — review changes like code

## Verification Criteria

- [ ] Critical constraints in first 3 lines
- [ ] Covers: definition structure, when to use agents vs. alternatives, capability scoping, instruction design, security
- [ ] Technical details (file format, frontmatter fields, allowed-tools) are accurate per current Claude Code documentation
- [ ] Includes clear guidance on when to use agents vs. skills vs. rules
- [ ] Security section covers capability restriction
- [ ] Positive framing, atomic constraints, no preamble
- [ ] No duplication of index principles (reference them, apply them, but state leaf-specific guidance only)
