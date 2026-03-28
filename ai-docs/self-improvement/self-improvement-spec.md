# Self-Improvement: Pipeline Learning from Retrospectives

## Problem

The Firebreak pipeline captures process observations in retrospectives after each code review cycle — what went wrong, what worked, what friction the pipeline itself introduced. These observations identify specific, actionable improvements to the context assets (skills, agents, leaf docs) that govern the pipeline's behavior. Today, retrospective observations are recorded but not acted on. The feedback loop is open: the pipeline repeats the same mistakes across runs because no mechanism translates retrospective findings into asset changes. Closing this loop requires a structured step that proposes targeted edits to context assets, grounded in observed failures, and subject to user approval.

## Goals / Non-goals

**Goals:**
- Translate retrospective observations into specific, user-reviewable proposals to add, edit, or remove instructions in Firebreak context assets
- Anchor every proposal to a specific retrospective observation and the necessity test: "if this change were reverted, is the agent more likely to repeat the observed mistake?"
- Support cross-cutting proposals — a failure observed in implementation may trace to a missing constraint in the spec skill
- Preserve context asset quality by requiring every proposal to comply with the context asset authoring rules (necessity test, progressive disclosure, write-for-agents style)
- Enable partial acceptance — the user can accept, discuss, or skip individual proposals

**Non-goals:**
- Automated application without user review — every proposal requires explicit user approval
- Changes to non-Firebreak assets (project CLAUDE.md, project rules, project hooks)
- Direct modification of the Firebreak source repo (`assets/`) — the skill modifies the user's installed assets; contributing changes upstream is the user's responsibility
- Retrospective quality improvement — this feature consumes retrospectives as-is; improving retro content is a separate concern
- Pipeline structural changes (adding/removing phases, changing gate logic) — proposals are limited to instruction-level changes within existing assets
- Historical trend analysis across multiple retrospectives — each invocation works from a single retrospective

## User-facing behavior

### Automatic invocation (primary path)

After the code review skill finalizes the retrospective, it automatically invokes `/fbk-improve <feature-name>`. The user does not need to trigger this manually — it is the natural next step in the pipeline. The code review skill's Retrospective section transitions directly into self-improvement analysis.

The skill locates the retrospective for the named feature and offers: "Found retrospective at `ai-docs/<feature>/...-retrospective.md`. Proceed with improvement analysis, or skip?" If the user skips, the skill exits. If the user proceeds (or does not respond within the conversational flow), the skill spawns a dedicated improvement agent with a clean context (no conversation history from prior phases).

### Manual invocation

The user can also invoke `/fbk-improve <feature-name>` directly at any time — for example, to re-run improvement analysis on an older retrospective, or after updating a retrospective with additional observations. The behavior is identical to the automatic path.

The agent returns a numbered list of proposals. Each proposal displays:
- **Target**: which asset file and which instruction(s)
- **Change**: add / edit / remove, with the specific diff
- **Observation**: the retrospective observation that motivates this change
- **Necessity**: why reverting the change would make the observed mistake more likely

Example output:

```
Proposal 1 — EDIT assets/skills/fbk-spec/SKILL.md
Observation: Retro noted spec did not constrain X, leading to implementation failure Y.
Change: Add instruction after line "..." :
  "When the technical approach references Z, require explicit specification of X."
Necessity: Without this, the spec skill has no trigger to surface X, and the
implementing agent will infer a default that conflicts with Y.

Proposal 2 — REMOVE assets/fbk-docs/fbk-sdl-workflow/task-compilation.md
Observation: Retro noted instruction "..." produced false-positive gate failures
in 3 of 4 review rounds.
Change: Remove the sentence "..."
Necessity: This instruction causes the task compiler to flag valid task structures
as incomplete. Removing it eliminates the false-positive trigger without losing
any genuine validation.
```

The user responds with which proposals to apply:
- "Apply 1, 3, 5" — the skill applies those changes to the target files
- "Discuss 2" — the skill explains the reasoning in more detail and the user can refine, accept, or reject
- "Skip 4" — no action taken

After applying accepted proposals, the skill presents a summary of changes made and exits.

**Edge cases:**
- If the retrospective contains no actionable observations (all process notes, no specific failures), the agent reports "No improvement proposals — retrospective contains no observations that map to specific asset changes" and exits.
- If the agent identifies a potential improvement but cannot formulate it as a single instruction change, it surfaces it as a discussion item rather than a proposal: "Discussion item: [observation]. This may require a structural change to [asset] that exceeds single-instruction scope. Consider addressing in a future spec."

## Technical approach

### Behaviors

**Retrospective location** (computation): Given a feature name, resolve the path to its retrospective file. Search `ai-docs/<feature-name>/` for files matching `*-retrospective.md`. Return the path or report that no retrospective was found.

**Asset discovery** (computation): Locate the Firebreak installation, then enumerate eligible assets. Use Glob to search for `fbk-*/SKILL.md` in both `.claude/skills/` (project) and `~/.claude/skills/` (global). Whichever location returns results is the installation root. If both return results, prefer project-level. If neither returns results, report that no Firebreak installation was found and exit. From the resolved installation root, enumerate all `fbk-*` prefixed files under `skills/`, `agents/`, and `fbk-docs/`. These are the files the skill modifies. The source files in the Firebreak repo's `assets/` directory are not modified; users who want to contribute improvements upstream port accepted changes from their installation to a PR against the Firebreak repo. Return the installation root and file list.

**Improvement analysis** (orchestration, delegated to agent): The core analysis behavior. The improvement agent receives:
- The retrospective content
- The context asset authoring rules (`assets/fbk-docs/fbk-context-assets.md` and its leaf docs)
- The enumerated asset files

The agent reads each asset, cross-references retrospective observations against the instructions in each asset, and produces proposals. For each observation that maps to a specific asset gap or excess:
1. Identify the target asset and the specific instruction (or absence of instruction)
2. Draft the change (add/edit/remove) as a concrete diff
3. Validate the change against the context asset authoring rules — necessity test, write-for-agents style, single verifiable constraint per instruction, positive framing
4. State the necessity argument: why reverting would increase the probability of the observed mistake

After drafting all proposals, the agent performs a quality review of each affected asset with the proposed changes applied:

1. **Self-correction**: Revise proposals in-place before presentation. If a proposed addition would make an existing instruction redundant, or if a proposed edit introduces a compound instruction or style violation, fix the proposal. This is invisible cleanup — the user sees only the corrected version.
2. **Removal proposals**: If the quality review reveals pre-existing bloat (instructions that no longer pass the necessity test, with or without the new additions), surface these as additional proposals in the numbered list. These proposals cite the authoring rules as motivation rather than a retro observation — their necessity argument is "this instruction does not pass the necessity test" rather than "this prevents a specific observed mistake."

**Proposal presentation** (orchestration): Format the agent's output as the numbered proposal list described in section 3. Present to user.

**Selective application** (orchestration): Parse user's accept/discuss/skip decisions. For accepted proposals, apply the diffs to the target files using Edit. For discussion items, relay the agent's detailed reasoning and enter a conversational loop until the user accepts, modifies, or rejects.

### Composition

1. Skill entry → retrospective location → asset discovery (parallel, no dependency)
2. Both results → spawn improvement agent with retro content + asset file list + authoring rules
3. Agent returns proposals → proposal presentation to user
4. User decisions → selective application

### Agent isolation

The improvement agent is spawned with a dedicated agent definition (`assets/agents/fbk-improvement-analyst.md`). Its spawn prompt contains:
- Path to the retrospective file (agent reads it)
- Path to the authoring rules index (`fbk-context-assets.md`; agent follows routing table to leaves as needed)
- List of installed asset paths (agent reads selectively based on retro observations)
- The proposal output format contract

No file contents are injected into the spawn prompt. The agent reads all files on demand.

The improvement agent operates as an **agent team lead** — it spawns sub-agents to analyze individual assets. Each sub-agent reads one asset (tracing its reference paths to understand the full instruction set a real agent would encounter), cross-references against the retro observations, and returns proposals for that asset. This mirrors how a real agent would encounter the instructions: in isolation, following the progressive disclosure paths. Analysis of one asset does not contaminate analysis of another.

The improvement agent does **not** receive: the feature spec, implementation code, code review conversation, or any prior conversation context. This isolation is intentional — the agent that participated in earlier phases carries context biases that produced the mistakes the retrospective observed. A fresh perspective is structurally better for identifying root causes in the instructions themselves.

### Integration seam declaration

- [ ] `fbk-code-review` skill → `fbk-improve` skill: automatic invocation contract (retrospective file persisted at `ai-docs/<feature>/*-retrospective.md` before invocation; feature name passed as argument)
- [ ] Skill (`fbk-improve`) → Improvement agent (`fbk-improvement-analyst`): agent spawn prompt contract (retro content, authoring rules paths, asset file list)
- [ ] Improvement agent → Skill: proposal output format (structured list with target, change type, diff, observation, necessity)
- [ ] Skill → target assets: Edit tool application of accepted diffs

## Testing strategy

### New tests needed

This project's deliverables are context assets (markdown skills, agents, docs), not application code. The test suite validates structural properties of assets — instruction presence, cross-reference integrity, format compliance — using TAP-format bash scripts with grep assertions. Behavioral validation of agent output is inherently nondeterministic and is covered by user verification steps, not automated tests.

- **Structural test**: Agent definition exists with correct frontmatter (tools restricted to Read/Grep/Glob), contains proposal output format specification, references authoring rules, specifies sub-agent team pattern, permits cross-cutting proposals, excludes spec/impl/review content — covers AC-02, AC-03, AC-04, AC-05, AC-08
- **Structural test**: Skill definition exists with correct frontmatter (allowed-tools includes Edit and Agent), contains retrospective location instructions with correct path pattern, Glob-based asset discovery referencing both project and global `.claude/`, agent spawn contract passing paths not contents, proposal presentation format, accept/discuss/skip flow, opt-out prompt, no-actionable-observations exit message — covers AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08
- **Integration test**: Code review skill contains `/fbk-improve` transition in Retrospective section, SDL workflow doc includes self-improvement stage, cross-asset references resolve (skill → agent, agent → authoring rules), Edit available for diff application — covers AC-01, AC-06
- **Reference integrity test**: Every Firebreak leaf doc is referenced by at least one other asset file. All inter-asset path references resolve to existing files under the installation path convention (`.claude/` prefix normalization). Catches orphaned docs, broken paths, and path conventions that break during installation — covers AC-01, AC-02, AC-05
- **Existing test update**: `test-code-review-integration.sh` gains assertion that code review skill contains `/fbk-improve` transition instruction — covers AC-01

### Existing tests impacted

`tests/sdl-workflow/test-code-review-integration.sh`: Add assertion that the code review skill contains a `/fbk-improve` invocation, validating the automatic invocation seam contract.

### Test infrastructure changes

None — structural tests use the existing TAP test pattern with grep assertions against asset files. No synthetic fixtures required.

### User verification steps

- UV-1: Invoke `/fbk-improve <feature>` after a completed code review cycle → skill locates and confirms the retrospective file
- UV-2: After confirmation, improvement agent produces a numbered proposal list where each proposal shows target, change, observation, and necessity → proposals are specific and traceable to retro observations
- UV-3: Respond with "apply 1, skip 2" → proposal 1's diff is applied to the target asset file, proposal 2's target file is unchanged
- UV-4: Respond with "discuss 2" → skill provides detailed reasoning for proposal 2 and accepts follow-up input

## Documentation impact

### Project documents to update

- `assets/skills/fbk-code-review/SKILL.md`: Add a transition instruction to the Retrospective section — after producing the retrospective, invoke `/fbk-improve <feature-name>`.
- `assets/fbk-docs/fbk-sdl-workflow.md`: Add the self-improvement step to the pipeline phase sequence, after code review and retrospective finalization.
- `assets/fbk-docs/fbk-context-assets.md`: No change needed — the existing authoring rules are consumed as-is. But confirm no routing table update is needed if a new leaf doc is created for improvement-specific guidance.

### New documentation to create

- Agent definition: `assets/agents/fbk-improvement-analyst.md` — the dedicated agent persona for improvement analysis.

## Acceptance criteria

- AC-01: `/fbk-improve <feature-name>` locates the retrospective at the expected path or reports that none was found.
- AC-02: The improvement agent receives only: retrospective content, context asset authoring rules, and the user's installed Firebreak asset files. It does not receive spec, implementation, or review conversation content.
- AC-03: Every proposal includes: target asset path, change type (add/edit/remove), specific diff, source retrospective observation, and necessity argument.
- AC-04: Every proposal's change is anchored to a specific retrospective observation — no speculative improvements disconnected from observed failures.
- AC-05: Every proposal's change complies with the context asset authoring rules: passes the necessity test, uses imperative direct-address style, contains a single verifiable constraint per instruction, and uses positive framing.
- AC-06: The user can selectively accept, discuss, or skip individual proposals. Accepted proposals are applied as diffs to the target files. Skipped proposals leave files unchanged.
- AC-07: When the retrospective contains no actionable observations, the skill reports this and exits without producing proposals.
- AC-08: Cross-cutting proposals are supported — an observation from a code review failure can produce a proposal targeting the spec skill or any other Firebreak asset.

## Open questions

*None — all design decisions resolved during pre-spec discussion.*

## Dependencies

- Existing Firebreak pipeline infrastructure: skill framework, agent spawning, context asset authoring rules
- Retrospective output from `/fbk-code-review`: the retrospective must be persisted as a file at a discoverable path (current behavior)
- Context asset authoring rules at `assets/fbk-docs/fbk-context-assets.md` and leaf docs
