# Durable-doc reconciliation — observability substrate

**Advisory only. Does not gate.** Compares the project's durable docs (architecture
overview, glossary, changelog, readme, decisions log) against the shipped substrate
code. Each item is tagged `[drift]` (doc contradicts or omits shipped behavior) or
`[note]` (minor / advisory).

**One-line summary:** Four real drifts — the architecture overview's measurement
section still describes only the old hook-harvesting capture and omits the whole
substrate; the changelog has no 0.5.2 section so the substrate is unrecorded; the
glossary is missing the four agreed terms (shape, topology, asset bundle, workflow
journal); and the readme command list omits `run-retro` — plus two notes and one
confirmed spec-internal inconsistency around what "clean-complete" requires.

---

## Items

### [drift] docs/architecture-overview.md — "Measurement (in progress)" omits the substrate

The measurement section still describes only the earlier hook-harvesting work: two
capture sources feeding "one report command" that aggregates per-stage metrics. It
says nothing about what shipped in this feature — the durable per-run record, the
shape/topology vocabulary, harvest-at-close, capture-level parity for the record,
or the run-retro reader. A cold agent reading this section would not learn the
substrate exists.

What the shipped code establishes that the section should describe:
- **Per-run record** — one JSON file per run at `.fbk-capture/runs/<run-id>.json`,
  assembled at workflow close (`fbk/harvest.py`), to the schema in
  `ai-docs/observability-substrate/design/record-schema.md`.
- **Shape / topology vocabulary** — every unit is labeled with one of five closed
  shapes (distill, implement, review, synthesize, gate) and a topology of
  cardinality (single / fan-out) and stance (collaborative / adversarial)
  (`fbk/shapes.py`, `fbk/attribution.py`).
- **Harvest-at-close** — the record is finalized only when the run is closed, fired
  from the hook router on `PostToolUse(Workflow)` and swept on `SessionStart`
  (`fbk/finalize.py`).
- **Capture-level parity** — the record honors the same capture policy as
  `events.jsonl`: at `off` no record is written; below `full`, free-text fields are
  redacted (`fbk/harvest.py`).
- **Run-retro reader** — a per-run reader renders the record as a per-unit summary
  (`fbk/run_retro.py`, wired as the `run-retro` command in `fbk/__init__.py`).

Suggested update (discuss before applying — project requires architecture changes be
discussed first): extend the "Measurement (in progress)" section with a short
paragraph describing the per-run record and its five capabilities above, and point
to `record-schema.md` for the field-level detail. Note the section's pointer
"Feature intent and behaviors live under `ai-docs/hook-harvesting/`" should also
reference `ai-docs/observability-substrate/`.

### [drift] CHANGELOG.md — no 0.5.2 section; substrate unrecorded

The top entry is `[0.5.1]`. There is no `[0.5.2]` section, so the substrate (the
per-run record, shape/topology vocabulary, harvest-at-close finalization, the
run-retro reader, and capture-level parity for the record) is not recorded anywhere
in the changelog.

Suggested update: add an `[0.5.2]` section with an **Added** entry for the
observability substrate. Suggested entry, in plain language: "Durable per-run
record — every workflow run is harvested at close into one JSON file under the
project-local capture directory, labeling each unit of work with its shape (distill,
implement, review, synthesize, gate) and topology (single vs fan-out, collaborative
vs adversarial), with token usage, timing, and journal results. The record honors
the same capture-level privacy policy as the event stream. A new `run-retro` command
reads one record and prints a per-unit summary." (Per project convention, check the
readme for required updates after the changelog edit — which is the readme item
below.)

### [drift] GLOSSARY.md — missing shape, topology, asset bundle, workflow journal

The glossary has no entries for the four terms the spec wanted defined, all of which
are load-bearing in the shipped code:
- **shape** — the closed five-member work-capability vocabulary in `fbk/shapes.py`
  (distill, implement, review, synthesize, gate); the resolver returns null for
  unknown personas rather than inventing a shape. Note the existing glossary already
  warns about "shape" collision (see the *slice shape* entry's LLM-priors note), so a
  new entry should disambiguate work-shape from slice-shape.
- **topology** — the per-unit cardinality (single / fan-out) and stance
  (collaborative / adversarial), parsed from the launch-prompt descriptor
  (`fbk/attribution.py`).
- **asset bundle** — the per-unit record of the instructions, persona, and
  decision-tree assets that composed an agent; only `persona` is populated in this
  slice, the other two reserved null (`fbk/harvest.py` `_build_unit`).
- **workflow journal** — the harness-written `journal.jsonl` in a run directory that
  serves as the authoritative agent roster for the harvest join (`fbk/harvest.py`
  `_read_journal`).

Suggested update: add the four entries following the glossary's authoring pattern
(definition + LLM priors), each pointing at how the term is used in the substrate
code.

### [drift] README.md — slash-command table omits run-retro

The shipped `run-retro` command (`fbk/__init__.py` COMMAND_MAP, `fbk/run_retro.py`)
is a user-facing reader, but the readme's "Slash commands" table does not list it,
and no readme prose mentions the per-run record or run-retro. (The readme already
treats the metrics plane in the v0.5.1 self-improvement-cycle paragraph; that
paragraph predates the substrate.) Note `run-retro` is an `fbk.py` subcommand, not a
slash command, so it may belong in the "Quick Start" machinery paragraph rather than
the slash-command table — the operator decides placement.

Suggested update (discuss before applying — project requires readme changes be
discussed first): mention the per-run record and the `run-retro` reader where the
readme describes the metrics plane / measurement, and decide whether to surface
`run-retro` in a command list.

### [note] docs/decisions-log.md — consistent; entries still labeled "hook-harvesting"

The decisions log carries the substrate's design and breakdown decisions (the
clean-complete-vs-truncated rule in D-04, the metrics-taxonomy split, the token
hard-split, and the independence of attribution-absent and journal-result-present in
D-17). These match the shipped code. The only minor staleness: every entry's status
line reads "metrics-plane / hook-harvesting feature" rather than naming the
observability substrate. Advisory only — the decisions are correct; the feature label
is just the earlier name. No change required for correctness.

### [note] design/record-schema.md and decisions vs. shipped code — consistent

The shipped record assembler (`fbk/harvest.py` `_assemble_record` / `_build_unit`)
matches the canonical schema field-for-field: schema_version "1.0", the per-unit
shape/topology/asset_bundle/tokens/journal fields, `ceremony_metrics` null in a
generic run, `harvested_at` preserved by value on re-harvest, and the
`tokens_available` available-vs-zero distinction. No drift between the design schema
and the code.

### [note] Spec-internal inconsistency — AC-04 text vs. what clean-complete actually requires

This is the known spec-internal inconsistency, confirmed. The acceptance text for the
completeness behavior (observability-substrate-spec.md, the AC-04 line) defines
clean-complete as **"a closed run with every started matched by a result is
clean-complete"** — it mentions only the journal result and says nothing about
transcript readability. But three other places require a readable transcript as well:
- the spec's own completeness-definition prose ("every started has a result,
  **transcripts readable**"),
- decision D-04 ("all agents balanced, **transcripts readable**"),
- and `record-schema.md` ("every started agent has a result **and a readable
  transcript**").

The shipped code follows the stricter reading: clean-complete requires both — see
`fbk/harvest.py`, where completeness is `clean-complete` only when
`all_have_results AND all_transcripts_readable`, else `truncated`. So the AC-04
acceptance text is narrower than the code, the schema, and D-04. This is a
spec-internal drift, not a code defect — the code matches the schema and the design
decision; only the AC-04 sentence is out of step.

Suggested update: when the spec is next touched, align the AC-04 sentence to include
the readable-transcript requirement so the acceptance text matches the schema, D-04,
and the shipped behavior. (Spec is ceremony scaffolding, not a durable doc, so this is
advisory and out of scope for any durable-doc edit.)
