---
id: task-08
type: test
wave: 2
covers: [AC-06]
files_to_create:
  - tests/sdl-workflow/test-type-severity-matrix.sh
completion_gate: "bash tests/sdl-workflow/test-type-severity-matrix.sh exits 0"
---

## Objective

Create a TAP-style bash test that exhaustively tests all 16 type-severity combinations against the validity matrix, confirming which are accepted and which are rejected by `pipeline.py validate`.

## Context

The type-severity validity matrix defines which combinations are valid:

|  | critical | major | minor | info |
|--|----------|-------|-------|------|
| behavioral | valid | valid | invalid | invalid |
| structural | invalid | invalid | valid | valid |
| test-integrity | valid | valid | valid | invalid |
| fragile | invalid | valid | valid | invalid |

Valid combinations (9): behavioral+critical, behavioral+major, structural+minor, structural+info, test-integrity+critical, test-integrity+major, test-integrity+minor, fragile+major, fragile+minor.

Invalid combinations (7): behavioral+minor, behavioral+info, structural+critical, structural+major, test-integrity+info, fragile+critical, fragile+info.

## Instructions

Create `tests/sdl-workflow/test-type-severity-matrix.sh` following the TAP pattern.

Define:
```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE="$PROJECT_ROOT/assets/scripts/pipeline.py"
```

Add a trap for cleanup: `trap 'rm -f /tmp/test-matrix-*.json' EXIT`

Create a helper function that generates a minimal valid sighting JSON array with a given type and severity, and feeds it to `pipeline.py validate`:

```bash
test_combination() {
  local type_val="$1"
  local sev_val="$2"
  local expect="$3"  # "valid" or "invalid"
  local desc="$type_val+$sev_val should be $expect"

  cat > /tmp/test-matrix-input.json <<EOJSON
[{
  "id": "S-01",
  "title": "Test sighting for matrix validation check",
  "location": {"file": "src/test.ts", "start_line": 1},
  "type": "$type_val",
  "severity": "$sev_val",
  "mechanism": "Test mechanism for matrix validation exhaustive check",
  "consequence": "Test consequence for matrix validation exhaustive check",
  "evidence": "Lines 1-5"
}]
EOJSON

  local out
  out=$(uv run "$PIPELINE" validate < /tmp/test-matrix-input.json 2>/dev/null)
  local count
  count=$(echo "$out" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "error")

  if [ "$expect" = "valid" ]; then
    if [ "$count" = "1" ]; then
      ok "$desc"
    else
      not_ok "$desc" "expected 1 valid sighting, got $count"
    fi
  else
    if [ "$count" = "0" ]; then
      ok "$desc"
    else
      not_ok "$desc" "expected 0 valid sightings (rejected), got $count"
    fi
  fi
}
```

Call the helper for all 16 combinations in this order:

```bash
# Valid combinations (9)
test_combination "behavioral" "critical" "valid"
test_combination "behavioral" "major" "valid"
test_combination "structural" "minor" "valid"
test_combination "structural" "info" "valid"
test_combination "test-integrity" "critical" "valid"
test_combination "test-integrity" "major" "valid"
test_combination "test-integrity" "minor" "valid"
test_combination "fragile" "major" "valid"
test_combination "fragile" "minor" "valid"

# Invalid combinations (7)
test_combination "behavioral" "minor" "invalid"
test_combination "behavioral" "info" "invalid"
test_combination "structural" "critical" "invalid"
test_combination "structural" "major" "invalid"
test_combination "test-integrity" "info" "invalid"
test_combination "fragile" "critical" "invalid"
test_combination "fragile" "info" "invalid"
```

End with standard summary block.

## Files to create/modify

Create: `tests/sdl-workflow/test-type-severity-matrix.sh` (make executable)

## Test requirements

Executable, exits 0/1. Requires `uv` and `python3`. 16 tests total (9 valid + 7 invalid).

## Acceptance criteria

- 16 TAP tests covering every cell in the 4x4 type-severity matrix
- 9 valid combinations accepted (1 sighting in output)
- 7 invalid combinations rejected (0 sightings in output)
- Tests use `pipeline.py validate` via subprocess invocation
- No hardcoded matrix logic in the test — the test exercises the pipeline's matrix implementation

## Model

sonnet

## Wave

2
