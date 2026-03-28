#!/usr/bin/env bash
# spec-gate.sh — Stage 1 structural validation for spec artifacts
# Make executable: chmod +x spec-gate.sh
# Called by /spec skill: spec-gate.sh <path-to-spec>

set -uo pipefail

SPEC="${1:-}"
FAILS=()

[[ -z "$SPEC" ]] && { echo "Usage: spec-gate.sh <path-to-spec>" >&2; exit 2; }
[[ -f "$SPEC" ]]  || { echo "File not found: $SPEC" >&2; exit 2; }

BASE="$(basename "$SPEC")"
if   [[ "$BASE" == *-spec.md ]];     then SCOPE="feature"
elif [[ "$BASE" == *-overview.md ]]; then SCOPE="project"
else echo "Cannot determine scope: $BASE (expected *-spec.md or *-overview.md)" >&2; exit 2
fi

# Return line number of first heading that matches prefix (case-insensitive), or empty
heading_line() {
  awk -v h="${1,,}" 'tolower($0) ~ ("^" h) { print NR; exit }' "$SPEC"
}

# Extract content between heading at $1 and next ## heading
section_body() {
  awk -v s="$1" 'NR==s{f=1;next} f&&/^## /{exit} f{print}' "$SPEC"
}

# Check heading present + non-empty; set allow_empty=1 to skip non-empty check
check_section() {
  local h="$1" allow_empty="${2:-0}"
  local ln; ln="$(heading_line "$h")"
  if [[ -z "$ln" ]]; then
    FAILS+=("Missing section: $h"); return
  fi
  if [[ "$allow_empty" -eq 0 ]]; then
    local content; content="$(section_body "$ln" | tr -d '[:space:]')"
    [[ -z "$content" ]] && FAILS+=("Empty section: $h")
  fi
}

# Open questions: empty is OK; if populated, each bullet needs rationale
check_open_questions() {
  local ln; ln="$(heading_line "## open questions")"
  [[ -z "$ln" ]] && return
  local body; body="$(section_body "$ln")"
  [[ -z "$(echo "$body" | tr -d '[:space:]')" ]] && return

  local prev_bullet="" prev_ok=0 bad=0
  while IFS= read -r line; do
    if [[ "$line" =~ ^[[:space:]]*[-*+][[:space:]] ]]; then
      [[ -n "$prev_bullet" && $prev_ok -eq 0 ]] && bad=1
      prev_bullet="$line"; prev_ok=0
      # Rationale on same line: text after the question mark
      [[ "${line#*[-*+] }" =~ \?.*[[:alpha:]] ]] && prev_ok=1
    elif [[ -n "$prev_bullet" && "$line" =~ ^[[:space:]] && -n "$(echo "$line" | tr -d '[:space:]')" ]]; then
      prev_ok=1  # indented continuation counts as rationale
    fi
  done <<< "$body"
  [[ -n "$prev_bullet" && $prev_ok -eq 0 ]] && bad=1
  [[ $bad -eq 1 ]] && FAILS+=("Open questions: items must include rationale, not just a bare question")
}

# Feature map must have at least one list item or sub-heading
check_feature_map() {
  local ln; ln="$(heading_line "## feature map")"
  [[ -z "$ln" ]] && return
  local has; has="$(section_body "$ln" | grep -Em1 '^[[:space:]]*[-*+][[:space:]]|^###' || true)"
  [[ -z "$has" ]] && FAILS+=("Feature map: must contain at least one list item or sub-heading")
}

if [[ "$SCOPE" == "feature" ]]; then
  for h in "## Problem" "## Goals" "## User-facing behavior" "## Technical approach" \
            "## Testing strategy" "## Documentation impact" "## Acceptance criteria" \
            "## Dependencies"; do
    check_section "$h"
  done
  check_section "## Open questions" 1
  check_open_questions

  # AC format validation
  AC_LN="$(heading_line "## acceptance criteria")"
  if [[ -n "$AC_LN" ]]; then
    AC_BODY="$(section_body "$AC_LN")"
    AC_IDS="$(echo "$AC_BODY" | grep -oE 'AC-[0-9]+|AC[0-9]+|Criteria-[0-9]+|REQ-[0-9]+' || true)"
    if [[ -z "$AC_IDS" ]]; then
      FAILS+=("Acceptance criteria: no AC identifiers found")
    else
      BAD_ACS="$(echo "$AC_IDS" | grep -vE '^AC-[0-9]+$' || true)"
      if [[ -n "$BAD_ACS" ]]; then
        FAILS+=("Acceptance criteria: invalid AC identifier format (expected AC-NN, found: $(echo "$BAD_ACS" | tr '\n' ', '))")
      fi
    fi
  fi

  # Testing strategy AC traceability
  TS_LN="$(heading_line "## testing strategy")"
  if [[ -n "$TS_LN" ]]; then
    TS_BODY="$(section_body "$TS_LN")"
    TS_ACS="$(echo "$TS_BODY" | grep -oE 'AC-[0-9]+' || true)"
    if [[ -z "$TS_ACS" ]]; then
      FAILS+=("Testing strategy: does not trace to any ACs")
    fi
  fi
else
  for h in "## Vision" "## Architecture" "## Technology decisions" \
            "## Feature map" "## Cross-cutting concerns"; do
    check_section "$h"
  done
  check_section "## Open questions" 1
  check_feature_map
  check_open_questions
fi

if [[ ${#FAILS[@]} -gt 0 ]]; then
  printf '%s\n' "${FAILS[@]}" >&2
  # Log failure to audit logger
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  LOGGER="$SCRIPT_DIR/audit-logger.py"
  if [[ -f "$LOGGER" ]]; then
    SPEC_NAME="$(basename "$SPEC" .md)"
    python3 "$LOGGER" log "$SPEC_NAME" gate_result '{"gate":"spec","result":"fail"}' 2>/dev/null || true
  fi
  exit 2
fi

# Injection detection (only on structural pass)
INJECTION_WARNINGS=0
if command -v python3 &>/dev/null; then
  INJECTION_WARNINGS=$(python3 - "$SPEC" <<'PYEOF'
import sys, re

spec_path = sys.argv[1]
warnings = 0

with open(spec_path, 'rb') as f:
    raw = f.read()

lines = raw.decode('utf-8', errors='replace').split('\n')

# 1. Control character detection (0x00-0x08, 0x0B-0x0C, 0x0E-0x1F)
for i, line in enumerate(lines, 1):
    for ch in line:
        code = ord(ch)
        if (0x00 <= code <= 0x08) or (0x0B <= code <= 0x0C) or (0x0E <= code <= 0x1F):
            print(f"WARNING: [injection] control character U+{code:04X} detected (line {i})", file=sys.stderr)
            warnings += 1
            break  # one warning per line

# 2. Zero-width character detection
zw_chars = {
    '\u200B': 'zero-width space',
    '\u200C': 'zero-width non-joiner',
    '\u200D': 'zero-width joiner',
    '\u2060': 'word joiner',
}
text = raw.decode('utf-8', errors='replace')
for i, line in enumerate(lines, 1):
    for ch, name in zw_chars.items():
        if ch in line:
            print(f"WARNING: [injection] {name} (U+{ord(ch):04X}) detected (line {i})", file=sys.stderr)
            warnings += 1
            break
# BOM not at position 0
if len(raw) > 3:
    bom = '\uFEFF'
    for i, line in enumerate(lines, 1):
        if bom in line and not (i == 1 and line.startswith(bom)):
            print(f"WARNING: [injection] BOM/zero-width no-break space in non-BOM position (line {i})", file=sys.stderr)
            warnings += 1
            break

# 3. HTML comment instruction detection
comment_pattern = re.compile(r'<!--(.*?)-->', re.DOTALL)
exempt_words = {'todo', 'fixme', 'note', 'hack'}
instruction_words = ['ignore', 'disregard', 'override', 'new instructions',
                     'forget', 'approve', 'you are', 'act as', 'pretend']

for m in comment_pattern.finditer(text):
    content = m.group(1).strip().lower()
    # Check if exempt
    words = set(re.findall(r'\w+', content))
    if words and words.issubset(exempt_words | {'', ' '}):
        continue
    # Check for instruction phrases
    for phrase in instruction_words:
        if phrase in content:
            # Find line number
            start = m.start()
            line_num = text[:start].count('\n') + 1
            print(f"WARNING: [injection] HTML comment contains instruction-like phrase '{phrase}' (line {line_num})", file=sys.stderr)
            warnings += 1
            break

# 4. Embedded instruction patterns outside code blocks
instruction_patterns = [
    'ignore previous instructions', 'ignore previous',
    'disregard above', 'disregard all',
    'you are now', 'new instructions:',
    'forget everything', 'override all constraints',
    'act as if', 'disregard above constraints',
]

# Strip fenced code blocks
in_fence = False
clean_lines = []
for line in lines:
    if line.strip().startswith('```'):
        in_fence = not in_fence
        clean_lines.append('')
        continue
    if in_fence:
        clean_lines.append('')
    else:
        # Strip inline code
        clean_lines.append(re.sub(r'`[^`]+`', '', line))

for i, line in enumerate(clean_lines, 1):
    lower = line.lower()
    for pattern in instruction_patterns:
        if pattern in lower:
            print(f"WARNING: [injection] embedded instruction pattern '{pattern}' (line {i})", file=sys.stderr)
            warnings += 1
            break

print(warnings)
PYEOF
  )
fi

# Output JSON result with injection warning count
printf '{"gate":"spec","scope":"%s","result":"pass","injection_warnings":%d}\n' "$SCOPE" "$INJECTION_WARNINGS"

# Log to audit logger
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGGER="$SCRIPT_DIR/audit-logger.py"
if [[ -f "$LOGGER" ]]; then
  SPEC_NAME="$(basename "$SPEC" .md)"
  python3 "$LOGGER" log "$SPEC_NAME" gate_result "{\"gate\":\"spec\",\"scope\":\"$SCOPE\",\"result\":\"pass\",\"injection_warnings\":$INJECTION_WARNINGS}" 2>/dev/null || true
fi
