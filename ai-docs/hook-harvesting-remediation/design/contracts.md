# Design contracts — hook-harvesting remediation

This remediation did not run a separate `/fbk-design` phase: it fixes defects in an
already-shipped, already-designed feature, so its contracts are **spec-originated**
(`IF-S-NN`) and authored directly in the spec's `## Interface contracts` section. There are
therefore no design-originated (`IF-D-NN`) contracts to carry from this page.

The authoritative envelope and module contracts for the underlying feature remain those in
`ai-docs/hook-harvesting/design/contracts.md` (`IF-D-01`…`IF-D-10`); this remediation does
not change their signatures, only the implementations that were found to diverge from them.

_No new design-originated contracts. See the spec's `## Interface contracts` for the
spec-originated (`IF-S`) remediation contracts._
