Each feature has a single retrospective file: `ai-docs/<feature-name>/<feature-name>-retrospective.md`. Every stage writes to this file. Create it with the feature header if it does not exist. Read the file before writing to preserve existing content from prior stages.

The retrospective has two kinds of content:

**Cumulative sections** (updated by each stage):
- **Timeline**: when each stage started and completed
- **Key decisions**: numbered list, each with rationale and the stage that made it
- **Scope changes**: what changed from initial scope and why

**Stage sections** (appended once by the owning stage):
- **Stage 1: Spec** — clarifying questions that revealed ambiguity, scope inclusions/exclusions, open questions deferred to later stages
- **Stage 2: Spec Review** — perspectives invoked, blocking findings and resolutions, spec revisions, iteration count
- **Stage 3: Breakdown** — compilation attempts, wave structure and rationale, task count, scope adjustments from compilation
- **Stage 4: Implementation** — metrics (per-task, per-wave, escalation counts), upstream traceability, failure attribution (see `implementation-guide.md` for field definitions)
- **Stage 5: Code Review** — findings summary, detection source breakdown, false positive rate
