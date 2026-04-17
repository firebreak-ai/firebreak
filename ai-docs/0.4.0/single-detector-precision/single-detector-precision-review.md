Perspectives: Architecture, Pragmatism, Quality, Measurability

# Single-Detector Precision — Spec Review

## Resolution Summary

All 18 findings resolved. Spec updated.

| Finding | Severity | Resolution |
|---------|----------|------------|
| R-01 | blocking | Added `verified-pending-execution` to status enum |
| R-02 | blocking | All fields required (no optional). Added `source_of_truth_ref`. `mechanism`+`consequence` replace `Observation`+`Expected`. |
| R-03 | important | Added Challenger receives definitions to pipeline step 5 |
| R-04 | important | Added `rejected-as-nit` to status enum for defense-in-depth |
| R-05 | important | Added dual-ID preservation rule to schema |
| R-06 | blocking | Switched to Python (`pipeline.py` via `uv run`), consolidated three scripts into one module |
| R-07 | important | Quarantine: rejected sightings written as full JSON to stderr |
| R-08 | important | Sequencing split into Phase A (pipeline, manual validation) and Phase B (benchmark) |
| R-09 | blocking | Fixed stale markdown reference — Challenger receives JSON |
| R-10 | important | Added content validation tests, inject script tests, preset validation tests |
| R-11 | important | Added existing test breakage section listing affected tests |
| R-12 | important | Added edge case tests for pipeline |
| R-13 | important | Split integration tests into deterministic (fixture) and live (structural assertions) |
| R-14 | blocking | Set precision floor P≥25%, F1≥35% alongside R≥68% |
| R-15 | blocking | Minimum 3 benchmark runs, report median and range |
| R-16 | important | Acknowledged small sample sizes, framed severity gradient as hypothesis |
| R-17 | important | Added recall fallback: <65% iterate on types, <60% widen preset |
| R-18 | important | Added provisional action thresholds for all per-run metrics |

## Threat Model

**Decision**: No threat model needed. No new trust boundaries, no auth/access control changes, no external API interaction. Scripts process local JSON files. Agent tool access unchanged (Read, Grep, Glob).

## Architectural Soundness

### R-01 [blocking] `verified-pending-execution` status silently dropped

The current Challenger agent defines a `verified-pending-execution` status for test-integrity sightings requiring test execution to confirm. The unified schema restricts `status` to `verified` or `rejected` — dropping this capability with no acknowledgment. The parser would reject any sighting carrying this status.

**Resolution**: Either add `verified-pending-execution` to the status enum and define its downstream behavior, or explicitly state the removal with rationale.

### R-02 [blocking] Three existing sighting fields have no schema equivalent

The current code-review-guide.md sighting format includes `Observation`, `Expected`, and `Source of truth` fields. The new JSON schema has `mechanism` and `consequence` but no equivalent for the expected-vs-actual comparison or the specific spec-AC reference. The `Expected` field is how the Challenger compares actual vs intended behavior — the behavioral comparison methodology's structured anchor.

**Resolution**: Add `expected_behavior` and `source_of_truth_ref` fields to the schema, or document how `mechanism` + `consequence` replaces the observation/expected pair and how the Challenger performs spec-AC comparison without a structured expected field.

### R-03 [important] Challenger receives no explicit type/severity definitions or matrix

The spec details what the Detector receives (persona, type definitions, severity definitions, matrix) but never states the Challenger receives the same. The Challenger performs reclassification — it needs the same definitions and matrix to avoid producing invalid combinations. The current SKILL.md already injects the guide into both agents, but the spec's pipeline section (4.8) doesn't mention it.

**Resolution**: State explicitly in section 4.8 that the Challenger receives type definitions, severity definitions, and validity matrix alongside the sightings.

### R-04 [important] Nit rejection protocol absent from unified schema

The Challenger currently has a specific nit-rejection protocol with separate counting in the retrospective. The `status` enum has no `rejected-as-nit` value. If nit filtering is now solely the Detector's responsibility ("Exclude nits" in the persona), state this explicitly and remove the nit-rejection protocol from the Challenger update.

### R-05 [important] Dual-ID preservation rule needed

A verified finding has both `id: "S-03"` (sighting) and `finding_id: "F-01"` (finding). The spec should state that `id` retains the original sighting ID even after `finding_id` is assigned, so implementers don't overwrite it.

## Over-Engineering / Pragmatism

### R-06 [blocking] Shell scripts for JSON processing — use Python

Three shell scripts (`domain-filter.sh`, `severity-filter.sh`, `sighting-to-markdown.sh`) consume and produce JSON arrays. Shell + JSON is the same class of fragility the spec is eliminating from the inject script. `jq` filter syntax for conditional field rendering (optional `reclassified_from`, sighting vs finding format) would be 50+ lines of jq per script. Python is already a dependency (inject script). `json.load()`/`json.dump()` is trivially robust.

**Resolution**: Switch to Python scripts, or consolidate into a single Python module with entry points: `python3 filter_pipeline.py --preset behavioral-only --min-severity minor < sightings.json`. One invocation, one failure point, one path resolution.

### R-07 [important] Quarantine rejected sightings instead of silent drop

The type-severity matrix enforcement rejects invalid combinations at parse time with no recovery. A genuinely valuable behavioral finding with wrong severity (minor instead of major) is lost entirely. Log the full sighting JSON in a quarantine file for post-run debugging, not just the rejection event.

### R-08 [important] Benchmark infrastructure as separate implementation phase

Steps 1-10 (pipeline) and steps 11-12 (benchmark) are naturally separable. Ship the pipeline first, validate manually on a handful of PRs, then invest in the inject rewrite and full benchmark. If the Detector produces malformed JSON 40% of the time, you want to know before burning benchmark credits.

## Testing Strategy

### R-09 [blocking] Stale reference: integration test says Challenger receives markdown

Section 6 integration test states "Verify the Challenger only receives filtered, markdown-converted sightings." Section 4.8 explicitly states "The Challenger receives and produces JSON." Direct contradiction within the spec.

**Resolution**: Replace with "Verify the Challenger only receives filtered JSON sightings that passed domain and severity filtering."

### R-10 [important] Six ACs have no test plan outside the 50-PR benchmark

AC-2 (Detector persona), AC-3 (type classification), AC-4 (severity definitions), AC-6 (mechanism-first), AC-7 (guide alignment), AC-13 (inject script) have no corresponding tests in Section 6. AC-2 through AC-7 are prompt/content changes — the existing test suite has structural content tests (grep-based TAP tests) for these files that should be extended. AC-13 needs fixture-based unit tests.

### R-11 [important] Existing tests will break

The Guardian identified 5+ existing tests that will break when the guide's format sections change:
- `test-code-review-structural.sh` tests 16, 18: check for "current behavior", "expected behavior", "Observation", "Expected"
- `test-instruction-hygiene-agents.sh` tests 5-6: check for "Pattern label:" in guide format sections
- `test-code-review-guide-extensions.sh` test 2: checks for "name-scope" in test-integrity definition

Section 6 should acknowledge breakage and include a task to update affected tests.

### R-12 [important] Filter script edge cases missing from test plan

Missing scenarios: empty input arrays, all sightings filtered (empty result), unknown preset name, malformed JSON from upstream, unicode in field values. These are shell/Python scripts processing LLM output — defensive edge case handling is cheap.

### R-13 [important] LLM output non-determinism unaddressed in testing

The orchestrator integration test produces different Detector/Challenger output on every run. Split into: (1) deterministic pipeline test (fixture-driven, no LLM), (2) live orchestrator test (structural assertions only — valid JSON, schema-compliant, pipeline ordering).

## Measurability

### R-14 [blocking] Precision target is unbounded

AC-15: "meets or exceeds v0.3.5 baseline recall (>=68%) while improving precision." Any result from P=20.6% to P=100% satisfies this. The decomposition experiment achieved P=28.5%. Without a floor, AC-15 cannot distinguish success from a null result.

**Resolution**: Define a minimum precision floor (e.g., P>=28% to match decomposition, or P>=25% as a conservative floor) and a minimum F1 target.

### R-15 [blocking] Single benchmark run insufficient for statistical significance

The spec acknowledges "run-to-run variance dominates instruction-level changes" from v0.4.0, yet designs for a single 50-PR run as validation. LLM output is stochastic — a single run cannot distinguish a 3pp precision improvement from noise.

**Resolution**: Specify minimum number of benchmark runs (e.g., 3, report median and range) or define an acceptable variance band the improvement must exceed.

### R-16 [important] Severity TP gradient claim lacks sample sizes

"Critical findings were 100% TPs; minor findings were ~10% TPs" — used to justify the severity filter, but sample sizes are not documented. If there were 5 critical findings, 100% has a confidence interval of 48%-100%. The claim should include counts so the evidence can be evaluated.

### R-17 [important] Recall preservation under filtering has no quantified mechanism

The spec targets >=68% recall after adding domain and severity filters. Filtering can only remove findings. The v0.3.5 behavioral-only projection was 67.2% — already below the target — assuming perfect classification. The persona change might recover recall, but no magnitude is estimated.

**Resolution**: Either lower the recall target to account for filter losses (e.g., >=60% with >=68% stretch), quantify expected persona-driven recall recovery, or define what happens if recall falls below target.

### R-18 [important] Per-run metrics lack action thresholds

Only domain filter loss (>10%) and parse failure rate (>30%) have defined thresholds. Remaining metrics (TP rate by type, severity gradient, reclassification rate, per-repo recall) have no thresholds. Define at least "healthy" ranges and "investigate" bounds for each.

## Testing Strategy Review

### New tests needed
- Content validation tests for Detector persona, type definitions, severity definitions (grep-based, following existing TAP test pattern)
- Filter script unit tests including edge cases (empty input, unknown preset, all-filtered, malformed JSON, unicode)
- Type-severity matrix exhaustive test (all 16 combinations)
- Inject script fixture-based unit tests
- Preset config schema validation test
- Cross-file consistency tests (type/severity terms appear in guide, Detector, Challenger)
- Deterministic pipeline integration test (fixture-driven, no LLM)
- Live orchestrator structural test (valid JSON, schema-compliant, pipeline ordering)

### Existing tests impacted
- `test-code-review-structural.sh` tests 16, 18 (finding/sighting format keywords)
- `test-instruction-hygiene-agents.sh` tests 5-6 (Pattern label format)
- `test-code-review-guide-extensions.sh` test 2 (test-integrity definition wording)
- `test-category-migration.sh` test 3 (vacuously true after format change)
- `test-classification-system.sh` tests 8-11 (may need updates for new persona content)

### Test infrastructure changes
- None — existing TAP test infrastructure and benchmark runner are sufficient.

## Threat Model Determination

**Security-relevant characteristics**: No new trust boundaries. No auth/access control changes. No external API interaction. Shell/Python scripts process local JSON files. The Detector and Challenger agents have the same tool access (Read, Grep, Glob) as before — no privilege escalation.

**Decision needed**: Does this feature need a threat model?
