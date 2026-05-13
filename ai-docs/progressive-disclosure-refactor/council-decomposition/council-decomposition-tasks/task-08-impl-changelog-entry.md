---
id: task-08
type: implementation
wave: 3
covers: [AC-14]
files_to_modify:
  - CHANGELOG.md
  - README.md
test_tasks: [task-01]
completion_gate: "CHANGELOG.md contains the Changed entry per spec §6.1; README.md line 99 updated per spec §6.1 user-approved wording; both verifiable by grep"
---

## 1. Objective

Adds a Changed entry to `CHANGELOG.md` documenting the `/fbk-council` skill decomposition AND updates `README.md` line 99 to drop the literal "6 agents" phrasing in the slash-command table.

## 2. Context

The repository follows the keepachangelog.com format: changes group under `### Added`, `### Changed`, `### Deprecated`, `### Removed`, `### Fixed`, `### Security` headings within each release block. The active development release at the top of `CHANGELOG.md` is `## [0.4.0]`. Existing entries under `## [0.4.0]` show the project's voice: bold lead phrase summarizing the change, then 1–3 sentences explaining what moved, why, and pointing at affected paths or specs.

This entry is added under the existing `### Changed` heading inside `## [0.4.0]` (do not create a new release block — release version assignment is the user's decision when they cut the next tag). The exact entry text is specified by the spec at §6.1:

> "Decomposed `/fbk-council` skill body. Extracted compaction recovery, decision protocol, conflict resolution, Ralph loop integration, and advanced observability commands to conditional leaves under `assets/fbk-docs/fbk-council/`. Replaced Quick/Full tier prescription with judgment-based council sizing."

This task runs in Wave 3, after Waves 1 and 2 land. By the time this task executes:
- The three new leaves exist at `assets/fbk-docs/fbk-council/{consensus-failure,compaction-recovery,ralph-integration}.md` (Wave 2: task-04, task-05, task-06).
- The SKILL has been rewritten (Wave 2: task-07).
- The structural smoke test passes (Wave 1: task-01 + Wave 2 implementations).
- The path-pattern test array covers the new leaves and `test-council-skill-references.sh` is deleted (Wave 1: task-03).

The entry references work that has actually shipped, so the description is accurate at write time.

The README references `/fbk-council` at line 99 (`Assemble 6 agents (architect, builder, guardian, security, analyst, advocate) to discuss any problem`). The user has approved the replacement wording (per spec §6.1, AC-14 part b). This task performs both the CHANGELOG entry AND the README edit — the README change is no longer pending discussion.

## 3. Instructions

1. Read `CHANGELOG.md`. Locate the `### Changed` heading inside `## [0.4.0]` (currently the active release block at the top of the file).

2. Append a new bullet under that `### Changed` heading, following the existing voice (bold lead phrase, then 1–3 sentences). The entry MUST begin with the literal word `Decomposed` (capital D) so AC-14 grep verification passes. The entry text is:

   ```
   - **Decomposed the `/fbk-council` skill body for progressive disclosure.** Extracted compaction recovery, decision protocol, conflict resolution, and Ralph loop integration into conditional leaves under `assets/fbk-docs/fbk-council/` (`compaction-recovery.md`, `consensus-failure.md`, `ralph-integration.md`); each loads only when its trigger fires. Replaced the Quick/Full tier prescription with a single judgment-based sizing instruction — the orchestrator selects council members per task from the members table; `quick`/`/fbk-qcouncil` retains a soft default of Architect+Builder+Guardian with Phase 1 alignment skipped, overridable when task content names security/users/metrics. Trigger phrases, member agents, output schemas, and downstream callers are preserved. Spec at `ai-docs/progressive-disclosure-refactor/council-decomposition/council-decomposition-spec.md`.
   ```

3. Place the new bullet so it reads naturally with surrounding entries. Either position it adjacent to the existing entry that begins `**Council session-state operations consolidated into `fbk.py session-state`.**` (since both are council-related) or at the top of the `### Changed` list — either placement is acceptable; do not interleave or split the existing entries.

4. Do not modify any other entry in `CHANGELOG.md`. Do not create a new release block. Do not bump the release version.

5. Verify by `grep -F 'Decomposed the `/fbk-council` skill body for progressive disclosure' CHANGELOG.md` returns one match, and `grep -F 'Quick/Full tier prescription' CHANGELOG.md` returns one match.

6. Edit `README.md` at line 99. Replace the line:

   ```
   | `/fbk-council` | Assemble 6 agents (architect, builder, guardian, security, analyst, advocate) to discuss any problem |
   ```

   with:

   ```
   | `/fbk-council` | Assemble specialized agents (architect, builder, guardian, security, advocate, analyst) — selected per task — to discuss any problem |
   ```

7. Verify the README edit by `grep -F 'Assemble specialized agents' README.md` returns one match AND `grep -F 'Assemble 6 agents' README.md` returns zero matches. Do not modify any other line of README.md.

## 4. Files to create/modify

- **Modify**: `CHANGELOG.md`
- **Modify**: `README.md`

## 5. Test requirements

No automated tests cover CHANGELOG content. Verification is by direct grep (step 5 above) and manual inspection of the diff.

## 6. Acceptance criteria

- **AC-14 (a) — CHANGELOG**: `CHANGELOG.md` contains a Changed entry under the active release describing the council decomposition. Verifiable by `grep -F 'Decomposed' CHANGELOG.md` AND `grep -F '/fbk-council' CHANGELOG.md` — both return at least one match.
- **AC-14 (b) — README**: `README.md` contains the user-approved updated line. Verifiable by `grep -F 'Assemble specialized agents' README.md` returns one match AND `grep -F 'Assemble 6 agents' README.md` returns zero matches.
- A new bullet under `### Changed` inside `## [0.4.0]` of `CHANGELOG.md` describes the council decomposition using the entry text from instruction step 2.
- No other entries in `CHANGELOG.md` or `README.md` are modified.
- The entry mentions the three leaf paths, the judgment-based sizing change, and references the spec path.

## 7. Model

Haiku

## 8. Wave

Wave 3
