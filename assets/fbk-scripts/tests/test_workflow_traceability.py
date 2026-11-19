"""Traceability sections and coverage at design and spec close (build step 7, plan decision 8).

Each document carries one named section of items: ``prd.md`` has **Commitments**, each design
file **Design choices**, and ``spec.md`` **Requirements**. Items are headings inside that
section; they link upstream with ordinary Markdown links to heading anchors. Design close
checks that every design choice links to a commitment and every commitment is covered by a
design choice. Spec close checks that every requirement links to a design choice (or to a
commitment, in a unit without design) and every upstream item is covered by a requirement.

Lead rulings these tests rely on (recorded in the step 7 brief):

1. **Sections and items.** A section is a heading whose text is exactly the section name, at any
   level. Its items are the headings exactly one level below it, up to the next heading at the
   section's level or higher. Deeper headings belong to the item above. An item's text runs from
   its heading to the next item or the end of the section. A section name used twice in one
   document is refused.
2. **Anchors.** One shared anchor function, keeping ``handoff``'s punctuation handling
   (lowercase, drop characters other than word characters, spaces and hyphens, spaces become
   hyphens). Two headings producing the same anchor are refused when a link targets that
   anchor, naming it. Untargeted duplicates are not refused.
3. **Link form.** Standard Markdown links, the path relative to the linking document's folder,
   with a ``#anchor``. A link resolving to an upstream document of this unit (or of its parent)
   must land on an item in the correct upstream section, or it is refused naming the item, the
   link and the reason. Links to anything else are ignored. An upstream link with no fragment is
   refused as a whole-document link.
4. **Correct section.** Design choices link commitments. Requirements link design choices with
   design, commitments without; with design, a requirement link to a commitment is refused.
5. **Child units.** A child's items may link to its own or its parent's upstream items; coverage
   is required only for the child's own items.
6. **Where.** Design close and spec close, before any review round is spent, naming every
   failing item. Each close re-checks, so a renamed upstream heading is caught at the next
   downstream close.

Lead rulings on the test author's questions (2026-10-23):

7. **Required sections.** ``prd.md`` and ``spec.md`` must each have their section with at least
   one item; only design files are exempt. A missing or empty Commitments section is refused at
   design close (spec close in a unit without design); a missing or empty Requirements section
   at spec close. Child units too.
8. **Intent close checks nothing new.** A prd.md flaw is first refused at design close (or spec
   close without design).
9. **Links outside items are ignored**, including upstream-looking links in free-form text
   outside the section.
10. **Fenced code blocks do not count** for items, sections, anchors, or links.
11. **Anchor consolidation is tested through behavior only.**

Round 1 ruling (2026-10-23): Firebreak reads a defined subset of Markdown in prd.md, design
files and spec.md, and refuses what it cannot read, naming the file and line and the way to
write it in the subset:

12. **Headings** are ATX only (up to three spaces, 1-6 ``#``, then a space or end of line). A
    bare ``#`` line is an empty heading and still ends a section. Closing ``#``s are stripped only
    after a space. A setext underline is refused: "write headings with #".
13. **Section and item headings are plain text.** Inline markup (emphasis ``*``/``_``,
    backticks, ``[``, ``]``, ``<``, ``>``) in one is refused: "write item names in plain text".
14. **Fences** open on three or more backticks or tildes after up to three spaces; a backtick
    fence's info string may not contain a backtick (a one-line ```` ```example``` ```` is not a
    fence). Lines starting with ``>`` are ignored for headings, fences and links.
15. **Links** are inline only: ``[text](destination)`` on one line, no spaces, title or angle
    brackets in the destination. Code spans and backslash-escaped brackets are removed first, so
    they never count. Other link-like syntax inside an item (a title, angle brackets, ``][``, a
    ``[label]: destination`` definition, a link broken across lines) is refused: "write links as
    [name](path#anchor) on one line".
16. **Fragments** are percent-decoded before matching; errors keep the original spelling.

Round 2 ruling (2026-10-23): the subset is an allowlist; outside fenced blocks the parser
accepts only the forms it knows and refuses the rest:

17. **No HTML.** ``<`` followed by a letter, ``/``, ``!`` or ``?`` outside code spans is refused
    anywhere in the document ("write plain Markdown; no HTML or comments").
18. **Plain-text names.** A section or item heading may not contain ``*``, backtick, ``[``,
    ``]``, ``<``, ``>``, or an underscore at the start or end of a word (``_cache`` and
    ``cache_`` refused, ``cache_dir`` fine). A heading that contains a section name
    case-insensitively plus any of those characters is refused as a malformed section heading.
19. **Code spans stay on one line.** A line inside an item with an unmatched backtick run is
    refused ("open and close inline code on one line").
20. **Images never count** for linkage or coverage.
21. **Anchors are checked both ways**: as written and with ``*``, backtick and word-boundary
    ``_`` removed; a fragment produced by more than one heading under either form is ambiguous
    and refused.
22. **Destinations** may contain one level of balanced parentheses.
23. **Every subset refusal names the file and line.**

Round 3 rulings (2026-10-23):

24. **Section names through markup.** A heading whose text, with ``*``, ``_``, backtick, ``[``,
    ``]``, ``<``, ``>`` removed, contains a section name case-insensitively but is not exactly
    that name is refused as a malformed section heading.
25. **Fences only at line start.** A line whose content, after a list marker, blockquote marker
    or more than three spaces of indentation, begins with three or more backticks or tildes is
    refused ("start fenced blocks at the beginning of a line, outside lists and quotes"). Only
    an unprefixed fence line with up to three spaces opens or closes a fence.
26. **No escaped backticks in items.** A backslash-backtick inside an item is refused ("write
    literal backticks inside inline code or a fenced block").
27. **Underscore runs.** The second anchor form removes whole underscore runs at word
    boundaries (``__Fast restore__`` gives ``fast-restore``), keeping internal underscores.

Shapes the tests assume, leaving names to the implementer: refusals are ``WorkflowError`` from
``close.close_phase``; a refusal message contains each failing item's heading text, each
refused link's target exactly as written (for example ``../prd.md#fast-restore``), and, for an
anchor refusal, the anchor. Reason words are matched loosely.

Red or guard: every test's docstring says which. **Red** tests fail today on an assertion
about missing behavior (most often ``DID NOT RAISE`` because close accepts); **guard** tests
pass today and pin behavior a plausible wrong implementation would break (named in each).
"""

import re
import sys
import textwrap
from pathlib import Path

import pytest

from fbk.workflow import close, engine, store
from .test_workflow_lifecycle import clean_review, observe_phase

ROOT_DOCS = Path(__file__).resolve().parents[3]
UNIT = "feature"

PRD = """\
# Nightly backups

Operators lose work when a disk fails. This unit adds nightly backups.

## Commitments

### Fast restore

An operator restores yesterday's files within ten minutes.

### Keep history

Thirty days of backups stay available.

#### Why thirty days

Audit asks for a month of history.

## Out of scope

### Offsite copies

Copies to a second site wait for a later unit.
"""

# Level-1 section with level-2 items, a deeper heading inside an item, links to code and an
# external URL in the free-form text, and a section after Design choices.
DESIGN = """\
# Storage design

Context: the agent runs from [the backup module](../../../src/backup.py), following
[vendor guidance](https://example.com/restic#restore).

# Design choices

## Snapshot store

Daily snapshots in one store serve [Fast restore](../prd.md#fast-restore).

### Store layout

One folder per day, named by date.

## Retention log

A log of snapshot dates serves [Keep history](../prd.md#keep-history).

# Notes

Free-form notes after the section.
"""

SPEC = """\
# Backup behavior

## Requirements

### Restore command

`backup restore <date>` restores the files, from [Snapshot store](design/storage.md#snapshot-store).

### History listing

`backup list` shows thirty days, from [Retention log](design/storage.md#retention-log).

#### Listing format

One date per line.

## Checks

Run the unit tests.
"""

# A unit without design: requirements link commitments directly.
SPEC_NO_DESIGN = """\
# Backup behavior

## Requirements

### Restore command

`backup restore <date>` restores the files, for [Fast restore](prd.md#fast-restore).

### History listing

`backup list` shows thirty days, for [Keep history](prd.md#keep-history).
"""

SCOPE = {"sources": ["src"], "tests": ["tests"], "docs": [], "checks": [[sys.executable, "-c", "pass"]]}


# --- harness -------------------------------------------------------------------------------


def configure(root):
    config = root / ".fbk/config.json"
    if not config.exists():
        store.atomic_json(config, {
            "schema_version": 1,
            "review_defaults": {
                p: {"mode": "single", "members": [], "reason": "Fixture operator chooses single review."}
                for p in ("design", "spec")
            },
        })


def make_unit(root, unit=UNIT, *, design=True, kind="feature", parent=None):
    configure(root)
    with store.transaction(root):
        engine.initialize(root, unit, kind=kind, parent=parent, design=design)
    store.atomic_json(root / f".fbk/{unit}/scope.json",
                      SCOPE if kind == "feature" else {"sources": [], "tests": [], "checks": []})
    return root / ".fbk" / unit


def write(base, rel, text):
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text))


def feature(root, *, design=True, prd=PRD, designs=None, spec=None):
    """A unit with its documents written; nothing entered yet."""
    base = make_unit(root, design=design)
    write(base, "prd.md", prd)
    if design:
        for name, text in (designs or {"storage.md": DESIGN}).items():
            write(base, f"design/{name}", text)
    write(base, "spec.md", spec if spec is not None else (SPEC if design else SPEC_NO_DESIGN))
    return base


def enter(root, phase, unit=UNIT):
    with store.transaction(root):
        engine.enter(root, store.load(root, unit), phase, "s")


def accept(root, phase, unit=UNIT):
    enter(root, phase, unit)
    result = close.close_phase(root, unit, phase, "s", reviewer=clean_review)
    assert result["accepted_phase"] == phase
    observe_phase(root, phase, unit=unit)


def refused(root, phase, unit=UNIT, *, entered=False):
    """Enter (unless already open) and close ``phase``; the close must refuse before any
    reviewer launches or review round is spent. Returns the refusal message."""
    if not entered:
        enter(root, phase, unit)
    launched = []

    def reviewer(*args):
        launched.append(args)
        return clean_review(*args)

    rounds = len(store.load(root, unit)["phases"][phase]["rounds"])
    with pytest.raises(store.WorkflowError) as failure:
        close.close_phase(root, unit, phase, "s", reviewer=reviewer)
    assert not launched, f"A reviewer launched before the traceability refusal at {phase} close."
    assert len(store.load(root, unit)["phases"][phase]["rounds"]) == rounds, (
        f"A review round was spent before the traceability refusal at {phase} close.")
    return str(failure.value)


def reopen(root, phase, reason, unit=UNIT):
    with store.transaction(root):
        engine.approve(root, store.load(root, unit), "s", "reopen", phase, reason)
    with store.transaction(root):
        engine.reopen(root, store.load(root, unit), phase, "s", reason)


def names_all(message, *items):
    missing = [item for item in items if item not in message]
    assert not missing, f"The refusal does not name {missing}: {message}"


# --- guards: valid documents close -----------------------------------------------------------


def test_valid_design_unit_closes_intent_design_and_spec(tmp_path):
    """Guard. Sections at different levels, deeper headings inside items with no links of
    their own, an Out of scope note with its own sub-heading, and code and external-URL links
    in free-form text all close. Catches: treating deeper headings (Why thirty days, Store
    layout, Listing format) or headings in other sections (Offsite copies) as items needing
    links or coverage; refusing links to code or external URLs; requiring one fixed level."""
    feature(tmp_path)
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase)


def test_valid_unit_without_design_links_requirements_to_commitments(tmp_path):
    """Guard. Without design, requirements linking commitments close spec. Catches: always
    demanding design-choice links, or refusing a requirement-to-commitment link regardless of
    routing."""
    feature(tmp_path, design=False)
    accept(tmp_path, "intent")
    accept(tmp_path, "spec")


def test_design_file_without_the_section_is_accepted_and_contributes_no_items(tmp_path):
    """Guard. A second design file with no Design choices section is accepted at design close
    and its headings need no requirement at spec close. Catches: refusing a design file without
    the section, or treating its headings as design choices that need links or coverage."""
    notes = "# Operator notes\n\n## Open questions\n\nWhich disk vendor to prefer.\n"
    feature(tmp_path, designs={"storage.md": DESIGN, "notes.md": notes})
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase)


def test_links_to_code_urls_and_other_documents_inside_items_are_ignored(tmp_path):
    """Guard. Links inside items to code, an external URL with a fragment, and a document that
    is not upstream are neither refused nor required to land on items. Catches: treating every
    link with a fragment as a traceability link."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/runbook.md").write_text("# Runbook\n\n## Restore steps\n")
    design = DESIGN.replace(
        "serve [Fast restore](../prd.md#fast-restore).",
        "serve [Fast restore](../prd.md#fast-restore), see [code](../../../src/backup.py#L10),"
        " [docs](https://example.com/restic#restore) and [runbook](../../../docs/runbook.md#restore-steps).",
    )
    feature(tmp_path, designs={"storage.md": design})
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase)


def test_untargeted_duplicate_headings_are_not_refused(tmp_path):
    """Guard. Two headings with the same anchor that no link targets do not refuse. Catches:
    refusing every duplicate heading instead of only a targeted one."""
    prd = PRD + "\n## Later\n\n### Ideas\n\nOne.\n\n## Parking lot\n\n### Ideas\n\nTwo.\n"
    feature(tmp_path, prd=prd)
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase)


def test_anchors_drop_punctuation_like_task_references(tmp_path):
    """Guard. A commitment named ``Restore, fast!`` is reached at ``#restore-fast``, the anchor
    task references already use. Catches: consolidating onto an anchor function that keeps
    punctuation (the repair module's ``restore,-fast!``)."""
    prd = PRD.replace("### Fast restore", "### Restore, fast!")
    design = DESIGN.replace("../prd.md#fast-restore", "../prd.md#restore-fast")
    feature(tmp_path, prd=prd, designs={"storage.md": design})
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase)


def test_link_inside_a_deeper_heading_counts_for_the_item_above(tmp_path):
    """Guard. A design choice whose only link sits under its deeper heading is linked. Catches:
    ending an item's text at any heading instead of at the next item."""
    design = DESIGN.replace(
        "A log of snapshot dates serves [Keep history](../prd.md#keep-history).",
        "A log of snapshot dates.\n\n### Why a log\n\nIt serves [Keep history](../prd.md#keep-history).",
    )
    feature(tmp_path, designs={"storage.md": design})
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase)


# --- design close ----------------------------------------------------------------------------


def test_design_choice_without_a_commitment_link_is_refused(tmp_path):
    """Red. A design choice with no link is refused by name, while every commitment stays
    covered. Catches: checking only coverage of commitments (one direction)."""
    design = DESIGN.replace(
        "## Retention log",
        "## Compression\n\nSnapshots are compressed; no link.\n\n## Retention log",
    )
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "Compression")


def test_uncovered_commitment_is_refused_at_design_close(tmp_path):
    """Red. A commitment no design choice links is refused by name, while every design choice
    has a link. Catches: checking only that each design choice links somewhere."""
    prd = PRD.replace("## Out of scope", "### Encrypt backups\n\nBackups are encrypted.\n\n## Out of scope")
    feature(tmp_path, prd=prd)
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "Encrypt backups")


def test_design_close_names_every_failing_item(tmp_path):
    """Red. Two unlinked design choices and two uncovered commitments are all named in one
    refusal. Catches: stopping at the first failing item, or at the first failing direction."""
    prd = PRD.replace(
        "## Out of scope",
        "### Encrypt backups\n\nEncrypted.\n\n### Verify backups\n\nVerified.\n\n## Out of scope",
    )
    design = DESIGN.replace(
        "## Retention log",
        "## Compression\n\nCompressed.\n\n## Deduplication\n\nDeduplicated.\n\n## Retention log",
    )
    feature(tmp_path, prd=prd, designs={"storage.md": design})
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "Compression", "Deduplication", "Encrypt backups", "Verify backups")


def test_design_close_checks_every_design_file(tmp_path):
    """Red. Failing design choices in two design files are both named. Catches: checking only
    the first (or one) design file."""
    second = "# Scheduling\n\n## Design choices\n\n### Nightly timer\n\nA timer runs at night; no link.\n"
    design = DESIGN.replace(
        "## Retention log", "## Compression\n\nCompressed; no link.\n\n## Retention log")
    feature(tmp_path, designs={"storage.md": design, "scheduling.md": second})
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "Compression", "Nightly timer")


@pytest.mark.parametrize("target,reason", [
    ("../prd.md#offsite-copies", r"section"),      # a heading in the Out of scope section
    ("../prd.md#nightly-backups", r"section|item"),  # the document title, above the section
    ("../prd.md#commitments", r"section|item"),    # the section heading itself is not an item
    ("../prd.md#why-thirty-days", r"item"),        # a deeper heading belongs to the item above
    ("../prd.md#fast-restor", r"anchor|heading"),  # no such heading
])
def test_link_not_landing_on_a_commitment_is_refused_even_beside_a_valid_link(tmp_path, target, reason):
    """Red. A design choice that also has a valid link is still refused for a link that misses
    a commitment, naming the item, the link and the reason. Catches: counting any link into
    prd.md, accepting an item once it has one valid link, treating the section heading or a
    deeper heading as an item, and ignoring an anchor that does not exist."""
    design = DESIGN.replace(
        "serve [Fast restore](../prd.md#fast-restore).",
        f"serve [Fast restore](../prd.md#fast-restore) and [more]({target}).",
    )
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    message = refused(tmp_path, "design")
    names_all(message, "Snapshot store", target)
    assert re.search(reason, message, re.I), f"The refusal gives no reason matching {reason!r}: {message}"


def test_whole_document_link_to_prd_is_refused(tmp_path):
    """Red. A link to prd.md with no fragment is refused as a whole-document link, even beside
    a valid link. Catches: ignoring fragmentless links, or accepting them as 0.6.0 did."""
    design = DESIGN.replace(
        "serve [Fast restore](../prd.md#fast-restore).",
        "serve [Fast restore](../prd.md#fast-restore), per [the PRD](../prd.md).",
    )
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    message = refused(tmp_path, "design")
    names_all(message, "Snapshot store", "../prd.md")
    assert re.search(r"whole|fragment|anchor", message, re.I), message


def test_link_text_after_the_section_does_not_count_for_the_last_item(tmp_path):
    """Red. The last design choice's only link sits in the Notes section after Design choices;
    the choice is refused as unlinked. Catches: letting an item's text run past the end of its
    section."""
    design = DESIGN.replace(
        "A log of snapshot dates serves [Keep history](../prd.md#keep-history).",
        "A log of snapshot dates.",
    ).replace(
        "Free-form notes after the section.",
        "The retention log serves [Keep history](../prd.md#keep-history).",
    ).replace(
        "serve [Fast restore](../prd.md#fast-restore).",
        "serve [Fast restore](../prd.md#fast-restore) and [Keep history](../prd.md#keep-history).",
    )
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "Retention log")


@pytest.mark.parametrize("duplicate", ["### Fast restore", "### Fast restore!"])
def test_link_to_a_duplicated_anchor_is_refused_naming_the_anchor(tmp_path, duplicate):
    """Red. prd.md has a second heading producing ``fast-restore`` (outside Commitments,
    exactly or through punctuation); the design link targeting it is refused naming the
    anchor. Catches: resolving to the first match, or numbering duplicates as GitHub does."""
    prd = PRD + f"\n## Background\n\n{duplicate}\n\nThe old restore took a day.\n"
    feature(tmp_path, prd=prd)
    accept(tmp_path, "intent")
    message = refused(tmp_path, "design")
    names_all(message, "fast-restore")
    assert re.search(r"duplicate|twice|more than one|two headings|same anchor|unique", message, re.I), message


def test_design_file_with_the_section_twice_is_refused(tmp_path):
    """Red. A design file with two Design choices sections is refused at design close, naming
    the section. Catches: reading only the first section, or merging both."""
    design = DESIGN + "\n# Design choices\n\n## Extra choice\n\nServes [Fast restore](../prd.md#fast-restore).\n"
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "Design choices")


def test_prd_with_the_commitments_section_twice_is_refused_by_design_close(tmp_path):
    """Red. prd.md with two Commitments sections passes intent close (ruling 8: intent checks
    nothing new) and is refused at design close, naming the section. Catches: reading only the
    first Commitments section."""
    prd = PRD + "\n## Commitments\n\n### Fast restore later\n\nAgain.\n"
    feature(tmp_path, prd=prd)
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "Commitments")


def test_renamed_commitment_is_caught_at_the_next_design_close(tmp_path):
    """Red. After design closes, intent is reopened and a commitment renamed; the next design
    close refuses the now-broken link by its target. Catches: checking links only once, or
    reporting only the uncovered renamed commitment without the broken link."""
    feature(tmp_path)
    accept(tmp_path, "intent")
    accept(tmp_path, "design")
    reopen(tmp_path, "intent", "Rename a commitment.")
    prd = tmp_path / f".fbk/{UNIT}/prd.md"
    prd.write_text(prd.read_text().replace("### Fast restore", "### Quick restore"))
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "Snapshot store", "../prd.md#fast-restore")


# --- spec close ------------------------------------------------------------------------------


def accepted_through_design(root, **documents):
    feature(root, **documents)
    accept(root, "intent")
    accept(root, "design")


def test_requirement_without_a_design_choice_link_is_refused(tmp_path):
    """Red. A requirement with no link is refused by name while every design choice stays
    covered. Catches: checking only design-choice coverage (one direction)."""
    spec = SPEC.replace("## Checks", "### Audit report\n\nA monthly report; no link.\n\n## Checks")
    accepted_through_design(tmp_path, spec=spec)
    names_all(refused(tmp_path, "spec"), "Audit report")


def test_uncovered_design_choice_is_refused_at_spec_close(tmp_path):
    """Red. A design choice no requirement links is refused by name while every requirement has
    a link. Catches: checking only that each requirement links somewhere."""
    design = DESIGN.replace(
        "## Retention log",
        "## Compression\n\nCompression serves [Fast restore](../prd.md#fast-restore).\n\n## Retention log",
    )
    accepted_through_design(tmp_path, designs={"storage.md": design})
    names_all(refused(tmp_path, "spec"), "Compression")


def test_spec_close_names_every_failing_item(tmp_path):
    """Red. Two unlinked requirements and two uncovered design choices are all named. Catches:
    stopping at the first failing item or direction."""
    design = DESIGN.replace(
        "## Retention log",
        "## Compression\n\nServes [Fast restore](../prd.md#fast-restore).\n\n"
        "## Deduplication\n\nServes [Keep history](../prd.md#keep-history).\n\n## Retention log",
    )
    spec = SPEC.replace(
        "## Checks",
        "### Audit report\n\nNo link.\n\n### Usage metrics\n\nNo link.\n\n## Checks",
    )
    accepted_through_design(tmp_path, designs={"storage.md": design}, spec=spec)
    names_all(refused(tmp_path, "spec"), "Audit report", "Usage metrics", "Compression", "Deduplication")


def test_requirement_linking_a_commitment_is_refused_when_the_unit_has_design(tmp_path):
    """Red. With design, a requirement's link to a commitment is refused as the wrong section,
    even beside a valid design-choice link. Catches: counting any upstream link, or letting a
    commitment link stand in for design."""
    spec = SPEC.replace(
        "from [Snapshot store](design/storage.md#snapshot-store).",
        "from [Snapshot store](design/storage.md#snapshot-store) for [Fast restore](prd.md#fast-restore).",
    )
    accepted_through_design(tmp_path, spec=spec)
    message = refused(tmp_path, "spec")
    names_all(message, "Restore command", "prd.md#fast-restore")
    assert re.search(r"section", message, re.I), message


@pytest.mark.parametrize("target,reason", [
    ("design/storage.md#notes", r"section|item"),        # a heading after Design choices
    ("design/storage.md#store-layout", r"item"),         # a deeper heading inside an item
    ("design/storage.md#snapshot-stor", r"anchor|heading"),
])
def test_requirement_link_not_landing_on_a_design_choice_is_refused(tmp_path, target, reason):
    """Red. A requirement link that misses a design choice is refused beside a valid link,
    naming the item, the link and the reason. Catches: counting any link into a design file."""
    spec = SPEC.replace(
        "from [Snapshot store](design/storage.md#snapshot-store).",
        f"from [Snapshot store](design/storage.md#snapshot-store) and [more]({target}).",
    )
    accepted_through_design(tmp_path, spec=spec)
    message = refused(tmp_path, "spec")
    names_all(message, "Restore command", target)
    assert re.search(reason, message, re.I), message


def test_requirement_link_into_a_design_file_without_the_section_is_refused(tmp_path):
    """Red. A design file with no Design choices section has no items, so a requirement link to
    one of its headings is refused (beside a valid link). Catches: treating any heading in a
    design file as a design choice."""
    notes = "# Operator notes\n\n## Open questions\n\nWhich disk vendor to prefer.\n"
    spec = SPEC.replace(
        "from [Snapshot store](design/storage.md#snapshot-store).",
        "from [Snapshot store](design/storage.md#snapshot-store) and [notes](design/notes.md#open-questions).",
    )
    accepted_through_design(tmp_path, designs={"storage.md": DESIGN, "notes.md": notes}, spec=spec)
    names_all(refused(tmp_path, "spec"), "Restore command", "design/notes.md#open-questions")


def test_whole_document_link_to_a_design_file_is_refused(tmp_path):
    """Red. A requirement link to a design file with no fragment is refused. Catches: ignoring
    fragmentless links to design files."""
    spec = SPEC.replace(
        "from [Snapshot store](design/storage.md#snapshot-store).",
        "from [Snapshot store](design/storage.md#snapshot-store), see [storage](design/storage.md).",
    )
    accepted_through_design(tmp_path, spec=spec)
    message = refused(tmp_path, "spec")
    names_all(message, "Restore command", "design/storage.md")
    assert re.search(r"whole|fragment|anchor", message, re.I), message


def test_spec_with_the_requirements_section_twice_is_refused(tmp_path):
    """Red. spec.md with two Requirements sections is refused, naming the section."""
    spec = SPEC + "\n## Requirements\n\n### Extra\n\nFrom [Retention log](design/storage.md#retention-log).\n"
    accepted_through_design(tmp_path, spec=spec)
    names_all(refused(tmp_path, "spec"), "Requirements")


def test_renamed_design_choice_is_caught_at_the_next_spec_close(tmp_path):
    """Red. After spec closes, design is reopened and a design choice renamed; the next spec
    close refuses the broken link by its target."""
    accepted_through_design(tmp_path)
    accept(tmp_path, "spec")
    reopen(tmp_path, "design", "Rename a design choice.")
    path = tmp_path / f".fbk/{UNIT}/design/storage.md"
    path.write_text(path.read_text().replace("## Snapshot store", "## Snapshot vault"))
    accept(tmp_path, "design")
    names_all(refused(tmp_path, "spec"), "Restore command", "design/storage.md#snapshot-store")


# --- spec close without design ---------------------------------------------------------------


def test_without_design_an_unlinked_requirement_and_an_uncovered_commitment_are_both_refused(tmp_path):
    """Red. Without design, spec close names a requirement with no commitment link and a
    commitment no requirement covers. Catches: skipping the check when design is off, checking
    one direction, or stopping at the first failure."""
    prd = PRD.replace("## Out of scope", "### Encrypt backups\n\nEncrypted.\n\n## Out of scope")
    spec = SPEC_NO_DESIGN + "\n### Audit report\n\nNo link.\n"
    feature(tmp_path, design=False, prd=prd, spec=spec)
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "spec"), "Audit report", "Encrypt backups")


def test_without_design_a_link_outside_commitments_is_refused(tmp_path):
    """Red. Without design, a requirement link to a prd heading outside Commitments is refused
    beside a valid link. Catches: counting any link into prd.md."""
    spec = SPEC_NO_DESIGN.replace(
        "for [Fast restore](prd.md#fast-restore).",
        "for [Fast restore](prd.md#fast-restore) and [later](prd.md#offsite-copies).",
    )
    feature(tmp_path, design=False, spec=spec)
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "spec"), "Restore command", "prd.md#offsite-copies")


def test_renamed_commitment_is_caught_at_the_next_spec_close_without_design(tmp_path):
    """Red. Without design, intent is reopened after spec and a commitment renamed; the next
    spec close refuses the broken link by its target."""
    feature(tmp_path, design=False)
    accept(tmp_path, "intent")
    accept(tmp_path, "spec")
    reopen(tmp_path, "intent", "Rename a commitment.")
    prd = tmp_path / f".fbk/{UNIT}/prd.md"
    prd.write_text(prd.read_text().replace("### Fast restore", "### Quick restore"))
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "spec"), "Restore command", "prd.md#fast-restore")


# --- child units -----------------------------------------------------------------------------

PARENT_PRD = """\
# Job platform

## Background

### Why a platform

Teams each wrote a scheduler.

## Commitments

### Shared scheduler

One scheduler serves every team.

### Cancel jobs

Any job can be cancelled.
"""

PARENT_DESIGN = """\
# Platform design

## Design choices

### One scheduler

A single scheduler serves [Shared scheduler](../prd.md#shared-scheduler).

### Job state machine

Explicit job states serve [Cancel jobs](../prd.md#cancel-jobs).
"""

PARENT_SPEC = """\
# Platform contract

## Requirements

### Scheduler API

From [One scheduler](design/overview.md#one-scheduler).

### Cancel API

From [Job state machine](design/overview.md#job-state-machine).
"""

CHILD_PRD = """\
# Console cancel

## Commitments

### Cancel from the console

An operator cancels a job from the console.
"""

CHILD_DESIGN = """\
# Console design

## Design choices

### Console button

A button serves [Cancel from the console](../prd.md#cancel-from-the-console) and the parent's
[Cancel jobs](../../platform/prd.md#cancel-jobs).

### Reuse scheduler

The console reuses the parent's [Shared scheduler](../../platform/prd.md#shared-scheduler).
"""

CHILD_SPEC = """\
# Console contract

## Requirements

### Button cancels

From [Console button](design/console.md#console-button) and the parent's
[Job state machine](../platform/design/overview.md#job-state-machine).

### Scheduler reuse

From [Reuse scheduler](design/console.md#reuse-scheduler).
"""


def parent_and_child(root, *, child_prd=CHILD_PRD, child_design=CHILD_DESIGN, child_spec=CHILD_SPEC,
                     child_has_design=True):
    """An accepted project unit and a child feature unit with its documents written."""
    base = make_unit(root, "platform", kind="project")
    write(base, "prd.md", PARENT_PRD)
    write(base, "design/overview.md", PARENT_DESIGN)
    write(base, "spec.md", PARENT_SPEC)
    for phase in ("intent", "design", "spec"):
        accept(root, phase, unit="platform")
    child = make_unit(root, "child", parent="platform", design=child_has_design)
    write(child, "prd.md", child_prd)
    if child_has_design:
        write(child, "design/console.md", child_design)
    write(child, "spec.md", child_spec)
    return child


def test_child_links_to_parent_items_count_and_parent_items_need_no_child_coverage(tmp_path):
    """Guard. A child's design choice may link only a parent commitment, and its requirement a
    parent design choice; the parent's items the child does not touch (One scheduler) need no
    coverage from the child. Catches: ignoring parent links, or demanding the child cover the
    parent's items."""
    parent_and_child(tmp_path)
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase, unit="child")


def test_child_link_to_a_parent_heading_outside_commitments_is_refused(tmp_path):
    """Red. A child design choice link to a parent heading outside Commitments is refused
    beside a valid link. Catches: checking parent links less strictly than own links."""
    design = CHILD_DESIGN.replace(
        "parent's [Shared scheduler](../../platform/prd.md#shared-scheduler).",
        "parent's [Shared scheduler](../../platform/prd.md#shared-scheduler), see "
        "[why](../../platform/prd.md#why-a-platform).",
    )
    parent_and_child(tmp_path, child_design=design)
    accept(tmp_path, "intent", unit="child")
    names_all(refused(tmp_path, "design", unit="child"), "Reuse scheduler", "../../platform/prd.md#why-a-platform")


def test_child_link_to_a_missing_parent_anchor_is_refused(tmp_path):
    """Red. A child requirement link to a parent design-choice anchor that does not exist is
    refused beside a valid link."""
    spec = CHILD_SPEC.replace(
        "From [Reuse scheduler](design/console.md#reuse-scheduler).",
        "From [Reuse scheduler](design/console.md#reuse-scheduler) and "
        "[one](../platform/design/overview.md#one-schedulr).",
    )
    parent_and_child(tmp_path, child_spec=spec)
    accept(tmp_path, "intent", unit="child")
    accept(tmp_path, "design", unit="child")
    names_all(refused(tmp_path, "spec", unit="child"), "Scheduler reuse",
              "../platform/design/overview.md#one-schedulr")


def test_link_to_an_unrelated_units_commitment_does_not_count(tmp_path):
    """Red. A child design choice whose only link lands on a commitment of a unit that is not
    its parent is unlinked and refused by name. Catches: counting any unit's prd.md."""
    other = make_unit(tmp_path, "other")
    write(other, "prd.md", "# Other\n\n## Commitments\n\n### Shared scheduler\n\nUnrelated.\n")
    design = CHILD_DESIGN.replace("../../platform/prd.md#shared-scheduler", "../../other/prd.md#shared-scheduler")
    parent_and_child(tmp_path, child_design=design)
    accept(tmp_path, "intent", unit="child")
    names_all(refused(tmp_path, "design", unit="child"), "Reuse scheduler")


# --- required sections (ruling 7) ------------------------------------------------------------

MISSING_REASON = r"missing|empty|no item|without|at least|has no|lacks"
NO_COMMITMENTS = {
    "missing": "# Nightly backups\n\nOperators lose work when a disk fails.\n",
    "empty": "# Nightly backups\n\n## Commitments\n\nNothing settled yet.\n\n"
             "## Out of scope\n\n### Offsite copies\n\nLater.\n",
}
NO_REQUIREMENTS = {
    "missing": "# Backup behavior\n\nFree text only.\n",
    "empty": "# Backup behavior\n\n## Requirements\n\nNone yet.\n\n## Checks\n\n### Unit tests\n\nRun them.\n",
}


@pytest.mark.parametrize("shape", sorted(NO_COMMITMENTS))
def test_prd_without_commitments_is_refused_at_design_close(tmp_path, shape):
    """Red. A prd.md with no Commitments section, or one with no item, is refused at design
    close even when no design file has a Design choices section, so nothing else fails.
    Catches: treating a missing section as zero items that need nothing."""
    feature(tmp_path, prd=NO_COMMITMENTS[shape], designs={"storage.md": "# Storage\n\nNotes only.\n"})
    accept(tmp_path, "intent")
    message = refused(tmp_path, "design")
    names_all(message, "Commitments")
    assert re.search(MISSING_REASON, message, re.I), message


@pytest.mark.parametrize("shape", sorted(NO_COMMITMENTS))
def test_without_design_missing_commitments_and_requirements_are_both_refused_at_spec_close(tmp_path, shape):
    """Red. Without design, a prd.md and a spec.md both lacking items are refused at spec close,
    naming both sections. Catches: vacuous coverage over zero items."""
    feature(tmp_path, design=False, prd=NO_COMMITMENTS[shape], spec=NO_REQUIREMENTS[shape])
    accept(tmp_path, "intent")
    message = refused(tmp_path, "spec")
    names_all(message, "Commitments", "Requirements")
    assert re.search(MISSING_REASON, message, re.I), message


@pytest.mark.parametrize("shape", sorted(NO_REQUIREMENTS))
def test_spec_without_requirements_is_refused_at_spec_close(tmp_path, shape):
    """Red. A spec.md with no Requirements section, or one with no item, is refused at spec
    close naming the section. Catches: reporting only the uncovered design choices."""
    accepted_through_design(tmp_path, spec=NO_REQUIREMENTS[shape])
    message = refused(tmp_path, "spec")
    names_all(message, "Requirements")
    assert re.search(MISSING_REASON, message, re.I), message


def test_child_prd_without_commitments_is_refused_at_design_close(tmp_path):
    """Red. A child whose design choices link only parent commitments still needs its own
    Commitments section with an item. Catches: exempting child units from the section rule."""
    design = CHILD_DESIGN.replace("[Cancel from the console](../prd.md#cancel-from-the-console) and ", "")
    parent_and_child(tmp_path, child_prd="# Console cancel\n\nAn operator cancels from the console.\n",
                     child_design=design)
    accept(tmp_path, "intent", unit="child")
    message = refused(tmp_path, "design", unit="child")
    names_all(message, "Commitments")
    assert re.search(MISSING_REASON, message, re.I), message


def test_child_spec_without_requirements_is_refused_at_spec_close(tmp_path):
    """Red. A child spec.md with no Requirements section is refused, naming the section."""
    parent_and_child(tmp_path, child_spec="# Console contract\n\nFree text only.\n")
    accept(tmp_path, "intent", unit="child")
    accept(tmp_path, "design", unit="child")
    message = refused(tmp_path, "spec", unit="child")
    names_all(message, "Requirements")
    assert re.search(MISSING_REASON, message, re.I), message


# --- links outside items (ruling 9) and fenced code (ruling 10) ------------------------------


def test_upstream_links_outside_items_are_ignored(tmp_path):
    """Guard. Upstream-looking links in free-form text outside the section, and between a
    section heading and its first item, are ignored even when they would be refused inside an
    item (whole-document, wrong section). Catches: checking every link in the document."""
    design = DESIGN.replace(
        "Context: the agent",
        "Background: [the PRD](../prd.md) and [later](../prd.md#offsite-copies).\n\nContext: the agent",
    ).replace("Free-form notes after the section.", "See [the PRD](../prd.md) again.")
    spec = SPEC.replace(
        "## Requirements\n",
        "## Requirements\n\nContext: [storage](design/storage.md) and [restore](prd.md#fast-restore).\n",
    ).replace("Run the unit tests.", "Run the unit tests; see [the PRD](prd.md).")
    feature(tmp_path, designs={"storage.md": design}, spec=spec)
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase)


def test_fenced_headings_do_not_make_anchors_or_sections_ambiguous(tmp_path):
    """Guard. A fenced copy of the Commitments heading and of an item heading creates no second
    section and no duplicate anchor. Catches: parsing headings inside code fences."""
    prd = PRD + "\n## Example\n\n```markdown\n## Commitments\n\n### Fast restore\n```\n"
    feature(tmp_path, prd=prd)
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase)


def test_link_to_a_heading_inside_a_fence_is_refused(tmp_path):
    """Red. A heading that exists only inside a fenced block within Commitments is no item and
    no anchor, so a link to it is refused beside a valid link. Catches: parsing fenced headings."""
    prd = PRD.replace("Audit asks for a month of history.\n",
                      "Audit asks for a month of history.\n\n```\n### Fenced idea\n```\n")
    design = DESIGN.replace(
        "serve [Fast restore](../prd.md#fast-restore).",
        "serve [Fast restore](../prd.md#fast-restore) and [idea](../prd.md#fenced-idea).",
    )
    feature(tmp_path, prd=prd, designs={"storage.md": design})
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "Snapshot store", "../prd.md#fenced-idea")


def test_link_inside_a_fence_does_not_link_its_item(tmp_path):
    """Red. A design choice whose only link sits in a fenced block is unlinked and refused by
    name; the commitment stays covered elsewhere. Catches: reading links inside code fences."""
    design = DESIGN.replace(
        "A log of snapshot dates serves [Keep history](../prd.md#keep-history).",
        "A log of snapshot dates.\n\n```\n[Keep history](../prd.md#keep-history)\n```",
    ).replace(
        "serve [Fast restore](../prd.md#fast-restore).",
        "serve [Fast restore](../prd.md#fast-restore) and [Keep history](../prd.md#keep-history).",
    )
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "Retention log")


def test_a_fenced_requirements_section_is_no_section(tmp_path):
    """Red. A spec.md whose only Requirements section is inside a fenced block has no
    Requirements section and is refused naming it. Catches: parsing fenced headings as a
    section and its items."""
    spec = "# Backup behavior\n\n```markdown\n" + SPEC.split("# Backup behavior\n\n", 1)[1] + "```\n"
    accepted_through_design(tmp_path, spec=spec)
    names_all(refused(tmp_path, "spec"), "Requirements")


# --- the Markdown subset (round 1 rulings 12-16) ---------------------------------------------

HEADING_REMEDY = r"with #"
PLAIN_REMEDY = r"plain text"
LINK_REMEDY = r"on one line"
HTML_REMEDY = r"HTML|comment"


def lines_of(text, *markers):
    """The 1-based line numbers of the lines containing any of ``markers``."""
    return [n for n, line in enumerate(text.splitlines(), 1) if any(m in line for m in markers)]


def names_line(message, file, numbers):
    """Ruling 23: a subset refusal names the file and the line (any one of ``numbers``, where
    the rulings leave open which of two lines is reported)."""
    assert numbers, "The test's marker was not found in its own document."
    pattern = rf"{re.escape(file)}\D{{0,12}}(?:{'|'.join(map(str, numbers))})\b"
    assert re.search(pattern, message), f"The refusal does not name {file} at line {numbers}: {message}"


def test_setext_item_heading_is_refused_with_the_hash_remedy(tmp_path):
    """Red. A design choice written as a setext heading (text over ``---``) is refused at design
    close, naming the file and saying to write headings with #. Catches: silently skipping
    setext headings, which lets an unlinked item escape (review finding 1)."""
    design = DESIGN.replace("## Retention log\n\nA log of snapshot dates serves [Keep history](../prd.md#keep-history).",
                            "## Retention log\n\nA log of snapshot dates serves [Keep history](../prd.md#keep-history).\n\n"
                            "Unlinked choice\n---------------\n\nNo link here.")
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    message = refused(tmp_path, "design")
    names_line(message, "design/storage.md", lines_of(design, "Unlinked choice", "---------------"))
    assert re.search(HEADING_REMEDY, message), message


def test_setext_section_heading_is_refused_with_the_hash_remedy(tmp_path):
    """Red. A Commitments section written as a setext heading is refused with the # remedy, not
    reported as a missing section. Catches: treating it as absent without saying why."""
    prd = PRD.replace("## Commitments", "Commitments\n-----------")
    feature(tmp_path, prd=prd)
    accept(tmp_path, "intent")
    message = refused(tmp_path, "design")
    names_line(message, "prd.md", [n for n in lines_of(prd, "Commitments", "-----------")])
    assert re.search(HEADING_REMEDY, message), message


@pytest.mark.parametrize("bad,markers", [
    ("[Gone](../prd.md#keep-history 'title')", ["'title'"]),
    ("[Gone](<../prd.md#keep-history>)", ["<../prd.md"]),
    ("[Gone][history]", ["[Gone][history]"]),
    ("\n\n[history]: ../prd.md#keep-history\n", ["[history]:"]),
    ("[Keep\nhistory](../prd.md#keep-history)", ["and [Keep"]),
], ids=["title", "angle-brackets", "reference", "definition", "across-lines"])
def test_unreadable_link_syntax_inside_an_item_is_refused_beside_a_valid_link(tmp_path, bad, markers):
    """Red. Link syntax inside an item that is not a one-line inline link is refused with the
    one-line remedy, even though the item also has a valid plain link. Catches: silently
    ignoring a link form the parser cannot read (review finding 2)."""
    design = DESIGN.replace(
        "serve [Fast restore](../prd.md#fast-restore).",
        f"serve [Fast restore](../prd.md#fast-restore) and {bad}",
    )
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    message = refused(tmp_path, "design")
    numbers = lines_of(design, *markers)
    if "\n" in bad.strip():
        numbers += [n + 1 for n in numbers]  # either line of a link broken across two lines
    names_line(message, "design/storage.md", numbers)
    assert re.search(LINK_REMEDY, message), message


def only_link(replacement):
    """DESIGN with Retention log's only link replaced; Keep history stays covered by Snapshot store."""
    return DESIGN.replace(
        "A log of snapshot dates serves [Keep history](../prd.md#keep-history).", replacement,
    ).replace(
        "serve [Fast restore](../prd.md#fast-restore).",
        "serve [Fast restore](../prd.md#fast-restore) and [Keep history](../prd.md#keep-history).",
    )


@pytest.mark.parametrize("replacement", [
    "A log of dates; example: `[Keep history](../prd.md#keep-history)`.",
    "A log of dates; example: \\[Keep history](../prd.md#keep-history).",
    "A log of dates.\n\n> It serves [Keep history](../prd.md#keep-history).",
], ids=["code-span", "escaped-bracket", "blockquote"])
def test_link_in_code_span_escape_or_blockquote_does_not_link_its_item(tmp_path, replacement):
    """Red. A design choice whose only apparent link is in a code span, after an escaped
    bracket, or in a blockquote is refused by name. Catches: counting literal link text
    (review findings 3 and 4)."""
    feature(tmp_path, designs={"storage.md": only_link(replacement)})
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "Retention log")


def test_one_line_backtick_example_is_not_a_fence(tmp_path):
    """Red. A line holding ```` ```example``` ```` does not open a fence, so a later unlinked
    requirement is still refused by name. Catches: opening a fence through the end of the file
    (review finding 4)."""
    spec = SPEC.replace(
        "### History listing",
        "```example``` is shown literally.\n\n### History listing",
    ).replace("## Checks", "### Audit report\n\nNo link.\n\n## Checks")
    accepted_through_design(tmp_path, spec=spec)
    names_all(refused(tmp_path, "spec"), "Audit report")


@pytest.mark.parametrize("heading", ["### _Fast restore_", "### `Fast` restore", "### *Fast* restore"])
def test_item_heading_with_markup_is_refused_as_not_plain_text(tmp_path, heading):
    """Red. A commitment heading with emphasis or backticks is refused at design close with the
    plain-text remedy. Catches: anchoring raw markup (``_fast-restore_``) (review finding 5)."""
    prd = PRD.replace("### Fast restore", heading)
    feature(tmp_path, prd=prd)
    accept(tmp_path, "intent")
    message = refused(tmp_path, "design")
    names_line(message, "prd.md", lines_of(prd, heading))
    assert re.search(PLAIN_REMEDY, message), message


def test_bare_hash_heading_ends_the_section(tmp_path):
    """Red. An empty ``#`` heading at the section's level ends Design choices, so a link after
    it does not count for the last choice, which is refused by name (review finding 6)."""
    design = only_link("A log of snapshot dates.\n\n#\n\nThe log serves [Keep history](../prd.md#keep-history).")
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "Retention log")


def test_attached_trailing_hash_is_part_of_the_heading_text(tmp_path):
    """Red. ``## Requirements#`` is not the Requirements section (closing hashes need a space
    before them), so the spec has no Requirements section and is refused naming it
    (review finding 6)."""
    accepted_through_design(tmp_path, spec=SPEC.replace("## Requirements", "## Requirements#"))
    names_all(refused(tmp_path, "spec"), "Requirements")


def test_percent_encoded_fragment_to_a_non_ascii_item_is_accepted(tmp_path):
    """Red. A commitment named ``Café restore`` is reached by ``#caf%C3%A9-restore``, as a browser
    resolves it. Catches: decoding paths but not fragments (review finding 7)."""
    prd = PRD.replace("### Fast restore", "### Café restore")
    design = DESIGN.replace("../prd.md#fast-restore", "../prd.md#caf%C3%A9-restore")
    feature(tmp_path, prd=prd, designs={"storage.md": design})
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase)


# --- review findings 8 and 9: coverage gaps ---------------------------------------------------


def test_child_requirement_linked_only_to_a_parent_design_choice_counts(tmp_path):
    """Guard. A child requirement whose only link is a parent design choice is linked, while
    another requirement covers both child choices. Catches: validating parent links but never
    crediting them toward a requirement's link (review finding 8, with design)."""
    spec = CHILD_SPEC.replace(
        "From [Console button](design/console.md#console-button) and the parent's\n",
        "From the parent's\n",
    ).replace(
        "From [Reuse scheduler](design/console.md#reuse-scheduler).",
        "From [Reuse scheduler](design/console.md#reuse-scheduler) and [Console button](design/console.md#console-button).",
    )
    assert "design/console.md#console-button" not in spec.split("### Scheduler reuse")[0]
    parent_and_child(tmp_path, child_spec=spec)
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase, unit="child")


def test_child_without_design_requirement_linked_only_to_a_parent_commitment_counts(tmp_path):
    """Guard. In a child without design, a requirement whose only link is a parent commitment is
    linked, while another requirement covers the child's commitment (review finding 8, without
    design)."""
    spec = (
        "# Console contract\n\n## Requirements\n\n"
        "### Cancel through the platform\n\nFor the parent's [Cancel jobs](../platform/prd.md#cancel-jobs).\n\n"
        "### Console cancel button\n\nFor [Cancel from the console](prd.md#cancel-from-the-console).\n"
    )
    parent_and_child(tmp_path, child_spec=spec, child_has_design=False)
    for phase in ("intent", "spec"):
        accept(tmp_path, phase, unit="child")


@pytest.mark.parametrize("second_name", ["a-scheduling.md", "z-scheduling.md"])
def test_spec_close_names_an_uncovered_choice_in_a_second_design_file(tmp_path, second_name):
    """Guard. With two design files holding choices, spec close names the one choice no
    requirement covers, whether its file sorts before or after the covered one. Catches:
    checking coverage in the first design file only (review finding 9; r3 finding 5)."""
    second = "# Scheduling\n\n## Design choices\n\n### Nightly timer\n\nA timer serves [Keep history](../prd.md#keep-history).\n"
    accepted_through_design(tmp_path, designs={"storage.md": DESIGN, second_name: second})
    names_all(refused(tmp_path, "spec"), "Nightly timer")


# --- round 2: the subset is an allowlist (rulings 17-23) -------------------------------------


def test_html_comment_around_a_heading_is_refused_with_file_and_line(tmp_path):
    """Red. A commented-out heading between items would end the section and hide the unlinked
    item after it; the comment is refused, naming spec.md and the line (review r2 finding 1)."""
    spec = SPEC.replace("## Checks", "<!--\n## Notes\n-->\n\n### Audit report\n\nNo link.\n\n## Checks")
    accepted_through_design(tmp_path, spec=spec)
    message = refused(tmp_path, "spec")
    names_line(message, "spec.md", lines_of(spec, "<!--", "-->"))
    assert re.search(HTML_REMEDY, message), message


@pytest.mark.parametrize("heading", ["# [Design choices](#choices)", "# <em>Design choices</em>"],
                         ids=["bracketed", "html"])
def test_marked_up_section_heading_in_a_second_design_file_is_refused(tmp_path, heading):
    """Red. A second design file whose section heading carries markup is refused with its file
    and line, not treated as a sectionless file whose unlinked choice escapes; the first file
    covers every commitment (review r2 finding 2)."""
    second = f"# Scheduling\n\n{heading}\n\n## Nightly timer\n\nNo link.\n"
    feature(tmp_path, designs={"storage.md": DESIGN, "scheduling.md": second})
    accept(tmp_path, "intent")
    names_line(refused(tmp_path, "design"), "design/scheduling.md", lines_of(second, heading))


def test_code_span_split_across_lines_inside_an_item_is_refused(tmp_path):
    """Red. A backtick opened on one line and closed on the next, wrapping the item's only link,
    is refused with the one-line remedy and the line (review r2 finding 3)."""
    design = only_link("A log of dates, `example\n[Keep history](../prd.md#keep-history)` here.")
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    message = refused(tmp_path, "design")
    names_line(message, "design/storage.md", lines_of(design, "`example", "#keep-history)` here"))
    assert re.search(r"one line", message), message


def test_an_image_neither_links_an_item_nor_covers_a_commitment(tmp_path):
    """Red. A choice whose only link is an image is unlinked, and the commitment only that image
    points at is uncovered; both are named (review r2 finding 4)."""
    design = DESIGN.replace("serves [Keep history](../prd.md#keep-history).",
                            "serves ![Keep history](../prd.md#keep-history).")
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "Retention log", "Keep history")


@pytest.mark.parametrize("earlier", ["_Fast restore_", "__Fast restore__", "___Fast restore___"])
def test_an_earlier_formatted_heading_makes_the_anchor_ambiguous(tmp_path, earlier):
    """Red. An earlier heading such as ``# _Fast restore_`` (or with double or triple underscore
    runs) yields ``fast-restore`` once its emphasis is removed, so a link to ``#fast-restore``
    is ambiguous and refused naming the anchor (review r2 finding 5; r3 finding 4, ruling 27)."""
    prd = PRD.replace("## Commitments", f"# {earlier}\n\nAn old note.\n\n## Commitments")
    feature(tmp_path, prd=prd)
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "fast-restore")


def test_a_parenthesized_design_filename_link_is_accepted(tmp_path):
    """Red. ``design/storage(v2).md#snapshot-store`` has one level of balanced parentheses and
    reaches the choice; the unit closes design and spec (review r2 finding 6)."""
    spec = SPEC.replace("design/storage.md", "design/storage(v2).md")
    feature(tmp_path, designs={"storage(v2).md": DESIGN}, spec=spec)
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase)


@pytest.mark.parametrize("name", ["Restore _cache", "Restore cache_"])
def test_item_name_with_a_word_boundary_underscore_is_refused(tmp_path, name):
    """Guard. An underscore at the start or end of a word in an item name is refused as not plain
    text, naming the line (ruling 18). Catches: a fix for finding 7 that accepts every
    underscore."""
    prd = PRD.replace("### Fast restore", f"### {name}")
    feature(tmp_path, prd=prd)
    accept(tmp_path, "intent")
    message = refused(tmp_path, "design")
    names_line(message, "prd.md", lines_of(prd, f"### {name}"))
    assert re.search(PLAIN_REMEDY, message), message


def test_item_name_with_an_inner_underscore_is_accepted(tmp_path):
    """Guard (passes today). ``Restore cache_dir`` is plain text; a link to
    ``#restore-cache_dir`` reaches it and the unit closes (review r2 finding 7). Catches:
    refusing every underscore."""
    prd = PRD.replace("### Fast restore", "### Restore cache_dir")
    design = DESIGN.replace("../prd.md#fast-restore", "../prd.md#restore-cache_dir")
    feature(tmp_path, prd=prd, designs={"storage.md": design})
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase)


def test_a_nested_design_file_resolves_links_from_its_own_folder(tmp_path):
    """Guard. ``design/storage/layout.md`` links ``../../prd.md#...`` and the spec links
    ``design/storage/layout.md#...``; design and spec close. Catches: resolving every design
    link from ``design/`` (review r2 finding 9)."""
    nested = DESIGN.replace("../prd.md#", "../../prd.md#").replace("../../../src/", "../../../../src/")
    spec = SPEC.replace("design/storage.md", "design/storage/layout.md")
    feature(tmp_path, designs={"storage/layout.md": nested}, spec=spec)
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase)


def test_a_plain_prose_comparison_is_not_html(tmp_path):
    """Guard. ``a < b`` and ``x<5`` in item text are prose, not HTML. Catches: refusing every
    ``<``."""
    design = DESIGN.replace("One folder per day, named by date.",
                            "One folder per day; keep a < b and x<5 when sorting.")
    feature(tmp_path, designs={"storage.md": design})
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase)


# --- round 3 (rulings 24-27) -----------------------------------------------------------------


def test_section_name_broken_by_markup_in_a_second_design_file_is_refused(tmp_path):
    """Red. ``# Design **choices**`` in a second design file is refused as a malformed section
    heading with its file and line, instead of making the file sectionless so its unlinked
    choice escapes (review r3 finding 1, ruling 24)."""
    second = "# Scheduling\n\n# Design **choices**\n\n## Audit log\n\nNo upstream link.\n"
    feature(tmp_path, designs={"storage.md": DESIGN, "scheduling.md": second})
    accept(tmp_path, "intent")
    names_line(refused(tmp_path, "design"), "design/scheduling.md", lines_of(second, "Design **choices**"))


def test_fence_inside_a_list_item_is_refused(tmp_path):
    """Red. A fenced block opened inside a list item would desynchronize fence tracking and hide
    the section after it; the list-prefixed fence line is refused with its file and line
    (review r3 finding 2, ruling 25)."""
    second = "- ```text\n  example\n  ```\n\n# Design choices\n## Audit log\nNo upstream link.\n"
    feature(tmp_path, designs={"storage.md": DESIGN, "scheduling.md": second})
    accept(tmp_path, "intent")
    message = refused(tmp_path, "design")
    names_line(message, "design/scheduling.md", lines_of(second, "```"))
    assert re.search(r"beginning of a line|outside lists|start fenced", message, re.I), message


def test_escaped_backtick_inside_an_item_is_refused_and_its_link_does_not_count(tmp_path):
    """Red. Escaped backticks around a code span that holds the item's only apparent link are
    refused with the file and line, and the item is named (review r3 finding 3, ruling 26)."""
    replacement = "A log of dates: \\`literal` [Keep history](../prd.md#keep-history) `code\\`."
    design = only_link(replacement)
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    message = refused(tmp_path, "design")
    names_line(message, "design/storage.md", lines_of(design, "\\`literal`"))
    names_all(message, "Retention log")
    assert re.search(r"backtick", message, re.I), message


def test_indented_fence_inside_an_item_is_refused(tmp_path):
    """Red (plain-shapes ruling, 2026-10-24). Inside a traceability section a fence opens only
    at column 0; a fence indented one space is refused, naming the file, its line and the item
    Snapshot store."""
    design = DESIGN.replace(
        "One folder per day, named by date.",
        "One folder per day, named by date.\n\n ~~~\n ## Not an item\n ~~~",
    )
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    message = refused(tmp_path, "design")
    names_line(message, "design/storage.md", lines_of(design, " ~~~"))
    names_all(message, "Snapshot store")


def test_column_zero_fence_still_hides_its_content(tmp_path):
    """Guard. Fences of backticks and of tildes at column 0 open and close: the heading and link
    inside them do not count, and the unit closes. Catches: a fix for the plain-shapes ruling
    that refuses or ignores every fence inside an item."""
    design = DESIGN.replace(
        "One folder per day, named by date.",
        "One folder per day, named by date.\n\n```text\n## Not an item\n[x](../prd.md#nope)\n```\n\n"
        "~~~\n## Also not an item\n~~~",
    )
    feature(tmp_path, designs={"storage.md": design})
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase)


# --- follow-ups left open at the review cap (round 4 majors) ---------------------------------


def test_followup_reference_link_with_parenthesized_suffix_does_not_link(tmp_path):
    """Strict expected failure (round 4 major 1). ``[read][label](../prd.md#keep-history)`` with
    ``[label]`` defined outside the section is a reference link to the definition, not a link
    to the commitment; the choice must be refused, not credited."""
    design = DESIGN.replace(
        "# Design choices", "[label]: https://example.com\n\n# Design choices",
    ).replace(
        "A log of snapshot dates serves [Keep history](../prd.md#keep-history).",
        "A log of snapshot dates, [read][label](../prd.md#keep-history).",
    )
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "Retention log")


def test_followup_tab_indented_fence_in_a_list_is_refused(tmp_path):
    """Strict expected failure (round 4 major 2). A tab-indented fence opener under a list item
    escapes ruling 25, and its two-space closer then opens a fence through the end of the file,
    hiding the second design file's unlinked choice."""
    second = "- Example\n\n\t```text\n\texample\n  ```\n\n# Design choices\n## Audit log\nNo link.\n"
    feature(tmp_path, designs={"storage.md": DESIGN, "scheduling.md": second})
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "design/scheduling.md")


def test_followup_blockquote_continuation_line_does_not_link(tmp_path):
    """Strict expected failure (round 4 major 3). A link on the unmarked line right after a
    ``>`` line continues the blockquote in Markdown, so it must not link the choice or cover
    the commitment."""
    design = DESIGN.replace(
        "A log of snapshot dates serves [Keep history](../prd.md#keep-history).",
        "A log of snapshot dates.\n\n> Example:\n[Keep history](../prd.md#keep-history)",
    )
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "Retention log")


def test_followup_earlier_linked_heading_is_refused(tmp_path):
    """Round 4 major 4, under the plain-shapes ruling (2026-10-24). ``# [Fast restore](other.md)``
    before Commitments holds link syntax, so the heading is refused naming prd.md and its line
    instead of its anchor being guessed."""
    heading = "# [Fast restore](other.md)"
    prd = PRD.replace("## Commitments", f"{heading}\n\nAn old note.\n\n## Commitments")
    feature(tmp_path, prd=prd)
    accept(tmp_path, "intent")
    names_line(refused(tmp_path, "design"), "prd.md", lines_of(prd, heading))


# --- Follow-up group C, review round 1 -------------------------------------------------------


def close_all(root, **documents):
    feature(root, **documents)
    for phase in ("intent", "design", "spec"):
        accept(root, phase)


@pytest.mark.parametrize("fence", ["~~~", "```"], ids=["tildes", "backticks"])
def test_followup_c_list_continuation_fence_does_not_hide_the_section(tmp_path, fence):
    """Red (round 1 finding 2). A fence indented two spaces under a list item belongs to the
    item and ends with it; it must not open a fence through the end of the file. The second
    design file is refused by name, whether for the fence or for its unlinked choice."""
    second = f"- Example\n\n  {fence}\n  sample\n\n# Design choices\n## Unlinked\nNo link.\n"
    feature(tmp_path, designs={"storage.md": DESIGN, "scheduling.md": second})
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "design/scheduling.md")


def test_followup_c_quote_inside_a_list_item_does_not_link(tmp_path):
    """Red (round 1 finding 3). ``- > Example`` opens a blockquote inside a list item, and the
    indented link line after it continues the quote; the choice whose only link it is must be
    refused by name, not credited."""
    design = only_link("A log of dates.\n\n- > Example\n  [Keep history](../prd.md#keep-history)")
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "Retention log")


@pytest.mark.parametrize("indent", ["\t", "    "], ids=["tab", "four-spaces"])
def test_followup_c_indented_code_line_does_not_link(tmp_path, indent):
    """Red (round 1 finding 4). After a blank line, a line indented a tab or four spaces outside
    any list is indented code; the choice whose only link it holds must be refused by name."""
    design = only_link(f"A log of dates.\n\n{indent}[Keep history](../prd.md#keep-history)")
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "Retention log")


@pytest.mark.parametrize("earlier", [
    '# [Fast restore](other.md "Background")',
    "[ref]: other.md\n\n# [Fast restore][ref]",
], ids=["link-with-title", "reference-link"])
def test_followup_c_earlier_heading_link_forms_make_the_anchor_ambiguous(tmp_path, earlier):
    """Red (round 1 finding 5). An earlier heading written as a titled or reference link renders
    with the anchor ``fast-restore``. Design close must refuse: either the link to
    ``#fast-restore`` as ambiguous, or the heading as outside the subset with prd.md and its
    line."""
    prd = PRD.replace("## Commitments", f"{earlier}\n\nAn old note.\n\n## Commitments")
    feature(tmp_path, prd=prd)
    accept(tmp_path, "intent")
    message = refused(tmp_path, "design")
    heading = earlier.splitlines()[-1]
    ambiguous = "fast-restore" in message and re.search(r"ambiguous", message, re.I)
    at_line = re.search(rf"prd\.md\D{{0,12}}{lines_of(prd, heading)[0]}\b", message)
    assert ambiguous or at_line, f"Neither the ambiguous anchor nor the heading's line is named: {message}"


@pytest.mark.parametrize("earlier", ["# `[Fast restore](other.md)`", "# \\[Fast restore](other.md)"],
                         ids=["code-span", "escaped-bracket"])
def test_followup_c_literal_link_text_in_an_earlier_heading_is_not_ambiguous(tmp_path, earlier):
    """Red (round 1 finding 6). Link syntax inside a code span or after an escaped bracket is
    literal text, so the heading's anchor is not ``fast-restore``; the unit closes."""
    close_all(tmp_path, prd=PRD.replace("## Commitments", f"{earlier}\n\nAn old note.\n\n## Commitments"))


@pytest.mark.parametrize("replacement", [
    "A log of snapshot dates.\n\n> Example\n>\n[Keep history](../prd.md#keep-history) is served.",
    "A log of snapshot dates.\n\n> Example\n- It serves [Keep history](../prd.md#keep-history).",
], ids=["marked-blank-line", "list-after-quote"])
def test_followup_c_link_after_a_finished_quote_is_accepted(tmp_path, replacement):
    """Red (round 1 finding 7). A marked blank line ends the quoted paragraph, and a list item
    interrupts it, so the link after either is outside the quote; the unit closes."""
    design = DESIGN.replace("A log of snapshot dates serves [Keep history](../prd.md#keep-history).", replacement)
    close_all(tmp_path, designs={"storage.md": design})


def test_followup_c_link_with_brackets_in_its_destination_is_accepted(tmp_path):
    """Red (round 1 finding 8). ``[API](https://example.com/search?filter[status][eq]=active)``
    is a valid one-line inline link beside the choice's upstream link; the unit closes."""
    design = DESIGN.replace(
        "serve [Fast restore](../prd.md#fast-restore).",
        "serve [Fast restore](../prd.md#fast-restore); see [API](https://example.com/search?filter[status][eq]=active).",
    )
    close_all(tmp_path, designs={"storage.md": design})


@pytest.mark.parametrize("literal", ["written `a][b` in notes", "written \\]\\[ in notes", "kept\tby date"],
                         ids=["code-span", "escaped", "tab-in-prose"])
def test_followup_c_literal_brackets_and_tabs_beside_a_link_are_accepted(tmp_path, literal):
    """Guard (round 1 finding 10). A literal ``][`` in a code span or as escaped brackets, or a
    tab inside prose, beside a genuine upstream link, closes. Catches: a blanket ban on the raw
    characters."""
    design = DESIGN.replace(
        "Daily snapshots in one store serve", f"Daily snapshots, {literal}, serve",
    )
    close_all(tmp_path, designs={"storage.md": design})


# --- Follow-up group C, review round 2 -------------------------------------------------------
#
# Operator ruling (2026-10-24): inside a traceability section only plain line shapes are
# accepted (blank, column-0 heading, paragraph, list item at column 0 or at an open item's
# content column, continuation at exactly that column, `> text` or a bare `>`, column-0 fence);
# everything else is refused naming file, line and item. Anywhere in such a document, a heading
# holding link syntax and a reference-link definition are refused.

QUOTE_CONTINUATION = r"blank line after a blockquote"


def refused_in_item(root, design, *markers):
    """Design close of ``design`` (as storage.md) is refused naming the file, the line holding
    any of ``markers``, and the item Retention log."""
    feature(root, designs={"storage.md": design})
    accept(root, "intent")
    message = refused(root, "design")
    names_line(message, "design/storage.md", lines_of(design, *markers))
    names_all(message, "Retention log")
    return message


@pytest.mark.parametrize("indent", ["    ", "\t"], ids=["four-spaces", "tab"])
def test_followup_c2_quote_indented_under_a_list_item_is_refused(tmp_path, indent):
    """Red (round 2 finding 1). A quote marker indented under a list item, and the link line
    continuing it, are refused with the file, line and item instead of crediting the link."""
    refused_in_item(tmp_path, only_link(
        f"A log of dates.\n\n- Example\n{indent}> Note\n{indent}[Keep history](../prd.md#keep-history)"),
        "> Note", "[Keep history](../prd.md#keep-history)")


def test_followup_c2_list_code_indented_past_the_content_column_is_refused(tmp_path):
    """Red (round 2 finding 2). Six spaces under ``- Example`` is code inside the list item; its
    indentation does not match the content column (2), so the line is refused, not credited."""
    refused_in_item(tmp_path, only_link("A log of dates.\n\n- Example\n\n      [Keep history](../prd.md#keep-history)"),
                    "      [Keep history]")


def test_followup_c2_thematic_break_then_indented_code_is_refused(tmp_path):
    """Red (round 2 finding 3). A thematic break followed by a four-space line (indented code)
    is refused at the break or the indented line, not read as a paragraph continuation."""
    refused_in_item(tmp_path, only_link("A log of dates.\n\n---\n    [Keep history](../prd.md#keep-history)"),
                    "---", "    [Keep history]")


@pytest.mark.parametrize("earlier", [
    "# [Keep \\[history\\]](guide.md)",
    "# [Keep `_history_`](guide.md)",
    "# [Keep \\_history\\_](guide.md)",
], ids=["escaped-brackets", "code-span-underscores", "escaped-underscores"])
def test_followup_c2_earlier_heading_holding_a_link_is_refused(tmp_path, earlier):
    """Red (round 2 findings 4 and 6). An earlier heading written as a link, whatever its label
    holds, is refused naming prd.md and its line; its anchor is neither guessed nor invented."""
    prd = PRD.replace("## Commitments", f"{earlier}\n\nAn old note.\n\n## Commitments")
    feature(tmp_path, prd=prd)
    accept(tmp_path, "intent")
    names_line(refused(tmp_path, "design"), "prd.md", lines_of(prd, earlier))


def test_followup_c2_shortcut_reference_definition_is_refused(tmp_path):
    """Red (round 2 finding 5). A definition outside the section turns ``[keep]`` inside the
    choice into a shortcut reference link; the definition line is refused with its file and
    line, so the hidden link cannot pass silently."""
    design = DESIGN.replace(
        "# Design choices", "[keep]: ../prd.md#keep-history\n\n# Design choices",
    ).replace(
        "A log of snapshot dates serves [Keep history](../prd.md#keep-history).",
        "A log of snapshot dates serves [Keep history](../prd.md#keep-history), see [keep].",
    )
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    names_line(refused(tmp_path, "design"), "design/storage.md", lines_of(design, "[keep]:"))


def test_followup_c2_thematic_break_after_a_quote_is_refused_as_a_break(tmp_path):
    """Red (round 2 finding 7). ``---`` right after a quote line is a thematic break, which the
    ruling refuses inside a section; the refusal names its line with a remedy other than the
    quote-continuation one."""
    design = only_link("A log of dates.\n\n> Example\n---\n[Keep history](../prd.md#keep-history)")
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    message = refused(tmp_path, "design")
    line = lines_of(design, "---")[-1]
    names_line(message, "design/storage.md", [line])
    at_break = [m for m in message.splitlines() if re.search(rf"design/storage\.md\D{{0,12}}{line}\b", m)]
    assert at_break and not any(re.search(QUOTE_CONTINUATION, m) for m in at_break), message


@pytest.mark.parametrize("replacement", [
    "A log of snapshot dates.\n\n> Example\n>\nIt serves [Keep history](../prd.md#keep-history).",
    "A log of snapshot dates.\n\n> Example\n- It serves [Keep history](../prd.md#keep-history).",
], ids=["paragraph-after-bare-marker", "list-item-after-quote-text"])
def test_followup_c2_block_after_a_quote_is_accepted(tmp_path, replacement):
    """Guard (round 2 finding 7). A paragraph after a bare ``>`` line, and a list item right
    after a quote text line, are outside the quote; the unit closes."""
    design = DESIGN.replace("A log of snapshot dates serves [Keep history](../prd.md#keep-history).", replacement)
    close_all(tmp_path, designs={"storage.md": design})


@pytest.mark.parametrize("replacement", [
    "A log of snapshot dates:\n\n- Dated folders\n  - It serves [Keep history](../prd.md#keep-history).",
    "A log of snapshot dates:\n\n- Dated folders kept\n  so it serves [Keep history](../prd.md#keep-history).",
    "A log of snapshot dates:\n\n- Dated folders kept.\n\n  It serves [Keep history](../prd.md#keep-history).",
    "A log of snapshot dates:\n\n1. Dated folders kept.\n\n   It serves [Keep history](../prd.md#keep-history).",
], ids=["nested-item", "continuation", "continuation-after-blank", "numbered-continuation"])
def test_followup_c2_list_lines_at_the_content_column_are_accepted(tmp_path, replacement):
    """Guard (ruling). A nested item and continuation lines at exactly the open item's content
    column (two for ``- ``, three for ``1. ``) are plain shapes; the unit closes."""
    design = DESIGN.replace("A log of snapshot dates serves [Keep history](../prd.md#keep-history).", replacement)
    close_all(tmp_path, designs={"storage.md": design})


@pytest.mark.parametrize("indent", [" ", "   ", "    "], ids=["one", "three", "four"])
def test_followup_c2_list_continuation_off_the_content_column_is_refused(tmp_path, indent):
    """Red (ruling). A continuation of ``- item`` indented other than two spaces is refused with
    the file, line and item."""
    refused_in_item(tmp_path, only_link(
        f"A log of dates:\n\n- Dated folders kept\n{indent}so it serves [Keep history](../prd.md#keep-history)"),
        "so it serves")


def test_followup_c2_leading_tab_is_refused(tmp_path):
    """Red (ruling). A line starting with a tab inside a section is refused with the file, line
    and item."""
    refused_in_item(tmp_path, only_link("A log of dates\n\tserves [Keep history](../prd.md#keep-history)."),
                    "\tserves")


@pytest.mark.parametrize("underline", ["===", "***", "___"])
def test_followup_c2_underline_or_break_inside_an_item_is_refused(tmp_path, underline):
    """Red (ruling). A setext underline or thematic break inside an item is refused with the
    file, line and item."""
    refused_in_item(tmp_path, only_link(
        f"A log of dates serves [Keep history](../prd.md#keep-history).\n{underline}"), underline)


@pytest.mark.parametrize("where", ["before", "after"])
def test_followup_c2_reference_definition_anywhere_is_refused(tmp_path, where):
    """Red (ruling). A reference-link definition is refused with its file and line wherever it
    sits in a document with a traceability section, not only inside an item."""
    definition = "[vendor]: https://example.com/restic"
    design = (DESIGN.replace("# Design choices", f"{definition}\n\n# Design choices") if where == "before"
              else DESIGN.replace("Free-form notes after the section.", f"Free-form notes.\n\n{definition}"))
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    names_line(refused(tmp_path, "design"), "design/storage.md", lines_of(design, definition))


@pytest.mark.parametrize("heading", ["# Notes on [restic](https://example.com/restic)",
                                     "# See [the guide][guide]"], ids=["inline", "reference"])
def test_followup_c2_heading_with_a_link_anywhere_is_refused(tmp_path, heading):
    """Red (ruling). A heading holding link syntax outside any traceability section is refused
    with its file and line, because heading anchors are computed document-wide."""
    design = DESIGN.replace("# Notes", heading)
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    names_line(refused(tmp_path, "design"), "design/storage.md", lines_of(design, heading))



# --- Follow-up group C, review round 3 -------------------------------------------------------
#
# Lead clarifications (2026-10-24): a list continuation holds ordinary text only; only a
# numbered item starting at 1 may follow paragraph or quote text without a blank line; a
# reference definition inside a quote or list item is refused anywhere in the document; a
# heading link label holding balanced brackets is link syntax; the section heading itself must
# start at column 0.

NESTED = "A log of dates:\n\n- Parent\n  - Child\n"


@pytest.mark.parametrize("block,marker", [
    ("    > Example\n    [Keep history](../prd.md#keep-history)", "> Example"),
    ("    ## Example\n    [Keep history](../prd.md#keep-history)", "## Example"),
    ("\n    ***\n    [Keep history](../prd.md#keep-history)", "***"),
    ("    ```\n    [Keep history](../prd.md#keep-history)\n    ```", "```"),
], ids=["quote", "heading", "thematic-break", "fence"])
def test_followup_c3_block_start_in_a_nested_list_continuation_is_refused(tmp_path, block, marker):
    """Red (round 3 finding 1). A quote, heading, thematic break or fence at a nested item's
    content column is not ordinary continuation text; it is refused with the file, line and
    item instead of crediting the link after it."""
    refused_in_item(tmp_path, only_link(NESTED + block), marker)


@pytest.mark.parametrize("replacement", [
    NESTED + "    continues and serves [Keep history](../prd.md#keep-history).",
    "A log of dates:\n\n" + "".join(f"{n}. Step {n}.\n" for n in range(1, 10))
    + "10. It serves [Keep history](../prd.md#keep-history)\n    on the tenth step.",
], ids=["nested-continuation", "numbered-to-ten"])
def test_followup_c3_plain_nested_continuation_and_double_digit_list_are_accepted(tmp_path, replacement):
    """Guard (round 3 finding 1). Plain text at a nested item's content column, and a list
    numbered 1 to 10 with a continuation at the tenth item's content column, close."""
    design = DESIGN.replace("A log of snapshot dates serves [Keep history](../prd.md#keep-history).", replacement)
    close_all(tmp_path, designs={"storage.md": design})


@pytest.mark.parametrize("replacement,marker", [
    ("A log of dates.\n\n> Example\n10. [Keep history](../prd.md#keep-history)", "10. [Keep"),
    ("Example sequence\n10. Preserve history\n\n    [Keep history](../prd.md#keep-history)", "10. Preserve"),
], ids=["after-quote", "after-paragraph"])
def test_followup_c3_numbered_line_not_starting_at_one_after_text_is_refused(tmp_path, replacement, marker):
    """Red (round 3 finding 2). A numbered line other than 1 right after quote or paragraph
    text continues that text in Markdown; it is refused with the file, line and item."""
    refused_in_item(tmp_path, only_link(replacement), marker, "    [Keep history]")


@pytest.mark.parametrize("replacement", [
    "A log of dates:\n1. It serves [Keep history](../prd.md#keep-history).",
    "A log of dates:\n\n10. It serves [Keep history](../prd.md#keep-history).",
    "A log of dates:\n\n" + "".join(f"{n}. Step {n}.\n" for n in range(1, 10))
    + "10. It serves [Keep history](../prd.md#keep-history).",
], ids=["one-after-text", "ten-after-blank", "ten-inside-a-list"])
def test_followup_c3_numbered_items_that_open_or_continue_a_list_are_accepted(tmp_path, replacement):
    """Guard (round 3 finding 2). ``1.`` right after paragraph text, ``10.`` after a blank
    line, and ``10.`` inside a list numbered from 1 all close."""
    design = DESIGN.replace("A log of snapshot dates serves [Keep history](../prd.md#keep-history).", replacement)
    close_all(tmp_path, designs={"storage.md": design})


@pytest.mark.parametrize("where,definition", [
    ("notes", "> [parent-choice]: ../prd.md#keep-history"),
    ("notes", "- [x]: https://example.com/restic"),
    ("item", "> [parent-choice]: ../prd.md#keep-history"),
], ids=["quote-in-notes", "list-item-in-notes", "quote-in-item"])
def test_followup_c3_reference_definition_inside_a_container_is_refused(tmp_path, where, definition):
    """Red (round 3 finding 3). A reference definition inside a quote or list item still
    defines a label for the whole document; it is refused with its file and line wherever it
    sits."""
    if where == "notes":
        design = DESIGN.replace("Free-form notes after the section.", f"Free-form notes.\n\n{definition}")
    else:
        design = DESIGN.replace("One folder per day, named by date.",
                                f"One folder per day, named by date.\n\n{definition}")
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    names_line(refused(tmp_path, "design"), "design/storage.md", lines_of(design, definition))


def test_followup_c3_heading_link_with_balanced_brackets_in_its_label_is_refused(tmp_path):
    """Red (round 3 finding 4). ``# [Restore [beta]](guide.md)`` is a link heading; it is refused
    naming prd.md and its line."""
    heading = "# [Restore [beta]](guide.md)"
    prd = PRD.replace("## Commitments", f"{heading}\n\nAn old note.\n\n## Commitments")
    feature(tmp_path, prd=prd)
    accept(tmp_path, "intent")
    names_line(refused(tmp_path, "design"), "prd.md", lines_of(prd, heading))


def test_followup_c3_indented_section_heading_is_refused(tmp_path):
    """Red (round 3 finding 5). `` # Design choices`` indented one space is refused naming the
    design file and its line; the section heading must start at column 0."""
    design = DESIGN.replace("# Design choices", " # Design choices")
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    names_line(refused(tmp_path, "design"), "design/storage.md", lines_of(design, " # Design choices"))


# --- Follow-up group C, review round 4 (logged follow-ups) -----------------------------------


@pytest.mark.xfail(strict=True, reason="Follow-up: A list item with extra spaces after its marker hides a later section")
def test_followup_c4_list_item_with_extra_marker_spaces_does_not_hide_the_section(tmp_path):
    """Round 4 major 1. ``-  Example`` has content at column 3, so the fence under it belongs to
    the item and ends with it. The second design file is refused by name, for the fence or for
    its unlinked choice, instead of losing its section."""
    second = "-  Example\n\n   ~~~\n   sample\n\n# Design choices\n## Unlinked\nNo link.\n"
    feature(tmp_path, designs={"storage.md": DESIGN, "scheduling.md": second})
    accept(tmp_path, "intent")
    names_all(refused(tmp_path, "design"), "design/scheduling.md")


@pytest.mark.xfail(strict=True, reason="Follow-up: A nested numbered item not starting at 1 hides an indented link")
def test_followup_c4_nested_numbered_item_not_starting_at_one_is_refused(tmp_path):
    """Round 4 major 2. A nested ``10.`` cannot interrupt the item's paragraph, so the six-space
    link after it renders as code; design close refuses, naming the file and line."""
    design = only_link(
        "A log of dates:\n\n- Recovery procedure\n  10. Restore backups\n\n      [Keep history](../prd.md#keep-history)")
    feature(tmp_path, designs={"storage.md": design})
    accept(tmp_path, "intent")
    names_line(refused(tmp_path, "design"), "design/storage.md",
               lines_of(design, "10. Restore backups", "      [Keep history]"))


@pytest.mark.xfail(strict=True, reason="Follow-up: A reference definition with a wrapped label escapes the definition check")
def test_followup_c4_reference_definition_with_a_wrapped_label_is_refused(tmp_path):
    """Round 4 major 3. A definition whose label wraps onto a second line still defines
    ``[Parent recovery choice]`` for the whole document; spec close refuses it, naming spec.md
    and the line."""
    spec = SPEC.replace(
        "## Requirements",
        "[Parent recovery\nchoice]: design/storage.md#snapshot-store\n\n## Requirements",
    ).replace(
        "from [Snapshot store](design/storage.md#snapshot-store).",
        "from [Snapshot store](design/storage.md#snapshot-store) and [Parent recovery choice].",
    )
    accepted_through_design(tmp_path, spec=spec)
    second = lines_of(spec, "choice]:")
    names_line(refused(tmp_path, "spec"), "spec.md", second + [n - 1 for n in second])

# --- guides and glossary ---------------------------------------------------------------------


def guide(name):
    return (ROOT_DOCS / "assets/fbk-docs/workflow" / name).read_text()


def test_glossary_defines_commitment_design_choice_and_requirement():
    """Red. GLOSSARY.md has an entry for each new term."""
    text = (ROOT_DOCS / "GLOSSARY.md").read_text()
    missing = [term for term in ("commitment", "design choice", "requirement")
               if not re.search(rf"^### {term}\b", text, re.M | re.I)]
    assert not missing, f"GLOSSARY.md has no entry for {missing}."


def test_intent_guide_states_the_commitments_section_and_the_out_of_scope_note():
    """Red. The intent guide names the Commitments section and says a commitment deliberately
    out of scope is removed or moved to an out-of-scope note."""
    text = guide("intent.md")
    assert "Commitments" in text, "The intent guide does not name the Commitments section."
    assert re.search(r"out[- ]of[- ]scope", text, re.I), "The intent guide has no out-of-scope note."


def test_design_guide_states_the_section_and_the_link_rule():
    """Red. The design guide names the Design choices section and says each links commitments
    through heading anchors."""
    text = guide("design.md")
    assert "Design choices" in text, "The design guide does not name the Design choices section."
    assert re.search(r"commitment", text, re.I) and re.search(r"anchor", text, re.I), (
        "The design guide does not state that design choices link commitments by anchor.")


def test_spec_guide_states_the_section_and_the_link_rule():
    """Red. The spec guide names the Requirements section and says requirements link design
    choices, or commitments without design, through heading anchors."""
    text = guide("spec.md")
    assert "Requirements" in text, "The spec guide does not name the Requirements section."
    assert re.search(r"design choice", text, re.I) and re.search(r"anchor", text, re.I), (
        "The spec guide does not state that requirements link design choices by anchor.")


def test_architecture_overview_describes_the_traceability_sections():
    """Red. The architecture overview names the three sections."""
    text = (ROOT_DOCS / "docs/architecture-overview.md").read_text()
    missing = [s for s in ("Commitments", "Design choices", "Requirements") if s not in text]
    assert not missing, f"The architecture overview does not name {missing}."
