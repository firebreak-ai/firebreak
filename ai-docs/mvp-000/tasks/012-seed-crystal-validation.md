# Task 012: Seed Crystal Validation

**Output**: Validation results (no output file — this is a verification task)
**Dependencies**: 001, 002, 003, 004, 005, 006, 007, 008, 009, 010, 011 (all files must exist)

## Context

This task validates that the seed crystal actually works — that the authored context assets successfully guide an agent to produce well-formed context assets. Generic "does this look right?" checks are unreliable (DeCRIM, EMNLP 2024). Use targeted tests for specific failure modes.

Read `ai-docs/mvp-000/plan.md` section: "Seed crystal validation"

## Validation Procedure

### Pre-test: Structural verification

Before running behavioral tests, verify the file structure is complete and internally consistent:

1. **All files exist** at the paths specified in the plan:
   - `CLAUDE.md`
   - `.claude/rules/context-asset-authoring.md`
   - `.claude/skills/context-asset-authoring/SKILL.md`
   - `.claude/docs/context-assets.md`
   - `.claude/docs/context-assets/claude-md.md`
   - `.claude/docs/context-assets/rules.md`
   - `.claude/docs/context-assets/skills.md`
   - `.claude/docs/context-assets/hooks.md`
   - `.claude/docs/context-assets/agents.md`
   - `.claude/docs/context-assets/referenced-docs.md`
   - `README.md`

2. **Routing chain is unbroken**:
   - CLAUDE.md references `.claude/docs/context-assets.md`
   - The rule trigger references `.claude/docs/context-assets.md`
   - The skill trigger references `.claude/docs/context-assets.md`
   - The index routing table references all 6 leaf files by correct relative paths
   - All referenced file paths actually exist

3. **Index instruction count**: Count discrete imperative instructions in `.claude/docs/context-assets.md`. Target: 35-42. Flag if significantly outside this range.

4. **No cross-file conflicts**: Verify no two files give contradictory instructions about the same concern.

### Behavioral tests

Run these 4 tests by giving the agent a concrete authoring task and checking the output against specific criteria. The agent should have access to the seed crystal files (CLAUDE.md, the rule trigger, the index, and relevant leaves).

**Test 1: Negative framing**
- Prompt: "Write a context asset (a rule file) for common error handling mistakes in Go"
- The topic naturally invites prohibitions ("don't return bare errors", "don't ignore errors")
- **Pass criteria**: Output uses positive framing. "Wrap errors with `fmt.Errorf` or a custom wrapper" rather than "Don't return bare errors."
- **Fail criteria**: Output contains "don't", "never", "avoid" as primary instruction framing without positive alternatives.

**Test 2: Atomicity**
- Prompt: "Write a context asset (a docs leaf) for Go coding standards"
- The topic is complex enough to generate compound instructions
- **Pass criteria**: Each instruction covers a single verifiable constraint. No semicolon-joined compound rules.
- **Fail criteria**: Instructions like "Use consistent naming and handle errors with wrapped types and ensure all public functions have doc comments."

**Test 3: Compression**
- Prompt: "Write a context asset (a CLAUDE.md) for a Python web API project"
- **Pass criteria**: Output contains no introductions ("This document describes..."), no motivational framing ("It's important to..."), no explanatory prose about why the file exists. Output is under 20 lines.
- **Fail criteria**: Output includes preambles, summaries, or prose explaining the purpose of the file.

**Test 4: Structure**
- Prompt: "Write a context asset (a docs leaf) covering TypeScript testing conventions, including at least 15 rules"
- **Pass criteria**: The most critical constraints appear in the first 3 lines. Section headers provide navigable structure. The document does not rely on a flat numbered list.
- **Fail criteria**: Critical rules are buried in the middle of a flat list, or the document lacks any structural hierarchy.

### Reporting

For each test, record:
- Prompt used
- Whether the test passed or failed
- If failed: the specific violation(s) observed and which principle/checklist item they violate
- Suggested fix: which file in the seed crystal should be modified to address the failure

If any test fails, the relevant file in the seed crystal has a bug. Identify which file's guidance is insufficient and what needs to change.

## Verification Criteria

- [ ] All 11 files exist at correct paths
- [ ] Routing chain is unbroken (all references resolve)
- [ ] Index instruction count is in the 35-42 range
- [ ] No cross-file conflicts found
- [ ] All 4 behavioral tests pass
- [ ] If any test fails, specific remediation is documented
