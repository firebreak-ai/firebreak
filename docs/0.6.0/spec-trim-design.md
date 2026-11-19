# Spec trim: a fresh session cuts the spec before its review

Branch `fix/review-inflation`. Decided with the operator on 2026-11-04. Evidence: `tmp/instruction-tuning/experiments-2026-11-02.md`, runs 38–49; the firebreak wiki synthesis `right-sizing-artifacts-and-tests-2026-11`.

## Why

Every spec example becomes at least one test that someone must keep working. Authors write examples to cover each rule from several sides. Reviewers only ever ask for more. Nothing in the workflow removes an example that catches no mistake the others miss. On the word-count evaluation unit, a fresh session told to cut and never add halved the tests without losing bug-catching power:

- Python: cases fell from about 20 to 10, with 11–12 of 13 seeded bugs caught and all 20 correct implementations passing.
- Go: cases fell from 36–40 to 19–20, with 11–12 bugs caught.

Excess tests compound over a project's life and never announce themselves. A missing test surfaces later with evidence and gets fixed once. So the trim cuts, and nothing during the unit puts a cut back.

## The shape

1. **When.** Spec close runs the trim automatically, before the review. It runs once per spec draft (the phase's generation) and again after a reopen. A close retried on the same draft reuses the earlier trim result.
2. **Who.** A fresh restricted session that may edit only `spec.md`. It never sees the authoring conversation.
3. **What it reads.**
   - Every active governing decision from every phase, with its quoted source. This is a new selection beside `decisions.for_readers`, which gives only the current phase's decisions plus live amendments. The later note on giving reviewers every phase's quotes reuses it.
   - The accepted intent, the accepted design, the spec draft, and the source and tests the spec refers to.
4. **What it does.** It follows the instructions below. It edits the spec and returns its cut list, one entry per item with the reason, as its structured reply.
5. **What the runtime does afterwards.**
   - **Adds the list section.** The runtime ends the spec with a `## Removed on purpose` section: its fixed opening paragraph, then the session's list. If nothing was cut, there is no section.
   - **Re-runs checks.** It re-runs the spec's structure checks and the invisible-character scan on the trimmed spec.
   - **Takes a new fingerprint.** It recomputes the spec's revision fingerprint before the review round is appended.
6. **Failure.**
   - **A trim that leaves no result** (crash, overload, timeout) is retried once automatically. If the retry also fails, the close goes on to review with the untrimmed spec and reports that the trim did not run.
   - **A trim whose result fails a check** returns the close to the author with the check's message. It is not rerun for that draft. The author fixes the spec, for example by writing an escape back, and closes again.
   - **Neither case** spends a review round or asks the human anything.
   - **An unchanged spec** is a valid result.
7. **What the human sees.** The close output and status each carry one line: the spec's size before and after, and the number of items cut, or that the trim did not run and why. The full list lives only in the spec section. The human approves nothing. To disagree with a cut, they reopen the spec or raise it at code review.

The opening paragraph the runtime writes:

> These were removed on purpose. A removed item is not a gap: do not report it or add it back during this unit. Only a later code review may restore one.

Every later reader of the whole spec sees this section, including the spec reviewer, breakdown, the test checkpoint and implement review. Task context carries only linked requirement sections, so the section does not count toward the task limits.

## The instructions

These are the instructions evaluated in runs 46–49 (`tmp/instruction-tuning/harness/collapse-prompt-final.md`). In the build, the runtime supplies the file list, takes the cut list from the session's structured reply, and writes the section's opening itself.

> Each example in the spec becomes at least one test that someone must keep working, so an example that catches no mistake the others miss is cost without benefit. Make the spec state the same agreed behavior with fewer words and fewer examples:
> - Keep the fewest examples that tell each rule apart from the ways an implementer is likely to misread or skip it. One example may show several rules. Merge examples that would catch the same wrong implementation, and remove one that catches nothing the rest miss.
> - Merge requirements a user would see as one behavior, keeping every link to the design choices they come from.
> - Remove text that repeats another document or the examples, and any property, check or detail that neither the human nor an accepted document asks for.
> - Remove an example written at an entry point the design does not name, unless it shows an effect the named entry points cannot observe.
>
> Never remove anything a human decision names, from any phase, or the last example of a rule. Keep the link form the spec already uses, any line whose exact form the workflow guides require (such as a review-only marker), and escape sequences as written. Add nothing.

## Invisible-character scan, widened

Runs 39 and 49 turned written escapes such as ` ` into the raw characters. The spec author did the same while drafting in run 49. The editing tools do this, so better wording won't stop it.

The raw character looks like an ordinary space, or like nothing at all. The example then appears to show something else, and a test copied from it can stop checking the rule.

`artifact_hygiene.py` will now also flag two Unicode categories:
- every space character except the ordinary space;
- every format character, which covers zero-width characters, the byte-order mark and direction marks.

It flags by category, not by a hand-kept list. The scan applies to all unit files and serves as the escape check after the trim. There is no separate check.

## What stays

- The spec reviewer and its round budget. In run 46 the reviewer caught a merge that had lost a check, which shows the review still catches over-cutting.
- Structure checks, the review-only marker form and the traceability links.
- Breakdown, the test checkpoint and implement, unchanged. They read the section like any other part of the spec.

## Not in this note

Each has its own later note:
- giving reviewers every phase's quotes;
- a test-checkpoint check that suggests removing change detectors and duplicate tests;
- trimming at the end of intent and design, each after its own harness runs.

## Watch items

- Larger units are untested. The word-count unit has about a dozen rules.
- Spec reviewers may still ask to add back a listed cut. Run 45 had one such request, before the opening paragraph took its final form.
- Go tests pinned to the `run` function's arguments in some runs. The trim does not address this.

## Build order

1. Widen the invisible-character scan, with tests for each new category and for the ordinary space staying allowed.
2. A decision selection across every phase, with tests.
3. The trim session inside spec close:
   - its brief file, fingerprinted like the phase briefs, plus its session kind in the constraint registry;
   - the once-per-draft record;
   - the single retry on no result;
   - the section the runtime writes;
   - the re-run checks and the revision fingerprint taken again.

   Tests cover each failure path, and confirm that no review round is spent.
4. The close output and status line.
5. Guides, a glossary entry for the trim and the "Removed on purpose" section, and a decision-log entry.
