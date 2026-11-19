# Maintainability benchmark

This kit measures how costly code is to change after different coding-agent workflows have written it.

## What it measures and why

An agent can pass every test today and still leave code that is slow and risky to change tomorrow. The cost that
matters is a later maintainer's time and attention: how much must be read, how far an edit spreads, how much is
rewritten on the way, and how often the change breaks something.

The benchmark holds correctness as a condition and measures cost. Every build and every later change is checked
against hidden tests, so a cheap change that breaks the program does not count as cheap.

## The design in brief

1. **A common starting codebase.** A working command-line program (the reference solution of one SlopCodeBench
   problem partway through its checkpoints) with a frozen test suite. Every approach starts from the same commit.
2. **Four approaches build three feature steps.** Each approach extends the program through the next three
   checkpoints of the problem, with the same request per checkpoint and a fresh session each time:
   - `plain`: one prompt per checkpoint, no workflow.
   - `tdd`: the lab's plain test-first workflow.
   - `exact`: the EXACT workflow.
   - Firebreak: five phases per checkpoint (intent, design, spec, breakdown, implement), driven turn by turn by an
     operator, a person or agent who answers the workflow's questions.
3. **Neutral maintainers make three engineering changes.** A plain session with no workflow gets a build's final
   code and one change request: stay fast on very large inputs, report every error in one run, or accept unknown
   values in input files.
   The same maintainer on every build, so differences come from the code it was handed.
4. **A code-state table.** Size, complexity, duplication, lint findings and test strength of each build, side by
   side with the common start.

Calibration: three hand-made versions of the same program (`top` is cleaned up, `middle` is the reference, `bottom`
is deliberately tangled) get the same three changes. They show whether a measure tells easy code from hard code,
and repeated runs show how much a measure moves by chance.

## Prerequisites and what to fetch

- Linux, `bash`, `git`, `jq`, [`uv`](https://docs.astral.sh/uv/), and Claude Code (`claude`) signed in. Real runs
  cost money; the stand-in commands below cost nothing.
- The SlopCodeBench problem set: https://github.com/SprocketLab/scb-problems
- The Agentic Coding Lab (EXACT): https://github.com/marcoemrich/agentic_coding_lab

Copy `settings.example.env` to `local/settings.env` and set `SCB_PROBLEMS` and `EXACT_LAB` to the two checkouts.
`FBK_ASSETS` names the Firebreak version a Firebreak build installs: a commit of this repository, or a folder.
Everything the kit makes goes under `local/`, which git ignores.

You also make by hand, under `local/`:

- `wrong-copies/<problem>-cp<N>/*.patch`: small patches that each break the starting program in one way, used to
  check that the frozen suite catches bugs.
- `changes-<problem>/<change>/`: for each change request in `prompts/`, its hidden tests (`tests/`), a reference
  solution as `reference.patch`, and, if the change alters old behavior, an updated regression suite
  (`regression-tests/` with a `run-regression.sh`).
- `anchors/<problem>/<name>/`: every codebase a maintainer will change, as a git repository. This holds the
  calibration versions and each build's final code without the workflow's own files (`.claude`, `.fbk`). No script
  makes these yet.

## The commands, in order

Paths are relative to this folder. Each script's header comment has the details.

Setup:

| Command | What it does |
|---|---|
| `setup/prepare-start.sh circuit_eval 5` | Makes the starting codebase in `local/starts/circuit_eval-cp5`. |
| `setup/write-start-suite.sh circuit_eval 5 local/runs-suite/w1` | One plain session writes the test suite for it. |
| `setup/score-suite.sh local/runs-suite/w1/project local/wrong-copies/circuit_eval-cp5` | Counts how many broken copies the suite catches. |

Then copy the suite to `local/start-tests/circuit_eval-cp5/`, remove the first start and run `prepare-start.sh`
again, so the start includes its tests.

Build:

| Command | What it does |
|---|---|
| `build/batch-build.sh "plain tdd exact" 3` | Three builds of each approach under one lock, then scores each. |
| `FBK_ASSETS=<commit> build/batch-build.sh "fbktl fbktl-own" 3` | Three builds of each setting of Firebreak's test-list trial (the `fbk-testplan` skill): a separate author writes and locks the test bodies (`fbktl`), or the implementer writes each body at its step (`fbktl-own`). A third, `fbktl-one`, has the one session do all the work with no subagents. A fourth, `fbktl-one-tidy`, is the same except that one fresh subagent does the closing tidy-up. One session per checkpoint and no operator: `prompts/fbk-testplan/build.txt` approves the printed plan in advance. `FBK_ASSETS` names the Firebreak commit installed and has no default for these. |
| `build/fbk-drive.sh start\|turn\|close\|finish <run> ...` | One Firebreak build, a turn at a time. Several builds can go at once under one lock: a later `start` joins it and needs `REQUESTS`, a folder of requests rendered beforehand. |
| `build/fbk-drive.sh abort\|resume <run>` | `abort` stops a build and brings home what exists. `resume` puts an aborted build back in its project folder and locks again, so turns can continue. |
| `prompts/fbk-design-council/` | Intent, design and spec prompts for a Firebreak build with the design phase on and a council the agent chooses; the other turns use `prompts/fbk/`. |
| `build/score-build.sh local/runs-ce/<run>` | Scores one build: hidden tests, per-checkpoint numbers, code state, audit. |
| `build/score-tests.sh local/runs-ce/<run>` | What a finished build's own tests are worth at its last checkpoint: `measure/testq.py` plants bugs in the code and records which tests catch them. Refuses while the lock is on. |
| `build/extend-builds.sh <run>...` | Continues copies of finished builds in `local/ext-builds`, each through its own workflow, with the three change requests as checkpoints 9 to 11. |
| `build/score-ext.sh local/ext-builds/<run>` | Scores a continued build: at each added checkpoint, the hidden cases of every change made so far and the regression suite as those changes amend it. Run one at a time. |
| `build/refactor-run.sh <codebase-repo> <target> <out-dir>` | One unattended run of the `fbk-refactor` skill on a copy of a finished codebase. `SKILL=fbk-test-cleanup` runs the test-cleanup skill instead. No hidden tests are run. |
| `FBK_ASSETS=<commit> build/interview-batch.sh` | Measures the plan step's interview: single checkpoints built from a short request, with no operator (`floor`) and with a simulated operator (`interview`, answered by `build/operator-server.py` from the full specification). Run once so far, on one build. |

Change:

| Command | What it does |
|---|---|
| `change/run.sh <change> <base-repo> <out-dir> [model]` | One maintainer session on one codebase. |
| `change/score.sh <change> <out-dir>` | Hidden tests for that change, then its scorecard. Run one at a time. |
| `change/batch-anchors.sh <model> <tag> <repeats>` | Every change on every calibration version, under one lock. |
| `change/noise.sh <change> <base> <from> <to>` | Repeats of one change on one base, then scores them. |
| `change/batch-builds.sh <model> <tag> <repeats> <codebase>...` | Every change on chosen codebases of `local/anchors/<problem>/`, under one lock, then scores them and prints the table. |

Read the results:

| Command | What it does |
|---|---|
| `measure/table.py [--ref <base>] <out-dir>...` | Maintainer runs side by side, with medians per change and base. |
| `measure/state.py [--ref <name>] [--mutants N] <repo>...` | The code-state table for any git repositories. |
| `measure/reference-footprint.py <change-dir> <base-repo>` | The size of a change's reference solution, for comparison. |
| `measure/testq.py build <repo> ...` | The measurement behind `score-tests.sh`, for any repository: which planted bugs each test catches. `testq.py swap` runs one repository's tests against another's code. |

Trial runs without cost: put a stand-in `claude` first on `PATH`. `build/fake-claude-build` (for `batch-build.sh`),
`build/fake-claude-fbk` (for `fbk-drive.sh`) and `change/fake-claude` (for `run.sh`) each make a small real edit and
print a session record in Claude Code's format.

## Running Firebreak builds

The other approaches build from one command. A Firebreak build needs an operator, because the workflow stops to ask
questions. Results compare across builds only when every build is run the way this section describes, so follow it
as written and record any departure with the results.

There are two roles. The **lead** (a person, or the agent session a person is talking to) prepares, starts, scores
and records. An **operator** (one agent per build) sends the turns and answers the workflow's questions.

**What stays fixed across builds being compared:**

- The Firebreak version. `FBK_ASSETS` names a commit of this repository; record it with the results.
- The model and effort (set in `build/fbk-drive.sh`), the starting codebase and the checkpoints.
- The prompt files, used unchanged: `prompts/fbk/` for the default variant (the agent decides whether a unit has a
  design phase; one reviewer), or `prompts/fbk-design-council/` for intent, design and spec when testing the design
  phase with a council.
- The operator's brief, `prompts/fbk/operator-brief.md`, sent unchanged apart from its five values.
- Three builds per variant. One build cannot rank two approaches.

**The lead's steps:**

1. **Render the requests** while the answers are unlocked, into one scratch folder per build outside the kit:
   `python3 setup/render-prompt.py <cp> circuit_eval tests > <scratch>/request-cp<cp>.md` for each checkpoint. The
   operator answers questions from these files.
2. **Start the builds.** `build/fbk-drive.sh start <run>` for the first, which takes the lock. For each further
   build at the same time, `REQUESTS=<its scratch folder> build/fbk-drive.sh start <run>`. Run every kit command
   from this folder, and keep the shell's working folder out of `local/`, which is locked during a build.
3. **Give each build its own operator** with `prompts/fbk/operator-brief.md`, filling in the kit folder, run name,
   scratch folder, checkpoints and variant. The operator closes each checkpoint and finishes or aborts the build.
4. **Wait for every build to end.** `change/lock.sh status` prints `unlocked` and `local/.fbk-builds` is gone.
5. **Score, one build at a time:** `build/score-build.sh local/runs-ce/<run> > local/runs-ce/<run>.score.out`.
   A build that was aborted is scored up to its last closed checkpoint.
6. **Keep the operator's record:** copy its answer files to `local/runs-ce/<run>-operator-answers/`, and keep its
   report with the results.
7. **Check the audit block** of each score output. A flagged path inside the project's own `.fbk` documents is the
   workflow linking its own files; anything else needs a look before the build counts.

**The operator's rules,** which the brief states in full:

- A question the request settles is answered from the request. Every other question gets the workflow's own
  recommendation. The operator adds no requirement, hint or correction.
- At most five answers in one phase. A phase still open after five ends the build with `abort`.
- The operator waits on each turn in the foreground with `build/fbk-wait.sh`, and never reads the project's code,
  `local/`, or another build.

**When a build is aborted.** The result is "did not finish within the answer limit", and that is a finding about the
workflow. `build/fbk-drive.sh resume <run>` continues an aborted build, but a resumed build has had more operator
help than the others: resume only on a person's decision, state the new answer limit, and record both with the
results.

**What to record for each build:** the Firebreak commit, the variant, whether each unit had design on, reviewers or
council members and review rounds per phase, operator answers per checkpoint and what each was, cost and session
minutes per checkpoint (in the score output), and whether it finished.

**Known hazards:**

- If the `claude` command updates itself during a build, reviewer launches can fail with an unknown-option error and
  the round still counts. Turn off automatic updates for the length of a build where you can, and note it when seen.
- The benchmark's request file is ignored by git, so the workflow's reviewers cannot see it until the session saves a
  copy among the unit's decisions. This costs review rounds in the version tested so far.
- Parallel builds share one machine and one account. They did not disturb each other in three builds at once.

## When Firebreak changes

The benchmark exists to test changes to Firebreak, so it has to keep working as Firebreak changes, and a result has
to say which version produced it.

**Testing a change to Firebreak:**

1. Commit the change. A build installs the `assets/` folder of the commit `FBK_ASSETS` names, so uncommitted work is
   not tested.
2. Run `setup/check-fbk-interface.sh <commit>`. It reads files only and says whether the prompts and the driver still
   match that version.
3. Run one checkpoint for real (`CPS="6 6"`, about a tenth of a full set's cost) and read the operator's report.
   This is the only check of what a session actually does: phases closing, questions asked, reviewers launching.
4. Run three builds of the new version, as "Running Firebreak builds" describes.
5. Compare with three builds of the version it was changed from, run with the same model, the same prompts variant
   and the same operator brief. Change one thing at a time; a build that differs in two things explains neither.
6. Record the commit, the variant and the comparison with the results.

**When earlier builds stop being a fair baseline.** Builds of the other approaches and of older Firebreak versions
stay valid as long as the model, the starting codebase, the checkpoints and the measures are the same. Rebuild the
baseline when any of those changes, and after a large update of the `claude` command, which changes how every
session behaves.

**What in this kit depends on Firebreak, and what to do when that part of Firebreak changes:**

| Firebreak changes this | This part of the kit depends on it | What to do |
|---|---|---|
| A phase skill is renamed, added or removed | `prompts/fbk*/[1-5]-*.txt` name the skills; `build/fbk-drive.sh` accepts five phase names in turn names and reports them accepted or open; the operator brief's turn table; `build/fake-claude-fbk` | Update all four together. `check-fbk-interface.sh` reports a missing skill. |
| How a closed phase is recorded | `build/fbk-drive.sh` asks the workflow's own `status` command which phase a unit is in and how many review rounds each phase had, and reads `.fbk/<unit>/state.json` only when that command gives nothing; `build/fake-claude-fbk` writes that state file | Update the driver's `phases_report` if the `status` output changes its `phase`, `review_rounds` or `review_plans` fields. The sign is a turn whose reply says a phase closed while the driver prints `open`, or a phases line that says it was read from the state file. |
| The words for turning design on, or for choosing one reviewer or a council | The sentences in `prompts/fbk/2-design.txt`, `3-spec.txt` and `prompts/fbk-design-council/` | Add a new prompts folder for the new wording. Leave the old folders as they are, since old results name them. |
| The review selection guide is renamed or moved | The council prompts refer to it by name | Reword the prompts in a new folder. `check-fbk-interface.sh` reports it missing. |
| New kinds of question to the operator (a new approval, a new way to close) | "Answering an open phase" in `prompts/fbk/operator-brief.md` | Add the case to the brief, keeping the rule: the request's words or the workflow's own recommendation. |
| How many review rounds a phase gets, or anything that changes how often the workflow stops | The limit of five answers per phase in the operator brief | Keep the limit unless it stops most builds; if it changes, say so with the results, since builds under different limits had different amounts of help. |
| The installer's options or where `assets/` sits | `install_arm` and `assets` in `build/fbk-drive.sh` | Update the driver. |
| The name or place of the workflow's own files in a project | `build/quality.py` leaves `.claude` and `.fbk` out of the code measures; `build/audit-build.py` reports paths outside the project | Update the skip list, or workflow files will be counted as code. |
| What the workflow's sessions are told at the start | `prompts/fbk/author-system.md`, appended to every session, asks for the "For the operator" and "Friction" sections the operator reads | Keep those two sections; the operator's work depends on them. |

**Rules that keep results comparable over time:**

- A prompt file or the operator brief that has produced recorded results is not edited in place. A change of
  wording goes in a new file or folder, and the results name which one they used.
- `FBK_ASSETS` defaults to a fixed commit in `build/fbk-drive.sh`. Move the default only when a new version becomes
  the baseline, and say so in the commit.
- The measures in `measure/` and `build/quality.py` are part of every result. A changed measure means every build in
  a comparison is scored again with the same scripts; the run folders keep each checkpoint's code for that.
- Every recorded result names: the Firebreak commit, the prompts folder, the model, the date, and the limits the
  operator ran under.

## How the answers are kept from sessions

A session that can read the hidden tests, a reference solution or another run's result is no longer a fair
measurement. Four things keep them apart:

- **The lock.** `change/lock.sh lock` removes all permissions from every answer location: the problem set's specs,
  tests, solutions and git history, each change's hidden tests and reference, the wrong copies, and every finished
  run. `unlock` puts them back. The batch scripts lock before the first session and unlock on exit, also after an
  interrupt. Scoring refuses to run while the lock is on.
- **Hidden work folders.** A session works outside the kit, in a folder with a random name inside a folder that
  can be entered but not listed. A session cannot find another session's folder by browsing.
- **Clean instructions.** Sessions do not load the operator's own instruction files from folders above the work
  folder.
- **The audit.** After a run, every path a session named outside its work folder is listed, and paths that point at
  an answer location are flagged.

Cautions:

- Sessions run as the same user as the lock, so the lock stops browsing and searching, not a program that changes
  permissions itself. The audit is the check on that.
- An audit flag says a location was named, not that anything was read. Read the calls in the session record to tell.
- Requests are rendered before the lock goes on, because the specs cannot be read afterwards.
- `EXTRA_ANSWER_PATHS` in the settings adds other places on your machine that hold answers or old runs.

## The measures and how to read them

Everything is computed from git history and session records. Nothing is judged by a model.

**Per build** (`score-build.sh`, written to `score.txt` and `score.json` in the run folder):

- Hidden tests passed per checkpoint, by group: core, functionality, error, and regression (earlier checkpoints'
  cases). This is the correctness condition.
- Per checkpoint: cost, minutes, code and test lines changed, and SlopCodeBench's erosion and verbosity scores.
  The workflow's own files are not counted.
- Code state at each checkpoint, as a ratio to the start: files, lines, function count and length, cyclomatic and
  cognitive complexity (two counts of branching and nesting), duplicated lines, lint findings in four groups, and
  test size.
- Test strength at the first and last checkpoint: statement coverage, and the share of a sample of small code
  changes (mutants) that the build's own tests catch.

**Per maintainer run** (`score.sh`, written to `measure.json`; `table.py` lines runs up):

- Outcome: the change's hidden cases and the regression cases passed, and the project's own suite.
- Attention: how many looks (reads and searches) and how many files before the first code edit; tool calls; time.
- Where the change landed: files, lines, places and functions touched.
- Difficulty: the length and complexity of the functions that had to be modified, measured before the change.
- Rework: lines the session wrote, and how many of those it later rewrote or removed.
- Own tests: tests added, modified or deleted; old tests that now fail; hidden failures that a green own suite
  missed.

Cautions:

- Read cost measures only for runs that pass the hidden tests, and compare the same change across codebases.
- One run says little. Use repeats and read medians; the calibration runs show the spread to expect.
- Rework numbers are marked `?` when the session record is incomplete (for example an edit made by a background
  shell command). The counts then miss work. Medians include marked runs, so check the `unrel` column.
- The older edit counts (`edits_per_file`, repeated edits) grow with the number of files a change touches, not with
  wasted work. Prefer lines written and rewritten.
- The speed change has timed cases: score one run at a time on a quiet machine. An unchanged program runs most of
  them into their limits, which takes several minutes.
- Mutants are a sample (150 by default, fixed seed), so the catch share has sampling error. A timed-out mutant
  counts as caught. Coverage needs coverage.py 7.10 or newer in the project's environment and is blank otherwise.
- A nested function's cognitive complexity also counts inside its parent's.
- `reference-footprint.py` is meaningful only on a base that is the unmodified reference program.
- Builds use one model, named in the build scripts; the maintainer's model is an argument to `run.sh`.

## What is not in the repository, and why

- **The problem, its tests and solutions, and everything made from them**: the starting codebase, its test suite,
  the wrong copies, the calibration versions, and each change's hidden tests and reference solution. SlopCodeBench
  files carry a notice that they must never appear in training corpora. A public repository gets collected into
  such corpora, so this material stays in `local/`. The three change requests in `prompts/` are tracked; their
  hidden tests are not, so the changes cannot be scored from this repository alone.
- **The interview measurement's requests**: `interview-batch.sh` reads `local/interview/cp<N>/` (a short request and
  an interface sheet for each checkpoint) and `local/interview/operator-brief.md`. They restate the problem's
  specifications, so they stay in `local/` for the same reason.
- **Run output**: session records, built projects, scores and tables. They are large and contain problem text.
- **The EXACT lab and the Firebreak assets a build installs**: fetched or exported when needed.

Credits and licenses for the work this kit builds on are in [NOTICE.md](NOTICE.md).
