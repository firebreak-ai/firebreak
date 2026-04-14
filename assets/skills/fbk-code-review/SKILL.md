---
description: >-
  Code review and remediation. Use when reviewing existing code, auditing
  for AI failure modes, performing post-implementation review, or
  co-authoring remediation specs from code review findings.
argument-hint: "[target-path or feature-name]"
allowed-tools: Read, Grep, Glob, Write, Edit, Bash, Agent
---

Read `.claude/fbk-docs/fbk-sdl-workflow/code-review-guide.md` for the behavioral comparison methodology, finding format, sighting format, orchestration protocol, and retrospective fields. Read `.claude/fbk-docs/fbk-sdl-workflow/ai-failure-modes.md` for the AI failure mode checklist used when no specs are available. Read `.claude/fbk-docs/fbk-design-guidelines/quality-detection.md` for structural detection targets applicable to all code reviews.

## Entry and Path Routing

Determine the invocation context:

- **Post-implementation review**: If invoked after `/implement` completion (the user accepted the stage-transition prompt), follow the post-implementation path in `references/post-impl-review.md`.
- **Standalone review**: For all other invocations, follow the conversational review path in `references/existing-code-review.md`.

## Source of Truth Handling

Check for existing specs — provided by the user or discovered in `ai-docs/`. If specs exist, use their ACs and UV steps as the primary comparison target. Run Intent Extraction for standalone and broad-scope reviews — documentation outside the spec often contains behavioral claims not covered by ACs. When no specs are available, the intent register and the AI failure mode checklist together form the comparison target. If no documentation and no existing code context is provided, ask the user what to review.

## Agent Team

Spawn agents as a team with fresh context per invocation. The agent complement is determined by the selected detection preset.

- **Tier 1 Detectors** (`fbk-t1-value-abstraction-detector`, `fbk-t1-dead-code-detector`, `fbk-t1-signal-loss-detector`, `fbk-t1-behavioral-drift-detector`, `fbk-t1-function-boundaries-detector`, `fbk-t1-cross-boundary-structure-detector`, `fbk-t1-missing-safeguards-detector`): Per-group detection agents, each with 3-5 assigned detection targets. Tools: Read, Grep, Glob. Construct all Tier 1 spawn prompts with identical code payloads in identical order to maximize prompt cache hits across agents.
- **Intent Path Tracer** (`fbk-intent-path-tracer`): Traces execution paths against the intent register. Tools: Read, Grep, Glob.
- **Test Reviewer** (`fbk-cr-test-reviewer`): Reviews test quality, test-intent alignment, and agentic test failure modes. Tools: Read, Grep, Glob.
- **Sighting Deduplicator** (`fbk-sighting-deduplicator`): Merges duplicate sightings before Challenger verification. No tools.
- **Challenger** (`fbk-code-review-challenger`): Verifies or rejects sightings. Tools: Read, Grep, Glob.

Inject the behavioral comparison methodology from `code-review-guide.md` and the relevant source of truth into each agent's spawn prompt. Agents do not inherit skills.

## Detection Presets

| Preset | Agents spawned | Use case |
|--------|---------------|----------|
| `behavioral-only` (default) | Groups 1-4 (value-abstraction, dead-code, signal-loss, behavioral-drift) + Intent Path Tracer | Highest signal-to-noise for most reviews |
| `structural` | Groups 5-7 (function-boundaries, cross-boundary-structure, missing-safeguards) | Architecture and design pattern analysis |
| `test-only` | Test Reviewer | Dedicated test quality pass |
| `full` | All 9 agents | Complete analysis — runs preset waves sequentially |

The default preset is `behavioral-only`. When the user does not specify a preset, apply `behavioral-only` silently. When the user requests a different scope by name (e.g., 'run a full review', 'also check the tests', 'structural review'), the orchestrator interprets and maps to the appropriate preset or toggle. Do not prompt users to select a preset.

Per-group toggles override any preset. Enable or disable individual groups by name to customize the agent complement. For example, `behavioral-only` + `test-reviewer` runs Groups 1-4 + Intent Path Tracer + Test Reviewer.

## Review Report

Create a review report file at the start of every review: `fbk-code-review-<YYYY-MM-DD>-<HHMM>.md` in the project's working directory. Write the intent register, verified findings, and retrospective to this file as the review progresses. The user opens this file to see rendered diagrams and review results.

## Pre-Spawn Linter Execution

Before spawning Detectors, discover and run project-native linters and static analysis tools. Search for lint configurations (`.eslintrc`, `eslint.config.*`, `.pylintrc`, `pyproject.toml`, `golangci-lint` configs) and run available tools. Capture raw text output, truncated to the first 100 findings if output is large. Include the linter output as supplementary context in each Detector's spawn prompt. Linter output is context, not pre-formed sightings — the Detector reads it to understand what mechanical issues the linter already caught and focuses on issues linters miss. Tag any sightings derived from linter output with detection source `linter`.

## Intent Extraction

Complete these steps before spawning Detectors.

### Discover documentation

Search for intent-bearing documents in priority order:
1. Feature specs in `ai-docs/` (acceptance criteria and UV steps)
2. README, CLAUDE.md, CONTRIBUTING.md, architecture docs
3. Inline module-level documentation (JSDoc, docstrings, module headers)
4. CI/CD configuration, deployment docs, API documentation

### Build the intent register

From discovered documentation, produce a structured intent register with two parts:

**Intent claims**: A list of up to 30 behavioral claims the project makes about itself. Each claim is one sentence describing what the project or a specific module is supposed to do. Prefer claims that are specific and verifiable.

**Intent diagram**: Generate a Mermaid diagram capturing module relationships, data flow, and key behavioral contracts. Optimize for the VSCode markdown preview renderer:
- Use `graph TD` or `graph LR` for data flow and module relationships
- Keep node labels under 30 characters
- Use subgraphs to group related modules
- Label edges with the behavioral contract (e.g., "filters by interest", "scores via AI")
- Avoid `classDef`, `click`, `callback`, and other advanced features that may not render

Write the intent register (claims + diagram) to the review report file.

### User checkpoint

Tell the user the review report file is ready for review. Ask specific questions to close ambiguity — areas where documentation is silent, contradictory, or where multiple interpretations exist. Proceed after the user confirms, corrects, or instructs the agent to continue as-is.

### Supplement from code

Where the intent register has gaps (modules with no documentation coverage), derive intent from code structure: function names, type signatures, module organization, and cross-module call patterns. Update the diagram and claims in the review report file.

## Detection-Verification Loop

Run the iterative detection and verification loop:

1. Resolve the selected detection preset to its agent groups. Spawn the preset's agents in parallel:
   - **Tier 1 Detectors**: Spawn each selected per-group agent by name. Inject into each spawn prompt: target code file contents first, then linter output (if available), then intent register claims last. Construct all Tier 1 spawn prompts with identical code payloads in identical order to maximize prompt cache hits across agents. Randomize the order of detection targets within each agent's group payload before injection. Groups 2 (dead-code) and 6 (cross-boundary-structure) also receive the Mermaid diagram; all other Tier 1 groups receive claims only.
   - **Intent Path Tracer** (if included in preset): Spawn `fbk-intent-path-tracer`. Inject: intent register (claims + Mermaid diagram) and entry points with associated intent claims. The Path Tracer reads code files on demand via tools.
   - **Test Reviewer** (if included in preset): Spawn `fbk-cr-test-reviewer`. Inject: test files in scope + their production imports first, then intent register claims (no Mermaid diagram) last.
   Instruct each agent to tag sightings with its detection source.

Identify entry points for the Intent Path Tracer from three sources: (1) Intent register — behavioral claims describing user-facing actions or triggers. (2) Conventional entry points — main files, route/command handlers, event listeners, exported CLI commands, cron/scheduler callbacks. (3) Package configuration — scripts in package.json, entry fields, CI workflow triggers. Provide up to 10 entry point file paths with the intent claim each relates to, prioritized by coverage of intent claims.

1a. When the preset wave spawned multiple agents, spawn the Sighting Deduplicator (`fbk-sighting-deduplicator`) with the complete sighting list from all agents in the wave. The Deduplicator merges sightings at the same file and overlapping line ranges, returns a deduplicated sighting list and a merge log. When the preset wave contains a single agent, skip the Deduplicator — pass sightings directly to Challenger verification. Record merge count and merged pairs from dedup logs in the retrospective.

For `full` runs, execute each preset wave sequentially: `behavioral-only` → `structural` → `test-only`. Within each wave, spawn all agents in parallel. Each wave runs its own Sighting Deduplicator (skipped for single-agent waves) and Challenger pass. After all preset waves complete, perform cross-preset finding dedup inline: if two findings from different presets reference the same file and overlapping line ranges, keep the higher-severity finding and note both detection sources. This cross-preset dedup is orchestrator-level — no additional agent spawn.

2. Collect sightings
3. Spawn Challengers with: target code file contents first, then sightings to verify, then verification instructions last. Batch sightings: spawn 1 Challenger per 5 sightings, grouped by originating detection category (matching the Tier 1 group, Intent Path Tracer, or Test Reviewer that produced them). Spawn all Challengers in parallel. Challengers run per preset wave, scoped to that wave's deduplicated sightings.
4. Collect verified findings and rejections
4a. After each verification round, append verified findings to the review report file.
4b. Filter each verified finding through two gates. Resolve the scripts directory: `S=$([ -f scripts/charter-filter.sh ] && echo scripts || echo ~/.claude/scripts)`. First, run `bash "$S/charter-filter.sh" <finding_type> <active_preset>` — drop findings that fail (out-of-charter for the active preset). Second, run `bash "$S/confidence.sh" <self_score> <agent_count> <challenger_verdict>` — drop findings with final confidence below 8.0. Record all excluded findings in the retrospective under a "Filtered" section with the reason (out-of-charter or below-threshold) and score.
5. When applying fixes for a verified finding, grep the same file and package for all instances of the identified pattern. Apply the fix to every instance.
6. Run additional rounds for weakened but unrejected sightings
7. Terminate when a round produces no new sightings above `info` severity (or no sightings), or after a maximum of 5 rounds.

In iterative detection rounds, only respawn an agent if its previous instance produced at least one verified sighting above info level. If an agent's sightings all failed Challenger verification or were info-level only, do not respawn that agent in the next round. Maximum 5 repetitions per agent regardless of output. This applies independently to each Tier 1 group, the Intent Path Tracer, and the Test Reviewer. When a merged sighting survives Challenger verification, all originating agents (per the Deduplicator's merge log) are credited for respawn eligibility.

Only verified findings surface to the user. Rejected sightings are excluded.

## Post-Fix Verification

After all fixes from a review session are applied, run the full test suite and confirm zero failures before closing the review.

## Broad-Scope Reviews

When the user requests a full codebase review rather than specific modules:

1. Survey the project structure and identify reviewable units
2. Propose a review order to the user
3. Spawn the selected preset's agent complement per unit. For broad-scope reviews with multiple independent units, spawn parallel agent teams — each unit gets its own preset-driven agent set reviewing independently with its own context. Agents do not share state across units.
4. Accumulate verified findings across units, watching for cross-module patterns
5. After all units complete, perform cross-unit pattern deduplication: identify findings from different units that describe the same underlying pattern, assign a shared pattern name (e.g., "string-error-dispatch", "dead-handler-registration"), and group them in the retrospective. Deduplicated findings retain their individual IDs but share the pattern label.
6. Checkpoint with the user after each unit

## Stuck-Agent Recovery

When a Detector or Challenger agent becomes unresponsive (no output within the expected time frame), relaunch it once with the same spawn prompt and context. If the relaunched agent is also unresponsive, escalate to the user with a summary of what the agent was assigned and where it stalled. Never perform the stuck agent's work directly — the orchestrator coordinates, it does not substitute for agents.

## Spec Conflict Detection

When multiple specs exist for the reviewed code, compare them for consistency. Surface conflicts between specs, or between specs and code, for user discussion during the conversational review.

## Retrospective

After the review completes, append the retrospective to the review report file, following the fields defined in `code-review-guide.md`.

After the retrospective is written to disk, invoke `/fbk-improve <feature-name>` to analyze the retrospective for pipeline improvement opportunities.
