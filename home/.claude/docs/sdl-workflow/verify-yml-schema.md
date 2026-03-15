Place `verify.yml` at `.claude/automation/verify.yml` in the project root.

## Schema

Each entry under `checks:` defines a verification check:

```yaml
checks:
  - name: "string - check identifier"
    command: "string - shell command to execute"
    required: true|false
    threshold: 0.8  # optional, check-specific
```

### Fields

- `name`: string. Unique check identifier.
- `command`: string. Shell command to execute from the project root.
- `required`: boolean. `true` = pipeline-blocking failure on check fail. `false` = advisory (log result, do not block).
- `threshold`: numeric, optional. Check-specific threshold value. When present, the execution engine passes the threshold to the check command (mechanism TBD in Phase 2). Checks that support thresholds document their threshold interpretation.

## Example checks

```yaml
checks:
  - name: test-execution
    command: "npm test -- --reporter json"
    required: true

  - name: linter
    command: "npm run lint -- --format json"
    required: true

  - name: test-hash-immutability
    command: "bash home/.claude/hooks/sdl-workflow/test-hash-gate.sh ai-docs/$FEATURE/"
    required: true
```

## Execution contract

The command runs in the project root. Exit 0 = check passed, non-zero = check failed. Stdout should be JSON with at minimum `{"result": "pass"|"fail"}`. Stderr is captured for error reporting.

## Required vs advisory

Required checks (`required: true`) block pipeline advancement. On failure, the pipeline state transitions to PARKED with the check failure attached as the reason.

Advisory checks (`required: false`) log results to the audit log but do not block pipeline progression. They appear in status output as informational notes.

## Threshold semantics

When a `threshold` value is present, the check command receives it as context for its pass/fail decision. Each check defines its own interpretation of the threshold (e.g., minimum coverage percentage, maximum allowed warnings). Checks without a threshold use their own internal defaults.
