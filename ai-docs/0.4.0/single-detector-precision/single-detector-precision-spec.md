# Single-Detector Precision — Feature Spec

## 1. Problem

Firebreak v0.3.5 code review achieves 68.4% recall but only 20.5% precision on the 50-PR Martian benchmark, averaging 9.0 findings per PR. Four out of five findings are false positives. The v0.4.0 decomposition experiment improved F1 from 31.6% to 37.6%, but analysis showed the gains came from domain filtering and instruction improvements — not multi-agent decomposition, which hurt recall by 13pp. The monolithic detector's full-diff context produces better recall; the precision problem is solvable with post-detection filtering and instruction changes.

### Root causes

1. **No domain scoping**: The behavioral-only review emits structural, test-integrity, and fragile findings that are outside the detection target. These are correct observations but irrelevant to the selected review domain, inflating FP count.
2. **Consequence-agnostic type classification**: Type definitions describe pattern shape ("naming issue → structural") rather than runtime consequence. This causes findings with real behavioral impact to be misclassified, and would cause a domain filter to drop valid findings.
3. **Consequence-leading wording**: Findings lead with downstream consequences ("orphaned DB rows") rather than the mechanism ("forEach(async) without await"). Human reviewers and benchmark judges expect mechanism-first framing.
4. **No severity filtering**: Info-level findings have near-zero TP rates in benchmark evaluation but still appear in output. There is no configurable threshold to drop low-value findings.
5. **Inconsistent sighting format**: Detector output format varies across runs, causing downstream scripts (domain filter, severity filter, inject pipeline) to fail on parse errors.

## 2. Goals

- Meet or exceed v0.3.5 baseline recall (R≥65%) while improving precision (P≥25%, F1≥35%) on the 50-PR Martian benchmark, evaluated via manually-triggered benchmark runs.
- Reduce average findings per PR from 9.0 to ≤5.0.
- Establish a deterministic, scriptable post-detection filtering pipeline (domain filter + severity filter) that runs without LLM involvement.
- Produce a structured JSON sighting format that parses reliably across all review runs, with a script to convert to markdown for human consumption.
- Formalize detection presets as named configurations with defined type allow-lists and severity defaults.
- Preserve the single-detector architecture (one Detector agent, one Challenger agent per review unit).

### Non-goals

- Multi-agent detector decomposition.
- Real-time confidence scoring or multi-agent agreement signals.
- Full repository access during diff-only benchmark runs.
- Changes to the Challenger agent's verification protocol.
- Confidence or reachability as separate sighting fields (reachability is embedded in the Challenger's caller-tracing protocol; confidence is uncalibrated for single-detector architecture).

## 3. Background and prior art

### v0.3.5 baseline (50 PRs)

| Metric | Value |
|--------|-------|
| TP | 93 |
| FP | 360 |
| FN | 43 |
| Precision | 20.5% |
| Recall | 68.4% |
| F1 | 31.6% |
| Avg/PR | 9.0 |

### v0.4.0 decomposition experiment

The decomposition split the monolithic detector into 7 domain-specific Tier 1 groups. Results at 50 PRs: F1=37.6% (P=28.5%, R=55.5%, 5.3/PR). Source: `feature/0.4.0-detector-decomposition` branch, `results/0.4.0-50pr-benchmark-results.md` and `results/judge_consensus_v040_50pr.jsonl` — cherry-picked in Phase B. Charter filtering (dropping non-behavioral findings) improved precision in a 20-PR subset (F1=42.4%) but hurt F1 at 50 PRs due to misclassification losses.

Key validated techniques:
- **Domain filter**: Dropping findings outside the target domain reduced FP count by ~50 per 20 PRs.
- **Mechanism-first wording**: Naming the exact code expression recovered 2 of 3 judge mismatches in targeted tests.
- **Consequence-based type classification**: Rewriting type definitions improved cal.com F1 from 33.3% to 44.0% (but was unmeasurable against run-to-run variance in discourse PRs).
- **Severity as discriminator**: Critical findings were 100% TPs; minor findings were ~10% TPs. Sample sizes per severity level were small — this gradient is a hypothesis to validate in the benchmark, not an established fact.

### Benchmark reference points

| Tool | P | R | F1 | Avg/PR |
|------|---|---|-----|--------|
| Cubic (#1, filtered) | 56% | 68% | 61.8% | 3.3 |
| claude-code raw | 34.8% | 40.9% | 37.6% | 3.2 |
| Firebreak v0.3.5 | 20.5% | 68.4% | 31.6% | 9.0 |

## 4. Technical approach

### Prompting design principle

The Detector and Challenger agents run on the same model (Claude) that orchestrates the pipeline. The model has the capability to trace call paths, construct failing inputs, reason about interface contracts, and produce senior-engineer-quality code review — but it does not engage these capabilities by default. The model's training distribution favors the most likely response, which for code review skews toward surface-level pattern matching, tutorial-grade observations, and consequence-leading descriptions.

Every prompt instruction in this pipeline exists to make the desired output more likely — to activate reasoning patterns the model already has but doesn't default to. The necessity test for each instruction is: **"Without this, does the model fall back to a lower-quality default behavior it has the capability to avoid?"**

This means:
- The Detector persona activates the senior engineering review distribution, not the generic assistant distribution.
- The three-questions workflow steers attention toward value tracing and input construction, which the model can do but doesn't do unprompted.
- The type-severity matrix forces the model to commit to a concrete, falsifiable claim before emitting — activating more careful self-verification.
- Mechanism-first wording counteracts the model's default toward consequence-leading abstractions.

Prompt instructions are not teaching the model new skills. They are raising the probability of capabilities the model already has.

### 4.1 Unified JSON schema (sightings and findings)

Replace the separate sighting and finding formats with a single JSON schema used throughout the pipeline. The Detector produces sightings (base schema). The Challenger adds verdict fields to the same objects, promoting verified sightings to findings. One schema, extended — no format translation, no field duplication, no accidental field loss.

**Base schema (Detector output):**

```json
{
  "id": "S-01",
  "title": "forEach(async) drops return value — promises fire-and-forget",
  "location": {
    "file": "src/handlers/workflow.ts",
    "start_line": 42,
    "end_line": 55
  },
  "type": "behavioral",
  "severity": "critical",
  "origin": "introduced",
  "detection_source": "intent",
  "source_of_truth_ref": "intent claim 3: sendReminder completes before the handler returns",
  "pattern": "async-in-sync-iterator",
  "mechanism": "forEach(async callback) discards the Promise returned by each iteration. The callbacks execute concurrently with no error propagation to the caller.",
  "consequence": "Workflow reminder emails fire without await. If any callback throws, the error is silently swallowed. Under concurrent requests, multiple reminder batches interleave.",
  "evidence": "Lines 42-48: bookingHandler.forEach(async (booking) => { await sendReminder(booking); }). forEach returns void, not Promise.",
  "remediation": "Replace forEach(async) with for...of loop or Promise.all(items.map(async ...))."
}
```

**Challenger verdict fields (added to the same object):**

Verified sighting:
```json
{
  "status": "verified",
  "finding_id": "F-01",
  "reclassified_from": { "type": "fragile", "severity": "minor" },
  "verification_evidence": "Traced caller chain from router.ts:18 → handler.ts:42. The caller awaits the return value, which is void.",
  "adjacent_observations": ["Adjacent to S-01: sendReminder also lacks error boundary for SMTP failures."]
}
```

Rejected sighting:
```json
{
  "status": "rejected",
  "rejection_reason": "The forEach callback is synchronous — no async keyword present. The Detector misread the diff."
}
```

When the Challenger reclassifies, it overwrites `type` and/or `severity` on the object and records the originals in `reclassified_from`. When it does not reclassify, `reclassified_from` is an empty object `{}`.

**Detector output fields** — the schema always has the same shape. The LLM is expected to produce all fields. The parser enforces two tiers:

**Required-or-reject** (parser rejects the sighting if missing or empty):
- `id`: sequential, reassigned by orchestrator
- `title`: mechanism-first, min 10 characters
- `location`: must contain `file` and at least `start_line`
- `type`: valid enum value
- `severity`: valid enum value
- `mechanism`: min 10 characters
- `consequence`: min 10 characters
- `evidence`: specific code path, line reference, or test case

**Required-with-defaults** (parser fills a default and logs a warning if missing):
- `origin`: default `"unknown"`. One of `introduced`, `pre-existing`, `unknown`.
- `detection_source`: default `"intent"`. One of `spec-ac`, `checklist`, `structural-target`, `intent`, `linter`.
- `source_of_truth_ref`: default `""`. The specific reference the Detector compared against (e.g., "AC-03", "AI failure mode #7", "intent claim 4"). Provides traceability for Challenger verification.
- `pattern`: default `""`. Cross-cutting pattern label.
- `remediation`: default `""`. One-line fix direction.

The defaults are a safety net for LLM output variance, not permission to skip fields. The parse failure rate metric (section 4.12) tracks systematic omissions — a high default-fill rate indicates the Detector prompt or guide needs adjustment.

**Required fields — Challenger output** (added to each sighting):
- `status` (one of `verified`, `verified-pending-execution`, `rejected`, `rejected-as-nit`)
- `verification_evidence` (required when status is `verified` or `verified-pending-execution`, min 10 characters)
- `rejection_reason` (required when status is `rejected`, min 10 characters)

**Orchestrator-assigned fields** (not produced by Challenger):
- `finding_id`: assigned by orchestrator after verification (F-01, F-02...)

**Challenger-required fields:**
- `reclassified_from`: object with `type` and `severity` when Challenger changed either, empty object `{}` when no reclassification
- `adjacent_observations`: array of strings, empty array `[]` when none observed

**Enum validation:**
- `type`: one of `behavioral`, `structural`, `test-integrity`, `fragile`. Reject any other value. Do not attempt fuzzy mapping.
- `severity`: one of `critical`, `major`, `minor`, `info`. Reject any other value.
- `origin`: one of `introduced`, `pre-existing`, `unknown`.
- `status`: one of `verified`, `verified-pending-execution`, `rejected`, `rejected-as-nit`. `verified-pending-execution` indicates the finding is credible from code reading but requires test execution for definitive confirmation — used for test-integrity sightings. The orchestrator treats `verified-pending-execution` like `verified` for filtering and reporting, with a caveat marker in the review report. `rejected-as-nit` indicates the sighting is technically accurate but functionally irrelevant (naming, formatting, style). The orchestrator treats it like `rejected` for filtering but counts nit rejections separately in the retrospective. A high nit-rejection rate indicates the Detector persona is not filtering nits effectively.

**Type-severity validity matrix** — the parser rejects these invalid combinations at both Detector and Challenger stages:

|  | critical | major | minor | info |
|--|----------|-------|-------|------|
| **behavioral** | valid | valid | invalid | invalid |
| **structural** | invalid | invalid | valid | valid |
| **test-integrity** | valid | valid | valid | invalid |
| **fragile** | invalid | valid | valid | invalid |

If an invalid combination is produced, the parser rejects the sighting/finding. Rejected sightings are written as complete JSON objects to stderr (quarantine log) — not just the rejection event, but the full sighting content for post-run re-evaluation. If >30% of sightings in a single run are rejected, surface a warning — this indicates prompt drift.

**ID assignment**: The orchestrator assigns sequential sighting IDs (S-01, S-02...) after Detector collection and finding IDs (F-01, F-02...) after Challenger verification. Detector and Challenger self-assigned IDs are ignored. The `id` field retains the original sighting ID even after `finding_id` is assigned — both IDs coexist on the same object for traceability.

**JSON-to-markdown conversion**: The `to-markdown` subcommand of `pipeline.py` converts a JSON array to the human-readable markdown format used in review reports. It handles both sightings (pre-Challenger) and findings (post-Challenger) — findings render with the F-NN ID, verification evidence, and reclassification note when present:

```markdown
### F-01: forEach(async) drops return value — promises fire-and-forget

- **Location**: `src/handlers/workflow.ts:42-55`
- **Type**: behavioral | **Severity**: critical | **Origin**: introduced
- **Detection source**: intent | **Pattern**: `async-in-sync-iterator`

**Mechanism**: forEach(async callback) discards the Promise returned by each iteration. The callbacks execute concurrently with no error propagation to the caller.

**Consequence**: Workflow reminder emails fire without await. If any callback throws, the error is silently swallowed. Under concurrent requests, multiple reminder batches interleave.

**Evidence**: Lines 42-48: bookingHandler.forEach(async (booking) => { await sendReminder(booking); }). forEach returns void, not Promise.

**Verification**: Traced caller chain from router.ts:18 → handler.ts:42. The caller awaits the return value, which is void.

**Remediation**: Replace forEach(async) with for...of loop or Promise.all(items.map(async ...)).
```

### 4.2 Detector agent persona and workflow

Replace the current Detector agent definition (`assets/agents/fbk-code-review-detector.md`) with a persona-driven definition. The current prompt is procedural — it tells the Detector to "describe what each function does, then compare against the source of truth." This produces generic, consequence-leading findings. The replacement gives the agent an identity that shapes how it reads code.

**Proposed agent definition:**

```markdown
---
name: code-review-detector
description: "Senior engineer reviewing code for bugs. Reads code closely, constructs failing inputs, traces caller contracts. Produces JSON sightings."
tools: Read, Grep, Glob
model: sonnet
---

You are a staff engineer who writes maintainable, production code that other engineers can pick up and work with.

Every sighting you produce must demonstrate three things:

1. **The mechanism**: the exact code expression that misbehaves and what it does wrong.
2. **A concrete failing input**: a specific value, state, or timing that triggers wrong output. If you cannot construct one without hypothesizing a code change, the issue is not behavioral.
3. **Caller impact**: who calls this code and what they expect. If the caller's expectation does not match what the code produces, that is a sighting.

Record observations using the JSON schema provided by the orchestrator. Classify using the type and severity definitions provided by the orchestrator. Validate your classification against the type-severity matrix before emitting.

Focus on the code the orchestrator directs you to. Use your tools to read code, not to modify it. Exclude nits.
```

**Why this passes the necessity test:**

The model has the capability to trace call paths, construct failing inputs, and reason about interface contracts. It does not engage these capabilities by default — the training distribution favors surface-level pattern matching and consequence-leading descriptions. Each instruction activates a capability the model already has:

| Instruction | Default behavior it overrides |
|-------------|-------------------------------|
| Staff engineer persona | Without it, the model defaults to a generic assistant that hedges, flags style issues, and writes verbose findings. The persona activates the senior engineering review distribution. |
| Output quality bar (three things) | Without it, the model pattern-matches on code shapes and reports observations without constructing concrete proof. The quality bar requires each sighting to demonstrate mechanism, failing input, and caller impact — the model already knows how to produce these, but doesn't by default. |
| "If you cannot construct one, the issue is not behavioral" | Without it, the model classifies by pattern shape. This forces the model to test its own classification claim before emitting. |
| "Caller impact" requirement | Without it, the model stays within the immediate code block. This nudges the model to check interface contracts — a reasoning pattern it has but doesn't default to. |

### 4.3 Challenger agent persona and workflow

Replace the current Challenger agent definition (`assets/agents/fbk-code-review-challenger.md`) with a persona-driven definition. The current prompt opens with "You are a skeptic" then shifts to 25 lines of procedural instructions. The skeptic identity gets one sentence — not enough weight to override the model's default toward agreement. The replacement strengthens the persona and applies the same output quality bar pattern as the Detector.

**Proposed agent definition:**

```markdown
---
name: code-review-challenger
description: "Senior engineer who demands proof for every code review finding. Independently reads code, traces callers, and rejects sightings that cannot be demonstrated with evidence."
tools: Read, Grep, Glob
model: sonnet
---

You are a senior engineer who is mistrustful of secondhand descriptions of code. You verify every claim by reading the code yourself, tracing actual values through expressions, and checking what callers expect. You keep the project's design intent in mind — code that works but contradicts the documented intent is a valid finding, and code that looks wrong but aligns with the intent is not.

Every sighting you verify or reject must demonstrate one of two outcomes:

1. **Verified**: You independently confirmed the mechanism by reading the code. You can describe the failing input and the wrong output in your own words, not the Detector's. If you cannot independently reproduce the Detector's reasoning from the code, reject the sighting.
2. **Rejected**: You found concrete counter-evidence — the code does not behave as the Detector described, the input is not constructible, the impact is inaccurately described, or the behavior aligns with the project's documented intent.

For behavioral sightings, trace at least one caller to confirm the behavioral claim is reachable in production. If no production caller exercises the path, reclassify as structural or reject.

When the Detector's type or severity classification does not match what the evidence shows, reclassify. Validate your reclassification against the type-severity matrix provided by the orchestrator.

Reject sightings that are technically accurate but functionally irrelevant (naming, formatting, style) as nits.

Report only verdicts on the sightings provided by the orchestrator. Use your tools to read code, not to modify it.
```

**Why this passes the necessity test:**

| Instruction | Default behavior it overrides |
|-------------|-------------------------------|
| "mistrustful of secondhand descriptions" persona | Without it, the model defaults to agreeing with plausible-sounding sightings. The training distribution heavily favors helpfulness and agreement — the Challenger needs enough persona weight to override that default toward independent verification. |
| "reading the code yourself, tracing actual values" | Without it, the model reasons abstractly about the Detector's description rather than using its Read/Grep/Glob tools to independently check the code. |
| "describe the failing input in your own words, not the Detector's" | Without it, the model paraphrases the Detector's mechanism and calls it verified. This forces independent reasoning — the model must construct its own description from the code. |
| "cannot independently reproduce the Detector's reasoning → reject" | Without it, the model hedges with "weakened" verdicts. This makes the binary clear: prove it yourself or reject it. |
| Design intent awareness | Without it, the model evaluates code in isolation. Including intent means the Challenger can confirm findings where code contradicts design, and reject findings where apparently-wrong code is actually intentional. |

### 4.4 Type and severity classification

Rewrite the type definitions in the Detector agent prompt. Classification is determined by runtime consequence, not pattern shape. Types constrain severities via the validity matrix in section 4.1.

**Type definitions (for the Detector prompt):**

> **behavioral**: The code produces wrong output, data loss, crash, or security bypass for a **concrete, constructible input** using the codebase as it exists in the diff. To classify as behavioral, you must be able to describe a specific input value, call sequence, or execution state that triggers the failure. If you cannot construct such an input without hypothesizing a code change, the finding is not behavioral. Behavioral findings are always critical or major.
>
> **structural**: The code has no wrong output under any input, but is harder to maintain than necessary. Dead code, naming inconsistency without dispatch confusion, duplication without behavioral divergence. Removing or renaming the code would not change any observable output. Structural findings are always minor or info.
>
> **test-integrity**: A test passes but does not verify what it claims. The test name, docstring, or surrounding context implies coverage that the assertions do not provide. A bug in test assertion logic (wrong operator, mocked-away SUT, tautological check) is test-integrity, not behavioral — even if the wrong assertion has a runtime consequence within the test. Dead code in a test file that does not affect test assertions is structural, not test-integrity. Test-integrity findings are critical, major, or minor.
>
> **fragile**: The code produces correct output today, but will break under a **specific, plausible change** you can name. To classify as fragile, you must name the change (e.g., "when the API changes page size from 10 to 20" or "when a second caller passes a non-default value"). If the break is imminent enough that the changed code path will fail on its next execution, the finding is behavioral, not fragile. If you cannot name a specific breaking change, the finding is structural. Fragile findings are always major or minor.

**Disambiguation rules:**
- If a naming issue causes a runtime collision or wrong dispatch, it is `behavioral` — follow the consequence, not the pattern.
- If the code under review is a test file, a bug in the test's assertion logic is `test-integrity`, not `behavioral`.
- To distinguish behavioral from fragile: can you construct a failing input using only the current code? Yes → behavioral. No, you need a hypothetical code change → fragile.

Mechanism-first wording is integrated into the Detector persona (section 4.2) via the output quality bar: "the exact code expression that misbehaves and what it does wrong." This is not a separate instruction — it follows naturally from requiring each sighting to demonstrate the mechanism as its first element.

### 4.5 Severity definitions

Severity is defined by observability — who can observe the problem and how. These definitions constrain valid type-severity combinations via the matrix in section 4.1.

**Severity definitions (for the Detector prompt):**

> **critical**: The next user who exercises the changed code path hits the bug. No special input or timing required — the failure is on the primary path. *A human reviewer would block the PR.*
>
> **major**: A developer can write a test that demonstrates the failure. The triggering input is constructible but not the default path — it requires a specific value, race condition, or error state. *A human reviewer would request changes.*
>
> **minor**: Observable only through code reading. No runtime failure can be demonstrated against the current codebase. Applies to structural issues worth noting and fragile patterns worth documenting. *A human reviewer might leave a comment.*
>
> **info**: Accurate observation with no recommended action. Excluded from finding count by default. *A human reviewer would not comment.*

### 4.6 Detection presets

Formalize presets as named configurations that define the domain filter's type allow-list and the severity filter's default threshold. Presets are the user-facing abstraction — the user selects a preset, and the orchestrator applies the corresponding filters.

| Preset | Allowed types | Default severity threshold | Use case |
|--------|--------------|---------------------------|----------|
| `behavioral-only` | behavioral | minor (drops info) | Default. PR review focused on bugs. |
| `structural` | structural | minor (drops info) | Tech debt audit. |
| `test-only` | test-integrity | minor (drops info) | Test quality review. |
| `full` | behavioral, structural, test-integrity, fragile | minor (drops info) | Complete analysis. |

The default preset is `behavioral-only`. When the user does not specify a preset, apply `behavioral-only` silently. When the user requests a different scope by name (e.g., "run a full review", "check the tests", "structural review"), the orchestrator maps to the appropriate preset. The user can override the severity threshold independently (e.g., "only show me critical and major").

Preset definitions live in a configuration file (`assets/config/presets.json`) so filter scripts can look up allowed types without hardcoding.

### 4.7 Filter pipeline (Python, run via uv)

Create `assets/scripts/pipeline.py` — a single Python module that handles validation, domain filtering, severity filtering, and markdown conversion. All JSON processing in one place, invoked via `uv run`. No shell scripts for JSON manipulation.

**Interface:**
```
uv run assets/scripts/pipeline.py validate < raw.json > validated.json
uv run assets/scripts/pipeline.py domain-filter --preset behavioral-only < validated.json > filtered.json
uv run assets/scripts/pipeline.py severity-filter --min-severity minor < filtered.json > final.json
uv run assets/scripts/pipeline.py to-markdown < final.json > report.md
```

Or as a single pipeline invocation:
```
uv run assets/scripts/pipeline.py run --preset behavioral-only --min-severity minor < raw.json > final.json
uv run assets/scripts/pipeline.py run --preset behavioral-only --min-severity minor --output-markdown < raw.json > report.md
```

**Subcommands:**

- **`validate`**: Parse JSON array, validate required fields, enum values, type-severity matrix. Reject malformed sightings to stderr. Assign sequential S-NN IDs. Output valid sightings.
- **`domain-filter`**: Read preset's allowed types from `assets/config/presets.json`, drop sightings with non-allowed types. Log dropped sightings to stderr.
- **`severity-filter`**: Drop sightings below minimum severity threshold (ordering: info < minor < major < critical). Log dropped sightings to stderr.
- **`to-markdown`**: Convert JSON array to markdown format for review reports. Handle both sightings (S-NN) and findings (F-NN with verification evidence and reclassification notes).
- **`run`**: Execute the full pipeline (validate → domain-filter → severity-filter) in a single invocation. Optionally append markdown conversion with `--output-markdown`.

**Dependencies**: Standard library only (`json`, `sys`, `argparse`, `pathlib`). No pip dependencies — `uv run` executes directly.

Consolidating into one module eliminates duplicate preset path resolution, reduces orchestrator script invocations from three to one, and keeps all JSON processing in a language designed for it.

### 4.8 Orchestrator pipeline update

Update `assets/skills/fbk-code-review/SKILL.md` Detection-Verification Loop:

Current flow:
1. Spawn Detector → collect sightings (markdown)
2. Spawn Challenger → verify/reject (markdown)
3. Repeat

New flow:
1. Spawn Detector with code-review-guide.md (containing type definitions, severity definitions, validity matrix, and JSON schema) + target code + intent register → collect sightings as JSON
2. Run `uv run pipeline.py run --preset <preset> --min-severity <threshold>` — validates, domain-filters, severity-filters in a single invocation
3. Spawn Challenger with filtered JSON sightings + type definitions, severity definitions, and validity matrix (same as Detector). The Challenger needs these to perform reclassification.
4. Validate Challenger output — status/evidence fields, matrix validation on any reclassified type-severity
5. Orchestrator filters to `status: verified` or `verified-pending-execution`, assigns F-NN IDs
6. Run `uv run pipeline.py to-markdown` — convert verified findings to markdown for review report. Adjacent observations from the Challenger are rendered at the end of each finding and accumulated into the retrospective.
7. Repeat from step 1 for weakened-but-not-rejected sightings. Terminate when a round produces no new sightings above info severity, or after a maximum of 5 rounds (carrying forward the existing SKILL.md termination bounds).

JSON stays as the working format throughout the pipeline. Markdown conversion happens once, at the end, for the human-facing review report. The Challenger receives and produces JSON — no format translation between agents. One Python invocation for filtering, one for markdown conversion.

The orchestrator resolves the active preset and severity threshold at the start of the review. Defaults: preset=`behavioral-only`, severity=`minor`. If >30% of sightings are rejected during validation at either stage, log a warning about prompt compliance.

### 4.9 Code review guide update

Update `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md` to align with the new definitions. The guide is the canonical reference — the orchestrator injects it into both the Detector and Challenger spawn prompts. Stale definitions in the guide would conflict with the updated Detector agent prompt.

**Sections to update:**

- **Finding Classification > Type axis** (currently line 69): Replace pattern-shape definitions ("code does something different from what its name, documentation, or spec says") with the consequence-based definitions from section 4.4. Include the disambiguation rules and severity constraints per type.
- **Finding Classification > Severity axis** (currently line 80): Replace subjective risk definitions ("significant risk under realistic conditions") with the observability-based definitions from section 4.5. Include the human-reviewer action mapping (block PR / request changes / comment / no action).
- **Sighting Format** (currently line 19): Replace the markdown template with a reference to the JSON schema in section 4.1. Document the required/optional fields, enum values, and type-severity validity matrix.
- **Finding Format** (currently line 46): Replace with a reference to the unified JSON schema in section 4.1. Sightings and findings share the same schema — findings are sightings with Challenger verdict fields added. The separate finding format section in the guide becomes a description of the Challenger's additions (`status`, `verification_evidence`, `reclassified_from`), not a separate template.
- **Orchestration Protocol** (currently line 91): Update to reflect the new pipeline flow from section 4.8 — JSON throughout, validation at both stages, domain filter, severity filter, markdown conversion once at the end.

### 4.10 Benchmark infrastructure

Copy the benchmark runner, inject, and judge scripts into the project so they can be run against the current branch for comparison:

- `ai-docs/detection-accuracy/martian-benchmark/run_reviews.sh` — headless benchmark runner
- `ai-docs/detection-accuracy/martian-benchmark/inject_results.py` — converts review output to benchmark format
- `ai-docs/detection-accuracy/martian-benchmark/judge_anthropic.py` — LLM judge (or subagent-based equivalent)
- `ai-docs/detection-accuracy/martian-benchmark/manifest.json` — 50-PR corpus
- `ai-docs/detection-accuracy/martian-benchmark/diffs/` — PR diffs
- `ai-docs/detection-accuracy/martian-benchmark/benchmark-prompt.md` — headless mode overrides

These already exist on the `feature/0.4.0-detector-decomposition` branch and will be cherry-picked.

### 4.11 Inject script rewrite

Rewrite `inject_results.py` to consume JSON findings instead of parsing markdown. The current script uses 11 regex patterns to extract severity, 6 patterns for location, and heuristic body extraction from markdown — all of which produced parse failures during the v0.4.0 benchmark run (104 "unknown" type findings across 50 PRs due to format variation). With the unified JSON schema, parsing is eliminated.

**Current behavior** (markdown parsing):
1. Read markdown review file
2. Split on finding headers using regex (`### F-NN`)
3. Extract severity via 11 ordered regex patterns across multiple format variants
4. Extract location via 6 regex patterns
5. Strip metadata fields from body using heuristic line matching
6. Output `{"path", "line", "body", "severity"}` per finding

**New behavior** (JSON consumption):
1. Read the JSON findings file produced by the pipeline (verified findings with `status: verified`)
2. Map schema fields directly to benchmark format:
   - `location.file` → `path`
   - `location.start_line` → `line`
   - `mechanism` + `consequence` → `body` (concatenated for benchmark judge matching)
   - `severity` → `severity`
   - `type` → `type` (new — enables post-hoc charter analysis)
   - `origin` → `origin` (new — enables origin-based analysis)
3. Apply severity filter (configurable `--min-severity`, same as pipeline filter)
4. Output to benchmark_data.json in the existing format

**What this eliminates:**
- All 11 severity regex patterns
- All 6 location regex patterns
- The `_is_metadata_line` heuristic
- The `parse_findings_flat` fallback parser
- Format-dependent parse failures

**What stays the same:**
- The `match_pr_to_benchmark` function (matching PRs to benchmark entries)
- The output format into benchmark_data.json
- The `--tool-name`, `--dry-run`, `--min-severity` CLI interface

The script also gains access to fields that were previously unparseable: `type`, `origin`, `detection_source`, `pattern`, `reclassified_from`. These enable richer benchmark analysis (per-type TP rates, origin-based filtering, reclassification tracking) without additional parsing.

### 4.12 Per-run benchmark metadata

Extend the benchmark infrastructure to capture per-finding metadata for each run, enabling type accuracy, severity calibration, and misclassification tracking:

```
run_date, pipeline_version, pr_id, finding_id, detector_type, detector_severity,
challenger_type, challenger_severity, reclassified, origin, judge_verdict,
matched_golden_index
```

The Challenger records reclassification via a `reclassified_from` field in the finding format. When the Challenger does not reclassify, the field is empty. When it does, it records the original type and severity. This makes Challenger reclassification auditable.

**Metrics computed per run** (provisional thresholds — calibrate after first full run):

| Metric | Healthy | Investigate |
|--------|---------|-------------|
| TP rate for behavioral type | ≥25% | <20% (type system not discriminating) |
| Domain filter loss (TPs dropped / total TPs) | <10% | ≥10% (misclassification problem) |
| Severity TP gradient | critical > major > minor > info | Ordering violated (severity definitions need tuning) |
| Challenger reclassification rate | <10% | ≥15% (Detector type assignment unreliable) |
| Parse failure rate | <5% | ≥30% (prompt drift) |
| Per-repo recall | ≥50% per repo | Any repo <30% (language-specific blind spot) |
| Nit rejection rate | <10% of sightings | ≥20% (Detector persona not filtering nits) |

## 5. Acceptance criteria

### AC-1: Unified JSON schema
Both Detector and Challenger produce JSON per the unified schema in section 4.1. The Detector outputs the base schema (sighting fields). The Challenger adds verdict fields (`status`, `verification_evidence` or `rejection_reason`, optional `reclassified_from`) to the same objects. The orchestrator validates at both stages: required fields present, enum values valid, type-severity matrix enforced. Malformed output is rejected with a warning.

### AC-2: Detector agent persona
The Detector agent definition (`assets/agents/fbk-code-review-detector.md`) uses the persona and output quality bar from section 4.2. The persona identifies the agent as a staff engineer. The quality bar requires each sighting to demonstrate mechanism, concrete failing input, and caller impact.

### AC-3: Challenger agent persona
The Challenger agent definition (`assets/agents/fbk-code-review-challenger.md`) uses the persona and output quality bar from section 4.3. The persona is mistrustful of secondhand code descriptions and verifies independently. Verified sightings demonstrate the Challenger's own reasoning from the code, not the Detector's. Rejected sightings include concrete counter-evidence. The Challenger keeps design intent in mind for verification and rejection decisions.

### AC-4: Consequence-based type classification
The Detector agent definition contains the type definitions from section 4.4 with disambiguation rules. Classification is determined by runtime consequence: if a finding has observable wrong behavior for a concrete, constructible input, its type is `behavioral` regardless of pattern shape.

### AC-5: Severity definitions
The Detector agent definition contains the severity definitions from section 4.5. Severity is defined by observability: critical = next user hits it, major = constructible test demonstrates it, minor = observable through code reading only, info = no action.

### AC-6: Type-severity validity matrix
The sighting parser rejects invalid type-severity combinations per the matrix in section 4.1. behavioral+minor, behavioral+info, structural+critical, structural+major, fragile+critical, fragile+info, and test-integrity+info are rejected.

### AC-7: Mechanism-first wording
Mechanism-first wording is embedded in the Detector persona's output quality bar (section 4.2): each sighting title names the exact code expression and what it does wrong. This is a natural consequence of requiring mechanism as the first of three demonstrated elements, not a separate instruction.

### AC-8: Code review guide alignment
`assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md` contains the consequence-based type definitions from section 4.4, the observability-based severity definitions from section 4.5, the JSON sighting schema reference from section 4.1, the updated finding format with `reclassified_from`, and the updated orchestration protocol from section 4.8. No conflicts exist between the guide and the Detector/Challenger agent prompts.

### AC-9: Detection presets
Preset definitions exist in `assets/config/presets.json` with the four presets from section 4.6. Each preset defines allowed types and default severity threshold. The orchestrator resolves the active preset at review start.

### AC-10: Filter pipeline
`assets/scripts/pipeline.py` exists, run via `uv run`. Subcommands: `validate` (schema validation, type-severity matrix, ID assignment), `domain-filter` (preset-based type filtering from `presets.json`), `severity-filter` (threshold-based severity filtering), `to-markdown` (JSON to markdown for both sightings and findings), `run` (full pipeline in single invocation). All subcommands read JSON on stdin, write JSON or markdown on stdout, log dropped/rejected items to stderr.

### AC-11: Orchestrator integration
The Detection-Verification Loop in SKILL.md follows the pipeline in section 4.8: Detector JSON → `uv run pipeline.py run` → Challenger JSON → validate → filter verified → `uv run pipeline.py to-markdown`. JSON is the working format throughout. Markdown conversion happens once for the review report. Preset defaults to `behavioral-only`, severity threshold defaults to `minor`. Both are overridable by user instruction.

### AC-12: Inject script rewrite
`inject_results.py` reads JSON findings directly per section 4.11, run via `uv run`. No markdown parsing, no regex-based field extraction. Maps unified schema fields to benchmark format. Supports `--min-severity`, `--tool-name`, and `--dry-run`. Passes `type`, `origin`, and `reclassified_from` through to benchmark data for per-run analysis.

### AC-13: Benchmark infrastructure
The Martian benchmark runner, manifest, diffs, inject script, and judge are present and runnable from the project directory. Per-run metadata captures the fields from section 4.12.

### AC-14: Benchmark validation
Manually-triggered 50-PR benchmark runs produce median: P≥25%, R≥65%, F1≥35%, average findings/PR ≤5.0 across a minimum of 3 runs. The improvement over the v0.3.5 baseline (F1=31.6%) must exceed the run-to-run range observed across the 3 post-change runs. If the 3 runs show high internal variance (range >5pp F1), additional runs are needed before concluding. No baseline variance data exists — the v0.3.5 baseline was a single run. The first calibration cycle establishes both the post-change performance and its variance simultaneously. The benchmark is an evaluation tool run by the team — it is not an automated gate in the review flow. Per-run metadata, per-repo breakdown, and comparison against v0.3.5 baseline documented in `ai-docs/detection-accuracy/martian-benchmark/results/`.

## 6. Testing strategy

### Unit tests

- **JSON sighting parser**: Test valid sightings parse correctly. Test missing required fields are rejected. Test invalid enum values are rejected. Test invalid type-severity combinations (e.g., behavioral+minor) are rejected.
- **Pipeline subcommands** (`pipeline.py`): Test each subcommand independently:
  - `validate`: Valid sightings pass. Missing required fields rejected. Invalid enums rejected. Invalid type-severity combinations rejected.
  - `domain-filter`: Each preset against each finding type. Behavioral-only passes behavioral, drops others. Full passes all. Stderr logging of drops. Preset lookup from presets.json.
  - `severity-filter`: Each threshold level. `minor` drops info. `major` drops info+minor. `critical` drops everything below critical.
  - `to-markdown`: All fields render correctly. Sighting format (S-NN) and finding format (F-NN with verification evidence, reclassification notes) both render. `rejected-as-nit` findings excluded from output.
  - `run`: Full pipeline produces same output as sequential subcommand invocations.
- **Type-severity validity matrix**: Exhaustive test of all 16 type-severity combinations against the matrix.
- **Pipeline edge cases**: Empty input arrays (output `[]`), all sightings filtered (output `[]`), unknown preset name (clear error to stderr, non-zero exit), malformed JSON input (clear error, non-zero exit), unicode in field values, empty-string pattern field passes validation.
- **Content validation tests**: Grep-based TAP tests (following existing test suite pattern) verifying: Detector persona contains staff engineer identity and output quality bar, type definitions contain consequence-based language, severity definitions contain observability-based language, guide contains matching definitions.
- **Inject script unit tests**: Fixture-based — feed known JSON findings, verify output matches expected benchmark format. Test field mapping, severity filtering, and edge cases.
- **Preset config validation**: Verify presets.json contains all four presets, each with valid `allowed_types` and `default_severity_threshold`.

### Integration tests

- **Deterministic pipeline test** (fixture-driven): Pass a canned JSON sighting array through validate → domain filter → severity filter → markdown conversion. Verify correct sightings survive, counts match, type-severity matrix rejects invalid combinations, and markdown output is well-formed. No LLM involvement.
- **Live orchestrator test** (non-deterministic): Run a review against a known diff. Assert structural properties only: output is valid JSON, schema-compliant, pipeline steps executed in order, Challenger receives filtered JSON sightings (not markdown). Accept that content varies across runs. Verify per-run metadata is captured.

### Existing test updates

The following existing tests will break due to format and definition changes and must be updated. Run the full test suite before and after implementation to catch any additional breakage.

**High-confidence breakage:**
- `test-code-review-structural.sh` tests 7, 16, 18: Test 7 checks Detector description for "analysis|detect|pattern" — new description uses "reviewing code for bugs." Tests 16, 18 check guide for "current behavior", "expected behavior", "Observation", "Expected" — replaced by `mechanism`, `consequence`, `evidence`.
- `test-instruction-hygiene-agents.sh` tests 1-6: Tests 1-2 check Detector for "Exclude nits" within a "Scope discipline" section — new Detector has "Exclude nits" but no "Scope discipline" heading. Tests 3-4 check Challenger for "pattern label" wording. Tests 5-6 check guide for "Pattern label:" — replaced by JSON `pattern` field.
- `test-classification-system.sh` tests 8, 10: Check Detector body for type and severity keywords — new Detector delegates these to "the orchestrator" without containing the values directly.
- `test-code-review-guide-extensions.sh` tests 1-2: Test 2 checks for "name-scope" in test-integrity definition — wording changed.

**Likely breakage (verify during implementation):**
- `test-code-review-integration.sh` tests 7, 8, 20: Check Detector/Challenger sighting ID format, orchestration loop keywords, finding format consistency.
- `test-orchestration-extensions.sh` tests 5, 8, 9: Check SKILL.md for stuck-agent recovery, quality-detection reference, detection source tagging — orchestrator rewrite may relocate these.
- `test-category-migration.sh` tests 8, 9: Check Detector output uses "type and severity" and Challenger "rejects nits."
- `test-challenger-extensions.sh` tests 1-6: Check Challenger for "adjacent observation", "caller tracing", "verified-pending-execution" — Challenger update may rephrase.
- `test-instruction-hygiene-orchestration.sh` tests 1-2, 6: Check SKILL.md and guide for "content-first ordering" language.
- `test-code-review-skill.sh` tests 5-9: Check SKILL.md path references — orchestrator rewrite may change these.

### Benchmark validation

- Run the full 50-PR Martian benchmark with the updated pipeline. Compare against v0.3.5 baseline and v0.4.0 decomposition results. Document P/R/F1, per-repo breakdown, per-type TP rate, per-severity TP rate, domain filter loss rate, parse failure rate, and Challenger reclassification rate.
- For the first calibration runs, use `--preset full` so the Challenger sees all sightings regardless of type. This measures the actual reclassification rate under the new type definitions and the true domain filter loss. Apply domain filtering post-hoc for scoring. Once the reclassification rate is confirmed low (<10%), switch subsequent runs to `--preset behavioral-only` to match production behavior.

## 7. Risks and mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Detector produces malformed JSON | Pipeline validation fails, findings lost | `pipeline.py validate` rejects with clear error messages; orchestrator re-prompts Detector with format reminder on first failure. Track parse failure rate — warn if >30%. |
| Detector produces invalid type-severity combinations | Sightings rejected by matrix validation | Detector prompt includes validity matrix. Rejected sightings logged for analysis. If rejection rate is high, add worked examples to prompt. |
| Consequence-based classification still produces misclassification | Domain filter drops valid behavioral findings, reducing recall | Monitor domain filter loss (TPs dropped / total TPs) per benchmark run. If >10%, add disambiguation examples. The concrete-input heuristic reduces this risk vs. v0.4.0's pattern-shape approach. **Recall fallback**: if benchmark recall drops below 65%, iterate on type definitions. If below 60%, widen the behavioral-only preset to include fragile findings. |
| Mechanism-first wording reduces finding detail | Findings become too terse for human reviewers | Consequence, Evidence, and Remediation fields preserve detail. Only the title and Mechanism field change. |
| Domain filter before Challenger misses reclassification | Challenger would have reclassified a structural finding as behavioral | Acceptable tradeoff for token savings. Challenger reclassification is rare (<5% of sightings in v0.4.0 data). Track reclassification rate via reclassified_from field. |
| Severity filter at `minor` is too aggressive or too lenient | Drops valuable findings or doesn't reduce noise enough | Threshold is configurable per preset and overridable by user. Default `minor` only drops info. Benchmark severity TP gradient will validate. |
| Origin classification unreliable on diff-only context | Pre-existing/introduced distinction is wrong, filters drop TPs | Origin defaults to `unknown`. Measure origin accuracy in benchmark before using it as a filter lever. For now, origin is metadata only — not used in filter pipeline. |

## 8. Dependencies and sequencing

No external dependencies. All changes are to context assets (agent prompts, skill orchestrator, shell scripts, config files) and benchmark infrastructure.

Sequencing is split into two phases. Phase A (pipeline) is validated manually on 3-5 PRs before investing in Phase B (benchmark automation). If Phase A surfaces prompt compliance issues (high parse failure rate, malformed JSON), iterate before burning benchmark credits.

**Phase A — Pipeline (ACs 1-11):**
1. Create preset configuration (`assets/config/presets.json`)
2. Implement `pipeline.py` (validate, domain-filter, severity-filter, to-markdown, run) via uv
3. Update Detector agent definition (persona, output quality bar)
4. Update Challenger agent definition (JSON input/output, verdict fields, `reclassified_from`, `rejected-as-nit`)
5. Update code-review-guide.md (type definitions, severity definitions, unified schema, orchestration protocol)
6. Update orchestrator pipeline (SKILL.md)
7. Update existing tests for new format and definitions
8. Manual validation: run 3-5 reviews, verify JSON compliance, filter behavior, and markdown output

**Phase B — Benchmark (ACs 12-14):**
9. Cherry-pick benchmark infrastructure from decomposition branch
10. Rewrite `inject_results.py` for JSON consumption via uv
11. Run benchmark validation with per-run metadata capture

## 9. Future considerations

- **Severity tuning from benchmark data**: Use per-severity TP rates to set optimal thresholds. If major TP rate is significantly higher than minor, consider defaulting to `major` threshold.
- **Confidence scoring**: If multi-agent agreement or Challenger confidence becomes measurable, add as a secondary filter. Requires architectural change (not viable with single detector).
- **Origin-based filtering**: Once origin classification accuracy is measured (>90% of TPs tagged `introduced`), add origin to the filter pipeline for benchmark and PR review modes.
- **Full repo context**: All 38 Martian benchmark tools had full repo access. Adding repo context to the Detector would improve recall on extra-diff-dependent findings (~21 of 43 baseline FNs are extra-diff dependent).
- **Affected symbols field**: When full-repo context is available, add `affected_symbols` for downstream impact tracking and cross-finding deduplication.
- **Persona pass across all agents and skills (0.4.1)**: Apply the prompting design principle to remaining agents and skills. Specific candidates: (a) 6 council agents — currently description-heavy, need activation-focused personas with output quality bars. (b) `fbk-improvement-analyst` — add one persona sentence: "precise analyst who only proposes changes backed by specific evidence from the retrospective, resists the urge to improve things that are working." (c) `fbk-test-reviewer` — add one persona sentence: "senior software validation engineer who writes and reviews tests for enterprise-grade software that is maintainable and functionally accurate to the design intent, suspicious of empty coverage and agentic test artifacts." (d) SDL workflow skills (`/fbk-spec`, `/fbk-breakdown`, `/fbk-implement`, `/fbk-spec-review`) — these run as the main session with no persona shaping. Consider whether they should become spawned agents or whether skill-level persona instructions are sufficient.
