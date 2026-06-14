---
title: "Quality Scan Technique"
type: concept
sources:
  - firebreak-quality-rubric-sketch
  - firebreak-sdl-workflow
tags:
  - sdl-pipeline
  - pattern
  - technique-skill
  - code-quality
  - review
  - refactored-sdl
created: 2026-05-26
updated: 2026-05-26
---

## Quality Scan Technique

A Pocock-style top-five code-quality scan run during code review. Surfaces the five highest-priority quality issues in the change set as structured findings. **Scan-only** — does not auto-fix. The operator (or a downstream skill invocation) decides what to do with each finding. A defined [[technique-skill]] invoked by [[fbk-code-review]] and optionally invokable out-of-ceremony for any diff.

A slimmer, in-ceremony cousin of the broader [[firebreak-quality-rubric-sketch]] vision — where the rubric is the full multi-dimensional eval system for self-improvement loops, the quality scan is the focused operator-facing five-item list at code-review time.

### Why scan-only

The strong temptation is to add an "auto-fix the top one" step. We deliberately don't, for two reasons:

**Modularity.** The capability is most useful when separated from the decision about what to do with the findings. The operator may want to "design a fix for the top one" via [[fbk-design]], or "ignore item three because it's out of scope," or "just file these for later." Coupling fix-application to the scan locks in one of those choices. Separating them keeps the capability composable.

**Trust.** Auto-fix at code-review time alters the artifact under review without going through the SDL's design-spec-breakdown discipline. A "quick fix" can introduce its own quality issues, bypass [[test-integrity-locking]], or change behavior the spec didn't anticipate. Scan-only preserves the discipline that fixes go through the full pipeline.

### Interaction shape

The technique is invoked with a change set (a diff, a feature directory's modified files, or the implementation produced during the current SDL cycle). The reviewer follows three steps:

1. **Survey the change set.** The reviewer reads the changed code, the spec it implements, and any directly referenced helpers in the surrounding codebase. The goal is to understand what was written and against what intent.

2. **Identify quality issues.** The reviewer enumerates candidate issues using the rubric vocabulary established in [[firebreak-quality-rubric-sketch]] — single-concern violations, missed reuse, scope creep, naming issues, comment quality, and similar. Issues are evaluated per the [[firebreak-code-quality-definition]] axes (comprehension cost, modification cost, modification confidence).

3. **Rank and surface the top five.** The reviewer selects the five highest-leverage issues by combined priority (severity × frequency × ease-of-addressing) and presents them as structured findings, each with location, type, description, and one suggested approach to address.

If fewer than five issues exist, the scan returns however many exist (zero is a valid result). If many exist, only the top five are surfaced — the technique is deliberately bounded.

### Output shape

A structured markdown file with one entry per finding. Each finding carries a **severity** field — critical / substantive / minor — using the same severity taxonomy as [[fresh-eyes-technique]]:

```markdown
# Quality Scan: <feature-name>

## Findings (top 5)

### 1. <slug>
- **Severity:** critical | substantive | minor
- **Type:** <single-concern | reuse-missed | scope-creep | naming | comments | other>
- **Location:** <file>:<line range>
- **Issue:** <one-line description>
- **Suggested approach:** <one or two sentences on how to address>

### 2. <slug>
…
```

The file lives in the feature directory at `quality-scan.md` or similar, and is part of the code-review ceremony products deleted at squash-merge.

### What follows the scan

The scan's output is consumed by:

1. **The code-review gate.** Mechanical check: the scan ran and produced an artifact with the expected structure (severity field populated, top-five or fewer entries). The gate does not block on severity — even critical-severity findings surface to the operator rather than halting the pipeline. The operator's response to findings is the decision point.
2. **The operator.** The operator decides what to do with each finding: address now (via a small fix or by spinning up a follow-up feature through [[fbk-design]]), defer to backlog, or dismiss with rationale.
3. **Future scans.** Findings dismissed-with-rationale stay surfaced if they reappear in later code-review cycles, but the rationale travels with them. The technique does not re-decide each cycle.

### Out-of-ceremony invocation

`/quality-scan <path>` or similar can be invoked outside the SDL on any code path or diff. Output shape is identical. The operator may use this for ad-hoc inspection of legacy code, third-party diffs, or to dry-run the scan on a draft change before formal code review.

### What it does not do

- **Does not auto-fix.** Findings are surfaced; addressing them is a separate decision.
- **Does not gate on aesthetic preferences.** The scan is rooted in [[firebreak-code-quality-definition]] axes; preferences unsupported by those axes (e.g., "I'd have named this differently with no other reason") don't surface.
- **Does not replace the broader quality rubric.** The [[firebreak-quality-rubric-sketch]] is a multi-dimensional eval system for self-improvement loops; the quality scan is the operator-facing top-five list at code-review time. They share vocabulary and concepts but operate at different scopes.
- **Does not run on pre-implementation artifacts.** Upstream artifacts get their own review at their gates (fresh-eyes at intent/design, the council at the spec gate). Quality-scan operates on actual code.

### Determinism note

Within a single scan run, the technique uses a fixed judge model and produces stable findings on the same input. Different scan invocations on the same code may produce slightly different top-five orderings due to LLM variance — the gate accepts this and operates on the artifact actually produced. Per-finding determinism (the same issue always shows up if present) is more reliable than ordering determinism (the same five always appear in the same order).

### Related

- [[firebreak-quality-rubric-sketch]] — the broader rubric this technique is a focused subset of
- [[firebreak-code-quality-definition]] — the axes findings are evaluated against
- [[adversarial-code-review]] — related code-review pattern, complementary not redundant
- [[grilling-technique]] · [[fresh-eyes-technique]] · [[test-review-technique]] — sibling technique skills
- [[hybrid-gate-pattern]] — quality-scan output serves as one of two semantic anchors for the code-review gate
- [[fbk-code-review]] — the phase skill that invokes the scan
- [[firebreak-sdl-workflow]]
