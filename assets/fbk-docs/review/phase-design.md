# Design review

The runtime sends this file's Decision, Check and Later deliverables sections to the design reviewer. Keep each item on one line.

## Decision

Can the proposed architecture satisfy accepted intent through feasible shared contracts and dependencies?

## Check

- Check the architectural approach, tradeoffs, shared interfaces, dependency direction, significant failure modes, and feasibility evidence for consequential assumptions.
- Trace architectural commitments to accepted intent. Private implementation details can be settled during implementation.
- Check who owns shared policies and whether plausible changes require synchronized edits across independent owners. Demonstrate the maintenance consequence before blocking; small cohesive modules, test seams, and private layout preferences alone are not defects.

## Later deliverables

- specification
- task breakdown
- implementation
- executable tests
- delivery documentation
