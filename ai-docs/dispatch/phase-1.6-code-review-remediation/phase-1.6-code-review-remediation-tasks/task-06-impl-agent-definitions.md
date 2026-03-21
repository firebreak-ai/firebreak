---
id: T-06
type: implementation
wave: 3
covers: ["AC-04", "AC-08", "AC-13"]
files_to_create: ["home/dot-claude/agents/code-review-detector.md", "home/dot-claude/agents/code-review-challenger.md"]
files_to_modify: []
test_tasks: ["T-01"]
completion_gate: "T-01 tests 4-17 pass (both agents exist, have correct frontmatter fields, correct tools allowlists, correct description language)"
---

## Objective

Creates the Detector and Challenger agent definition files at `home/dot-claude/agents/code-review-detector.md` and `home/dot-claude/agents/code-review-challenger.md`.

## Context

The Detector and Challenger are focused agents spawned as a team by the `/code-review` skill orchestrator. They never operate in the main session — they always get clean context through the team model. The orchestrator injects the behavioral comparison methodology from `docs/sdl-workflow/code-review-guide.md` and the AI failure mode checklist from `docs/sdl-workflow/ai-failure-modes.md` into each agent's spawn prompt. The agents do not need `skills` frontmatter.

The existing agent definition at `home/dot-claude/agents/test-reviewer.md` provides the frontmatter convention: YAML between `---` delimiters with `name`, `description`, `tools`, `model` fields. Follow that exact convention.

**Detector constraints:**
- `name:` value must contain `detector` (case-insensitive)
- `description:` must contain code analysis language — at least one of: `analysis`, `analyz`, `detect`, `code review`, `pattern` (case-insensitive)
- `tools:` must list exactly `Read, Grep, Glob, Bash` — read-only access plus Bash for project-native tool discovery. Must NOT contain `Write` or `Edit`.
- `model:` set to `sonnet`
- Body must reference sightings with the `S-` ID format
- Body must include an instruction to check for project-native analysis tools (lint configs, type checkers, static analysis) before falling back to manual code reading

**Challenger constraints:**
- `name:` value must contain `challenger` (case-insensitive)
- `description:` must contain adversarial verification language — at least one of: `adversarial`, `verif`, `challenger`, `skeptic`, `evidence` (case-insensitive)
- `tools:` must list exactly `Read, Grep, Glob` — pure analysis, no tool execution. Must NOT contain `Bash`, `Write`, or `Edit`.
- `model:` set to `sonnet`
- Body must reference findings with the `F-` ID format
- Body must include rejection/disproval capability language — at least one of: `reject`, `disprove`, `dismissed`, `counter-evidence`

## Instructions

1. Read `home/dot-claude/agents/test-reviewer.md` for the frontmatter convention and body structure.

2. Create `home/dot-claude/agents/code-review-detector.md`:

   Frontmatter:
   ```yaml
   ---
   name: code-review-detector
   description: "Analyzes code through behavioral comparison, producing sightings of potential issues by describing what code does and comparing against specs or the AI failure mode checklist. Use for code analysis, pattern detection, and behavioral comparison tasks."
   tools: Read, Grep, Glob, Bash
   model: sonnet
   ---
   ```

   Body content (write as direct-address imperatives following the test-reviewer pattern):

   a. Opening instruction: "Analyze the target code through the behavioral comparison lens provided by the orchestrator. Describe what each function or module does, then compare that behavior against the source of truth (spec ACs or AI failure mode checklist)."

   b. **Project-native tool discovery** section: "Before reading code manually, check for project-native analysis tools. Search for lint configurations (`.eslintrc`, `eslint.config.*`, `.pylintrc`, `pyproject.toml`), type checker configs (`tsconfig.json`, `mypy.ini`), and static analysis setups. Run available tools via Bash and incorporate their output into your analysis. Fall back to manual code reading with Grep and Glob when no project-native tools are available."

   c. **Sighting output** section: "Record each observation as a sighting using the format provided by the orchestrator. Assign a sequential sighting ID starting from `S-01`. Assign a category to each sighting: `semantic-drift`, `structural`, `test-integrity`, or `nit`. Describe what you observed in behavioral terms — what the code does, not what is wrong with it."

   d. **Scope discipline** section: "Analyze only the code the orchestrator directs you to. Do not expand scope beyond what is indicated. Do not write files — you are read-only."

3. Create `home/dot-claude/agents/code-review-challenger.md`:

   Frontmatter:
   ```yaml
   ---
   name: code-review-challenger
   description: "Performs adversarial verification of code review sightings, demanding concrete evidence before promoting a sighting to a verified finding. Use for evidence-based assessment, skeptical review, and adversarial verification tasks."
   tools: Read, Grep, Glob
   model: sonnet
   ---
   ```

   Body content:

   a. Opening instruction: "Verify or reject each sighting provided by the orchestrator. You are a skeptic — demand concrete proof for every observation. A sighting becomes a verified finding only when you can demonstrate the issue with evidence from the code."

   b. **Verification protocol** section: "For each sighting, read the referenced code location and the source of truth. Apply the behavioral comparison lens: describe what the code does, then assess whether the Detector's observation is accurate. Produce one of two outcomes for each sighting:"

   c. **Verified finding**: "If the sighting is accurate, promote it to a verified finding. Assign a sequential finding ID starting from `F-01`. Preserve the sighting's location and category (you may reclassify the category if evidence warrants). Provide concrete evidence — the specific code path, line reference, or behavioral proof that confirms the issue."

   d. **Rejection**: "If the sighting is inaccurate or unsubstantiated, reject it with counter-evidence. State what the code actually does and why the Detector's observation does not hold. Disproved sightings do not surface to the user."

   e. **Scope discipline** section: "Do not generate new sightings. Your role is to verify or reject the sightings you received. Do not write files — you are read-only."

## Files to create/modify

- `home/dot-claude/agents/code-review-detector.md` (create)
- `home/dot-claude/agents/code-review-challenger.md` (create)

## Test requirements

This is an implementation task. The corresponding test task T-01 validates:
- Tests 4-10: Detector exists, has frontmatter, correct name, non-empty description, correct tools (Read/Grep/Glob/Bash, no Write/Edit), code analysis language in description
- Tests 11-17: Challenger exists, has frontmatter, correct name, non-empty description, correct tools (Read/Grep/Glob, no Bash/Write/Edit), adversarial verification language in description

## Acceptance criteria

- AC-04: Both agent descriptions use matchable language for their respective roles (code analysis/pattern detection for Detector, adversarial verification/evidence-based assessment for Challenger)
- AC-08: Detector tools are `Read, Grep, Glob, Bash`; Challenger tools are `Read, Grep, Glob`. Neither has Write or Edit. The orchestrator is the single writer.
- AC-13: The Detector agent definition includes instructions to discover and use project-native lint/AST/static analysis tools via Bash before falling back to manual code reading

## Model

Haiku

## Wave

Wave 3
