# Code-review executable-path follow-on — Design Manifest

Design pages for finishing the migration of the code-review executable validation/handoff path onto the generic-agent contract, and extending the same tool-enforced guarantees to every finding-mode review type. A merge prerequisite for the `fbk/unified-review-shape` branch.

- design/overview.md — what the feature is, the two defects, the full-sweep scope, the component map (pipeline program plus review skills), and what stays unchanged.
- design/cli-lens-wiring.md — the first defect: the validator rejects every id-less finding; the fix wires the lens vocabulary in via an optional `--lens` flag on `validate` and `run`, leaving the default no-lens path byte-identical.
- design/normalized-handoff-and-rejoin.md — the second defect: the challenger sees the researcher's framing; the fix is a tool-enforced `normalize` step plus a positional re-join, with the full seven-stage data flow and the verdict-to-finding correlation key.
- design/composable-pipe-for-lens-presets.md — why test, coherence, and task review drive the pipeline through `validate --lens | severity-filter` instead of code review's `run`, and why no preset-file entries are added.
- design/contracts.md — the five contracts this feature introduces or changes, with the shared-convention check.

Decomposition rationale: vertical slices by the single boundary the feature protects — the validation vocabulary is set at the program's command-line boundary and never assumed from built-in constants inside a function the command calls — with one page per concern (lens wiring, neutral handoff and re-join, the divergent command shape for the three new review types) and one contracts page.

Decisions recorded: 9 — see `docs/decisions-log.md`, entries dated 2026-06-24. Eight in "Code-review executable-path follow-on — design phase": two operator-chosen fixes carried from the seed (wire the lens in; insert a normalize step), three operator forks resolved this phase (full enforcement sweep, the normalize step as a tool command, two plumbing paths accepted), and three determined by the existing code and ratified (positional correlation, the fixed min-length gate, per-preset wiring with an abstract spine). A ninth in "positional re-join hardening declined": position-only is locked and the echoed-index-token hardening is declined, after both cold reviews flagged the reorder limitation.
