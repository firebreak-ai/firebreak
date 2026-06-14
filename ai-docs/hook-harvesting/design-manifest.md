# Design Manifest — Deterministic Metrics Plane (Hook Harvesting)

- design/overview.md
- design/capture-sources.md
- design/reporting-and-injection.md
- design/configuration-and-lifecycle.md
- design/contracts.md

Decomposition rationale: vertical slices by capability boundary — each page owns one capability a reader reasons about as a unit (where events originate, what consumes them, how the plane is governed), plus a contracts page for the schemas that cross process and trust boundaries.

Decisions recorded: 11 (appended to docs/decisions-log.md under 2026-06-10, design phase)
