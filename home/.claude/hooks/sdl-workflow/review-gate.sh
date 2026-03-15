#!/usr/bin/env bash
# review-gate.sh — Stage 2 structural validation for review and threat model artifacts
# Usage: review-gate.sh <review-path> <perspectives> [threat-model-path]
# Exit 0: pass (JSON to stdout). Exit 2: failures (list to stderr).

set -euo pipefail

REVIEW="${1:-}"
PERSPECTIVES="${2:-}"
THREAT_MODEL="${3:-}"
failures=()

fail() { failures+=("$1"); }

[[ -z "$REVIEW" ]]        && { echo "review-gate: review path required" >&2; exit 2; }
[[ -z "$PERSPECTIVES" ]]  && { echo "review-gate: perspectives list required" >&2; exit 2; }
[[ ! -f "$REVIEW" ]]      && { echo "review-gate: review file not found: $REVIEW" >&2; exit 2; }

# Extract a named section from a file (content between heading and next ##)
section_of() { awk -v pat="$1" 'tolower($0)~tolower(pat){s=1;next} s&&/^## /{s=0} s{print}' "$2"; }

# 1. Perspective coverage
IFS=',' read -ra PERSP_LIST <<< "$PERSPECTIVES"
for p in "${PERSP_LIST[@]}"; do
  p="${p//[[:space:]]/}"
  grep -qi "$p" "$REVIEW" || fail "Missing perspective in review: $p"
done

# 2. Severity tags — at least one per perspective section, and overall
grep -qiE 'blocking|important|informational' "$REVIEW" \
  || fail "No severity tags (blocking/important/informational) found in review"
for p in "${PERSP_LIST[@]}"; do
  p="${p//[[:space:]]/}"
  sec=$(section_of "^## .*$p" "$REVIEW")
  if [[ -n "$sec" ]]; then
    echo "$sec" | grep -qiE 'blocking|important|informational' \
      || fail "No severity tag under perspective section: $p"
  fi
done

# 3. Threat model determination section
if ! grep -qiE '^##[[:space:]]+threat model' "$REVIEW"; then
  fail "Missing ## Threat Model ... section"
else
  sec=$(section_of '^## threat model' "$REVIEW")
  echo "$sec" | grep -qiE '\byes\b|\bno\b|\bskip\b' \
    || fail "Threat model determination missing decision (yes/no/skip)"
  [[ $(echo "$sec" | wc -w) -lt 10 ]] \
    && fail "Threat model determination section missing rationale"
fi

# 4. Testing strategy — all 3 categories required
if ! grep -qiE '^##[[:space:]]+test' "$REVIEW"; then
  fail "Missing testing strategy section (## Testing / ## Test ...)"
else
  sec=$(section_of '^## test' "$REVIEW")
  echo "$sec" | grep -qiE 'new tests?|tests? needed'         || fail "Testing: missing 'new tests needed'"
  echo "$sec" | grep -qiE 'existing tests?|tests? impacted'  || fail "Testing: missing 'existing tests impacted'"
  echo "$sec" | grep -qiE 'test infrastructure|infrastructure changes?' \
    || fail "Testing: missing 'test infrastructure changes'"
fi

# 5 & 6. Threat model document checks (only when $3 provided)
TM_PRESENT=false
if [[ -n "$THREAT_MODEL" ]]; then
  TM_PRESENT=true
  if [[ ! -f "$THREAT_MODEL" ]]; then
    fail "Threat model file not found: $THREAT_MODEL"
  else
    grep -qiE '^##[[:space:]]+assets'           "$THREAT_MODEL" || fail "Threat model missing: ## Assets"
    grep -qiE '^##[[:space:]]+threat actors?'   "$THREAT_MODEL" || fail "Threat model missing: ## Threat Actors"
    grep -qiE '^##[[:space:]]+trust boundaries?' "$THREAT_MODEL" || fail "Threat model missing: ## Trust Boundaries"
    grep -qiE '^##[[:space:]]+threats'          "$THREAT_MODEL" || fail "Threat model missing: ## Threats"
    for pat in '^## assets' '^## threat actors?' '^## trust boundaries?' '^## threats'; do
      sec=$(section_of "$pat" "$THREAT_MODEL")
      [[ -z "$(echo "$sec" | tr -d '[:space:]')" ]] \
        && fail "Threat model section is empty: $pat"
    done
  fi
fi

# Report all failures or emit success JSON
if [[ ${#failures[@]} -gt 0 ]]; then
  for f in "${failures[@]}"; do echo "FAIL: $f" >&2; done
  exit 2
fi

persp_json="["; first=true
for p in "${PERSP_LIST[@]}"; do
  p="${p//[[:space:]]/}"
  [[ "$first" == true ]] && first=false || persp_json+=","
  persp_json+="\"$p\""
done
persp_json+="]"

echo "{\"gate\": \"review\", \"perspectives\": $persp_json, \"threat_model\": $TM_PRESENT, \"result\": \"pass\"}"
