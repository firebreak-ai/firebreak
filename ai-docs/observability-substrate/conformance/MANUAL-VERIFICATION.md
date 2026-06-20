# Conformance Manual Verification Procedure

**Purpose.** This procedure proves that the observability substrate spine works
end to end: a workflow runs, a record appears at close with no command typed,
the reader renders a fully attributed table, and the record survives a project
move. Following it top to bottom and observing every expected result means the
conformance acceptance criterion is met.

This procedure is run by a human operator against the live harness. It is not
an automated test and cannot be run by pytest — the workflow spawns real Claude
Code subagents, which require the live harness environment.

---

## Prerequisites

Before starting, confirm all four of the following:

1. **Instrumented project.** The project you are working in has capture enabled.
   Run:
   ```
   python fbk.py capture-level
   ```
   The output must say `standard` or `full`. Any other value (including `off`)
   means the harvest will not write a record — resolve that before continuing.

2. **Substrate modules installed.** The five substrate modules must be present
   under `assets/fbk-scripts/fbk/`: `shapes.py`, `attribution.py`, `harvest.py`,
   `finalize.py`, and `run_retro.py`. The `run-retro` command must appear in the
   command map (`fbk.py` will list available commands if you run it with no
   arguments).

3. **Conformance workflow present.** The file
   `ai-docs/observability-substrate/conformance/workflow.mjs` must exist. This is
   the runnable workflow produced by task-24. If it is absent, do not proceed —
   this procedure verifies that workflow; without it there is nothing to run.

4. **Hook router wired.** The `finalize_runs` trigger must be registered in the
   hook router for both `PostToolUse` (Workflow tool) and `SessionStart` events.
   If you are unsure, check `assets/fbk-scripts/fbk/hook_router.py`.

---

## Step 1 — Run the conformance workflow and confirm the run directory

**Mapped to UV-1.**

Open a Claude Code session in your project directory and run the conformance
workflow:

```
/workflow ai-docs/observability-substrate/conformance/workflow.mjs
```

Wait for the workflow to finish. It launches three agents: one that implements a
small change, one that reviews it, and one adversarial code reviewer. All three
must complete before the workflow closes.

**What to look for.** After the workflow finishes, Claude Code will have written
a run directory under the harness's projects root (typically
`~/.claude/projects/<project-hash>/<session-id>/subagents/workflows/<run-id>/`).
Find the run id — it appears in the workflow output, usually on a line like:

```
Transcript dir: ~/.claude/projects/<project-hash>/<session-id>/subagents/workflows/<run-id>
```

Note the `<run-id>` value. You will use it in every step that follows.

Inside that run directory, confirm both of these files exist:
- `journal.jsonl` — the authoritative agent roster (one line per start/result event per agent)
- Three transcript files, one per agent (file names contain the agent id)

**Pass condition for this step.** The run directory exists, `journal.jsonl` is
present, and three transcript files are present — one for each launched agent.

---

## Step 2 — Confirm the record appeared at close with no command typed

**Mapped to UV-2.**

Without typing any command, look under `.fbk-capture/runs/` in your project
directory:

```
ls .fbk-capture/runs/
```

You should see a file named `<run-id>.json` where `<run-id>` matches the id you
noted in step 1. This file is written automatically by the `PostToolUse(Workflow)`
hook the moment the workflow returns — the operator does not trigger it.

**What to look for.** The file `<run-id>.json` is present. Its presence confirms
that the finalization trigger fired on the `PostToolUse(Workflow)` event and
`harvest` ran to completion.

If the file is absent immediately after the workflow closed, wait a few seconds
and look again — hook execution is asynchronous. If it is still absent, the
finalization trigger did not fire; check that the hook router is wired correctly
(see prerequisite 4).

**Pass condition for this step.** `.fbk-capture/runs/<run-id>.json` exists and
the operator did not type any command to produce it.

---

## Step 3 — Read the record and confirm full attribution

**Mapped to UV-3.**

Run the reader from your project directory, passing the run id you noted in
step 1:

```
python fbk.py run-retro <run-id>
```

The output is a per-unit block for each agent in the run, sorted by agent id.
You will see a header line `run: <run-id>`, then `units: 3`, then three blocks
separated by `---`.

**What to look for in the output.** Check each of the following across the three
blocks:

| Field | What you must see |
|---|---|
| `shape` | All three must be non-null (no em dash). Expected values: `implement` for the implementer unit, `review` for each of the two review units. |
| `cardinality` | One block must show `single` (the implementer). Two blocks must show `fan-out` (the two review agents). |
| `stance` | At least one block must show `adversarial` (the code-review-detector unit). The other two show `collaborative`. |
| `persona` | All three must be non-null. Expected values: `fbk-implementer`, `test-reviewer`, `code-review-detector` — one each. |

An em dash (`—`) in `shape`, `cardinality`, `stance`, or `persona` means the
attribution descriptor was missing or could not be parsed for that unit —
investigate `parse_attribution` and the workflow's prompt construction before
concluding this step passes.

A line containing `no harvest record` means the record file was not found;
re-check step 2.

A line containing `partial record` means the record was not finalized cleanly;
check whether the workflow completed normally before the hook fired.

**Pass condition for this step.** The reader prints three units. Every unit has a
non-null shape, cardinality, stance, and persona. The cardinality split is exactly
one `single` and two `fan-out`. At least one unit shows `adversarial` stance.

---

## Step 4 — Move the project directory and confirm the record is portable

**Mapped to UV-5.**

Move the entire project directory to a new location. For example:

```
mv /path/to/my-project /tmp/moved-project
```

Then open a new terminal, change into the moved directory, and run the reader
again with the same run id:

```
cd /tmp/moved-project
python fbk.py run-retro <run-id>
```

**What to look for.** The output is identical to what you saw in step 3. No
lines contain `no harvest record`, `malformed record`, or `partial record`. The
record is self-contained: it stores no absolute paths from the original location,
so it reads correctly regardless of where the project lives.

**Pass condition for this step.** The output matches step 3's output exactly.
The reader finds the record at `.fbk-capture/runs/<run-id>.json` under the moved
directory and renders it without error or reconstruction.

---

## Expected overall outcome

When all four steps pass as described, the conformance acceptance criterion is
met: the substrate spine works end to end. Specifically:

- A workflow run produces a `journal.jsonl` and per-agent transcripts in the run
  directory (step 1).
- The record appears under `.fbk-capture/runs/` on a normal workflow close,
  triggered automatically, with no operator command (step 2).
- The reader renders three fully attributed units — non-null shape, the correct
  cardinality mix, an adversarial stance present, and a populated persona for
  each unit (step 3).
- The record is portable: it reads correctly after the project directory is moved
  (step 4).

If any step does not pass, the spine is not fully functional. Note which step
failed and the exact output observed; that is the diagnostic starting point.

---

## Note on UV-4 (deterministic repeat)

UV-4 (byte-identical output on a second read of the same record) is covered by
the automated unit tests for the reader (task-14) and does not require a manual
step here. If you want to spot-check it, run `fbk.py run-retro <run-id>` twice
and diff the outputs — they should be identical.
