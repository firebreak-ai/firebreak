"""Traceability sections and their links: prd.md's Commitments, each design file's Design
choices, and spec.md's Requirements. Items are the headings one level below a section; they
link upstream items with ordinary Markdown links to heading anchors. Design and spec close
check those links and coverage in both directions. Tasks link requirements through anchored
acceptance_refs entries; breakdown close checks that coverage, and each task's context carries
the chain from its requirements to their design choices and commitments.

A requirement is behavioral by default. One whose first line under its heading is
``Checked by review: <reason>`` is review-only: breakdown needs no test task for it, and the
implementation review assesses it instead.

Firebreak reads a defined subset of Markdown and refuses what it cannot read. Inside a
traceability section only plain line shapes are accepted: blank lines, headings, paragraph
lines, list items and their continuations at the item's text column, quotes marked line by
line, and fenced blocks, all starting at column 0 unless nested in a list. Anywhere in such a
document, a heading holding a link and a reference-link definition are refused."""

import os
import re
from pathlib import Path
from urllib.parse import unquote

from . import evidence
from .store import WorkflowError, confined, load, unit_dir

COMMITMENTS, DESIGN_CHOICES, REQUIREMENTS = "Commitments", "Design choices", "Requirements"
# Each section's items and how a refusal names one of them and its plural.
_KINDS = {
    COMMITMENTS: ("commitment", "commitments"),
    DESIGN_CHOICES: ("design choice", "design choices"),
    REQUIREMENTS: ("requirement", "requirements"),
}
_HEADING = re.compile(r" {0,3}(#{1,6})(?:[ \t]+(.*))?")
_FENCE = re.compile(r" {0,3}(`{3,}|~{3,})(.*)")
# A fence run anywhere else on a line: after a list or blockquote marker, or indented as code.
_PREFIXED_FENCE = re.compile(r"(?: {4,}|[ \t]*(?:(?:>|[-*+]|\d{1,9}[.)])[ \t]*)+)(?:`{3}|~{3})")
_QUOTE = re.compile(r" {0,3}>")
_SETEXT = re.compile(r" {0,3}(?:=+|-+)[ \t]*")
_BREAK = re.compile(r" {0,3}(?:(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,})")
_LIST = re.compile(r" {0,3}(?:[-*+]|\d{1,9}[.)])(?:[ \t]|$)")
# A plain list item: its marker, one space, then text; group 1 is the text.
_ITEM = re.compile(r"(?:[-*+]|\d{1,9}[.)]) (\S.*)")
# A reference definition, also inside a quote or list item, where it still defines a label.
_DEFINITION = re.compile(r"[ \t]*(?:(?:>|[-*+]|\d{1,9}[.)])[ \t]*)*\[[^\]]+\]:")
_CODE_SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")
_HTML = re.compile(r"<[A-Za-z/!?]")
# The bracket forms an item's text may hold: an inline link or image on one line, its
# destination free of spaces and angle brackets with at most one level of balanced
# parentheses, and plain bracketed text that is not followed by a link's ( [ or :.
_DESTINATION = r"(?:[^\s()<>]|\([^\s()<>]*\))+"
_LINK = re.compile(rf"(!?)\[[^\[\]]*\]\(({_DESTINATION})\)")
_BRACKETED = re.compile(r"\[[^\[\]]*\](?![(\[:])")
_MARKUP = re.compile(r"[`*\[\]<>]|(?<!\w)_|_(?!\w)")
HEADING_REMEDY = "write headings with #, not a line of - or = under the text"
PLAIN_REMEDY = "write item names in plain text"
SECTION_REMEDY = "write the section heading as its plain name"
LINK_REMEDY = "write links as [name](path#anchor) on one line"
HEADING_LINK_REMEDY = "write headings in plain text, without links"
DEFINITION_REMEDY = "write links inline as [name](path#anchor), with no reference definitions"
CODE_REMEDY = "open and close inline code on one line"
HTML_REMEDY = "write plain Markdown; no HTML or comments"
FENCE_REMEDY = "start fenced blocks at the beginning of a line, outside lists and quotes"
QUOTE_REMEDY = "leave a blank line after a blockquote, or mark each of its lines with >"
QUOTE_SHAPE_REMEDY = "write a quote at the beginning of a line as > and plain text"
TAB_REMEDY = "indent with spaces, not tabs"
INDENT_REMEDY = "start the line at the beginning, or indent it with spaces to where its list item's text starts"
LIST_REMEDY = (
    "write a list item as a -, *, + or number marker, one space and plain text, and its continuation "
    "lines as plain text"
)
NUMBER_REMEDY = "start a list right after text at 1, or leave a blank line before it"
BREAK_REMEDY = "leave out horizontal rules and underlines; write headings with #"
BACKTICK_REMEDY = "write literal backticks inside inline code or a fenced block"
MARKER = "Checked by review:"
MARKER_REMEDY = (
    f"write {MARKER} <reason> only as the first line under the requirement's heading, unindented "
    "and with a reason"
)


def anchor(heading):
    """The anchor a heading answers to: lowercase, characters other than word characters,
    spaces and hyphens dropped, spaces turned into hyphens. Duplicates are not numbered."""
    return re.sub(r"[^\w -]", "", heading.lower()).replace(" ", "-")


def _anchors(heading):
    """The anchors a heading may answer to: as written, and with emphasis and code marks
    removed, as renderers do."""
    return {anchor(heading), anchor(re.sub(r"[*`]|(?<!\w)_+|_+(?!\w)", "", heading))}


def _plain(text):
    """Whether text after a quote or list marker is ordinary text, starting no other block."""
    return not (_LIST.match(text) or _HEADING.fullmatch(text) or _FENCE.match(text)
                or text.startswith(">") or _BREAK.fullmatch(text))


def _split(content):
    """A document's lines, broken only at Markdown line endings: other characters that Python
    treats as line breaks, such as a vertical tab, stay inside their line."""
    return re.split(r"\r\n|\r|\n", re.sub(r"(?:\r\n|\r|\n)\Z", "", content)) if content else []


def _classify(content):
    """Each line as (kind, value), and each line's remedy when it is not a plain shape, or None.
    Kinds: ``fence`` for fence lines and fenced content, ``quote`` for blockquote lines,
    ``heading`` with (level, text), ``setext`` for an underline under text, ``prefixed`` for a
    fence opener after a list or quote marker, indented as code, or indented under a list item,
    and ``text`` for everything else. Every kind but ``fence`` keeps its raw line last.

    Plain shapes, judged with the open list items' text columns: a blank line; a heading,
    paragraph line, quote or fence at column 0; a list item at column 0 or at an open item's
    text column; a continuation line at an open item's text column; a quote line that is ``>``
    alone or ``>``, a space and ordinary text; after quoted text, only a blank line, a heading
    or a list item. Continuation lines hold ordinary text, and right after paragraph or quoted
    text a numbered item starts at 1. Leading tabs, other indentation, underlines and horizontal
    rules are not plain."""
    lines, shapes, fence, columns, quoted, paragraph = [], [], None, [], False, False
    for line in _split(content):
        spaced = line.expandtabs(4)
        indent = len(spaced) - len(spaced.lstrip(" "))
        if fence:
            closing = re.fullmatch(rf" {{0,3}}{re.escape(fence[0])}{{{len(fence)},}}[ \t]*", spaced)
            fence = None if closing else fence
            lines.append(("fence", None))
            shapes.append(FENCE_REMEDY if closing and indent else None)
            continue
        shape, after_quote, after_paragraph, quoted, paragraph = None, quoted, paragraph, False, False
        if not line.strip():
            kind = "text"
        elif (opening := _FENCE.fullmatch(spaced)) and not (opening[1][0] == "`" and "`" in opening[2]):
            # Indented to an open list item's text, the fence belongs to the item and ends with it.
            if indent and columns and indent >= columns[0]:
                kind = "prefixed"
            else:
                kind, fence, columns, shape = "fence", opening[1], [], FENCE_REMEDY if indent else None
        elif _PREFIXED_FENCE.match(spaced):
            kind = "prefixed"
        elif "\t" in line[:len(line) - len(line.lstrip())]:
            kind, shape = "text", TAB_REMEDY
        elif _QUOTE.match(line):
            kind, columns = "quote", []
            rest = line.lstrip()[1:]
            quoted = bool(rest.strip())
            if indent or quoted and not (rest.startswith(" ") and _plain(rest[1:])):
                shape = QUOTE_SHAPE_REMEDY
        elif heading := _HEADING.fullmatch(line):
            kind, shape = "heading", INDENT_REMEDY if indent else None
            if not indent:
                columns = []
        elif _SETEXT.fullmatch(line) and lines and lines[-1][0] == "text" and lines[-1][1].strip() \
                and not _LIST.match(lines[-1][1]):
            kind = "setext"
        else:
            kind = "text"
            rest = spaced[indent:]
            item = _ITEM.fullmatch(rest)
            if _BREAK.fullmatch(line) or _SETEXT.fullmatch(line):
                shape = BREAK_REMEDY
            elif item and (after_quote or after_paragraph) and rest[0].isdigit() and not re.match(r"1[.)]", rest):
                shape = NUMBER_REMEDY
            elif after_quote and not item:
                shape = QUOTE_REMEDY
            elif indent and indent not in columns:
                shape = INDENT_REMEDY
            elif not (item and _plain(item[1])) and (_LIST.match(rest) or not _plain(rest)):
                shape = LIST_REMEDY
            else:
                columns = columns[:columns.index(indent) + 1] if indent else []
                if item:
                    columns.append(indent + len(rest) - len(item[1]))
                paragraph = not item and not indent
        if kind == "heading":
            # Closing #s are stripped only after a space; a bare # line is an empty heading.
            text = re.sub(r"(?:^|[ \t]+)#+$", "", (heading[2] or "").strip()).strip()
            lines.append(("heading", (len(heading[1]), text, line)))
        else:
            lines.append((kind, None if kind == "fence" else line))
        shapes.append(shape)
    return lines, shapes


def headings(content):
    """ATX headings outside fenced code and blockquotes, as (line number, level, text)."""
    return [(n, *value[:2]) for n, (kind, value) in enumerate(_classify(content)[0]) if kind == "heading"]


def resolve(document, target):
    """The repository path a link target names, relative to the linking document's folder;
    the document itself for a bare fragment, None for a URL or an absolute path."""
    path = unquote(target.split("#", 1)[0])
    if not path:
        return document
    if ":" in path or path.startswith("/"):
        return None
    return os.path.normpath(str(Path(document).parent / path))


def _uncoded(line):
    """A line with its one-line code spans blanked out."""
    return _CODE_SPAN.sub(lambda m: " " * len(m[0]), line)


def _item_line(line):
    """The link targets on one line of an item's text and the remedy for anything outside the
    subset there. Only known forms are accepted: code spans, escaped brackets, inline links,
    images (which never count as links), and plain bracketed text; any other backtick or
    bracket is refused."""
    if "\\`" in line:
        return [], BACKTICK_REMEDY
    text = _uncoded(line)
    if "`" in text:
        return [], CODE_REMEDY
    text = re.sub(r"\\[\[\]]", "", text)
    # A reference link may be followed by text that reads as an inline link's destination;
    # brackets inside a destination are not link syntax.
    if "][" in _LINK.sub(lambda m: m[0][:m[0].index("](") + 2] + ")", text):
        return [], LINK_REMEDY
    links = [target for image, target in _LINK.findall(text) if not image]
    if re.search(r"[\[\]]", _BRACKETED.sub("", _LINK.sub("", text))):
        return [], LINK_REMEDY
    return links, None


def parse(content, section):
    """A document's headings by anchor, how many times ``section`` appears, the items of its
    first appearance, and the lines outside the Markdown subset as (line, where, remedy), where
    names the item or section holding a line inside the section and is empty otherwise. Each item
    carries its link targets and its own refused lines; each heading inside the section records
    whether it is the section heading, an item, or part of an item. A Requirements item also
    carries ``review``, its review-only reason or None; a marker line anywhere else in the item,
    or one with no reason, is refused as one of its lines."""
    lines, shapes = _classify(content)
    found = [(n, *value[:2]) for n, (kind, value) in enumerate(lines) if kind == "heading"]
    unreadable = []
    for number, (kind, value) in enumerate(lines):
        raw = value[2] if kind == "heading" else value
        if kind == "setext":
            unreadable.append((number, HEADING_REMEDY))
        elif kind == "prefixed":
            unreadable.append((number, FENCE_REMEDY))
        elif raw is not None and _HTML.search(_uncoded(raw)):
            unreadable.append((number, HTML_REMEDY))
    anchors = {}
    for index, (_, _, title) in enumerate(found):
        for each in _anchors(title):
            anchors.setdefault(each, []).append(index)
    starts = [i for i, (_, _, title) in enumerate(found) if title == section]
    unreadable += [
        (number, SECTION_REMEDY) for number, _, title in found
        if _MARKUP.search(title) and section.lower() in re.sub(r"[*_`\[\]<>]", "", title).lower()
    ]
    items, roles, region = [], {}, range(0)
    if starts:
        # Heading anchors are document-wide, and a definition changes what bracketed text means.
        for number, (kind, value) in enumerate(lines):
            if kind == "heading" and re.search(r"\[.*\][(\[]", re.sub(r"\\[\[\]]", "", _uncoded(value[1]))):
                unreadable.append((number, HEADING_LINK_REMEDY))
            elif kind in ("text", "quote") and _DEFINITION.match(value):
                unreadable.append((number, DEFINITION_REMEDY))
        level = found[starts[0]][1]
        roles[anchor(section)] = ("section", None)
        end = next((i for i in range(starts[0] + 1, len(found)) if found[i][1] <= level), len(found))
        for number, depth, title in found[starts[0] + 1:end]:
            if depth == level + 1:
                items.append({"name": title, "anchor": anchor(title), "line": number,
                              "links": [], "unreadable": [],
                              **({"review": None} if section == REQUIREMENTS else {})})
                roles[anchor(title)] = ("item", None)
                if _MARKUP.search(title):
                    unreadable.append((number, PLAIN_REMEDY))
            else:
                roles.setdefault(anchor(title), ("inside", items[-1]["name"] if items else None))
        last = found[end][0] if end < len(found) else len(lines)
        region = range(found[starts[0]][0], last)
        unreadable += [(number, shapes[number]) for number in region if shapes[number]]
        stops = [item["line"] for item in items[1:]] + [last]
        raw = _split(content)
        for item, stop in zip(items, stops, strict=False):  # with no items, stops still holds the section end
            # The item's own section: its heading up to the next item or the section's end.
            item["text"] = "\n".join(raw[item["line"]:stop]).strip()
            first = True
            for number in range(item["line"] + 1, stop):
                kind, value = lines[number]
                if kind in ("text", "heading"):
                    links, remedy = _item_line(value if kind == "text" else value[1])
                    item["links"] += links
                    if remedy:
                        item["unreadable"].append((number + 1, remedy))
                if section == REQUIREMENTS:
                    if kind == "text" and value.strip().startswith(MARKER):
                        reason = value.strip()[len(MARKER):].strip()
                        # The marker starts its line; an indented one may be a code example.
                        if first and reason and value.startswith(MARKER + " "):
                            item["review"] = reason
                        else:
                            item["unreadable"].append((number + 1, MARKER_REMEDY))
                    if kind != "text" or value.strip():
                        first = False
    kind = _KINDS[section][0]

    def where(number):
        owner = next((i for i in reversed(items) if i["line"] <= number), None)
        if number not in region:
            return ""
        return f', {kind} "{owner["name"]}"' if owner else f", in the {section} section"

    return {
        "anchors": anchors, "sections": len(starts), "items": items, "roles": roles,
        "unreadable": sorted({(number + 1, where(number), remedy) for number, remedy in unreadable}),
    }


def _read(root, path):
    try:
        return confined(root, path).read_text()
    except (OSError, UnicodeError) as exc:
        raise WorkflowError(f"Cannot read {path} for the traceability check: {exc}") from exc


def _documents(root, record):
    """A unit's traceability documents by phase; design files only when the unit has design."""
    base = unit_dir(root, record["unit"]).relative_to(root).as_posix()
    designs = (
        [p for p in evidence.expand(root, [f"{base}/design"]) if p.endswith(".md")]
        if record["design"] else []
    )
    return {"intent": [f"{base}/prd.md"], "design": designs, "spec": [f"{base}/spec.md"]}


def check(root, record, phase):
    """At design or spec close, refuse naming every failing item: each design choice (or
    requirement) links only to items of the correct upstream section and to at least one, and
    every item of the unit's own upstream section is linked. A child's links to its parent's
    accepted items count; coverage is required only for the unit's own items. The unit's own
    documents read at this close are refused where they leave the Markdown subset."""
    own = _documents(root, record)
    units = [own, _documents(root, load(root, record["parent"]))] if record["parent"] else [own]
    source = DESIGN_CHOICES if phase == "design" else REQUIREMENTS
    target = DESIGN_CHOICES if phase == "spec" and record["design"] else COMMITMENTS
    target_phase = "design" if target == DESIGN_CHOICES else "intent"
    # Links into any upstream document, own or the parent's, are traceability links.
    sections = {"intent": COMMITMENTS, "design": DESIGN_CHOICES}
    if phase == "design":
        del sections["design"]
    upstream = {}
    for documents in units:
        for p, section in sections.items():
            for path in documents[p]:
                upstream[path] = (section, parse(_read(root, path), section))
    required = {own["intent"][0]} if target == COMMITMENTS else set()
    problems = []
    for p in sections:
        for path in own[p]:
            problems += [f"{path} line {n}{at}: {remedy}." for n, at, remedy in upstream[path][1]["unreadable"]]
    for path in own[target_phase]:
        _section_problems(path, target, upstream[path][1], path in required, problems)
    if target == DESIGN_CHOICES and not any(upstream[path][1]["sections"] for path in own["design"]):
        problems.append(
            f"No design file of unit {record['unit']} has a Design choices section, so its "
            "requirements have no design choice to link; add the section and its items to the design."
        )
    kind, kinds = _KINDS[source]
    target_kind = _KINDS[target][0]
    covered = set()
    for path in own[phase]:
        document = parse(_read(root, path), source)
        problems += [f"{path} line {n}{at}: {remedy}." for n, at, remedy in document["unreadable"]]
        _section_problems(path, source, document, phase == "spec", problems)
        for item in document["items"]:
            name, linked = item["name"], False
            problems += [f'{path} line {n}, {kind} "{name}": {remedy}.' for n, remedy in item["unreadable"]]
            for link in item["links"]:
                landing = resolve(path, link)
                if landing not in upstream:
                    continue
                reason = _landing(link, landing, *upstream[landing], target, kinds)
                if reason:
                    problems.append(f'{path}, {kind} "{name}": {reason}')
                else:
                    linked = True
                    covered.add((landing, unquote(link.split("#", 1)[1])))
            if not linked:
                problems.append(f'{path}, {kind} "{name}" links to no {target_kind}.')
    for path in own[target_phase]:
        for item in upstream[path][1]["items"]:
            if (path, item["anchor"]) not in covered:
                problems.append(f'{path}, {target_kind} "{item["name"]}": no {kind} links to it.')
    if problems:
        raise WorkflowError(
            f"Unit {record['unit']}: {phase} close needs every {kind} to link a {target_kind} and "
            f"every {target_kind} to be linked by a {kind}. Fix each item below, then close again:\n"
            + "\n".join(f"- {p}" for p in problems)
        )


def _section_problems(path, section, document, required, problems):
    if document["sections"] > 1:
        problems.append(f"{path} has the {section} section more than once; keep one.")
    elif required and not document["sections"]:
        problems.append(f"{path} has no {section} section; add it with at least one item.")
    elif required and not document["items"]:
        problems.append(f"{path} has an empty {section} section; give it at least one item.")


def _landing(link, path, section, document, target, kinds):
    """Why a traceability link fails, or None when it lands on an item of ``target``."""
    if "#" not in link:
        return f"link {link} names the whole document; link the anchor of one item instead."
    fragment = unquote(link.split("#", 1)[1])
    titles = document["anchors"].get(fragment, [])
    if not titles:
        return f"link {link} names no heading anchor in {path}."
    if len(titles) > 1:
        return (f"link {link} is ambiguous: more than one heading in {path} produces the anchor "
                f"{fragment}; give each heading a unique name.")
    if section != target:
        return f"link {link} lands outside the {target} section; {kinds} link {_KINDS[target][1]}."
    role, owner = document["roles"].get(fragment, (None, None))
    if role == "section":
        return f"link {link} lands on the {section} section heading, not on an item."
    if role == "inside":
        where = f'the item "{owner}"' if owner else f"the {section} section"
        return f"link {link} lands on a heading inside {where}, not on an item."
    if role != "item":
        return f"link {link} lands outside the {section} section of {path}."
    return None


def _lineage(root, record):
    """The unit and its ancestors, nearest first."""
    units = [record]
    while units[-1].get("parent"):
        units.append(load(root, units[-1]["parent"]))
    return units


def requirement_specs(root, record):
    """The spec.md files a task may link requirements in: the unit's own, then its parent's,
    each with whether its unit has design."""
    units = _lineage(root, record)[:2]
    return {_documents(root, unit)["spec"][0]: unit["design"] for unit in units}


def spec_entry(ref, specs):
    """The spec path, line and fragment of an anchored entry into one of ``specs``, or None
    for any other entry. A line is written as ``path:N`` before the fragment."""
    path, _, fragment = ref.partition("#")
    line = None
    if ":" in path and path.rsplit(":", 1)[-1].isdigit():
        path, line = path.rsplit(":", 1)
    path = os.path.normpath(path)
    if "#" not in ref or path not in specs:
        return None
    return path, line, fragment


def requirement_links(root, record, refs):
    """The anchored entries of ``refs`` into the unit's own or its parent's spec.md, as
    (spec path, requirement item), and each such entry that misses a requirement as
    (entry, reason). Fragments are percent-decoded; an entry naming a line as well as an
    anchor is refused. Other entries are not requirement links."""
    specs = {path: parse(_read(root, path), REQUIREMENTS) for path in requirement_specs(root, record)}
    links, problems = [], []
    for ref in refs:
        found = spec_entry(ref, specs)
        if not found:
            continue
        path, line, fragment = found
        if line is not None:
            problems.append((ref, f"link {ref} names both a line and an anchor; link the requirement by its anchor alone."))
            continue
        reason = _landing(ref, path, REQUIREMENTS, specs[path], REQUIREMENTS, _KINDS[REQUIREMENTS][1])
        if reason:
            problems.append((ref, reason))
        else:
            item = next(i for i in specs[path]["items"] if i["anchor"] == unquote(fragment))
            links.append((path, item))
    return links, problems


def task_coverage(root, record, tasks):
    """At breakdown close, refuse naming every problem: an anchored spec.md entry that misses a
    requirement, a task linking no requirement of its own unit, and a requirement of the unit
    that no implementation task, no test task, or neither links. A review-only requirement needs
    no test task; a test task may still link it. A child's links to its parent's requirements
    are checked but count toward neither rule."""
    own = _documents(root, record)["spec"][0]
    requirements = parse(_read(root, own), REQUIREMENTS)["items"]
    linked = {"implementation": set(), "tests": set()}
    problems = []
    for task in tasks:
        links, refused = requirement_links(root, record, task.get("acceptance_refs", []))
        problems += [f"Task {task['id']}: {reason}" for _, reason in refused]
        anchors = {item["anchor"] for path, item in links if path == own}
        if not anchors and not task.get("refactor"):
            problems.append(
                f"Task {task['id']} links no requirement of unit {record['unit']}; add an acceptance_refs "
                f"entry {own}#<anchor> for each requirement it serves."
            )
        # A refactor task needs no requirement link: its worker reads the accepted spec and
        # design whole. A link it does carry delivers nothing.
        if not task.get("refactor"):
            linked[task["stage"]] |= anchors
    for item in requirements:
        needed = (("implementation", "implementation task"),) + (() if item["review"] else (("tests", "test task"),))
        missing = [kind for stage, kind in needed if item["anchor"] not in linked[stage]]
        if missing:
            problems.append(f'{own}, requirement "{item["name"]}": no {" and no ".join(missing)} links it.')
    if problems:
        raise WorkflowError(
            f"Unit {record['unit']}: breakdown close needs every task to link a requirement of this unit "
            "and every requirement to be linked by an implementation task and, unless it is review-only, a "
            "test task. Fix each item below, then close again:\n" + "\n".join(f"- {p}" for p in problems)
        )


def review_only(root, record):
    """The review-only requirements of the unit's own spec.md, each as its reference, name and
    reason, in document order. Spec and implement close refuse a missing spec.md before any
    review, so a unit without one has nothing to assess."""
    own = f"{unit_dir(root, record['unit']).relative_to(root).as_posix()}/spec.md"
    if not confined(root, own).is_file():
        return []
    return [
        {"requirement": f"{own}#{item['anchor']}", "name": item["name"], "reason": item["review"]}
        for item in parse(_read(root, own), REQUIREMENTS)["items"] if item["review"]
    ]


def task_chain(root, record, task_id, refs):
    """The chain a task's context carries: the requirements its anchored entries link, in link
    order; the design choices those requirements link; and the commitments those design choices
    link, or that the requirements link directly in a unit without design. An item's links are
    followed into the upstream documents of its own unit and that unit's ancestors, never into a
    descendant's; other links are not followed. Each list keeps first appearance without
    duplicates. Also returns each requirement's whole-chain size and every document read. An
    entry that misses a requirement, or a followed link that misses an item of the correct
    section, is refused naming the task."""
    links, refused = requirement_links(root, record, refs)
    problems = [reason for _, reason in refused]
    units = _lineage(root, record)
    documents = [_documents(root, unit) for unit in units]
    bases = [unit_dir(root, unit["unit"]).relative_to(root).as_posix() for unit in units]
    owner = {}
    for index, phases in enumerate(documents):
        for paths in phases.values():
            for path in paths:
                owner.setdefault(path, index)
    parsed = {}

    def landed(path, item, kind, target):
        """The items of ``target`` that ``item``'s links in ``path`` land on, among the
        upstream documents of its own unit and that unit's ancestors."""
        sections = {"intent": COMMITMENTS}
        if target == DESIGN_CHOICES or kind == "requirement":
            sections["design"] = DESIGN_CHOICES
        eligible = {p: section for phases in documents[owner[path]:]
                    for phase, section in sections.items() for p in phases[phase]}
        # Where those documents live, so a link into one that no longer exists is refused, and
        # the design folders of the task unit's ancestors routed to skip design, whose design
        # files no longer count.
        places, skipped = [], {}
        for index, (unit, base) in enumerate(zip(units[owner[path]:], bases[owner[path]:], strict=True), owner[path]):
            places.append(f"{base}/prd.md")
            if "design" in sections and unit["design"]:
                places.append(f"{base}/design/")
            elif "design" in sections and index:
                skipped[f"{base}/design/"] = unit["unit"]
        # An item outside the Markdown subset may hide links, so none of its links are used.
        if item["unreadable"]:
            problems.extend(f'{path} line {n}, {kind} "{item["name"]}": {remedy}.' for n, remedy in item["unreadable"])
            return []
        found = []
        for link in item["links"]:
            landing = resolve(path, link)
            if landing not in eligible:
                ancestor = next((u for p, u in skipped.items()
                                 if landing and landing.endswith(".md") and landing.startswith(p)), None)
                if ancestor:
                    problems.append(
                        f'{path}, {kind} "{item["name"]}": link {link} names a design choice of unit '
                        f"{ancestor}, which is routed to skip design; link an item that still counts."
                    )
                elif landing and any(landing == p or p.endswith("/") and landing.startswith(p) for p in places) \
                        and not confined(root, landing).exists():
                    problems.append(f'{path}, {kind} "{item["name"]}": link {link} names {landing}, which does not exist.')
                continue
            section = eligible[landing]
            if landing not in parsed:
                try:
                    parsed[landing] = parse(_read(root, landing), section)
                except WorkflowError as exc:
                    problems.append(f'{path}, {kind} "{item["name"]}": link {link} cannot be followed. {exc}')
                    continue
                # A document outside the Markdown subset may hide items, so none of it is used.
                problems.extend(f"{landing} line {n}{at}: {remedy}." for n, at, remedy in parsed[landing]["unreadable"])
            if parsed[landing]["unreadable"]:
                continue
            reason = _landing(link, landing, section, parsed[landing], target, f"{kind}s")
            if reason:
                problems.append(f'{path}, {kind} "{item["name"]}": {reason}')
            else:
                fragment = unquote(link.split("#", 1)[1])
                found.append((landing, next(i for i in parsed[landing]["items"] if i["anchor"] == fragment)))
        return found

    for path in dict.fromkeys(path for path, _ in links):
        problems.extend(f"{path} line {n}{at}: {remedy}." for n, at, remedy in parse(_read(root, path), REQUIREMENTS)["unreadable"])
    chain = {"requirements": {}, "design_choices": {}, "commitments": {}}
    sizes = []
    for path, item in links:
        requirement = {"requirements": [(path, item)], "design_choices": [], "commitments": []}
        if units[owner[path]]["design"]:
            requirement["design_choices"] = landed(path, item, "requirement", DESIGN_CHOICES)
            for choice in requirement["design_choices"]:
                requirement["commitments"] += landed(*choice, "design choice", COMMITMENTS)
        else:
            requirement["commitments"] = landed(path, item, "requirement", COMMITMENTS)
        own = {}
        for kind, entries in requirement.items():
            for at, each in entries:
                ref = f"{at}#{each['anchor']}"
                entry = {"ref": ref, "name": each["name"], "text": each["text"]}
                chain[kind].setdefault(ref, entry)
                own.setdefault(ref, entry)
        sizes.append((f"{path}#{item['anchor']}", sum(len(e["text"]) for e in own.values())))
    if problems:
        raise WorkflowError(
            f"Task {task_id}: its traceability chain cannot be followed. Each anchored acceptance_refs entry "
            "into spec.md must land on a requirement, and each link the chain follows must land on an item "
            "of the correct section. Fix each below in its accepted document or the task, then launch again:\n"
            + "\n".join(f"- {p}" for p in dict.fromkeys(problems))
        )
    sources = sorted({path for path, _ in links} | set(parsed))
    return {kind: list(entries.values()) for kind, entries in chain.items()}, sizes, sources


def routing(root, record):
    """The lineage and design routes a task's chain is followed by: each unit from this one up
    through its ancestors, with whether it has design."""
    return [[unit["unit"], bool(unit["design"])] for unit in _lineage(root, record)]
