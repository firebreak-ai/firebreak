# Observability Substrate — Quality Scan

Summary: Five quality opportunities, all minor or info; the dominant theme is duplicated path literals and near-identical helper pairs across harvest, finalize, and run-retro that should be consolidated into shared constants/helpers.

## 1. Capture-path literals duplicated across modules

Severity: minor
Location: fbk/harvest.py:161
Opportunity: The `.fbk-capture` and `runs` path segments are written as bare string literals in harvest.py (lines 161, 507, 588), finalize.py (line 73), and run_retro.py (line 22), while gate_check.py already defines `_CAPTURE_DIR_NAME = ".fbk-capture"`.
Why it matters: A future rename of the capture directory or runs subdirectory has to be applied in five hand-found places, and a missed one silently splits readers and writers onto different paths.
Suggested change: Promote a shared `CAPTURE_DIR_NAME` and `RUNS_SUBDIR` (plus a small `runs_dir(project_cwd)` helper) into the capture package and have all three modules import them.

## 2. FBK_PROJECTS_ROOT resolution and run-glob pattern duplicated

Severity: minor
Location: fbk/finalize.py:86
Opportunity: The `os.environ.get("FBK_PROJECTS_ROOT", os.path.expanduser("~/.claude/projects"))` lookup and the `*/*/subagents/workflows/*` glob pattern appear in both `_glob_run_dirs` (finalize.py) and `_resolve_run_dir` (harvest.py:92-97).
Why it matters: The two copies must stay byte-identical for the sweep and the single-run resolver to agree on where runs live; drift between them would make recovery sweeps and targeted finalizes look in different trees.
Suggested change: Extract one shared helper that returns the projects root and one that builds the workflows glob pattern, used by both call sites.

## 3. Earliest/latest timestamp helpers are near-identical twins

Severity: info
Location: fbk/harvest.py:274
Opportunity: `_earliest_ts_str` and `_latest_ts_str` (lines 274-299) are line-for-line identical except for the `<` versus `>` comparison.
Why it matters: Two copies of the same scan-and-compare loop double the surface for a future fix (e.g. tie-breaking or parse-error handling) to be applied inconsistently.
Suggested change: Collapse into one helper parameterised by an `operator.lt`/`operator.gt` (or a `pick_latest: bool`) argument, or use `min`/`max` with a key that parses via `_parse_ts`.

## 4. Absent-descriptor dict literal repeated instead of shared

Severity: info
Location: fbk/harvest.py:349
Opportunity: The literal `{"cardinality": None, "stance": None, "attribution_absent": True}` is constructed in `_build_unit` (harvest.py:349) and independently inside `parse_attribution` as `_absent` (attribution.py:37).
Why it matters: The two modules each encode the same "no attribution" shape, so a change to the descriptor's default keys must be remembered in both places to keep the unit builder and the parser in agreement.
Suggested change: Expose a single constructor or constant for the absent-descriptor from attribution.py and have `_build_unit` call it on the no-first-message path.

## 5. Null-tokens dict hand-built where the harvester already owns the shape

Severity: info
Location: fbk/harvest.py:377
Opportunity: When tokens are unavailable, `_build_unit` hand-builds the four-key all-None tokens dict (lines 377-383), duplicating the canonical token key set that token_harvester already enumerates in `transcript_token_totals` and its totals seed.
Why it matters: The four token field names now live in three spots; adding or renaming a token field means editing the harvester and this fallback in lockstep or the record schema diverges.
Suggested change: Have token_harvester expose the token-key set (or a `null_tokens()` builder) and construct the unavailable-tokens fallback from it.
