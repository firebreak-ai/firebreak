# Task 15: Cross-Asset Validation

## Objective

Validate all created SDL workflow assets against context asset authoring principles and cross-asset consistency.

## Context

This task reviews all 14 assets produced by tasks T-01 through T-14 as an integrated system. Individual tasks verify their own acceptance criteria. This task verifies the assets work together and all follow the shared authoring principles.

### Assets to validate

**Docs (6 files)**:
- `home/.claude/docs/sdl-workflow.md` (index)
- `home/.claude/docs/sdl-workflow/feature-spec-guide.md`
- `home/.claude/docs/sdl-workflow/review-perspectives.md`
- `home/.claude/docs/sdl-workflow/threat-modeling.md`
- `home/.claude/docs/sdl-workflow/task-compilation.md`
- `home/.claude/docs/sdl-workflow/implementation-guide.md`

**Skills (4 files)**:
- `home/.claude/skills/spec/SKILL.md`
- `home/.claude/skills/spec-review/SKILL.md`
- `home/.claude/skills/breakdown/SKILL.md`
- `home/.claude/skills/implement/SKILL.md`

**Scripts (4 files)**:
- `home/.claude/hooks/sdl-workflow/spec-gate.sh`
- `home/.claude/hooks/sdl-workflow/review-gate.sh`
- `home/.claude/hooks/sdl-workflow/breakdown-gate.sh`
- `home/.claude/hooks/sdl-workflow/task-completed.sh`

### Validation criteria

**1. Authoring principles (per-asset)**:

For each doc and skill, verify:
- [ ] Starts with first instruction — no preamble, no "this document..."
- [ ] All instructions use direct-address imperatives
- [ ] No passive or third-person framing
- [ ] Positive framing throughout (prohibitions paired with alternatives)
- [ ] Each instruction is a single verifiable constraint
- [ ] No research citations or paper references (those belong in the spec, not in agent-facing assets)
- [ ] No motivational framing ("it's important to...", "best practice is...")
- [ ] Passes the Necessity Test — every sentence prevents a concrete mistake

**2. Cross-asset consistency**:

- [ ] Index doc routes to all 5 leaf docs by correct path
- [ ] Each skill references its correct leaf doc by path
- [ ] Each skill calls its correct gate script by path
- [ ] Gate script paths in skills match actual script locations
- [ ] Skill descriptions are distinct enough to avoid cross-matching (e.g., `/spec` description shouldn't also match `/spec-review` scenarios)
- [ ] Transition protocol is consistent: each skill's transition invokes the correct next skill with the feature name
- [ ] Compaction notes are present in skills that transition to the next stage

**3. Spec coverage**:

Cross-reference the SDL workflow spec (`ai-docs/sdl-workflow/sdl-workflow-spec.md`) against the created assets. Check that:
- [ ] All structural prerequisites from the enforcement mapping table are implemented in gate scripts
- [ ] All stage behaviors described in the spec are captured in the corresponding doc + skill
- [ ] The verification gate model (structural then semantic, reported separately) is reflected in each stage's doc
- [ ] The external feedback rule is captured in the index doc and respected in the implementation guide's re-plan protocol
- [ ] Iteration caps per stage are documented in the index doc

**4. Script validation**:

For each gate script:
- [ ] Accepts documented arguments
- [ ] Returns exit 0 on success, exit 2 on failure
- [ ] Reports all failures (not just the first)
- [ ] Has executable permission or notes for setting it

## Instructions

1. Read ALL 14 asset files listed above.
2. Read the context asset authoring principles at `home/.claude/docs/context-assets.md`.
3. Read the SDL workflow spec at `ai-docs/sdl-workflow/sdl-workflow-spec.md`.
4. For each doc and skill: run through the authoring principles checklist (section 1). Note any violations with the specific file and line.
5. Run cross-asset consistency checks (section 2). Verify paths, transitions, and descriptions.
6. Run spec coverage checks (section 3). Cross-reference spec requirements against created assets.
7. Run script validation checks (section 4).
8. Produce a validation report:
   - **Pass**: asset, check, status
   - **Fail**: asset, check, what's wrong, suggested fix
   - Summary: total checks, passed, failed

9. If failures are found: report them with specific locations and fixes. Do NOT modify the files — report only. The user or a revision task addresses the fixes.
10. This task writes no files — it is a read-only validation pass.

## Files to Create/Modify

- **Reads**: all 14 assets listed above + authoring principles + spec
- **Creates**: none (output is the validation report in conversation)

## Acceptance Criteria

- AC-15: All assets pass the Necessity Test and follow the 6 context asset authoring principles. Cross-asset consistency verified. Spec coverage confirmed.

## Model

Sonnet

## Wave

3
