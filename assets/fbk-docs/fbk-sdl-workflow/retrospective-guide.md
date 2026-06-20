Each feature has a single retrospective file: `ai-docs/<feature-name>/<feature-name>-retrospective.md`. Every stage writes to this file. Create it with the feature header if it does not exist. Read the file before writing to preserve existing content from prior stages. Each stage appends its section rather than overwriting — call `fbk.retro.append_section(retrospective_path, stage_name, content)` to do this; the function reads the file before writing so prior stage sections survive.

The retrospective has two kinds of content:

**Cumulative sections** (updated by each stage):
- **Timeline**: when each stage started and completed
- **Key decisions**: numbered list, each with rationale and the stage that made it
- **Scope changes**: what changed from initial scope and why

**Stage sections** (appended once by the owning stage):
- **Intent** — clarifying questions that revealed what the work is and why, the PRD/inventory produced, open questions deferred
- **Design** — the module shape and contracts proposed, the decisions appended to the durable decisions log, the decomposition rationale
- **Spec** — clarifying questions that revealed ambiguity, scope inclusions/exclusions, open questions deferred to later stages
- **Spec Review** — perspectives invoked, blocking findings and resolutions, spec revisions, iteration count
- **Breakdown** — compilation attempts, wave structure and rationale, task count, scope adjustments from compilation. Where compilation stumbled, name the underlying cause class (such as an underspecified contract, a hidden dependency between tasks, or an ambiguous sizing call) rather than only listing what broke. Call out any candidate improvement to the breakdown step that this run suggests, and note anything earlier review should have caught but let through. Surface these only where they genuinely came up — skip the headings rather than inventing entries.
- **Implementation** — metrics (per-task, per-wave, escalation counts), upstream traceability, failure attribution (see `implementation-guide.md` for field definitions). For attribution, group failures by the same root-cause classes the implementation stage records — spec gap, compilation gap, implementation error, process gap — rather than recording each failure in isolation, so the retrospective lines up with what implementation captured. Call out any candidate improvement to the pipeline this run points to, and note anything an earlier stage should have caught but let reach implementation. Add these only where the thinking genuinely occurred; leave them out otherwise.
- **Code Review** — findings summary, detection source breakdown, false positive rate. Group the findings by root-cause class so a pattern across them is visible, not just a flat tally. Call out any candidate improvement to the review step the run suggests, and — most useful here — what each review pass missed and why it slipped through, so future passes can close the gap. Record these only where they reflect real observations from the run, not as boxes to fill.
