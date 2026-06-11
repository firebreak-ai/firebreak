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
