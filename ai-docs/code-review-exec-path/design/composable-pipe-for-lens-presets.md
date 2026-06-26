# Why the three new review types use a different command shape

## The discovery

Code review drives the pipeline through one all-in-one `run` command: `pipeline run --preset <P> --min-severity <S>`. That command does three things in sequence — validate, domain-filter, severity-filter — and the domain-filter step reads a preset file to decide which finding types are allowed. The preset file contains only code review's four type-filters (`behavioral-only`, `structural`, `test-only`, `full`).

Test review, coherence review, and task review have no entry in that preset file, and their finding types (the kinds of problem each lens looks for) are not registered there either. So `pipeline run --preset <name>` simply fails for them with "unknown preset." Code review's all-in-one command is not available to the other three.

## The resolution: let the lens do the type-filtering

The three new review types use the composable pipe instead:

```
<researcher findings> | pipeline validate --lens <type>-lens.md | pipeline severity-filter --min-severity <threshold>
```

No domain-filter step is needed, because the lens-parameterized validator already does that job. `validate_sighting(finding, vocab)` rejects any finding whose type is not in the lens's declared type set. A finding with a type the lens does not recognize is rejected at validation, before any filtering — so for these review types the lens is the single source of which types are allowed.

This is why no entries are added to the preset file. Adding them would create a second place that lists each review type's finding types, duplicating what the lens already declares — two lists that can drift apart. The lens stays the single authority.

## The consequence accepted

The four finding-mode review types are not wired identically at the command level. Code review keeps its `run` command and its preset-file type-filter; the other three use the `validate --lens | severity-filter` pipe and let the lens filter types. This was an explicit operator choice (two paths accepted) over the alternatives of teaching `run` to read the lens or migrating code review onto the pipe and retiring `run`.

The **guarantees** each path delivers are the same — lens-validated findings, a tool-enforced neutral handoff, lens-validated verdicts. Two observable behaviors are **not** identical, and the design states them rather than claiming uniformity it does not have:

- **Finding-id numbering differs.** Code review's `run` reassigns contiguous `S-NN` ids *after* its severity filter, so its ids have no gaps. The composable pipe assigns ids at the `validate` stage and then `severity-filter` drops below-threshold records *without* renumbering, so the surviving ids can be non-contiguous (for example `S-01, S-03, S-06`). This does not affect the re-join, which is positional, and the human-facing `F-NN` identifiers are assigned later regardless. It is an internal cosmetic difference, not a guarantee gap.
- **Severity filtering is not lens-governed on either path.** The `severity-filter` command ranks against the built-in severity order, not the lens's declared severities. The lens's severity set *is* enforced — but at the `validate --lens` stage, which rejects a finding whose severity is outside the lens (so a `task-review` finding marked `info`, a severity the task lens does not declare, is rejected at validation). The threshold filter itself stays built-in. So the lens is the single authority for which *types* are allowed and which severities are *valid*, while the *threshold* comparison is a fixed ordering shared by all review types.

Code review is the honest special case because it alone carries a preset-file type-filter.

## The one cosmetic loss

Dropping the domain-filter step for the three new review types also drops its "DROPPED (domain): …" log line for out-of-type findings. Those findings are still reported — as "REJECTED: invalid type …" lines from validation — so nothing is silently lost; only the log wording differs.

## A note for a future implementer

Do not "fix" the absent domain-filter step by adding these review types to the preset file. The absence is deliberate: the lens-parameterized validator is the type-filter for these review types. A catching test for each (a finding whose type is valid under code review's built-in vocabulary but not under this review type's lens must be rejected by `validate --lens`) proves the substitution is safe.
