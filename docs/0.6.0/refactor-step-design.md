# Refactor step: a required refactor in implement, and a standalone refactor skill

Decided with the operator on 2026-11-05, after comparing Firebreak with EXACT Coding (firebreak wiki `exact-coding-firebreak-application`, candidate 5). Not built yet.

## Why

Firebreak has no refactor step. The word "refactor" appears nowhere in the implementation, breakdown, implement-skill or handoff guides. Implement's close review inspects duplication, coupling and complexity, but nothing in the unit is tasked with improving them.

The Agentic Coding Lab's strongest code-quality finding is that a required refactor at a set rhythm carries quality: it roughly halved peak complexity and cut code smells to about a tenth of unguided coding. It sets a minimum level rather than multiplying quality. A bare "use TDD" produced the heaviest code in their matrix, so a refactor stated in prose but not enforced is not enough. Pocock's skills, which moved refactoring out of the build loop into review, had the longest functions in the field. Only 14 of 60 refactoring claims held up when checked by hand, so claims need checking.

## The shape

One method, two callers. The method lives in one place; implement and the standalone skill each point to it, as EXACT's `red`, `green` and `refactor` skills point to `predictive-tdd`.

### The method

Adapted from EXACT Coding's Predictive TDD v1.2 refactor phase (MIT-licensed, `marcoemrich/agentic_coding_lab`, export 2026-10-29), which the lab evaluated. The adapted asset credits it in its frontmatter with a source link.

1. **Beck's four rules of simple design, in order:** the code passes the tests, reveals its intention, has no duplication (including duplicated knowledge), and has the fewest elements. Linters are evidence, not a replacement for this review.
2. **Responsibility review:** state each changed unit's job as one sentence in the spec's terms; name the policies it owns; ask "if one policy changed while another stayed fixed, would this unit change for both reasons?" A well-named boundary around one independently changing policy outranks "fewest elements".
3. **Boundary trial:** when the review finds a believable boundary, try the strongest one, keep it when the names and dependencies make the policy easier to find and change with the tests still green, and undo it otherwise. Analysis alone is not the attempt.

The refactor's return lists every change kept with its reason, every trial undone with why the boundary did not help, and "no improvement" with the review behind it when nothing changed, so a skipped review cannot pass for an empty one.

EXACT's measured `end-refactor` pass (smell, cognitive-complexity, McCabe and code-mass tools, one change at a time) is left out for now: it needs per-language tools Firebreak does not have, and EXACT calls it optional and costly. Revisit if larger targets show cross-file duplication the checklist misses.

### In implement

- **After each wave.** Breakdown plans refactor tasks after each wave of implementation tasks. EXACT refactors after every test; once per wave is coarser and untested, so the evaluation below checks it.
- **One subagent per wave, not per task.** Duplication across tasks built side by side, and misplaced boundaries, only show when the wave's code is seen together; per-task refactors would also collide on shared files. The refactor subagent gets the wave's changes as a diff, the spec's rules and the locked tests, not the build history; the lab found isolation from history costs nothing on current models. When a wave is too large for one context, breakdown splits its refactor by file group (directory or module), never by implementation task.
- **Required, and checked by the plan check.** Breakdown close refuses a plan where an implementation task's production files are not owned by a later refactor task that depends on it. The breakdown author chooses the file groups; the runtime checks coverage. `breakdown.md` states the requirement in the same words the check uses.
- **Safe by the locked tests.** Refactor tasks run in writing code, where no worker can change a test. Their checks are the whole-unit checks, which must pass.
- **Claims checked at close.** Implement's close review receives each refactor task's return and checks it against the delivered code. A claimed change missing from the code, or a believable boundary never tried, is a finding. No extra subagent per wave: the lab found a separate review stage costs more than the refactor it replaces saves.

### Standalone

`fbk-refactor` (working name) refactors one target the operator chooses, in any git project, outside the workflow. Its result is a branch, a production-only commit with tests unchanged, and a report listing each change and trial.

Without locked tests, its safety net is the project's own suite, which can be weak (the cleanup trial's original suite caught 11 of 35 wrong versions). So it first checks the target's tests with a scoring kit, as `fbk-test-cleanup` does. When the suite misses a wrong version, it stops, names the rules the missed versions break, and suggests `fbk-test-cleanup` for the target; the operator's only choice is to clean up first or proceed anyway.

The rule-settling step, the kit-writer brief and `run-kit.py` move from `skills/fbk-test-cleanup/` to a shared location under `fbk-docs/`, and both skills point there. A cleanup report at `.fbk/test-cleanup/<target>.md` supplies the starting rules; when none exists, the refactor skill settles the rules and writes that report, so a later cleanup starts from them.

## Evaluation before merging

Two risks EXACT's evidence does not cover: the coarser once-per-wave rhythm, and extra steps causing early stops (in the lab, two harmless-looking prose additions made agents stop at about half their cycles on the larger `claim-office` exercise, correctness 0.96 to about 0.3).

Build on a branch, then run the Python `claim-office` exercise through Firebreak with and without the refactor step, from intent, spec and breakdown written once and frozen so the arms differ only in the refactor tasks; three implement runs per arm. Measure correctness with the exercise's 15 hidden scenarios (an early stop shows as a drop), function length and McCabe complexity with a Python tool run through `uvx`, and time and tokens. The lab's published numbers for about ten workflows give reference points. The existing harness (`tmp/instruction-tuning/harness/`) runs it headlessly; the operator authorizes the eval projects' phase crossings in advance so it can run overnight. This also starts two evaluation-kit candidates: `claim-office` as the larger unit, and the early-stop check.

## Open for the build

- **What counts as a wave (decided).** The runtime has no waves: task start checks only that the task's dependencies are finished, that no running task writes what it owns or reads, and the implement stage; the lead launches each ready set together, and that set is the wave. So the plan check enforces coverage only: every production file an implementation task owns is also owned by a refactor task that depends on it. A file changed in two waves needs a refactor in both. `breakdown.md` asks for one refactor task per wave; a single refactor at the end would pass the check, and the check is tightened only if the `claim-office` runs show refactors bunched at the end.
- **How a refactor task is marked (decided).** An implementation task with a marker such as `"refactor": true`, not a new `stage`. About eight places in the runtime test for `stage == "implementation"` (test-before-code ordering, writing-code only, no test ownership, required completion, coverage, the close review's split), and a refactor task needs every one of them; only the new plan check and the close review read the marker. The coverage rule that every requirement is linked by an implementation task ignores refactor tasks, and a refactor task need not link any requirement (see the context cap below).
- **New files from a boundary trial (decided).** A refactor task owns the production folders of its file group; a task may already own a folder, and new files inside it need no `creates` entry (from reading `check_listed_paths`; confirm with a test in the build). Where tests share a folder with production code, as in Go, an implementation task cannot own the folder, so the refactor task lists files and its trial works within them, listing in its return any boundary it could not extract. A runtime change letting a wildcard exclude test files waits until a real unit needs it; the planned Go trial will show whether one does.
- **Measured pass.** Excluded for now, above.
- **Context cap (decided 2026-11-06, replacing the provisional call).** A refactor task links no requirement: its worker reads the unit's accepted spec and design whole, which its packet lists under `rules_sources`, and its acceptance references are the whole `prd.md` and `spec.md`. The first kanban run showed the provisional call failing: one requirement's linked chain was 13,040 characters and the web module's tasks served five requirements (about 26,000), so no split by folder fit the 16,000-character cap; the author worked around it with path-only references, and breakdown spent all three review rounds on whether every requirement was linked.

## Later

Review implement's close-review criteria against EXACT's findings once this step is built.
