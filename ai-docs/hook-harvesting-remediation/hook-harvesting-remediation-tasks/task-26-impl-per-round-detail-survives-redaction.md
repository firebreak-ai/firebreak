---
id: task-26
type: implementation
wave: 4
covers: [AC-08]
files_to_modify:
  - assets/fbk-scripts/fbk/gates/code_review.py
  - assets/fbk-scripts/fbk/capture/schema.py
  - assets/fbk-scripts/fbk/report.py
  - assets/fbk-scripts/tests/test_gates_code_review.py  # scope revisions: (attempt 1) add the missing `from tests import capture_fixtures` import — latent wave-1 authoring defect masked by the projection skip guard; (attempt 2) in test_valid_round_file_emits_event, replace the stale `"rounds" not in data` assertion (old strip-the-list model, missed by the slice's retired-tests list) with assertions that data["rounds"] is present and every entry carries only the three projected keys (raised, survived, enum severity) with no free text. No other test change permitted.
test_tasks: [task-08, task-09]
dependencies: [task-08, task-09]
completion_gate: "task-08 tests pass (projection unit test, gate main() integration test, one-row-per-round rendering test) and task-09's rebuilt test_standard_level_strips_freetext_payload passes; the rest of tests/test_gates_code_review.py, tests/test_report_rendering.py, and tests/test_capture_event_writer.py stay green"
---

## Objective

Make per-round code-review detail survive to the report at the default capture level: the gate allowlist-projects each round entry at the untrusted round-log boundary, redaction stops deleting the rounds list and instead recurses into it, and the report renders one row per detection round.

## Context

Slice: per-round-detail-survives-redaction. Three coordinated defects:
- `fbk/gates/code_review.py` (main, lines 142-171) writes round entries verbatim from `.code-review-rounds.json` — untrusted input per the project threat model — so free text under an unknown key would reach the events file under a key the redaction denylist has never met.
- `fbk/capture/schema.py` lists `"rounds"` in `FREETEXT_KEYS` (line 35), so `redact` deletes the entire per-round list at `standard` — the report can never render per-round detail.
- `fbk/report.py` collapses each `CODE_REVIEW_ROUNDS` event to a single totals row (`review_rounds` collection at lines 411-424, render at lines 493-503) and carries a dead `round_count`-style field (the `"rounds": round_count` entry, line 423) nothing renders.

Privacy model to preserve: the gate's allowlist projection is the control at the trust boundary; the redaction recursion is defense-in-depth behind it. Redaction stays a key denylist; no event is dropped; `redact` at `full` still returns the payload untouched.

**Gate interface (copied verbatim from task-08 — do not paraphrase).** In `fbk/gates/code_review.py`:

```python
# Fixed severity vocabulary for round entries (matches fbk.pipeline.VALID_SEVERITIES).
ROUND_SEVERITIES = ("critical", "major", "minor", "info")

def project_round_entries(rounds: list) -> list:
    """Allowlist-project round entries read from the untrusted round log.

    Returns a new list: each entry becomes {"raised": ..., "survived": ...}
    plus "severity" only when entry.get("severity") is a member of
    ROUND_SEVERITIES.  Every other key is dropped.  Order is preserved.
    raised/survived are already int-validated by _read_round_log.
    """
```

`main()` applies `project_round_entries` to the rounds before computing totals and writing the event (totals are computed from raised/survived, which projection preserves, so totals are unchanged).

**Schema contract (copied from task-09):** `"rounds"` is removed from `FREETEXT_KEYS`; `schema.redact(data, level)` at any non-`full` level removes every key in `FREETEXT_KEYS` at the top level AND recursively inside nested dicts and inside dicts contained in nested lists, returning copies (input never mutated).

**Render contract (copied verbatim from task-08):** the detection-rounds section prints one line per entry of each `CODE_REVIEW_ROUNDS` event's `data["rounds"]`, flattened in event order and numbered from 1: `  detection round {i}: raised={raised}  survived={survived}  severity={severity}` — the `severity=` segment omitted when the entry has no severity key. The dead `round_count` field is removed. The kill-rate line keeps its current computation from per-event `total_raised`/`total_survived`.

Three-files justification: the projection (producer), the redaction recursion (transport), and the per-round render (consumer) are one seam contract asserted by one set of guards — landing them separately leaves the guard tests red across waves.

Constraints: do NOT modify any test file; file scope is exactly the three files listed. Paths relative to `/home/rahvin/context-assets/assets/fbk-scripts/`.

## Instructions

1. In `fbk/gates/code_review.py`, add `ROUND_SEVERITIES` and `project_round_entries` (verbatim signature/docstring above) after the `MAX_ROUND_FILE_BYTES` constants (line 15) and before `_read_round_log`. Implementation per the docstring:
   ```python
   projected = []
   for entry in rounds:
       slim = {"raised": entry.get("raised"), "survived": entry.get("survived")}
       if entry.get("severity") in ROUND_SEVERITIES:
           slim["severity"] = entry["severity"]
       projected.append(slim)
   return projected
   ```
   (New list and new dicts — the input entries are not mutated.) Done when the unit fixture `[{raised 3, survived 1, severity major}, {raised 2, survived 0, severity minor, notes ...}, {raised 1, survived 1, severity catastrophic}]` projects to exactly `[{raised 3, survived 1, severity major}, {raised 2, survived 0, severity minor}, {raised 1, survived 1}]`.
2. In `main()` (line 149), project before totals: change `rounds = round_log.get("rounds", [])` to `rounds = project_round_entries(round_log.get("rounds", []))`. The following `total_raised`/`total_survived` sums and the event payload then read only projected entries. Add a one-line comment: the round log is untrusted input; only `raised`/`survived`/enum-valid `severity` may reach the events file. Done when the written `data["rounds"]` can never carry an unknown key.
3. In `fbk/capture/schema.py`, remove the `"rounds",` line (35) from `FREETEXT_KEYS` and rewrite `redact` (lines 43-61) to recurse:
   ```python
   if level == "full":
       return data
   return _strip_freetext(data)
   ```
   with a private helper:
   ```python
   def _strip_freetext(value):
       """Recursively remove FREETEXT_KEYS from dicts, including dicts nested
       inside lists. Returns copies; the input is never mutated."""
       if isinstance(value, dict):
           return {k: _strip_freetext(v) for k, v in value.items() if k not in FREETEXT_KEYS}
       if isinstance(value, list):
           return [_strip_freetext(v) for v in value]
       return value
   ```
   Update the `redact` docstring: free-text keys are stripped at every nesting depth (defense-in-depth behind the code-review gate's allowlist projection, which is the control at the trust boundary). Done when a `reason_text` planted inside a round entry is stripped at `standard` while the entry's numeric fields and enum severity survive.
4. In `fbk/report.py`, rework the `CODE_REVIEW_ROUNDS` handling:
   - Collection (lines 411-424): keep `review_rounds` as the per-event totals list for the kill rate, but drop the dead `round_count` derivation and the `"rounds": round_count` entry — each element becomes exactly `{"raised": data.get("total_raised", 0), "survived": data.get("total_survived", 0)}`. Additionally flatten the per-round entries into a new list in the same pass: `all_rounds = []` extended with `data.get("rounds", [])` for each event, in event order (guard with `isinstance(..., list)`).
   - Render (lines 493-503): in the non-empty branch, print one line per entry of `all_rounds`, numbered from 1:
     ```python
     for i, entry in enumerate(all_rounds, 1):
         line = f"  detection round {i}: raised={entry.get('raised')}  survived={entry.get('survived')}"
         if "severity" in entry:
             line += f"  severity={entry['severity']}"
         print(line)
     ```
     The non-empty condition becomes `if review_rounds:` as today (totals drive the kill rate even when a `standard`-level pre-fix event carries no rounds list — then zero round rows print, which is correct for legacy lines). The kill-rate line and the empty-case branch (lines 499-502) are unchanged. Done when two round entries in one event render as exactly two `detection round N:` rows.
5. Run the gating tests. Expected values: gate integration — one event, `source == "code_review"`, projected rounds exactly as step 1, `total_raised == 6`, `total_survived == 2`, raw file free of `FREE-TEXT-LEAK` and `catastrophic`; writer — `data["rounds"] == [{"raised": 3, "survived": 1, "severity": "major"}]` at `standard` with `tool_input` gone; render — two rows plus `kill rate: 0.80`. Existing-green spot checks: rendering smoke fixture (one round, no severity) renders `detection round 1: raised=3  survived=1` and kill rate 0.67; report-integration fixture renders one row from its 5/2 round and kill rate 0.60.

## Files to create/modify

- `assets/fbk-scripts/fbk/gates/code_review.py` (modify)
- `assets/fbk-scripts/fbk/capture/schema.py` (modify)
- `assets/fbk-scripts/fbk/report.py` (modify)

## Test requirements

- Gating: task-08's `tests/test_gates_code_review.py::test_project_round_entries_allowlists_exactly_three_keys`, `::test_round_log_projected_before_event_write`, and `tests/test_report_rendering.py::test_standard_level_renders_one_row_per_detection_round`; task-09's rebuilt `tests/test_capture_event_writer.py::test_standard_level_strips_freetext_payload`.
- Must stay green: the rest of `tests/test_gates_code_review.py` (round-log validation), `tests/test_report_rendering.py` (smoke labels, kill rate 0.67), `tests/test_capture_event_writer.py`, `tests/test_capture_report_integration.py`'s kill-rate assertion (0.60), and `tests/test_capture_schema.py` if present (drift check untouched).

## Acceptance criteria

- AC-08: at `standard` the report renders per-round raised/survived/severity; the gate allowlist-projects each round entry to exactly `raised`, `survived`, and enum-validated `severity` before the event is written; the per-round numeric fields are not stripped by redaction, and redaction recurses into nested round entries as defense-in-depth.

## Model

Sonnet

## Wave

Wave 4
