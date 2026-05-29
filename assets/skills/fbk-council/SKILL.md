---
name: fbk-council
description: Assembles the development council — a team of specialized agents (selected per task from architect, builder, guardian, security, advocate, analyst) who discuss collaboratively, ask clarifying questions, and work toward consensus recommendations.
---

# Council Assembly Protocol

## The Council Members

| Agent | Role | Subagent Type | Research Domains |
|-------|------|---------------|------------------|
| **Architect** | Tech Lead - systems design, patterns, long-term vision | `fbk-council-architect` | Architecture patterns, framework comparisons, similar tool designs, RFC/ADR examples |
| **Builder** | Senior Engineer - implementation reality, pragmatics. **Complexity Watchdog (implementation cost)** | `fbk-council-builder` | Build tooling, CI/CD patterns, language-specific best practices, library comparisons |
| **Guardian** | Quality Engineer - reliability, edge cases, testing | `fbk-council-guardian` | Testing frameworks, reliability patterns, known failure modes, industry standards |
| **Security** | Security Engineer - vulnerabilities, threat modeling (proportional security) | `fbk-council-security` | CVE databases, OWASP guidelines, security documentation standards, compliance frameworks |
| **Advocate** | Product Voice - user needs, purpose, actual benefit. **Complexity Watchdog (user burden)** | `fbk-council-advocate` | UX patterns, onboarding examples, competitor analysis, user research methodologies |
| **Analyst** | Metrics Specialist - observability, proving claims with data | `fbk-council-analyst` | Benchmarking methodologies, industry metrics, statistical approaches, measurement tools |

**Complexity Watchdogs**: Builder and Advocate have explicit authority to flag over-engineering. Builder watches for implementation complexity that exceeds problem complexity. Advocate watches for user-facing complexity that creates unnecessary burden. Both can call for a "complexity checkpoint" to pause and simplify.

**Research Expectation**: Each agent SHOULD use WebSearch to gather external context relevant to their domain before forming recommendations. Cite sources when making claims about industry standards or best practices.

## Council Sizing

- When the trigger is `quick` or `/fbk-qcouncil`, default to a 3-agent council of Architect + Builder + Guardian unless task content explicitly requires a different domain. If the task names security/auth/credentials, substitute Security for one of the defaults (typically Guardian). If the task names users/UX/accessibility, substitute Advocate. If the task names performance/metrics/observability, substitute Analyst. Quick councils default to skipping the Phase 1 alignment round; run Phase 1 alignment only if agents explicitly request it during discussion.
- Size the council for the current task. Select members from the table whose domain is relevant. Smaller councils for focused single-component decisions; larger councils for cross-cutting changes that touch security, user experience, or measurement.
- If a new dimension emerges during discussion that requires a member you did not initially select, spawn that member as an additional teammate.

## Discussion Phases

### Phase 0: Task Intake

Before initializing a new session, run `python3 "$HOME"/.claude/fbk-scripts/fbk.py session-state recovery-check`. If `recovering` is `true` in the JSON output, read `.claude/fbk-docs/fbk-council/compaction-recovery.md` and resume from the returned `current_phase`.

**Session Initialization** (new sessions only): Create the council session marker file and initialize logging:
```bash
SESSION_ID="council-$(date +%Y%m%d-%H%M%S)"
python3 "$HOME"/.claude/fbk-scripts/fbk.py session-manager register "$SESSION_ID" full
python3 "$HOME"/.claude/fbk-scripts/fbk.py session-logger init "$SESSION_ID" --tier full --task "Task summary"
```
`session-manager register` writes the session-id marker file that recovery relies on; no additional echo/redirect is needed.

**Logging**: Session logging is **automatic by default**. Logs are written under `~/.claude/council-logs/`. Use `/fbk-council --no-log` to disable logging for a session — `--no-log` suppresses the four default logging commands (`session-logger init`, `session-logger phase-start`, `session-logger phase-end`, `session-logger finalize`). The SESSION_ID should be maintained throughout the session for phase timing and contribution tracking.

**Escape Hatch Check**:
Before proceeding, check for abort signal:
```bash
python3 "$HOME"/.claude/fbk-scripts/fbk.py session-state check-abort
```
Exit code 0 means continue. Exit code 2 means the user requested abort — the command has already cleared the abort file; announce "Council abort requested by user" and stop.

If the user hasn't provided a substantial task in this message, ask them to describe:
- What they want the council to review or design
- Any relevant context (paste specifications, describe the problem, etc.)

The task should be meaningful - a specification to review, a feature to design, an architecture decision to make.

After EACH phase completes, write checkpoint state via `python3 "$HOME"/.claude/fbk-scripts/fbk.py session-state checkpoint <phase-name> --session-id "$SESSION_ID" --completed <comma-list> --summary <str> --decisions <comma-list>`. This populates the state file that `recovery-check` reads on subsequent resume.

### Phase 1: Internal Alignment (Team Discussion Before User Questions)

**Goal**: Reduce user burden by having agents answer each other's questions first.

Before asking the user anything, the council aligns internally:

1. Invoke all selected council members in parallel, asking each to:
   - State what they need to understand about the task
   - Surface any assumptions they're making
   - Identify what data/context exists (use tools to check codebase, docs, etc.)
   - **Conduct brief external research relevant to their domain**

**External Research Guidance**:

Each agent should consider whether external research would strengthen their contribution:

| Agent | Research Triggers | Example Searches |
|-------|-------------------|------------------|
| **Architect** | Mentions of patterns, frameworks, or "how do others do X" | "hexagonal architecture Go examples", "CLI plugin systems comparison" |
| **Builder** | Build/deploy questions, library choices, performance concerns | "goreleaser best practices 2026", "Go CLI binary distribution" |
| **Guardian** | Testing strategies, reliability requirements, edge cases | "property-based testing Go", "CLI tool testing patterns" |
| **Security** | Auth, credentials, data handling, compliance mentions | "CLI tool security documentation examples", "API key handling best practices" |
| **Advocate** | Onboarding, UX, documentation, competitor references | "developer tool onboarding patterns", "CLI UX best practices" |
| **Analyst** | Metrics, benchmarks, measurement approaches, claims to verify | "AI coding tool benchmarks", "token efficiency measurement methodology" |

**Research Constraints**:
- **Time-boxed**: 1-2 searches per agent maximum in Phase 1
- **Cite sources**: Include URLs when referencing external findings
- **Relevance filter**: Only research if it would materially inform the discussion
- **Don't block on research**: If search fails or returns poor results, proceed without

2. Compile their responses and run a brief alignment round where agents:
   - Answer each other's questions from their expertise
   - **Share relevant external findings with the team**
   - Clarify shared understanding of the task
   - Identify threat level/data sensitivity (Security input)
   - Flag only questions that genuinely require user input

**Constraints on this phase:**
- **Time-boxed**: Maximum 2 exchanges before proceeding
- **No solution design**: This phase is for task understanding only, not proposing implementations
- **Output**: A shared "Task Understanding Statement" and a minimal list of user-required clarifications

**Success criteria**: The number of questions escalated to the user should be significantly fewer than the questions initially surfaced internally.

**Prompt template for Phase 1 alignment:**
```
You are [Agent Name] on a development council. The team has been given a task to discuss.

TASK:
[Insert full task/context here]

YOUR ROLE: [Role description from Council Members table]
YOUR RESEARCH DOMAINS: [From Research Domains column]

Your job in this phase is to:
1. Identify what you need to understand about the task
2. Surface assumptions you're making
3. **Conduct 1-2 web searches if external context would strengthen your analysis**
4. Identify clarifying questions (if any)

**Research Guidance:**
Consider searching for:
- Industry standards or best practices relevant to this task
- How similar projects/tools handle comparable challenges
- Recent developments in your domain (use current year in searches)
- Evidence to support or challenge assumptions

Use WebSearch for general queries, WebFetch for specific URLs.
If you find relevant external sources, cite them with URLs.

Be specific. Don't ask generic questions - ask about things that are genuinely unclear or missing that would affect your analysis.

Format your response as:
**[Your Name]'s Initial Assessment:**

**External Research Conducted:**
- [Search/fetch performed]: [Key finding] ([URL])
- Or: "No external research needed for this task"

**Assumptions:**
- [List key assumptions you're making]

**Questions for Team/User:**
1. [Question]
2. [Question]
(or "No questions - I have enough context to proceed.")
```

### Phase 2: User Clarification (Only If Needed)

**Goal**: Ask the user only questions that couldn't be resolved internally.

- Only fire this phase if Phase 1 produced user-required clarifications.
- Present only the filtered questions that survived internal alignment.
- Group by theme rather than by agent (reduces redundancy).
- Wait for user responses; skip to Phase 3 if Phase 1 resolved everything internally.

### Phase 3: Independent Discussion (No User Involvement)

**Goal**: Thorough collaborative discussion working toward consensus.

Conduct **1 round** of discussion (extend to 2 only if critical unresolved dissent exists). Research shows additional rounds decrease decision quality (ACL 2025). In each round:

1. Invoke agents in a rotating order (vary who speaks first each round)
2. Each agent sees the full discussion transcript so far
3. Each agent contributes their perspective, responds to others, builds on ideas

**Prompt template for discussion rounds:**
```
You are [Agent Name] on a development council. The team is having an independent discussion.

ORIGINAL TASK:
[Insert task]

USER'S ANSWERS TO INITIAL QUESTIONS:
[Insert Q&A from Phase 1]

DISCUSSION SO FAR:
[Insert transcript of all previous contributions]

---

It's your turn to contribute. As [role], review what's been said and add your perspective:
- Respond to points made by other council members
- Add new considerations from your area of expertise
- **If making claims about best practices or industry standards, cite sources or conduct a quick search to verify**
- Support good ideas explicitly
- Challenge or refine ideas you disagree with
- Work toward building consensus

**Research Check**: Before asserting "X is best practice" or "industry standard is Y", consider:
- Do I have a source for this claim?
- Would a quick WebSearch strengthen or refute my assumption?
- Has another agent shared research I should reference?

Keep your contribution focused and substantive (2-4 paragraphs). Don't repeat what others have said - advance the discussion.

If a consensus is emerging, acknowledge it. If you see unresolved disagreements, name them clearly.

Format:
**[Your Name]:** [Your contribution]

**Sources cited:** [URLs if any, or "None - based on codebase analysis and domain expertise"]
```

**Round management:**
- Round 1 (Primary): All agents give perspectives, respond to each other, and work toward synthesis
- Round 2 (Optional): Only if critical dissent remains unresolved after Round 1 - focus on resolving specific disagreements

After each round, briefly summarize the state of discussion before proceeding. If an agent has nothing new to add, they should explicitly pass rather than repeat prior points.

When Round 1 of Phase 3 ends without consensus, read `.claude/fbk-docs/fbk-council/consensus-failure.md` and apply the decision protocol for the task type; if the decision protocol surfaces an unresolved conflict between agents, apply the resolution-by-conflict-type rules in the same leaf.

### Phase 4: Final Questions (Team → User)

**Goal**: Surface any new questions that emerged during discussion.

1. Invoke all agents with the full discussion transcript
2. Ask each if they have NEW questions that emerged from the discussion
3. Compile any questions and present to user
4. If no new questions, proceed to output

**Prompt template for Phase 4:**
```
You are [Agent Name]. The council has completed its discussion.

ORIGINAL TASK:
[Insert task]

FULL DISCUSSION TRANSCRIPT:
[Insert all discussion]

---

Based on the discussion, do you have any NEW questions for the user that emerged? These should be questions that:
- Weren't obvious before the discussion
- Would materially affect the council's recommendations
- Are critical to resolve before finalizing

If you have new questions, list them. If not, say "No new questions."
```

### Phase 5: Consensus Output

After all phases complete, synthesize the council's conclusions using this **required output schema**:

```markdown
## Council Recommendation
[1-2 sentence clear statement of what to do]

## Summary
[Brief overview of what the council discussed and concluded]

## Consensus Points
[Bullet list of points where all agents agreed]

## Recommendations
[Numbered list of concrete, actionable recommendations with owners if applicable]

## Dissenting Views
[Named disagreements that weren't resolved - attribute to specific agents]
[If none: "No unresolved dissent."]

## Unresolved Concerns
[Issues raised that need further investigation or user decision]
[If none: "No open concerns."]

## Security Considerations
[Any security-relevant points raised by the Security agent - always surface these explicitly]

## Research Conducted
[Summary of external research performed during the session]

| Agent | Searches | Key Findings |
|-------|----------|--------------|
| Architect | [N] | [Brief summary or "None"] |
| Builder | [N] | [Brief summary or "None"] |
| Guardian | [N] | [Brief summary or "None"] |
| Security | [N] | [Brief summary or "None"] |
| Advocate | [N] | [Brief summary or "None"] |
| Analyst | [N] | [Brief summary or "None"] |

**Sources Cited:**
- [URL 1]: [What it informed]
- [URL 2]: [What it informed]
[Or: "No external research conducted - analysis based on codebase review and domain expertise"]
```

This schema ensures users receive structured, actionable output with transparent dissent and visible research accountability.

After producing the consensus output, unregister the session — register and unregister bracket every session:

```bash
python3 "$HOME"/.claude/fbk-scripts/fbk.py session-manager unregister "$SESSION_ID"
```

### Phase 5.5: Self-Evaluation (MANDATORY)

**Goal**: Enable continuous improvement of the council system itself.

**ORCHESTRATOR: You MUST execute this phase after Phase 5 and before the Session State Footer.**

The orchestrator conducts a brief self-evaluation:

1. **Reflect on session quality** (silent - logged only):
   - What worked well in this session?
   - What friction or inefficiency occurred?
   - Were there patterns that suggest process improvements?

2. **Generate improvement proposals** (if any):
   - Only propose changes when confidence is high and impact is clear
   - Each proposal must be specific and actionable (not vague suggestions)
   - Tag proposals by risk: `[SAFE]` (docs), `[MODERATE]` (prompts), `[ELEVATED]` (code)

3. **Log self-evaluation**:
```bash
python3 "$HOME"/.claude/fbk-scripts/fbk.py session-logger self-eval "$SESSION_ID" \
  --worked "parallel invocation efficient" \
  --friction "permission prompts interrupted flow" \
  --proposal "Expand auto-approval for Read tool during research phases" \
  --confidence 0.8
```

**Visibility Rules** (per Advocate's recommendations):
- **No proposals**: Show nothing to user (silent success)
- **Low-confidence proposals**: Log silently, do not surface
- **High-confidence proposals**: Add brief section to output (see schema below)

**Self-Evaluation Output Schema** (only when proposals exist):

```markdown
---
## Council Self-Evaluation

**Session Quality**: [Brief 1-line assessment]

### Proposed System Improvement

**Risk**: [SAFE|MODERATE|ELEVATED]
**Target**: `[file path]`
**Rationale**: [1-2 sentences explaining the friction observed]

<details>
<summary>View Proposed Change</summary>

[Exact diff or content change]

</details>

**To apply**: Run `[specific command]` or say "apply council improvement"
**To dismiss**: No action needed.
```

**Constraints**:
- Maximum 1 proposal per session (prevents suggestion fatigue)
- Proposals that were previously dismissed are not re-proposed for 5 sessions
- Self-evaluation content must not exceed 10% of main output length

### Immutable Core (Security Boundary)

The following components are **never self-modifiable**, even with user permission. This prevents recursive self-modification loops that could degrade council quality:

| Component | Path | Rationale |
|-----------|------|-----------|
| Proposal Validator | (future: `proposal-validator.py`) | Cannot weaken its own validation |
| Permission Hook | `council-permissions-hook.py` | Cannot expand its own permissions |
| Immutable Core Definition | This section of SKILL.md | Cannot remove itself from protection |
| Evaluation Criteria | Phase 5.5 success metrics | Cannot redefine what "good" means |

**If a self-improvement proposal targets an immutable component:**
1. Log the attempt with `--blocked-by-immutable-core` flag
2. Do not surface to user (silently reject)
3. The council may propose workarounds that don't touch immutable components

## Session State Footer

At the END of every council output (after Phase 5.5 and before any post-session cleanup), include a structured state block. Use the CONTINUE variant when the task is ongoing; use the COUNCIL_COMPLETE variant when the task is finished.

CONTINUE variant:

```markdown
---
## Session State
**Task**: [Brief task description]
**Iteration**: [N] of [estimated total or "ongoing"]
**Phase Completed**: [Last completed phase]
**Next Phase**: [What comes next, or "None - task complete"]
**Key Decisions**: [Bullet list of decisions that should not be re-litigated]
**Remaining Work**: [What still needs to be done, or "None"]

<!-- COUNCIL_STATUS: CONTINUE -->
```

COUNCIL_COMPLETE variant:

```markdown
---
## Session State
**Task**: [Brief task description]
**Iteration**: [Final]
**Phase Completed**: All phases complete
**Outcome**: [Brief summary of what was accomplished]

<!-- COUNCIL_STATUS: COUNCIL_COMPLETE -->
```

The structured fields are parsed by `recovery-check` if a future session resumes after compaction; preserve the field names exactly.

## Ralph Integration

When invoked inside a Ralph loop, read `.claude/fbk-docs/fbk-council/ralph-integration.md` and follow its checkpointing and exit-marker protocol. Detection: state file `~/.claude/council-logs/council-state.json` exists AND its `status` field equals `CONTINUE` AND `iteration` < `max_iterations`, OR explicit invocation via `/ralph-loop`. A stale state file with `status: COUNCIL_COMPLETE` or with `iteration` >= `max_iterations` does NOT activate Ralph mode — those are leftover artifacts from prior completed sessions and the orchestrator should clean them via `session-state cleanup` before proceeding with a normal `/fbk-council` session.

Use Ralph mode for multi-phase implementation, complex refactoring requiring deliberation at decision points, or exploratory work where scope may evolve across iterations. Avoid for quick one-off questions, time-sensitive work, or tasks with unclear success criteria.

## Observability

Session logging is **automatic by default** for tracking council performance over time. Use `--no-log` flag to disable.

**Log directory**: `~/.claude/council-logs/`

### Default Logging Commands

```bash
# Initialize session (Phase 0)
python3 "$HOME"/.claude/fbk-scripts/fbk.py session-logger init "$SESSION_ID" --tier full --task "Task description"

# Log phase timing
python3 "$HOME"/.claude/fbk-scripts/fbk.py session-logger phase-start "$SESSION_ID" "Phase-3-Discussion"
python3 "$HOME"/.claude/fbk-scripts/fbk.py session-logger phase-end "$SESSION_ID" "Phase-3-Discussion"

# Finalize session (Phase 5)
python3 "$HOME"/.claude/fbk-scripts/fbk.py session-logger finalize "$SESSION_ID"

# Register and unregister sessions
python3 "$HOME"/.claude/fbk-scripts/fbk.py session-manager register "$SESSION_ID" full
python3 "$HOME"/.claude/fbk-scripts/fbk.py session-manager unregister "$SESSION_ID"
```

For non-default logging commands (`contribution`, `tool-use`, `outcome`, `show`, `permission-request`), see: `fbk.py session-logger --help`.

## The Orchestrator (You)

Nine load-bearing facilitator instructions:

1. Do not contribute technical opinions. Facilitate. Manage the process; do not become a seventh voice.
2. Name specific agents when attributing views. Do not synthesize anonymously.
3. Surface minority views prominently in the Dissenting Views section. Dissent is signal, not noise.
4. Default to one discussion round. Extend to two only when critical dissent remains unresolved after Round 1. Empirical research (ACL 2025) shows additional rounds decrease decision quality.
5. Maintain a running transcript visible to each agent across phases.
6. Phase Sequence (mandatory): Phase 0 → Phase 1 → Phase 2 (if needed) → Phase 3 → Phase 4 (if new questions) → Phase 5 → Phase 5.5 → Session State Footer. Phase 5.5 self-evaluation is mandatory after Phase 5 output and before the Session State Footer; never skip it.
7. Parallel Invocation: when invoking multiple agents in the same phase, use a SINGLE message with multiple Task tool calls to maximize parallelism. Sequential spawns waste latency.
8. Per-phase checkpoint: after each phase completes, invoke the checkpoint trigger (§4.2 item 5a). Compaction can occur between phases; the state file is the only mechanism that survives it.
9. Time management: if discussion goes in circles, move to the next phase. Don't let phases drag.

## Trigger Phrases

This skill activates on:
- `/fbk-council` - Full council (default trigger; orchestrator sizes the council per task)
- `/fbk-council quick` or `/fbk-qcouncil` - Quick council (soft default: Architect + Builder + Guardian, Phase 1 skipped — overridable per task)
- `/fbk-council --no-log` - Full council without session logging
- `/fbk-council quick --no-log` - Quick council without session logging
- `/fbk-assemble` - Full council
- "assemble the team" - Full council
- "convene the council" - Full council
- "quick council" - Quick council

## Example Invocation

User: `/fbk-council` + pastes a specification document

You: Acknowledge receipt, then proceed through phases systematically.
