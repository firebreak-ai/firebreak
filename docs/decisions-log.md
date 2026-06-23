# Decisions Log

Append-only, chronological record of constraining decisions made during Firebreak's design and development. A new entry supersedes rather than rewriting an old one — old entries are never edited.

Each entry records: what was decided, the alternative considered, the rationale, and what the decision constrains going forward.

---

## 2026-05-29 — fbk-architect is author-only this cycle

**Status**: accepted
**Author**: fbk-architect

**Decided**: `fbk-architect` is built as an author-only skill this cycle. The earlier framing that it should be a "superset the council architect collapses into" is dropped from the build requirement.

**Alternative considered**: Build fbk-architect as a superset persona that the council-architect role converges toward over time, embedding the collapse logic now.

**Rationale**: The council migration is out of scope for this cycle, and the superset relationship cannot be validated until the migration actually happens. Building for an unvalidatable future constraint is speculative scope.

**Constrains**: The future council-architect collapse remains a live design question. When the migration occurs, a decisions-log entry should record how fbk-architect's scope was updated. Until then, fbk-architect has no special relationship to the council pattern in code.

---

## 2026-05-29 — Code-review gate lands in a new code_review.py module

**Status**: accepted
**Author**: fbk-architect

**Decided**: The code-review gate is implemented as a new `code_review.py` module rather than being folded into the existing `review.py`.

**Alternative considered**: Extend `review.py` (which gates the spec-review phase) to also handle code-review gate logic, sharing the module across both gates.

**Rationale**: `review.py` gates a different phase and is called by the spec-review and breakdown flows. Folding code-review gate logic into it would couple two distinct gates into one module, entangle callers, and require changes to `review-gate`/`validate_review` paths that are tested and stable. The new module calls `test_hash.verify_manifest` for its hash check rather than duplicating a second hash path.

**Constrains**: `review.py`, `review-gate`, and `validate_review` remain untouched. Code-review gate callers import from `code_review.py`. If the two gate modules share enough logic in the future, extraction to a shared util is the right path — not a merge back into `review.py`.

---

## 2026-05-29 — Python runtime must not depend on system-wide packages

**Status**: accepted (documenting an existing constraint that was not previously written down)
**Author**: rahvin / operator constraint

**Decided**: Firebreak's Python runtime — installer, dispatcher (`fbk.py`), gate modules, shell tests — must not depend on system-wide Python packages. The dependency management and execution path is `uv`.

**Alternative considered**: Continue using `python3` directly with `pip install --user pyyaml` (the current pattern across the installer and all 60+ shell tests). This pattern is silently broken on systems that enforce PEP 668 (externally-managed-environment), which includes recent Arch, Debian/Ubuntu, and Homebrew-installed Python on macOS. On such systems, `pip install --user` fails and `python3 -c "import yaml"` returns ImportError unless the user has manually set up a venv outside Firebreak's awareness.

**Rationale**: Firebreak is most often installed globally (operator workflow) and should run reliably across systems regardless of how the system Python is locked down. `uv` handles project-local virtualenv creation, Python version pinning (already declared in `pyproject.toml`'s `requires-python = ">=3.11"`), and dependency resolution without touching system packages. The "easy option" — `uv run` at every Python invocation point — is also the correct one.

**Constrains**:
- The installer must bootstrap `uv` (or assume it's present and fail clearly if absent) rather than `pip install`-ing pyyaml.
- The shell-test pattern `python3 "$DISPATCHER"` must become `uv run python3 "$DISPATCHER"` (or the dispatcher must be invoked via a wrapper that itself calls `uv run`).
- Skill body invocations that read `python3 "$HOME"/.claude/fbk-scripts/fbk.py <gate>` must migrate to `uv run python3 ...` or to a wrapper command.
- The dispatcher's shebang should be reviewed for consistency.

This migration is out of scope for the refactored-sdl branch, which inherited the existing `python3`-direct pattern and would have produced an inconsistent codebase if it had unilaterally migrated only its own surface. The migration warrants its own feature spec.

**Tracked follow-up**: A future feature spec (`uv-runtime-migration` or equivalent) covers the installer rewrite, the shell-test pattern migration, the skill body invocation updates, and the dispatcher shebang. The refactored-sdl `/fbk-improve` proposals at `ai-docs/refactored-sdl/fbk-improve-proposals-2026-05-29.md` should be applied either before or after that migration without conflict.

---

## 2026-06-09 — Blast-radius set is derived by the spec-authoring agent using reference tooling

**Status**: accepted
**Author**: fbk-architect (operator-confirmed)

**Decided**: The spec-authoring agent computes the blast-radius set for `## Interface contracts` deterministically by running the project's reference-finding tooling ("find all callers" / "find all importers") against each module the spec's module-touch policy declares as changed. The resulting dependent set is the blast-radius set; each dependent's pre-existing interface contract becomes an `IF-S-NN` entry with `design-ref: pre-existing`. This is a mechanical derivation step, not a judgment call. The spec gate verifies only that blast-radius entries are present and well-formed — it does not recompute or check completeness of the caller set. Per-language completeness verification is a deferred follow-on.

**Alternative considered**: Author judgment — the spec author lists touched modules by inspection without running reference tooling.

**Rationale**: Author judgment introduced the risk of systematic under-listing (modules the author did not think to check), which the gate cannot detect and spec review can only partially catch — the exact silent-gap failure this feature exists to close. Reference tooling is available in every target project environment where a spec is authored, and the derivation is mechanical enough that the agent can execute it reliably. Keeping the gate responsibility shape-only (not completeness) avoids requiring per-language static analysis in a gate that is language-blind and runs across arbitrary target projects.

**Constrains**: The `feature-spec-guide.md` instruction for the spec-authoring agent must direct it to use reference tooling for blast-radius derivation. The spec gate enforces only field-completeness and identifier-form on blast-radius entries, not whether the set is complete. Per-language completeness checking is deferred to a follow-on feature.

---

## 2026-06-09 — Contract identifiers use separate namespaces: IF-D-NN for design, IF-S-NN for spec

**Status**: accepted
**Author**: fbk-architect (operator-confirmed)

**Decided**: The `IF` identifier space is split into two prefixed namespaces: `IF-D-NN` for design-originated contracts (minted in `design/contracts.md` during the design phase) and `IF-S-NN` for spec-originated contracts (minted by the spec author for pre-existing blast-radius entries and spec-discovered new contracts). When the spec carries a design contract forward, it copies the `IF-D-NN` identifier verbatim — inheritance, not re-minting. Collision between the two namespaces is structurally impossible.

**Alternative considered**: A single shared `IF-NN` sequence with operator-resolves as the collision response when design is re-edited after the spec has minted entries.

**Rationale**: Operator-resolves leaves an undetected collision possible — a hollow carry (same id, wrong content) that spec review may miss if it is not run. Separate namespaces make the collision impossible at the source, communicate different semantics visually (`IF-D` came from design, `IF-S` added at spec), and let downstream agents apply different handling rules by prefix alone. The added cost is two identifier patterns instead of one; the regex `^IF-[DS]-[0-9]{2,}$` handles both at the gate.

**Constrains**: Design pages use `## IF-D-NN — <name>` headings exclusively. Spec entries carrying design contracts use `IF-D-NN` verbatim; spec entries for blast-radius and spec-discovered contracts use `IF-S-NN`. The spec gate's id-format check validates both prefixes; the design-anchor walk extracts only `IF-D-NN` from `design/contracts.md`. Any future change to the prefix scheme is a contract-evolving change requiring a retired-tests entry and a gate-regex update.

---

## 2026-06-09 — Contract gate checks land in a new contracts.py module

**Status**: accepted
**Author**: fbk-architect (operator-confirmed)

**Decided**: The four new spec-gate check functions (structural completeness, design-anchor walk, AC-coverage, seam-coverage) are implemented in a new `fbk/gates/contracts.py` module, imported by `spec.py`.

**Alternative considered**: Extend `spec.py` directly with the four new functions.

**Rationale**: Consistent with the 2026-05-29 decision that placed the code-review gate in its own module rather than extending `review.py`. The new checks read a file outside the spec (the design contracts page), enforce a distinct invariant set, and will be tested in isolation. Folding them into `spec.py` would couple distinct concerns and make the module harder to test. The `fbk.injection` and `fbk.slices` helper-module pattern in the existing gate establishes the import-from-helper precedent.

**Constrains**: `spec.py` imports from `fbk.gates.contracts` at module top level. `ImportError` from this import fails the gate at startup — callers must ensure the module is installed. Any renaming of the module is a contract-evolving change requiring caller updates.

---

## 2026-06-09 — design/contracts.md parsed via level-two IF-D-NN headings

**Status**: accepted
**Author**: fbk-architect (operator-confirmed)

**Decided**: Identifiers in `design/contracts.md` are extracted using `re.findall(r"^## (IF-D-[0-9]{2,})", design_text, re.MULTILINE)`. Each level-two heading of the form `## IF-D-NN` or `## IF-D-NN — <name>` constitutes one contract entry.

**Alternative considered**: Fenced blocks per entry; flat field lines with no headings.

**Rationale**: Heading-level anchors are already how `spec.py` navigates all sections (`heading_line`, `section_body`). The `^##` anchoring prevents prose mentions of identifiers from being counted. The design page stays readable in any markdown renderer. Fenced blocks would require a new parser and look like code rather than design documentation.

**Constrains**: Design-page authors must use the `## IF-D-NN` heading form for each contract entry — any entry not starting with a level-two heading matching that pattern is not counted. Identifier mentions in prose (e.g., "see IF-D-01") do not constitute an entry.

---

## 2026-06-09 — Seam-coverage matching uses a case-insensitive substring scan

**Status**: accepted
**Author**: fbk-architect (operator-confirmed)

**Decided**: The seam-coverage check matches component names from integration-seam declarations against the full body of `## Interface contracts` using a case-insensitive substring scan. No dedicated `components:` field is added to the contract entry schema.

**Alternative considered**: Require a `components:` field per contract entry and exact-match against it; or exact string match against current contract fields.

**Rationale**: The PRD explicitly labels this a mechanical approximation. A substring scan is implementable on the existing section-body parse surface without schema changes. A `components:` field would add authoring cost to a heuristic before any feature has used the schema. The check's error message states the heuristic nature; the operator remains the final judge.

**Constrains**: The `components:` field remains available as a future refinement if the heuristic produces too many false passes. Adding a required `components:` field to the contract entry schema would be a contract-evolving change requiring a retired-tests entry.

---

## 2026-06-09 — Contract-drift elevation extends the architecture reviewer's brief

**Status**: accepted
**Author**: fbk-architect (operator-confirmed)

**Decided**: Spec review's contract-drift elevation is implemented by adding drift-detection instructions to the architecture reviewer's brief in `review-perspectives.md`, not by adding a required checklist entry to the review gate.

**Alternative considered**: A new required checklist entry in the review gate's structural prerequisites (would require a gate code change in `review.py`).

**Rationale**: Contract drift is a semantic concern — whether the spec's carried contracts match the design's intent — and semantic checks belong in the agent review layer, not the deterministic gate. The 2026-05-29 decision established that `review.py` is not modified for gate concerns outside its original scope. Extending the reviewer's brief requires only a text change, keeps the review gate's prerequisites deterministic, and the architecture reviewer is almost always engaged for features with contracts.

**Constrains**: The drift check runs only when the architecture reviewer is engaged. If a future feature bypasses that reviewer while having a `design/contracts.md`, drift detection will not run; adding "feature has design/contracts.md" as an engagement signal for the architecture reviewer is the natural follow-on.

---

## 2026-06-10 — Event capture is globally armed but per-project gated

**Status**: accepted (intent-phase decision for the metrics-plane / hook-harvesting feature)
**Author**: rahvin / operator constraint

**Decided**: The metrics-plane feature installs a hook router into the global Claude configuration so it can fire in any project, but it captures nothing unless the current project is Firebreak-managed or carries an explicit capture marker. Capture always writes to the project's own gitignored capture directory, never to the global configuration directory. Free-form payloads — tool-call arguments and prompt text alike — are recorded only at the `full` capture level; the shipped default in a Firebreak-managed project is `standard`, which records that events occurred without their payloads. Uninstrumented projects stay off regardless.

**Alternative considered**: Ambient global capture (the router records in every project once installed). Rejected on three grounds: privacy (full capture records prompt and argument text, which crosses a consent boundary in projects the operator never opted in), overhead (two interpreter spawns per tool call in every project is unjustifiable ambient cost), and sandbox writability (per-project sandboxes mount parts of the global config directory read-only, so capture cannot reliably land there).

**Rationale**: The metrics plane exists to make Firebreak self-measuring without trusting agents to narrate the retrospective. That value is local to Firebreak-managed work, so the cost and privacy exposure of capture should be local to it too. Cross-project aggregation, if ever wanted, is a manual sweep outside sandboxes — not a central write path.

**Constrains**:
- Any shipped hook router must perform its per-project capture gate check as its first action and exit immediately when the project is not instrumented.
- Capture must be fail-silent: never break a tool call or pipeline command, never emit to stdout, never write to the global config directory.
- When the global install ships, any leftover project-level router registration from an earlier capture experiment must be removed, or events duplicate.
- Both capture sources (the hook router and the dispatcher chokepoint) share one versioned event envelope and event-type vocabulary so the report can join them.

---

## 2026-06-10 — Chokepoint recorder captures gate stdout via in-process redirect

**Status**: accepted (design-phase decision for the metrics-plane / hook-harvesting feature)
**Author**: fbk-architect

**Decided**: The pipeline chokepoint recorder captures the JSON payload that gates print to stdout by temporarily redirecting `sys.stdout` to an in-memory buffer during the module call, then re-emitting the captured bytes to real stdout before the process exits. The captured text is included in the pipeline-command event as the gate result payload.

**Alternative considered**: Re-running a "read-only" path of each gate module after the fact to get the result, or having each gate write its result to a temp file as a side-channel. Both require changes to individual gate modules; the in-process redirect requires changes only to the chokepoint wrapper.

**Rationale**: The existing gate contract — print JSON to stdout, exit with a code — is relied on by callers and cannot change. The redirect is invisible to gates and callers alike, because captured bytes are re-emitted before the process exits.

**Constrains**: Future gate modules must not write progress or diagnostic text to stdout — only the final JSON result; anything else belongs on stderr. If stdout is not redirectable in a given runtime, the chokepoint wrapper detects this, skips capture, and calls the module directly; the event is omitted for that invocation.

---

## 2026-06-10 — Gate result stored as summary at standard capture, verbatim at full capture

**Status**: accepted (design-phase decision for the metrics-plane / hook-harvesting feature)
**Author**: fbk-architect

**Decided**: When the chokepoint recorder captures a gate's JSON result, it stores a summarized envelope at standard capture level (gate name, result, failure count, finding count) and the full verbatim JSON at full capture level. The report command reads whichever form is present.

**Alternative considered**: Always store verbatim gate JSON. Rejected because gate finding lists can be long and their format changes as gates evolve, making the event file large and schema-unstable without value to the metrics plane at standard operation.

**Rationale**: Standard capture is the lean shipped default — lifecycle and outcome signals, no payloads. Full capture is the debugging profile, where the complete gate result is valuable for tracing. Matching payload verbosity to capture level is consistent with how tool-call payloads are handled elsewhere.

**Constrains**: The report command must branch on the capture-level field when reading pipeline-command events to know whether a full gate result is available. Code paths that expect verbatim findings require full capture to be active.

---

## 2026-06-10 — All pipeline events share one events file; per-spec audit logs retired from the write path

**Status**: accepted (design-phase decision for the metrics-plane / hook-harvesting feature)
**Author**: fbk-architect

**Decided**: The new event writer appends all events — from the hook router, the chokepoint recorder, the verification hook, and the code-review gate — to a single `.fbk-capture/events.jsonl` file in the project directory, with the spec name as a field on every record. The two existing per-spec audit-log call sites (in the spec gate and the task-reviewer gate) are replaced with event-writer calls to this shared file. Existing per-spec `.log` files under `.claude/automation/logs/` are not deleted but receive no new writes.

**Alternative considered**: Keep the per-spec topology and add a merge step in the report command. Rejected because the merge adds complexity and the per-spec files were only ever written by two gates; a shared file makes the report's read path uniform and consistent with the hook router's existing capture behavior.

**Rationale**: The prototype validated the single-file approach end-to-end. Cross-spec filtering by the report command is a simple field match on a bounded file; the per-project retention cap keeps the file small enough for this to be cheap.

**Constrains**: The report command reads only `events.jsonl`. Any operator tooling that reads per-spec `.log` files directly will need updating. The existing audit module is preserved for backward compatibility but is no longer the write path for any gate.

---

## 2026-06-10 — Capture level and opt-in marker live in .fbk-capture/capture.cfg

**Status**: accepted (design-phase decision for the metrics-plane / hook-harvesting feature)
**Author**: fbk-architect

**Decided**: The capture level for a project (off, standard, or full) is stored in a plain key=value file at `.fbk-capture/capture.cfg` (for example, `capture_level=standard`). The presence of this file with any valid capture level is also the explicit opt-in marker for non-Firebreak projects. Firebreak-managed projects default to standard when the file is absent.

**Alternative considered**: A capture-level key in the existing `.claude/automation/config.yml` YAML file. Rejected because the per-project capture gate check runs on the hot path in every Claude tool call, and parsing YAML requires the PyYAML library, which adds startup cost and a dependency to a path that must complete in well under a second.

**Rationale**: A single-line key=value read is cheap and dependency-free, appropriate for the hot path. Collocating the config file in `.fbk-capture/` means the capture directory is self-contained: data, retention lockfiles, and configuration all live in one place the operator knows to look.

**Constrains**: The capture level is not discoverable via the existing config loader. Operators who expect all project settings in `config.yml` must be directed to `.fbk-capture/capture.cfg`. Documentation must cover both locations. The `capture.cfg` file is gitignored alongside the rest of `.fbk-capture/`.

---

## 2026-06-10 — Known Firebreak agent list derived from installed persona files

**Status**: accepted (design-phase decision for the metrics-plane / hook-harvesting feature)
**Author**: fbk-architect

**Decided**: The list of known Firebreak agent names used to filter subagent-completion events is derived at module load time by scanning installed persona files under the global Claude directory for frontmatter containing an agent-type key. A hardcoded fallback list covering the currently-known agents is used when the scan fails; a stale-fallback flag is set and surfaced as a warning in the report output.

**Alternative considered**: A hand-maintained constants list in the codebase. Rejected because adding a new agent persona file would not automatically update the filter, silently excluding that agent's completions from aggregated counts with no error.

**Rationale**: Deriving the list from the same files that define agents keeps the filter current automatically whenever a new agent is installed. The scan is a one-time glob at import time, not per-event.

**Constrains**: Agent persona files must include an agent-type frontmatter key to be recognized. Agents installed after the hook router process has started are not visible until the next process — acceptable because router processes are short-lived (one per tool call).

---

## 2026-06-10 — Token stage attribution uses a hard split on state-engine transition timestamps

**Status**: accepted (design-phase decision for the metrics-plane / hook-harvesting feature)
**Author**: fbk-architect

**Decided**: The post-hoc token harvester attributes each transcript turn to the pipeline stage whose transition timestamp is the latest one before that turn's timestamp. When a single session spans a stage boundary, turns before the transition timestamp go to the earlier stage and turns at or after go to the later stage.

**Alternative considered**: Marking turns near a stage boundary as ambiguous and attributing them to the later stage with a flag. Rejected as additional complexity for a case that is rare and affects only a handful of turns.

**Rationale**: The prototype validated that state-engine timestamps and transcript timestamps are close enough for stage-level attribution. The table is a coarse-grained summary; misattributing one or two turns at a boundary has negligible effect on per-stage totals, and the rule is consistent across cycles so before/after comparison is unaffected.

**Constrains**: The hard split may misattribute tokens generated during the brief overlap between a Python-layer transition and the agent's first action in the new stage. Turn-level accuracy is not a goal of this feature; the limitation is documented in the harvester module.

---

## 2026-06-10 — Code-review round data flows from skill to gate via a file in the feature directory

**Status**: accepted (design-phase decision for the metrics-plane / hook-harvesting feature)
**Author**: fbk-architect

**Decided**: The code-review skill writes a file named `.code-review-rounds.json` to the feature directory during its orchestration of detection and challenge rounds. The code-review gate reads this file at check time and emits a round-summary event. If the file is absent, no event is emitted and no error is raised.

**Alternative considered**: Having the skill write round events directly to the events file, or adding a new sub-command for the skill to call. Both require the skill (an agent-mediated context asset) to write directly to the event store or invoke a new command — adding coupling and a new trust boundary between the agent and the capture system.

**Rationale**: The gate already reads the feature directory for its artifact checks. A file-based handoff is the most durable interface for data that originates in agent-mediated skill execution: the skill writes when it has the data, the gate reads when it runs, and neither depends on the other being available simultaneously.

**Constrains**: The code-review skill instructions must be updated to write the round file. Until that ships, the gate-side code works but the round event is always absent. The file format is a contract between skill and gate (a schema version, the spec name, and a rounds array with raised, survived, and severity-breakdown per round); a malformed file produces no event and a stderr warning.

---

## 2026-06-10 — Retention uses a size cap with operator-lockable cycle protection

**Status**: accepted (operator ruling, design phase)
**Author**: rahvin / operator ruling

**Decided**: The events file self-prunes when it exceeds a size cap (default ~5MB) by dropping the oldest lines, but skips any line belonging to a spec that has a corresponding empty file in `.fbk-capture/locked/`. To protect a baseline cycle for before/after comparison, the operator creates an empty lock file named after the spec in that directory.

**Alternative considered**: Automatic cycle protection (the system infers which cycles to protect from completion status), or no automatic pruning at all. Automatic protection was rejected because deciding which cycle is "the baseline" requires context the retention module does not have and should not acquire; no-pruning was rejected because the brief requires the file stay bounded without operator action.

**Rationale**: The size cap keeps the file bounded without intervention for the common case. The lockfile gives explicit operator control for the before/after use case without the retention module needing to understand cycle semantics. The protection action is deliberate, appropriate where losing the data would be costly.

**Constrains**: If an operator forgets to lock a baseline before the cap is reached, that baseline is pruned without warning. Documentation must make the lock step visible where an operator sets up a before/after evaluation. The lock directory is gitignored alongside the rest of `.fbk-capture/`.

---

## 2026-06-10 — Gate pass rate reported as two separate rows (first-try and after-rework)

**Status**: accepted (operator ruling, design phase)
**Author**: rahvin / operator ruling

**Decided**: The report's gate-outcome section shows two rows for each gate: the fraction of stage entries where the gate passed on the first attempt (before any park), and the fraction of post-park re-attempts that passed. These are computed separately by correlating gate events with the state engine's park history.

**Alternative considered**: A single blended pass rate counting all gate attempts including post-park ones. Rejected because it flattens a meaningful distinction — a gate that passes cleanly half the time and always passes after rework operates differently from one that rarely passes first try and also struggles after rework.

**Rationale**: The distinction between first-try performance and rework performance is exactly what the metrics plane exists to surface; blending the two would obscure the signal the before/after evaluation depends on.

**Constrains**: The report must correlate pipeline-command events with the state engine's error history and stage timestamps to classify each gate attempt as first-try or post-park. A gate attempt is post-park if it occurs after a parked transition for the same spec and stage, followed by a ready re-entry. This logic must be tested against the state machine's known transitions.

---

## 2026-06-10 — Challenger kill rate counts every raise event including re-raises

**Status**: accepted (operator ruling, design phase)
**Author**: rahvin / operator ruling

**Decided**: The kill-rate denominator is the total number of raise events across all code-review rounds, counting each round's raised figure independently even when the same issue was raised in a prior round. The numerator is total raised minus total confirmed (issues that survived to the final quiet round).

**Alternative considered**: Deduplicate issues across rounds and count each distinct issue once. Rejected because the code-review skill does not produce stable issue identifiers across rounds; deduplication would require fuzzy matching or a protocol change to the skill.

**Rationale**: The kill rate is a detector-noise signal, not an accuracy measurement. Counting re-raises captures the full volume of unproductive detection work: a detector that raises the same issue three times before confirming it generated more noise than one that raised it once.

**Constrains**: If cross-round deduplication is later wanted, the round file format must add a stable issue identifier per raise — a breaking change requiring a schema-version bump. The current interpretation is documented as a known limitation for readers who expect deduplication.

---

## 2026-06-10 — Retrospective metrics injection is deterministic and per-stage, triggered by the state-engine transition

**Status**: accepted (operator ruling, overrides fbk-architect recommendation)
**Author**: rahvin / operator ruling

**Decided**: A machine-written metrics block is appended to the spec's retrospective file at every stage completion, triggered from within the state engine's transition call, not by an operator command. A new retro-injector module calls the report's stage-summary aggregation and appends the result via the existing retrospective append function. The agent's interpretive prose is appended separately by skill instructions in a distinct section, as today. No operator-run retrospective command is added.

**Alternative considered**: A single retrospective command the operator runs at end of cycle. Rejected because retrospective sections are appended at multiple stage boundaries throughout the cycle, not once at the end, and the injection must be deterministic — not dependent on an operator action or an agent instruction.

**Rationale**: The state-engine transition is the only code path that fires reliably at every stage boundary without additional hooks or operator involvement. The state engine is already authoritative about stage completion; making it responsible for triggering the metrics append keeps the two concerns co-located. The agent's prose and the machine block coexist as distinct append-only sections, with the machine block carrying a parseable provenance marker so the two are always distinguishable.

**Constrains**: The injection is wrapped in a full try/except inside the transition call — a failed injection must never prevent a stage transition from succeeding. Injection fires only when leaving an active working stage (the in-progress states), not on parks, ready re-entries, the initial queued creation, or checkpoint states. Token rows are excluded from the injected block because token attribution is post-hoc; the full report command supplies tokens. The retrospective file path is resolved by convention and must be reconciled with the existing `<feature>-retrospective.md` naming at spec time.

---

## 2026-06-12 — Hook-harvesting remediation: shared non-active-state constant, install-time capture sentinel, gate rates cover all gate types

**Status**: accepted (remediation spec, operator-confirmed at spec review 2026-06-12)
**Author**: rahvin / remediation spec

**Decided**: Three resolutions from the hook-harvesting remediation. (1) One authoritative "not an active working stage" set, `NON_ACTIVE_STATES`, lives in `fbk/state.py` beside `WORKING_STAGES`, derived from the same transition map; the active-stage resolver and the report import it by identity — no module may carry its own copy. (2) The installer creates the `.claude/automation/.fbk-managed` sentinel at install time, so a freshly-installed Firebreak project is instrumented and captures events with no manual step. (3) Gate pass-rates cover all gate types: the rate classifier reads the chokepoint's `PIPELINE_COMMAND` outcomes for the spec, task-reviewer, and code-review gates alongside task-completion verification, and the chokepoint is the single writer of gate-outcome events (the gates' own duplicate writes are removed).

**Alternative considered**: (1) Homing the constant in the capture package — rejected because `state.py` already imports the capture package, so the reverse import would close a cycle. (3) Relabelling the metric as verification-only, or keeping the gates as a second event writer — rejected because two events per dispatch double-count attempts and break exact-fraction rates, and a gates-as-source design would need a second two-module name agreement of exactly the parallel-literal kind the shared constant eliminates.

**Rationale**: The independent review found the remediation's own code reproducing the producer/consumer drift class the feature measures; each decision removes a place where two modules had to agree by convention.

**Constrains**: Any new pipeline state lands in the shared sets automatically (derived, not listed); uninstall does not remove the sentinel; a future gate command must be added to the report's `GATE_COMMAND_NAMES` to enter the rates.

---

## 2026-06-22 — Unified review shape — design phase

**Status**: accepted (operator-confirmed through design grilling, 2026-06-22)
**Author**: rahvin / design grilling (forks) + fbk-architect analysis (ratified items)

**Decided**: Fifteen design decisions for the unified review shape — one generic adversarial review pattern that every review type runs as a preset over.

Seven operator-judgment forks:
1. *Lens home and grain.* Two generic role agents (a researcher, a challenger) own only the generic reviewer persona; per-type "what to look for" lives in swappable review-lens documents loaded at spawn; genuinely shared detection passes live once in a referenced shared-detection document, never copied into a lens.
2. *Remediation location.* The loop never writes — it returns confirmed findings. The caller applies fixes and re-invokes the loop on the changed artifact as a fresh pass; only code review (the lone read-write type) documents the fix-then-re-invoke step.
3. *Migration mechanism.* Thin presets: each existing skill file keeps its path and becomes a thin wrapper over the shared loop plus its lens, migrated one type at a time (code review → test review → fresh-eyes → new presets).
4. *Coherence placement and output.* The new cross-unit coherence review runs post-breakdown, pre-implementation, writing coherence-review.md (each confirmed mismatch plus a Verdict: line that gates entry to implementation).
5. *Coherence contract universe.* Explicit declared contracts only — declared interface signatures, named data shapes with required fields, documented handoff seams, locked type contracts; consumer sets may be many-to-one.
6. *Cross-model hole.* The loop names no model; model is a per-preset setting; a future cross-model preset fills a role slot with a different family without touching the loop, which carries an explicit guard that a different-model reviewer is the round's role-holder, not an extra round.
7. *Canonical vocabulary.* The shape is the adversarial review pattern; the roles are researcher and challenger; per-type knowledge is a review lens; a configured type is a review preset; the shared spine is the review loop. Glossary entries minted for adversarial review pattern, researcher, challenger, review lens, review preset.

Eight items determined by the requirements and the existing review code, ratified: the abstract finding/verdict/confirmed contract and four challenger outcomes; the termination rule and round cap (5 default, 1 for fresh-eyes); the cardinality dials and the isolation invariant stated as an enforceable constraint; the challenger's handoff order (artifact cold first, then de-framed claims and cited sources); the inject-versus-spawn rule per role hole; the four test-review checkpoints (spec, pre-lock, final, and the newly-named task-review pass); which types have live verdicts to preserve versus are newly realized; and the council→test-review handoff boundary (only the spec file crosses, never council output).

**Alternative considered**: Per-type role-agent personas carrying the lens (rejected — reproduces the persona/lens fusion this feature exists to kill and proliferates ~10 near-structure agents); fixes applied inside the loop (rejected — forces every read-only review type to opt out of a mutation it never needs); staged file replacement (rejected — larger blast radius, every gate moves at cutover); a wider implicit-assumption contract universe for coherence (rejected — by the post-breakdown gate the SDL has already eliminated ambiguity, so an inferred-only contract is an upstream failure, not the coherence review's job); a named cross-model dial on the shape (rejected — bakes a non-goal feature's concept into the shape and risks the "more rounds / stronger model" framing the requirements forbid).

**Rationale**: The shape's whole value is that a quality improvement made once becomes a property every review type inherits, so the loop, the isolation rules, and the five carried behaviors live in one generic place and only the lens varies per type. Each fork was resolved toward the option that keeps the loop generic and the isolation invariant load-bearing. The five carried review-quality behaviors all map onto the shape cleanly (false-passing-test scan as lens content run by a generic detection-pass property; fix-pairs-with-regression-test as a confirm-stage discipline; remediation-earns-its-own-pass as the loop-reentry rule; verify-before-acting as the challenge stage existing; dead-code-trace and challenger-reads-cited-source as generic challenger disciplines), which is the required signal that the factoring is right.

**Constrains**: The isolation invariant is a hard constraint, not a quality goal — any factoring that lets a researcher see challenger framing or a challenger inherit researcher framing is a defect. Every existing verdict and gate artifact is preserved byte-identical (code review's report and .code-review-rounds.json, test review's Verdict: line across all checkpoints, fresh-eyes' empty-Critical-section check). Test review is the one behavior-change case: it gains an independent challenger while its verdict stays identical. The coherence review needs a new breakdown-to-implementation gate that does not yet exist. Fresh-eyes critical observations must be written as bullet-list items or the gate check silently passes them. The seven integration seams (lens injection, the de-framed findings handoff, cited-source injection, verdict-path contracts, the round-history artifact, the council handoff, and the fresh-eyes gate format) are the load-bearing boundaries the spec and implementation must each wire explicitly.

---

## 2026-06-23 — Unified review shape — spec and implementation phase

**Status**: accepted (operator-confirmed at spec review and spec-gate, 2026-06-22; implemented 2026-06-23)
**Author**: rahvin / spec-review council + cross-model passes (decisions); fbk-implement (outcome)

**Decided**: Four operator decisions resolved as the shape moved from design into a built feature, plus the implementation outcome.

1. *Round-history trust boundary stays locked.* The code-review gate's round-log projection is an allowlist that deliberately keeps the per-round severity breakdown out of the events file. An earlier spec-authoring instinct to enrich the gate to read that field was reversed once the council read the actual gate test: the boundary is a control, not an oversight. The migrated code review writes the same findings report and round-history file, byte-for-byte, as before.
2. *Validation is parameterized per lens, not per skill.* The find-then-verify validation machinery lived in one place hardwired to code review. It now takes a per-lens vocabulary, so each review type validates against its own finding types and severities. The default path (no lens supplied) behaves exactly as the old single-purpose validator did, so nothing downstream of code review changes.
3. *Scan-only review types fold into the shape.* The top-five quality scan and the durable-doc reconciliation both spawned the very detector agent this feature retires. Rather than orphan them, both became degenerate single-pass presets — one generic researcher, their own lens, no challenger — declaring a scan output mode that bypasses the find-then-verify validator so their native output shape is preserved, never forced into the finding schema.
4. *Coherence review runs in a fresh subagent behind a new gate.* The new cross-unit coherence review runs automatically after task assembly and pre-lock test review, in a separate cleared subagent rather than the breakdown agent's own author-saturated context, and a new coherence gate guards entry to implementation. The gate is enforced on the implementation prerequisite as well, so invoking implementation directly cannot bypass it. The review's model is a per-preset setting, leaving a clean slot for a future cross-model reviewer.

**Alternative considered**: Enriching the gate to read the severity breakdown (rejected — breaks a deliberate trust-boundary control); changing only the gate layer (rejected — the validation machinery the migration depends on lives in the shared pipeline, not the gate); leaving quality scan and doc reconciliation as separate skills on the deleted detector agent (rejected — orphans two live capabilities and keeps a parallel agent path the feature exists to remove); wiring the coherence gate only into breakdown (rejected — leaves a direct-to-implementation bypass of the central no-bypass promise).

**Rationale**: Each decision was resolved toward preserving every existing verdict and gate contract while moving the shared machinery into one generic place. The recurring lesson across spec review and two cross-model passes: an operator decision must not rest on an incomplete reading of the code it changes — the trust-boundary reversal happened only because a reviewer read the locking test.

**Constrains**: The round-log allowlist must keep projecting only its three permitted fields at the trust boundary. The per-lens validator's no-lens default must stay behavior-identical to the retired single-purpose validator. Scan-mode presets must never be routed back through the finding validator. The coherence gate must remain enforced on both the breakdown exit and the implementation entry. The four superseded domain review agents are deleted outright with their telemetry registry references removed — no parallel old/new agent path survives.

**Outcome (implementation, 2026-06-23)**: Built in four waves; full test suite 650 passing, zero regressions against the 527-test baseline. One contract-vocabulary escalation (a drafted spine document whose prose did not match its paired structural test, resolved in one revision) and one conformance fix (a lens missing its identity heading, caught by the lens-format conformance test). The live end-to-end run of the migrated skills against a real artifact remains the operator's manual validation step. A breakdown-completeness gap surfaced: the spec's documentation-impact section produced no breakdown tasks, so these documentation updates were applied after implementation rather than as tracked work.
