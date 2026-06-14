---
title: "Design Manifest"
type: concept
sources:
  - firebreak-sdl-workflow
tags:
  - sdl-pipeline
  - pattern
  - design-phase
  - refactored-sdl
created: 2026-05-26
updated: 2026-05-28
---

## Design Manifest

A per-feature index file in the feature directory listing every design page produced or modified during that feature's design phase. The mechanical anchor for the design-phase [[hybrid-gate-pattern]] check.

### Why this exists

When the [[fbk-design]] phase writes several design pages into `ai-docs/<feature-name>/design/`, a question arises at gate time: did design actually produce what it should have, or did the agent silently skip a topic? An explicit index of "what design said it wrote" lets the gate check the claim against the actual files on disk, cheaply and deterministically.

### File location and shape

`ai-docs/<feature-name>/design-manifest.md` — lives in the feature directory alongside the PRD, behavior inventory, and other ceremony products. Deleted at squash-merge along with the rest of the feature directory. (Enduring decisions go to the durable decisions log, not here.)

The manifest is markdown with a structured page list:

```markdown
# Design Manifest: <feature-name>

## Capabilities designed

- `design/<slug>.md` — <one-line description>

## Pages modified (changes to existing assets)

- `design/<slug>.md` — <one-line summary of change>

## Decisions recorded

- durable decisions log — <count> entries appended this phase (the decisions log is a durable artifact, not part of the feature directory; the manifest only points to it)

## Notes
- Free-form notes about scope of design phase work that aren't tied to specific pages.
```

### Bidirectional gate check

At design closure, the [[hybrid-gate-pattern]] runs a bidirectional check against the feature directory:

**Manifest → files.** Every page listed in the manifest exists as a file under `ai-docs/<feature-name>/design/`. Mechanically verifiable.

**Files → manifest.** Every design page present in that directory appears in the manifest. Mechanically verifiable by listing the directory.

Drift in either direction fails the gate. A manifest entry pointing to a non-existent page means design over-promised. A design page absent from the manifest means design did work the operator can't see in the index.

### Writing the manifest

[[fbk-design]] writes the manifest incrementally as it produces or modifies design pages. The manifest is not produced as a single batch at design's end — it is updated immediately after each page is written. This means an interrupted design phase leaves a partial manifest that accurately reflects the work done up to that point.

The gate runs the bidirectional check against the final state of the manifest at design closure.

### Related

- [[hybrid-gate-pattern]] — the gate that consumes the manifest
- [[fbk-design]] — the phase skill that produces the manifest
- [[stage-transition-protocol]]
- [[firebreak-sdl-workflow]]
