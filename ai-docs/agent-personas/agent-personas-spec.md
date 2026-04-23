# Agent Personas — Feature Spec

## Problem

The model's training data is dominated by demos, tutorials, proof-of-concept code, and beginner-oriented content. When Firebreak agents operate without persona activation, they default to this distribution — producing output that is functional but not enterprise-grade. This affects every pipeline stage: spec drafting that accepts ambiguity instead of surfacing it, task decomposition that misses coverage gaps, implementation that takes tutorial shortcuts, test strategies that validate happy paths, and code review that flags surface patterns instead of tracing behavioral impact. The model has enterprise-grade capabilities across all of these domains, but they are not the default distribution.

The code-review Detector and Challenger demonstrated that activation-focused personas measurably shift output quality. The Detector persona ("staff engineer who writes maintainable, production code") combined with output quality bars (mechanism, failing input, caller impact) moved the model from surface-level pattern matching to senior engineer reasoning. This is a cross-cutting principle: grounding agents in professional enterprise roles nudges the model toward more care for maintainability, production readiness, and professional standards — but it is currently applied to only 2 of 10 agents.

The remaining pipeline has three persona problems:

1. **Description-heavy personas (council agents)**: The 6 council agents follow a verbose template (~75 lines each) that describes who the agent *is* — personality traits, expertise lists, communication style — rather than constraining what the output *demonstrates*. This is narrative, not activation. It does not shift the model's output distribution because it describes the role without setting quality bars.
2. **Missing personas (execution agents)**: The test-reviewer and improvement-analyst have no role activation. They receive task instructions and operate on the generic assistant distribution.
3. **No agent definitions (skill-spawned teammates)**: The spec author, task compiler, and implementation agents have no agent definitions at all — skills spawn anonymous teammates with inline instructions and no persona framing.

There is no authoring guidance for agent personas. The existing `agents.md` context asset doc covers agent *definition structure* (frontmatter fields, tool scoping, when to use agents vs alternatives) but says nothing about how to write effective persona content — specifically, how to activate the enterprise software development distribution that produces higher-quality output across all pipeline stages.

## Goals

- Shift the default output distribution across the entire Firebreak pipeline from demo/tutorial-grade to enterprise-grade by applying professional role personas to every agent that produces substantive output. Whether the quality shift occurred is assessed by human review during pipeline use, not by automated metrics. Structural tests verify personas follow the authoring guidance; the quality impact is a human judgment.
- Establish agent persona authoring guidance in the existing `agents.md` context asset doc, covering: the enterprise activation principle, activation-focused framing, output quality bars, anti-defaults, when personas help vs when they are unnecessary, and the prompting design principle (personas activate existing model capabilities, not teach new skills).
- Restructure the 6 council agent personas from description-heavy to activation-focused with output quality bars. Preserve their existing roles and specializations.
- Add personas to the test-reviewer and improvement-analyst agents.
- Create new agent definitions for roles currently running without persona framing: spec author, task compiler, and implementer.
- Apply the persona authoring guidance consistently across all modified agents — every persona grounds the agent in a professional enterprise role as a baseline, then specializes for the domain.

### Non-goals

- Changing which council agent roles exist or their count. The 6-role composition (architect, analyst, builder, guardian, security, advocate) is preserved.
- T1 detector agents, intent-path-tracer, cr-test-reviewer, or sighting-deduplicator — these are not present on this branch.
- Modifying the Detector or Challenger personas — these are already the quality standard.
- Changing the council skill's orchestration logic or discussion protocol. The council skill's prompt templates contain turn-management instructions ("Keep your contribution to 2-4 paragraphs", "Don't repeat what others have said") that overlap stylistically with the communication guidance removed from agent personas. These are discussion protocol constraints, not quality bars — they belong in the skill, not the persona. Cleaning up the skill templates is deferred to a skill integration spec if needed.
- Changing agent tool assignments, model assignments, or frontmatter fields beyond description updates.
- Skill workflow modifications. Skills that spawn the new agents will need workflow changes to reference them, but that is a separate concern. This spec creates the agent definitions only.

## User-facing behavior

After this feature, agents across the pipeline produce output characteristic of senior engineers in an enterprise environment rather than the generic assistant distribution. The observable change is in output quality — maintainability, structure, professional standards — not in workflow or interaction patterns.

- **Council agents**: Produce tighter output structured around evidence and concrete recommendations rather than verbose role descriptions. Same names, roles, and expertise areas.
- **Test reviewer**: Operates with role activation grounding it as a QA authority. Existing checkpoint logic and evaluation criteria are unchanged.
- **Improvement analyst**: Operates with role activation grounding it in process improvement. Existing workflow and proposal format are unchanged.
- **New agent definitions** (spec author, task compiler, implementer): Available for skills to spawn when those skills are updated in a future spec. The agent definitions establish the persona; skill integration is a separate concern.

No new slash commands, workflows, or interaction patterns are introduced. No existing agent task logic or evaluation criteria are modified — only persona framing is added or restructured.

## Technical approach

### Prompting design principle

The model's training data is dominated by demos, tutorials, PoC code, and beginner-oriented content. This is the largest representation in training data and forms the default output distribution. Enterprise-grade capabilities — rigorous specification, systematic decomposition, production-quality code, thorough test planning, senior-level code review — exist in the model's weights but are not the default. They correspond to a smaller but distinct region of the training distribution: enterprise codebases, professional engineering documentation, production incident analyses, senior engineer code reviews.

A persona that grounds an agent in a professional enterprise role activates this distribution. The effect is cross-cutting — it applies to every pipeline stage:

| Stage | Default distribution | Enterprise distribution |
|-------|---------------------|------------------------|
| Spec authoring | Compliant drafting, accepts user framing | Surfaces ambiguity, demands behavioral precision |
| Council review | Generic advisory tone | Domain-expert reasoning with evidence |
| Task decomposition | Arbitrary granularity, coverage gaps | Systematic AC-to-task tracing |
| Implementation | Tutorial-grade, happy-path code | Production patterns, error handling, existing-code integration |
| Test planning | Happy-path validation | Edge cases, failure modes, behavioral completeness |
| Code review | Surface-level pattern matching | Mechanism tracing, failing input construction |

The Detector and Challenger already demonstrate this: their personas activate the senior engineering distribution and produce measurably better results. This spec extends the same principle across the entire pipeline.

Every persona instruction exists to make the desired output more likely. The necessity test: **"Without this, does the model fall back to a lower-quality default behavior it has the capability to avoid?"**

### Personas target maintainability; the pipeline engineers correctness

Research on persona prompting and code generation (CodePromptEval, arXiv:2412.20545; PRISM, arXiv:2603.18507) establishes a consistent finding: expert personas reduce code smells, cyclomatic complexity, and cognitive complexity (maintainability improvements) but do not improve — and may slightly reduce — functional correctness. The PRISM study found that expert personas consistently damaged coding benchmark scores because persona prefixes activate instruction-following circuitry that competes with factual recall.

This finding is not a problem for Firebreak — it is the reason personas fit the pipeline architecture. Firebreak engineers correctness deterministically through structural mechanisms: spec gates validate completeness before review, test-first development ensures behavioral coverage before implementation, per-wave verification gates block progress on test failures, the test reviewer validates test quality at multiple checkpoints, and mutation testing identifies coverage gaps. These mechanisms catch correctness defects regardless of the agent's persona.

What the pipeline cannot gate deterministically is *maintainability* — code that passes all tests but is tutorial-grade, overly complex, poorly structured, or hard for other engineers to work with. This is precisely the quality dimension that persona activation improves. The persona strategy and the pipeline's deterministic gates are complementary:

- **Pipeline gates** → correctness (testable, verifiable, blocking)
- **Enterprise personas** → maintainability (code smells, complexity, structure, production patterns)

Research on multi-agent systems reinforces this complementarity. ChatDev's ablation study (ACL 2024) found that removing agent roles caused a 44% quality drop — the largest single ablation impact — but the gains came from structural differentiation (different agents evaluating different quality dimensions), not persona labels alone. MetaGPT's ablation showed consistent improvement as roles were added. The research supports role-based agent architectures when roles create genuinely different evaluation perspectives, which is the council's design.

The research also identifies where personas do not add value: purely mechanical tasks (sighting deduplication, format validation) and tasks where role differentiation would not change the evaluation criteria. The persona authoring guidance incorporates this distinction.

### 4.1 Persona authoring guidance

Add a new section to `assets/fbk-docs/fbk-context-assets/agents.md` covering persona design. This guidance applies to all Firebreak agents and any future agents.

**Enterprise activation as the baseline:**

Every agent persona grounds the agent in a professional role within an enterprise software development organization. This is the single highest-leverage persona instruction — it shifts the output distribution from demo-grade to production-grade along quality dimensions that the pipeline cannot gate deterministically: maintainability, code structure, naming clarity, appropriate abstraction levels, and professional standards.

Persona activation improves maintainability metrics (reduced code smells, cyclomatic complexity, cognitive complexity) while correctness is neutral to slightly reduced. This is the intended tradeoff for Firebreak: the pipeline's deterministic gates (spec gates, test-first development, per-wave verification, mutation testing) engineer correctness. Personas cover the gap those gates cannot reach. The detailed research rationale (CodePromptEval, PRISM) is documented in the agent-personas spec.

The role activation line names the seniority level, the domain, and the enterprise context. Domain specialization (architecture, security, testing, implementation) layers on top of this baseline.

**Structure of an effective persona:**

1. **Role activation** (1-2 sentences): Ground the agent in a senior professional role within an enterprise engineering organization. Name the expertise level and domain. This is the single most impactful line — it determines which training distribution the model draws from. Example: "You are a staff engineer at an enterprise software company who writes maintainable, production code that other engineers can pick up and work with."

2. **Output quality bars** (3-6 items): State what the output must demonstrate, not how to produce it. Each bar is a falsifiable constraint — the output either meets it or doesn't. Quality bars replace the description-heavy "How You Contribute" and "Communication Style" sections.

3. **Anti-defaults** (1-3 items, optional): Name the specific default behavior the persona counteracts. Include only when the default is both likely and harmful. Example: "Lead with the mechanism, not the consequence" counteracts the model's default toward consequence-leading descriptions.

**What not to include:**

- Expertise lists (the model already has the knowledge; the role activation line selects the distribution)
- Communication style guidance (quality bars constrain output better than style descriptions)
- Personality descriptions ("Thoughtful, measured, sees connections others miss" — this is narrative, not activation)
- Generic professional advice ("Be direct about concerns but constructive in offering alternatives" — this is true of all professional communication)

**Personas and spawn prompts:**

The persona defines what quality the output demonstrates. The spawn prompt defines what the task is and what format to use. Quality bars and anti-defaults belong in the persona; task details, output format, and workflow steps belong in the spawn prompt. When both address the same concern, the persona's quality bar takes precedence.

**Reference implementations:**

The Detector (`fbk-code-review-detector.md`) and Challenger (`fbk-code-review-challenger.md`) are the canonical examples of the activation-focused pattern. The Challenger is especially concise — role activation line, two quality outcomes, no section headings — demonstrating the minimal effective persona.

**When a persona is unnecessary:**

A persona adds value when the model's default distribution produces noticeably lower quality than the activated distribution. For purely mechanical tasks (sighting deduplication, format validation, file enumeration), a persona is overhead — the task instructions are sufficient.

### 4.2 Council agent restructuring

Rewrite each council agent's body from the current template to the activation-focused pattern. The restructuring preserves each agent's role, specialization, and complexity-watchdog authority where assigned.

**Current pattern** (example from Architect, ~65 lines):
```
You are **The Architect**, a senior technical leader...

## Your Identity
Role / Perspective / Personality

## Your Expertise
- 7-item bullet list

## How You Contribute to Discussions
- 5-item numbered list

## Your Communication Style
- 5-item bullet list

## In Council Discussions
When reviewing... (5 items)
When designing... (4 items)

## Critical Behaviors
- 7-item bullet list
```

**Target pattern** (estimated 20-35 lines body per agent, validated by the 40-line structural threshold):
```
Role activation line.

## Output quality bars
- Falsifiable constraint 1
- Falsifiable constraint 2
- ...

## Anti-defaults (if applicable)
- Default behavior → what to do instead

## Authority (if applicable)
- Specific authority granted (e.g., complexity watchdog)
```

**Per-agent restructuring notes:**

- **Architect**: Activate "principal engineer reviewing system design." Quality bars: every recommendation references the architectural constraint that motivates it; tradeoff analysis names what is sacrificed, not only what is gained; identify when a proposal creates structural debt and name the specific future cost.
- **Analyst**: Activate "observability engineer who designs measurement systems." Quality bars: every claim includes how to measure it; distinguish "we believe" from "we know" with the evidence that would convert belief to knowledge; name the specific metric and its collection mechanism.
- **Builder**: Activate "staff engineer who has shipped and maintained production systems." Quality bars: complexity assessments name the specific hard part, not just "this will be complex"; alternatives are concrete enough to implement; preserve complexity watchdog authority. Anti-default: resist endorsing elegant abstractions that add implementation cost without proportional value.
- **Guardian**: Activate "QA architect who designs testing strategies." Quality bars: edge cases include the specific input or state that triggers them; testing recommendations name the test type, the behavior covered, and the failure mode caught; distinguish "must handle" from "nice to handle" with the risk assessment that determines which.
- **Security**: Activate "application security engineer conducting threat analysis." Quality bars: threats name the attack vector, the exploitable mechanism, and the impact; security recommendations include risk rating (critical/high/medium/low) with the exploitability assessment that determined it; preserve proportional security (match security measures to actual threat level).
- **Advocate**: Activate "product manager evaluating feature proposals." Quality bars: user impact assessments name the specific user action affected and the observable change; scope challenges articulate what user value is lost if the scope is reduced; preserve complexity watchdog (user burden) authority.

### 4.3 Test reviewer persona

Add a persona to the existing `fbk-test-reviewer.md` agent. The test reviewer has pipeline-blocking authority but currently operates with no role activation.

Activate "senior QA engineer with authority to block releases." Quality bars: every finding cites the specific criterion violated and the evidence; pass results demonstrate that every checkpoint was evaluated, not just that nothing was flagged; treat pipeline-blocking authority as an obligation to be thorough, not a license to be pedantic.

### 4.4 Improvement analyst persona

Add a persona to the existing `fbk-improvement-analyst.md` agent. The improvement analyst traces retrospective observations to instruction gaps but currently operates with no role activation.

Activate "process improvement engineer analyzing production incidents." Quality bars: every proposal traces from a specific retrospective observation to a specific instruction gap; necessity arguments explain why the mistake recurs without the proposed instruction; removal proposals from the quality review justify why the instruction no longer passes the necessity test.

### 4.5 New agent definitions

Create three new agent definitions for roles currently running without persona framing.

#### Spec author agent

File: `assets/agents/fbk-spec-author.md`

Activate "principal engineer writing technical specifications." Quality bars: surface ambiguity in behavioral contracts rather than silently assuming an answer; technical approach sections are specific enough that a reviewer can challenge design decisions and a task compiler can derive tasks without follow-up questions; refuse to hand-wave integration points — name the components, the data flow, and the failure modes.

Anti-default: the model's default spec-writing mode is compliant drafting — it agrees with the user's framing rather than probing for gaps. The persona activates the adversarial design review distribution.

Tools: Read, Grep, Glob (read-only — the skill handles writes).

#### Task compiler agent

File: `assets/agents/fbk-task-compiler.md`

Activate "tech lead decomposing a reviewed spec into implementable units." Quality bars: every AC traces to at least one task; every task traces to at least one AC; tasks include explicit file paths and completion gates; wave ordering reflects actual dependencies, not arbitrary sequencing.

Anti-default: the model's default decomposition produces tasks that are either too granular (one function per task) or too coarse (one wave per feature). The persona activates systematic decomposition that matches task boundaries to behavioral boundaries.

Tools: Read, Grep, Glob (read-only — the skill handles writes).

This single agent serves both the test-task and impl-task roles in `/fbk-breakdown`. The persona (role activation, quality bars, anti-defaults) is invariant across both roles — what differs is the task context injected by the spawn prompt (spec-only for test tasks, spec + test task files for impl tasks). Splitting into two agents would duplicate the identical persona into two files that differ only in the description field.

#### Implementer agent

File: `assets/agents/fbk-implementer.md`

Activate "senior engineer implementing against a reviewed specification." Quality bars: implementation follows the spec's technical approach, not an alternative design the agent prefers; code passes the referenced test tasks, not tests the agent writes ad-hoc; when the task file is ambiguous, implement the conservative interpretation and flag the ambiguity rather than guessing.

Anti-default: the model's default implementation mode produces tutorial-grade code — it works for the happy path but is harder to maintain than necessary. The persona targets maintainability: prefer composition over deep inheritance, name variables for their domain meaning, extract repeated logic into named functions, follow existing code patterns in the codebase. The pipeline's test-first gates and per-wave verification handle correctness — the persona's job is to ensure the code that passes those gates is also code other engineers can read, modify, and extend.

Tools: Read, Grep, Glob, Edit, Write, Bash (full implementation capability).

### Integration seam declaration

- [ ] `agents.md` guidance → all agent definitions: persona authoring principles referenced by agent authors when writing or modifying agent personas
- [ ] `/fbk-council` skill → restructured council agents: skill spawns agents with unchanged protocol, agents produce output shaped by restructured personas
- [ ] `/fbk-spec-review` skill → council agents + test-reviewer: skill orchestrates unchanged, agents operate with updated personas

## Testing strategy

### New tests needed

This feature modifies context assets (markdown files), not executable code. There are no unit-testable functions or runtime code paths. Verification is through structural validation and human assessment of output quality.

- **Structural validation**: Verify all modified and new agent files have valid YAML frontmatter with required fields (name, description, tools). For persona-only agents (council agents, new agent definitions): verify the full file does not exceed 40 lines. For agents with task logic (test-reviewer, improvement-analyst): verify the persona section (from body start to the first task-logic heading) does not exceed 40 lines; the full file length is unconstrained. — covers AC-02, AC-03, AC-04, AC-05, AC-06.
- **Documentation content validation**: Verify `agents.md` contains a persona authoring guidance section with required subsections: enterprise activation baseline, correctness-vs-maintainability rationale, persona structure (role activation, quality bars, anti-defaults), reference implementations, what not to include, and when personas are unnecessary. — covers AC-01.
- **Persona quality assessment**: Spawn each modified agent in isolation (not through a skill) with a task prompt representative of its domain. Verify the output demonstrates role activation (the agent's first substantive output paragraph references its professional role or domain authority), quality bars are observable in output structure, and no description-heavy patterns appear (expertise lists, personality preambles, communication style). This is a qualitative assessment, not an automated test — two reviewers may disagree on edge cases. — covers AC-02, AC-03, AC-04, AC-05, AC-06.

### Existing tests impacted

No automated test suite exists for context assets. The Martian benchmark evaluates code review quality (Detector + Challenger) but does not cover council, spec authoring, task compilation, or implementation agents.

### Test infrastructure changes

None — testing is structural validation and human assessment.

### User verification steps

UV-1: Read a restructured council agent file → persona is 20-35 lines with a role activation line, output quality bars section, and optional anti-defaults/authority sections. No "Your Identity," "Your Expertise," "Communication Style," or "Critical Behaviors" sections remain.

UV-2: Read the updated `agents.md` → persona authoring guidance section is present, covering enterprise activation baseline, persona structure (role activation, quality bars, anti-defaults), what not to include, and when personas are unnecessary. Research rationale (correctness vs maintainability) is included.

UV-3: Read each new agent file (`fbk-spec-author.md`, `fbk-task-compiler.md`, `fbk-implementer.md`) → each contains a role activation line grounding the agent in an enterprise professional role, output quality bars that are falsifiable, and optional anti-defaults naming the specific default behavior counteracted.

UV-4: Read the test-reviewer agent file → persona section added with role activation and quality bars. Existing checkpoint logic and evaluation criteria are preserved unchanged.

UV-5: Read the improvement-analyst agent file → persona section added with role activation and quality bars. Existing workflow (input contract, proposal output format, scope discipline) is preserved unchanged.

## Documentation impact

### Project documents to update

- `assets/fbk-docs/fbk-context-assets/agents.md`: Add persona authoring guidance section. This is the primary documentation deliverable. Include the correctness-vs-maintainability conclusion (personas improve maintainability, pipeline handles correctness) without academic citations — agent authors need the conclusion, not the research argument. The detailed rationale with citations lives in the agent-personas spec for anyone who wants the full argument.
- `CHANGELOG.md`: Add entry for agent persona restructuring under the 0.4.0 release.

### New documentation to create

None — all guidance is added to existing docs.

## Acceptance criteria

AC-01: `agents.md` contains a persona authoring guidance section covering: enterprise activation as the baseline, the correctness-vs-maintainability rationale, persona structure (role activation, output quality bars, anti-defaults), personas and spawn prompts, reference implementations, what not to include, and when personas are unnecessary.

AC-02: All 6 council agent files use the activation-focused pattern: role activation line, output quality bars, optional anti-defaults, optional authority section. No expertise lists, communication style sections, personality descriptions, or "How You Contribute" / "Critical Behaviors" sections.

AC-03: The test-reviewer agent file includes a persona with role activation and output quality bars. Existing checkpoint logic and evaluation criteria are preserved unchanged.

AC-04: The improvement-analyst agent file includes a persona with role activation and output quality bars. Existing workflow sections are preserved unchanged.

AC-05: Three new agent files exist: `fbk-spec-author.md`, `fbk-task-compiler.md`, `fbk-implementer.md`, each with activation-focused personas following the guidance in AC-01.

AC-06: All modified and new agents pass the persona authoring guidance's own criteria: role activation present, output quality bars are falsifiable (a quality bar is falsifiable if a reviewer can construct a specific output that violates it), no description-heavy patterns. This is a human judgment — structural tests verify the sections exist, but content quality is assessed by human review.

## Open questions

*None — all design decisions resolved during pre-spec discussion.*

## Follow-up work

Three new agent definitions (`fbk-spec-author`, `fbk-task-compiler`, `fbk-implementer`) are not usable until the skills that spawn them are updated to reference the agent definitions. The following skills need a separate spec for skill integration:

- `/fbk-spec`: currently runs as the main session with no agent delegation
- `/fbk-breakdown`: currently spawns unnamed teammates with inline task instructions
- `/fbk-implement`: currently spawns unnamed teammates with inline task instructions

## Dependencies

- Single-detector-precision spec (completed): established the prompting design principle and the activation-focused persona pattern used as the model for this work.
- Existing `agents.md` context asset doc: the persona guidance extends this existing doc.
- Existing council agent files: the restructuring modifies these in place.
- Existing test-reviewer and improvement-analyst agent files: persona additions modify these in place.
