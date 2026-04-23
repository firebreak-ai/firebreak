Perspectives: Architecture, Pragmatism, Measurability

# Agent Personas — Spec Review

## Architectural Soundness

### F-01: 40-line structural validation ceiling will fail agents with task logic [blocking]

The testing strategy states: "Verify no agent file exceeds 40 lines." The test-reviewer agent is 172 lines; the improvement-analyst is 47 lines. Both preserve existing task logic unchanged (AC-03, AC-04). Adding a persona on top pushes them well past 40 lines.

The 40-line ceiling is appropriate for persona-only agents (council agents, new agent definitions). It is invalid for agents whose body includes substantial task logic.

**Resolution**: Split structural validation into two categories: (1) persona-only agents — 40-line ceiling on the full file; (2) agents with task logic — 40-line ceiling on the persona section only, measured from the body start to the first task-logic heading.

### F-02: Missing forward-reference integration seams for new agent-to-skill bindings [important]

Three new agents (`fbk-spec-author`, `fbk-task-compiler`, `fbk-implementer`) are created without the skill modifications to reference them. The integration seam declaration does not include these future bindings, creating risk that agent definitions are designed without considering how skills actually spawn teammates.

**Resolution**: Add a "Future integration seams" subsection listing the three skill-to-agent bindings. Include enough detail about each skill's current spawn pattern that implementers design agent definitions compatible with the consumption context.

### F-03: No guidance on persona vs skill-injected instruction precedence [important]

The authoring guidance covers persona structure but says nothing about how persona instructions interact with skill-injected spawn prompts. Council agents receive 30+ line prompt templates from the council skill. The breakdown and implement skills inject task file paths and completion gates inline. When persona quality bars and spawn prompt instructions address the same concern, agents need a resolution principle.

**Resolution**: Add a subsection to the authoring guidance: "Personas and spawn prompts." State the principle: the persona defines what quality the output demonstrates; the spawn prompt defines what the task is and what format to use.

### F-04: Council skill prompt templates re-introduce style guidance that personas remove [important]

The council skill's Phase 1/3 prompt templates inject communication style instructions ("Keep your contribution focused and substantive (2-4 paragraphs)", "Don't repeat what others have said") — the same kind of content the spec removes from council personas. After restructuring, agents will have activation-focused personas plus skill-injected style guidance.

**Resolution**: Add an explicit non-goal acknowledging this inconsistency: "The council skill's prompt templates contain communication style guidance that overlaps with the patterns this spec removes from agent personas. Cleaning up the skill templates is deferred to the skill integration spec." This prevents implementers from being confused by the contradiction.

### F-05: Task compiler single-agent-two-roles lacks differentiation justification [important]

The spec proposes one `fbk-task-compiler` agent for both test-task and impl-task generation, with the spawn prompt differentiating. But the two roles receive different context (test-task gets spec only; impl-task gets spec + test task files) and produce different output (compile-and-fail gates vs test-pass gates). The anti-default about granularity operates differently across the two contexts.

**Resolution**: Either confirm the persona works identically for both roles with a brief justification, or split into two agent definitions.

### F-06: Detector/Challenger not formally referenced as canonical examples in guidance [important]

The guidance describes the pattern abstractly but does not point agent authors at the Detector and Challenger files as the reference implementation. These are the two agents that already follow the pattern — they are the best teaching tool for future agent authors.

**Resolution**: Add a "Reference implementations" callout in the guidance section pointing to `fbk-code-review-detector.md` and `fbk-code-review-challenger.md`.

## Over-engineering / Pragmatism

### F-07: 15-25 line target is unrealistic for council agents [important]

The Detector (the target pattern) is 48 lines total, ~35 lines body. Council agents have analogous domain needs: the Builder's complexity watchdog authority is 8 lines of load-bearing content. The per-agent quality bars in the spec are 3-4 sentences each (~6-10 lines). Realistic estimate: 20-35 lines body.

The 40-line validation threshold is more honest than the 15-25 claim. Either raise the target to 20-35 or drop the hard range and anchor on the validation threshold.

**Resolution**: Revise target from "15-25 lines" to "20-35 lines" or remove the line count estimate and reference the 40-line validation threshold as the upper bound.

### F-08: New agent files need explicit follow-up work section [important]

Three agent definitions will sit unused in `assets/agents/` until someone writes a skill integration spec. The risk is dead-code drift.

**Resolution**: Add a "Follow-up work" section naming the specific skills (`/fbk-spec`, `/fbk-breakdown`, `/fbk-implement`) that need updating to reference these agent definitions.

### F-09: Research rationale is over-specified for `agents.md` audience [important]

The research rationale (paper citations, competing-modes theory) is repeated three times in the spec and specified as a deliverable in `agents.md`. Future agent authors need the conclusion (personas improve maintainability, pipeline handles correctness) but not the full academic argument.

**Resolution**: Keep research rationale to 1-2 sentences in `agents.md` with the conclusion. The detailed rationale lives in this spec for anyone who wants the full argument.

## Measurability

### F-10: Goal 1 has no baseline, metric, or falsifiability [blocking]

"Shift the default output distribution across the entire Firebreak pipeline from demo/tutorial-grade to enterprise-grade" — how will we know if it worked? The spec proposes no baseline measurement, no metric, and no before/after comparison. Without falsifiability, matching the template and declaring victory is possible without evidence the output distribution actually shifted.

**Resolution**: Define what evidence would indicate the personas are *not* working (what would falsify the claim?). At minimum, add a note that quality impact will be assessed qualitatively in the first pipeline execution using the restructured agents, and that the Martian benchmark will be re-run to check for regression on Detector/Challenger.

### F-11: MetaGPT "linear improvement up to 5" claim unverifiable [important]

The specific framing of "linear improvement up to 5, with each role adding a distinct evaluation dimension" does not appear in the MetaGPT paper (arXiv:2308.00352). The paper shows roles improve performance, but the specificity of the claim is not supported.

**Resolution**: Soften to "MetaGPT's ablation showed consistent improvement as roles were added" without the "linear" and "up to 5" specificity.

### F-12: AC-06 "falsifiable" criterion is human judgment [important]

"Output quality bars are falsifiable" — who judges this? The structural test can check that quality bars exist but cannot assess whether their content is falsifiable vs vague.

**Resolution**: Accept AC-06 as human judgment and note it explicitly. Add a concrete litmus test: "a quality bar is falsifiable if a reviewer can construct a specific output that violates it."

### F-13: Spot-check is subjective assessment, not a test [important]

"Persona quality spot-check" has no pass/fail criteria that two independent reviewers would agree on. "Role activation is demonstrated" and "quality bars are observable" are judgment calls.

**Resolution**: Rename from "test" to "assessment." Add a concrete mechanical check: "the agent's first substantive output paragraph references its professional role or domain authority."

## Test Strategy Review

**Result: FAIL**

Two defects identified by the test reviewer at Checkpoint 1:

1. **AC-01 has no test coverage.** AC-01 requires persona authoring guidance in `agents.md`, but the structural validation test only covers agent files (frontmatter, line counts). The documentation content in `agents.md` is not validated by any described test.

2. **UV-2 has no test mapping.** UV-2 checks that `agents.md` contains the guidance section, but no test in the testing strategy covers this verification.

**Remediation**: Add a third test: "Documentation content validation — verify `agents.md` contains a persona authoring guidance section with required subsections." Assign AC-01 to this test and remove AC-01 from the structural validation coverage claim.

## Testing Strategy

### New tests needed

The spec's testing strategy was updated during review to address CP1 defects:

1. **Structural validation** — frontmatter checks, line-count thresholds (split for persona-only vs task-logic agents). Covers AC-02 through AC-06.
2. **Documentation content validation** — verifies `agents.md` guidance section contains required subsections. Covers AC-01.
3. **Persona quality assessment** (renamed from "spot-check") — qualitative human assessment of agent output with a mechanical anchor (first paragraph references professional role). Covers AC-02 through AC-06.

### Existing tests impacted

None — no automated test suite exists for context assets. The Martian benchmark covers Detector/Challenger only; those agents are not modified.

### Test infrastructure changes

None — testing is structural validation and human assessment.

## Informational Notes

- Research citations (CodePromptEval, PRISM, ChatDev) are largely accurate. Cognitive complexity claim is slightly overstated (mixed results, not clean reduction). ChatDev interpretation ("structural differentiation, not persona labels") is the spec author's reading, not a direct finding. (Analyst)
- Per-agent restructuring notes are concrete enough to implement from. A task compiler can derive tasks with clear completion criteria. (Builder)
- Testing strategy is appropriate for context-asset work. Structural validation is the right tool. (Builder)
- Frontmatter `description` field updates are unaddressed — current descriptions are description-heavy in the same way as the personas. Clarify whether they're in scope. (Architect)

## Threat Model Determination

**Security-relevant characteristics**: This feature modifies markdown context asset files (agent definitions, documentation). No data is processed, no trust boundaries are crossed, no new entry points are created, no auth/access control is changed. Agent personas are system prompt content — they cannot be modified by end users or external input during execution.

**Decision**: No. No new trust boundaries, no data handling changes, no external API interaction, no user-modifiable inputs. Context asset files are system prompt content loaded at agent spawn time.

## Finding Summary

| ID | Finding | Category | Severity |
|----|---------|----------|----------|
| F-01 | 40-line ceiling fails agents with task logic | Architecture | Blocking |
| F-10 | Goal 1 has no baseline or falsifiability | Measurability | Blocking |
| F-02 | Missing forward-reference integration seams | Architecture | Important |
| F-03 | No persona vs spawn-prompt precedence guidance | Architecture | Important |
| F-04 | Council skill templates re-introduce removed style guidance | Architecture | Important |
| F-05 | Task compiler two-roles lacks justification | Architecture | Important |
| F-06 | Detector/Challenger not referenced as examples | Architecture | Important |
| F-07 | 15-25 line target unrealistic | Pragmatism | Important |
| F-08 | New agent files need follow-up work section | Pragmatism | Important |
| F-09 | Research rationale over-specified for agents.md | Pragmatism | Important |
| F-11 | MetaGPT claim unverifiable | Measurability | Important |
| F-12 | AC-06 "falsifiable" is human judgment | Measurability | Important |
| F-13 | Spot-check is assessment, not test | Measurability | Important |
| — | Test strategy review | Testing | FAIL (2 defects) |
