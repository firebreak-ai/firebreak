# Martian Benchmark Deviation Analysis

**Version**: Firebreak v0.3.5
**Scope**: 50 PRs, 136 golden comments, 452 Firebreak findings
**Date**: 2026-04-09
**Judge**: Consensus (3x independent Opus sub-agents per PR, majority vote, 95.6% unanimous)
**Data source**: `deviation_map.json` (automated from `judge_consensus.json`)

---

## Executive Summary

Firebreak v0.3.5 achieves **68.4% recall** (93/136 golden comments matched) with **20.5% precision** across all finding types. The precision gap is a scope mismatch: 56% of false positives are non-behavioral finding types (structural, test-integrity, fragile) that the benchmark doesn't score. Filtering to behavioral findings only projects **F1=46.4%**, which would place Firebreak between Devin (44.6%) and Augment (53.4%) on the leaderboard — and Firebreak ran diff-only while all competing tools had full repo access.

---

## 1. Judge Methodology

### The judge variance problem

Initial evaluation used a single-pass in-conversation judge (Opus). Spot-checking revealed vocabulary-mismatch errors: findings describing the same bug as golden comments were marked null because the framing differed (e.g., "DateTimePaginator allows negative offset" vs "Django querysets do not support negative slicing").

A single Opus sub-agent re-run disagreed with the original on ~25% of judgments. A Sonnet sub-agent run disagreed on ~28%. Neither run was ground truth — the variance is inherent to the semantic matching task.

### Consensus protocol

To produce a stable baseline, each of the 136 golden-to-findings comparisons is evaluated by **3 independent Opus sub-agents** running in parallel with isolated context windows. Each agent receives the benchmark's judge prompt (semantic matching, accept different wording, focus on same underlying issue). Results are aggregated by **majority vote**.

- **95.6% unanimous** (130/136 judgments): all 3 agents agreed
- **4.4% split** (6 judgments): 2-1 decisions on genuinely ambiguous cases
- **0 failures** across 150 agent invocations

This methodology should be used for all future benchmark evaluations to ensure comparability across versions.

### Split votes (the 6 ambiguous cases)

| Severity | PR | Golden | Votes | Consensus |
|----------|-----|--------|-------|-----------|
| High | grafana PR103633 | Asymmetric cache trust logic | [null, 1, null] | null |
| High | keycloak PR36880 | Orphaned permissions from feature flag | [2, 3, 2] | match→2 |
| High | keycloak PR37038 | Incorrect canManage() permission check | [5, null, null] | null |
| Medium | cal.com PR14740 | uniqueGuests doesn't deduplicate input | [15, 18, 15] | match→15 |
| Low | discourse PR5 | Float/flexbox layout conflict | [2, 2, null] | match→2 |
| Low | discourse PR7 | Lightness value inversion | [null, 1, null] | null |

---

## 2. Headline Numbers

| Metric | Firebreak v0.3.5 |
|--------|-----------------|
| **Precision** | **20.5%** |
| **Recall** | **68.4%** |
| **F1** | **31.6%** |
| Findings/PR (avg) | 9.0 |
| Golden/PR (avg) | 2.7 |
| TP | 93 |
| FP | 360 |
| FN | 43 |

### Leaderboard comparison

| Tool | P | R | F1 | Context |
|------|---|---|-----|---------|
| cubic-v2 (leader) | 55.6% | 68.6% | 61.4% | Full repo |
| augment | 46.0% | 63.5% | 53.4% | Full repo |
| **Firebreak v0.3.5 (behavioral-only projected)** | **35.5%** | **67.2%** | **46.4%** | **Diff only** |
| devin | 54.2% | 38.0% | 44.6% | Full repo |
| claude (raw) | 35.7% | 40.1% | 37.8% | Full repo |
| claude-code | 30.7% | 40.1% | 34.8% | Full repo |
| Firebreak v0.3.5 (all types) | 20.5% | 68.4% | 31.6% | Diff only |

Firebreak's behavioral-only projection beats Devin (+1.8pp F1) and raw Claude (+8.6pp). The gap to cubic-v2 (15pp) is almost entirely precision — recall is nearly identical (67.2% vs 68.6%). Firebreak achieved this running diff-only while every other tool had full repository access.

## 3. Recall Analysis

### Severity-stratified recall

| Severity | TP | FN | Recall |
|----------|----|----|--------|
| Critical | 8 | 1 | **88.9%** |
| High | 28 | 13 | **68.3%** |
| Medium | 33 | 14 | **70.2%** |
| Low | 24 | 15 | **61.5%** |

### The 43 false negatives

By auto-classified category:

| Category | Count | Examples |
|----------|-------|---------|
| api-misuse | 8 | Django negative slicing, missing React key prop, Rails serializer convention |
| style | 7 | Redundant optional chaining, magic numbers, docstring mismatches |
| logic-error | 5 | Wrong permission check, falsy zero, misleading error return |
| data-integrity | 4 | Case-sensitive validation, migration normalization gap |
| null-safety | 4 | Nil request panic, missing state check |
| type-error | 4 | Go Exec signature, SpawnProcess subclass, datetime floor/ceil |
| test-quality | 3 | Test name mismatch, unused test parameter |
| naming | 2 | Typo in method name, inconsistent file/function naming |
| other | 3 | Cache trust asymmetry, component dependency, postMessage targetOrigin |
| race-condition | 1 | Thread-safety of lazy instance variable |
| security | 1 | X-Frame-Options ALLOWALL |
| error-handling | 1 | Missing try-catch for import failures |

### Total-miss PRs (0 TPs)

7 PRs had zero true positives despite having golden comments:

| PR | Golden | Findings | Analysis |
|----|--------|----------|----------|
| grafana PR106778 | 2 | 13 | Framework-specific (React component dependency chain) |
| grafana PR107534 | 1 | 8 | Golden is test-specificity issue (unused param) |
| sentry-greptile PR5 | 3 | 8 | Found different issues than golden |
| sentry PR95633 | 3 | 7 | Framework-specific (Python queue.shutdown, magic numbers) |
| keycloak PR36882 | 1 | 9 | Found structural/test issues, missed picocli exit() |
| discourse PR9 | 2 | 2 | Ruby thread-safety / symbol normalization |
| discourse PR7 | 3 | 6 | CSS lightness value mismatches (1 split-vote near-miss) |

## 4. Precision Analysis

### Why precision is low

Firebreak produces 9.0 findings/PR vs 2.7 golden comments/PR. The surplus generates benchmark FPs regardless of finding quality.

### FP breakdown by finding type

| Finding Type | FP Count | % of FPs | In golden set? |
|-------------|----------|----------|----------------|
| behavioral | 160 | 44.4% | Yes (most goldens are behavioral) |
| structural | 86 | 23.9% | Rarely |
| test-integrity | 78 | 21.7% | Almost never |
| fragile | 36 | 10.0% | Rarely |

**56% of FPs are non-behavioral findings** the golden set structurally cannot reward.

### FP breakdown by severity

| Severity | FP Count | % of FPs |
|----------|----------|----------|
| minor | 200 | 55.6% |
| major | 137 | 38.1% |
| critical | 16 | 4.4% |
| info | 7 | 1.9% |

### Severity calibration

Firebreak consistently over-rates severity relative to the golden set. Among TPs where both golden and Firebreak severity are known: 57% of Low goldens were rated major by Firebreak. Only 3 cases of under-rating (High golden → minor finding).

## 5. Per-Repo Variance

| Repo | PRs | P | R | F1 |
|------|-----|---|---|---|
| cal_dot_com | 10 | 22.3% | 80.6% | 34.9% |
| keycloak | 10 | 21.6% | 66.7% | 32.6% |
| discourse | 10 | 20.7% | 67.9% | 31.7% |
| sentry | 10 | 20.4% | 64.5% | 31.0% |
| grafana | 10 | 16.9% | 59.1% | 26.3% |

Sentry improved significantly under consensus judging (31.0% from 21.5% under manual judge) — the original judge missed several sentry matches due to vocabulary mismatch.

## 6. Implications for 0.4.0

### What the deviation data tells us

1. **Per-type detection filters are the highest-leverage precision improvement.** Behavioral-only filtering projects F1 from 31.6% to 46.4% (+14.8pp). This is a spawn-time decision in the decomposed architecture — skip unwanted detector groups entirely.

2. **Minor findings are the single largest precision drag** (200 FPs, 55.6%). A severity threshold filter stacks with type filtering.

3. **Diff-only evaluation disadvantage** — Firebreak ran diff-only while all competing tools had full repo access (see Section 8). Providing repo context would likely recover many of the extra-diff-dependent FNs.

4. **Output verbosity is a cost lever.** Intent register and retrospective are diagnostic scaffolding that inflates tokens. Production-mode findings-only output could reduce cost 60-70%.

### Scoring projections under decomposition

| Config | P | R | F1 |
|--------|---|---|-----|
| All types (current) | 20.5% | 68.4% | 31.6% |
| Behavioral only | ~35.5% | ~67.2% | ~46.4% |
| Behavioral only + repo context (projected) | ~35-40% | ~80-85% | ~50-55% |

## 7. The Extra-Diff Knowledge Dependency Pattern

### Discovery

All competing tools on the Martian benchmark receive the **full repository** via `step0_fork_prs.py` (clones repo, pushes to fork org, recreates PR). Tools review with full codebase access. Golden comments were created by human reviewers with full repo context.

**Firebreak was the only tool evaluated diff-only.** This was not a deliberate choice — `run_reviews.sh` passes just the diff file to `claude -p`.

### Pattern definition

**Extra-Diff Knowledge Dependency**: A detection failure where the information required to identify the bug is not present in the diff. The reviewer must bring knowledge from the broader codebase, framework documentation, or runtime behavior.

Of the 43 FNs, **~21 are extra-diff dependent**. Among the High-severity FNs, the majority are extra-diff dependent.

### Three sub-types

**Sub-type 1: Framework/Runtime Behavior Knowledge (~12 FNs)**

| FN | Language | Knowledge required |
|----|----------|--------------------|
| Django negative slicing | Python | Django QuerySets raise on negative indices |
| `queue.shutdown(immediate=False)` | Python | Method doesn't exist in stdlib `queue` |
| SpawnProcess not a Process subclass | Python | `get_context('spawn').Process` returns different class on POSIX |
| `hash()` non-deterministic | Python | CPython hash randomization across processes |
| Rails `include_?` suffix | Ruby | Rails serializer naming convention |
| Thread-safety of lazy `@loaded_locales` | Ruby | Ruby instance variable init not thread-safe |
| picocli `exit()` calls `System.exit()` | Java | picocli API semantics |
| BouncyCastle vs default keystore | Java | Java crypto provider resolution |
| `dbSession.Exec(args...)` signature | Go | xorm's Exec requires string first arg |
| `postMessage` targetOrigin spec | JS | Web API spec requirement |
| React `key` prop | React | React reconciliation requirement |
| `sample_rate = 0.0` is falsy | Python | Python truthiness edge case |

**Sub-type 2: Cross-File Contract Knowledge (~7 FNs)**

| FN | Language | Knowledge required |
|----|----------|--------------------|
| React component dependency chain | React | `SilenceGrafanaRuleDrawer` depends on Ruler rule |
| Interface implementations not updated | TypeScript | Lark/Office365 didn't get new param |
| Keycloak passkey auth flow | Java | `context.getUser()` null on initial login |
| Resource owner mismatch | Java | `findByName` owner vs `getOrCreateResource` owner |
| Permission model `canManage()` | Java | Keycloak authorization resource model |
| Migration data normalization | Ruby | Existing rows include `http://` |
| Cache trust asymmetry | Go | Full cache flow across check/grant/deny |

**Sub-type 3: Regression/History Knowledge (~2 FNs)**

| FN | Language | Knowledge required |
|----|----------|--------------------|
| Nil request panic is a regression | Go | Previous middleware handled nil requests |
| OAuth state uses static value | Python | Should be per-request random |

### Recall projections with repo context

| Scenario | Recovered FNs | Recall | With behavioral-only F1 |
|----------|--------------|--------|------------------------|
| Current (diff-only) | — | 68.4% | 46.4% |
| Conservative (cross-file only) | +7-10 | ~74-77% | ~49-51% |
| Moderate (+ framework-visible) | +15-18 | ~80-82% | ~52-55% |

### Recommended action

Re-run 5-10 extra-diff FN PRs with repo context to empirically validate the projected recall improvement.

---

## 8. Action Items

### Methodology (established)
1. Use consensus judge protocol (3x independent Opus sub-agents, majority vote) for all future benchmark evaluations
2. Use `build_deviation_map.py` against `judge_consensus.json` for deviation analysis
3. Report behavioral-only projection alongside all-types score for leaderboard comparison

### For 0.4.0 evaluation
4. Re-run full 50-PR benchmark after detector decomposition lands
5. Implement per-type detection filters; measure actual (not projected) behavioral-only score
6. Spot-audit 10 random behavioral major FPs to determine valid-vs-hallucination rate

### For detection accuracy
7. Re-run 5-10 extra-diff FN PRs with repo context to validate recall projections
8. Evaluate whether repo-aware review mode belongs in 0.4.0 scope

---

## Appendix: Infrastructure

| File | Purpose |
|------|---------|
| `manifest.json` | PR metadata + golden comments (from Martian benchmark) |
| `reviews/*.md` | Firebreak review outputs (50 PRs) |
| `judge_consensus.json` | Consensus judge results (3x Opus majority vote) |
| `judge_consensus.jsonl` | Raw judge data with all votes and reasoning |
| `judge_variance.json` | Split vote analysis (6 non-unanimous judgments) |
| `deviation_map.json` | Structured deviation data (per-PR TPs, FPs, FNs) |
| `deviation_map.md` | Rendered per-PR detail |
| `build_deviation_map.py` | Generates deviation map from judge + manifest + reviews |
| `prepare_judge_batches.py` | Prepares PR batches for judge agents |
| `run_judge.sh` | Consensus judge orchestrator (3x parallel agents per PR) |
| `aggregate_judge.py` | Aggregates judge votes, computes consensus, reports variance |
