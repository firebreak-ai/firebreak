Each feature has a single retrospective file: `ai-docs/<feature-name>/<feature-name>-retrospective.md`. Every stage writes to this file. Create it with the feature header if it does not exist. Read the file before writing to preserve existing content from prior stages. Each stage appends its section rather than overwriting — call `fbk.retro.append_section(retrospective_path, stage_name, content)` to do this; the function reads the file before writing so prior stage sections survive.

The retrospective has two kinds of content:

**Cumulative sections** (updated by each stage):
- **Timeline**: when each stage started and completed
- **Key decisions**: numbered list, each with rationale and the stage that made it
- **Scope changes**: what changed from initial scope and why

**Stage sections** (appended once by the owning stage):
- **Stage 1: Intent** — clarifying questions that revealed what the work is and why, the PRD/inventory produced, open questions deferred
- **Stage 2: Design** — the module shape and contracts proposed, the decisions appended to the durable decisions log, the decomposition rationale
- **Stage 3: Spec** — clarifying questions that revealed ambiguity, scope inclusions/exclusions, open questions deferred to later stages
- **Stage 4: Spec Review** — perspectives invoked, blocking findings and resolutions, spec revisions, iteration count
- **Stage 5: Breakdown** — compilation attempts, wave structure and rationale, task count, scope adjustments from compilation
- **Stage 6: Implementation** — metrics (per-task, per-wave, escalation counts), upstream traceability, failure attribution (see `implementation-guide.md` for field definitions)
- **Stage 7: Code Review** — findings summary, detection source breakdown, false positive rate
