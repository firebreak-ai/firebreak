# Phase 1: Pipeline Core — Task Overview

## Dependencies

Dependencies:
- T-01 (test-state-engine)
- T-02 (impl-state-engine)
- T-03 (test-audit-logger)
- T-04 (impl-audit-logger)
- T-05 (test-config-loader)
- T-06 (impl-config-loader)
- T-07 (test-spec-validator)
- T-08 (impl-spec-validator)
- T-09 (test-hash-gate)
- T-10 (impl-hash-gate)
- T-11 (test-task-reviewer-deterministic)
- T-12 (impl-task-reviewer-deterministic)
- T-13 (test-status-command)
- T-14 (impl-status-command) ← T-02
- T-15 (test-test-reviewer-agent)
- T-16 (impl-test-reviewer-agent)
- T-17 (test-review-integration)
- T-18 (impl-review-integration) ← T-16
- T-19 (test-breakdown-integration)
- T-20 (impl-breakdown-integration) ← T-16, T-12

## Model Routing Summary

| Task | Model | Rationale |
|------|-------|-----------|
| T-01 | Haiku | Single test file, clear structure |
| T-02 | Sonnet | Multi-concern implementation (19 states, transition validation, JSON persistence) |
| T-03 | Haiku | Single test file, clear structure |
| T-04 | Haiku | Single file, straightforward append-only logging |
| T-05 | Haiku | Single test file with fixtures |
| T-06 | Sonnet | Multi-file (loader + schema doc), YAML parsing, layering logic |
| T-07 | Haiku | Single test file with fixture corpus |
| T-08 | Sonnet | Refactoring existing script, adding injection detection in embedded Python |
| T-09 | Haiku | Single test file, clear structure |
| T-10 | Haiku | Straightforward hash computation script + schema doc |
| T-11 | Opus | 17 cross-referencing fixture files requiring internal consistency |
| T-12 | Sonnet | Multi-concern validation (frontmatter parsing, cross-task checks, embedded Python) |
| T-13 | Haiku | Single test file with fixtures |
| T-14 | Haiku | Single file, reads JSON and formats output |
| T-15 | Haiku | Single test file, structural grep checks |
| T-16 | Sonnet | Complex agent definition with 5 checkpoint specifications |
| T-17 | Haiku | Single test file, structural grep checks |
| T-18 | Sonnet | Skill modification + new doc, requires understanding existing skill structure |
| T-19 | Haiku | Single test file, structural grep checks |
| T-20 | Sonnet | Skill modification + new doc, sequential agent architecture |

## Coverage Map

| AC | Primary Task | Supporting Tasks |
|----|-------------|-----------------|
| AC-01 | T-02 (impl-state-engine) | T-01 (test-state-engine) |
| AC-02 | T-04 (impl-audit-logger) | T-03 (test-audit-logger) |
| AC-03 | T-06 (impl-config-loader) | T-05 (test-config-loader) |
| AC-04 | T-08 (impl-spec-validator) | T-07 (test-spec-validator) |
| AC-05 | T-18 (impl-review-integration) | T-17 (test-review-integration) |
| AC-06 | T-16 (impl-test-reviewer-agent) | T-15 (test-test-reviewer-agent), T-18 (impl-review-integration) |
| AC-07 | T-20 (impl-breakdown-integration) | T-19 (test-breakdown-integration) |
| AC-08 | T-12 (impl-task-reviewer-deterministic) | T-11 (test-task-reviewer-deterministic) |
| AC-09 | T-10 (impl-hash-gate) | T-09 (test-hash-gate) |
| AC-10 | T-14 (impl-status-command) | T-13 (test-status-command) |

## Wave Assignments

### Wave 1

Foundation infrastructure — state tracking, audit logging, project configuration.

| Task | Type | Description |
|------|------|-------------|
| T-01 | test | State engine tests: transition validation, persistence, PARKED/READY lifecycle |
| T-03 | test | Audit logger tests: append-only JSON lines, read, directory creation |
| T-05 | test | Config loader tests: 3-layer merge, cold-start detection, verify.yml, malformed config |
| T-02 | impl | State engine: Python script managing per-spec JSON state with 19-state transition graph |
| T-04 | impl | Audit logger: Python script appending structured JSON lines per spec |
| T-06 | impl | Config loader: Python script with layered config + config.yml schema doc |

### Wave 2

Gate scripts, status command, and test reviewer agent — deterministic validation, pipeline observability, and agent definition.

| Task | Type | Description |
|------|------|-------------|
| T-07 | test | Spec validator tests: structural checks, injection detection, false-positive corpus |
| T-09 | test | Hash gate tests: manifest creation, modification/deletion/addition detection |
| T-11 | test | Task reviewer deterministic tests: frontmatter validation, AC coverage, file scope |
| T-13 | test | Status command tests: output formatting, PARKED display, not-found handling |
| T-15 | test | Test reviewer agent structural tests: file exists, 5 checkpoints, artifact sets |
| T-16 | impl | Test reviewer agent definition: .claude/agents/test-reviewer.md with 5 checkpoints |
| T-08 | impl | Spec validator: refactored spec-gate.sh with injection detection |
| T-10 | impl | Hash gate: test-hash-gate.sh computing SHA-256 manifests + verify.yml schema doc |
| T-12 | impl | Task reviewer deterministic: gate script validating task file structure and consistency |
| T-14 | impl | Status command: dispatch-status.sh reading state JSON and formatting output |

### Wave 3

Skill integration — connecting pipeline components to existing skills.

| Task | Type | Description |
|------|------|-------------|
| T-17 | test | Review integration structural tests: skill references test reviewer, brownfield doc |
| T-19 | test | Breakdown integration structural tests: sequential agents, Agent Teams, brownfield doc |
| T-18 | impl | Review integration: modified /spec-review skill + brownfield-spec.md instruction doc |
| T-20 | impl | Breakdown integration: modified /breakdown skill + brownfield-breakdown.md instruction doc |
