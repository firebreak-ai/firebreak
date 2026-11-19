"""The artifact hygiene scan reports every character a reviewer cannot see, and nothing else."""

import pytest
from fbk.workflow import artifact_hygiene as hygiene
from fbk.workflow import store


def write(root, name, data):
    path = root / name
    path.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    return name


@pytest.mark.parametrize(
    "char, codepoint, name",
    [
        ("\x00", "U+0000", "NULL"),
        ("\x07", "U+0007", "BELL"),
        ("\x0b", "U+000B", "LINE TABULATION"),
        ("\x0c", "U+000C", "FORM FEED"),
        ("\x1b", "U+001B", "ESCAPE"),
        ("\x1f", "U+001F", "INFORMATION SEPARATOR ONE"),
        ("\x7f", "U+007F", "DELETE"),
        ("", "U+0085", "NEXT LINE"),
        (" ", "U+2028", "LINE SEPARATOR"),
        (" ", "U+2029", "PARAGRAPH SEPARATOR"),
        ("\u0080", "U+0080", "CONTROL CHARACTER"),
        ("\u00a0", "U+00A0", "NO-BREAK SPACE"),
        ("\u2003", "U+2003", "EM SPACE"),
        ("\u3000", "U+3000", "IDEOGRAPHIC SPACE"),
        ("\u200b", "U+200B", "ZERO WIDTH SPACE"),
        ("\ufeff", "U+FEFF", "ZERO WIDTH NO-BREAK SPACE"),
        ("\u200f", "U+200F", "RIGHT-TO-LEFT MARK"),
    ],
)
def test_each_invisible_character_class_is_reported_by_codepoint_and_name(tmp_path, char, codepoint, name):
    # A NUL inside the binary probe marks the file binary; place it past the probe window.
    lead = "x" * (hygiene.BINARY_PROBE + 1) + "\n" if char == "\x00" else ""
    path = write(tmp_path, "spec.md", lead + "The escape " + char + " ends the record.\n")
    report = hygiene.scan_files(tmp_path, [path])
    assert report["outcome"] == "findings"
    assert report["total"] == 1
    assert report["findings"] == [
        {"path": path, "line": 2 if lead else 1, "column": 12, "codepoint": codepoint, "name": name}
    ]
    assert hygiene.describe(report["findings"][0]) == f"{path}:{2 if lead else 1}:12 {codepoint} {name}"


def test_tab_newline_and_carriage_return_are_allowed_and_crlf_files_are_clean(tmp_path):
    path = write(tmp_path, "spec.md", "one\ttwo\r\nthree\r\n\r\nfour\n")
    report = hygiene.scan_files(tmp_path, [path])
    assert report == {"outcome": "clean", "scanned": [path], "skipped": [], "findings": [], "total": 0}


def test_ordinary_spaces_and_visible_text_in_any_script_are_clean(tmp_path):
    path = write(tmp_path, "spec.md", "café naïve 中文 日本語 Ελληνικά — “quoted” → 😀 `\\u00a0`\n")
    report = hygiene.scan_files(tmp_path, [path])
    assert report["outcome"] == "clean" and report["total"] == 0


def test_undecodable_bytes_are_reported_as_replacement_characters(tmp_path):
    path = write(tmp_path, "spec.md", b"ok\nbad \xff\xfe byte\n")
    report = hygiene.scan_files(tmp_path, [path])
    assert [(f["line"], f["column"], f["codepoint"], f["name"]) for f in report["findings"]] == [
        (2, 5, "U+FFFD", "REPLACEMENT CHARACTER"),
        (2, 6, "U+FFFD", "REPLACEMENT CHARACTER"),
    ]


def test_binary_and_oversized_files_are_skipped_not_reported_clean(tmp_path, monkeypatch):
    binary = write(tmp_path, "image.png", b"\x89PNG\x00\x0b\x0b")
    monkeypatch.setattr(hygiene, "SIZE_LIMIT", 16)
    large = write(tmp_path, "large.md", "y" * 17)
    clean = write(tmp_path, "clean.md", "fine\n")
    report = hygiene.scan_files(tmp_path, [binary, large, clean])
    assert report["outcome"] == "skipped"
    assert report["findings"] == [] and report["total"] == 0
    assert report["scanned"] == [clean]
    assert [s["path"] for s in report["skipped"]] == [binary, large]
    assert report["skipped"][0]["reason"] == "binary content"
    assert report["skipped"][1]["reason"].startswith("larger than")


def test_findings_are_capped_with_the_total_count_retained(tmp_path):
    first = write(tmp_path, "a.md", "\x0b" * 40 + "\n")
    second = write(tmp_path, "b.md", "\x0c" * 40 + "\n")
    report = hygiene.scan_files(tmp_path, [first, second])
    assert report["total"] == 80
    assert len(report["findings"]) == hygiene.FINDINGS_LIMIT
    assert [f["path"] for f in report["findings"]].count(first) == 40
    message = hygiene.failure_message(report)
    assert message.count("\n" + first + ":") == 40 and "... and 30 more" in message
    assert message.endswith("or remove it, then close again.")


def test_line_and_column_count_characters_after_multibyte_text(tmp_path):
    path = write(tmp_path, "spec.md", "héllo wörld \r\n日本語 tab\there\x1b\nlast\n")
    report = hygiene.scan_files(tmp_path, [path])
    assert [(f["line"], f["column"], f["codepoint"]) for f in report["findings"]] == [
        (1, 12, "U+2028"),
        (2, 13, "U+001B"),
        (3, 5, "U+0085"),
    ]


def test_require_clean_raises_one_line_per_finding_and_returns_the_clean_report(tmp_path):
    dirty = write(tmp_path, "dirty.md", "a\nb\x0bc\n")
    with pytest.raises(store.WorkflowError) as failure:
        hygiene.require_clean(tmp_path, [dirty])
    assert "dirty.md:2:2 U+000B LINE TABULATION" in str(failure.value)
    assert "Write each character as an escape" in str(failure.value)
    clean = write(tmp_path, "clean.md", "a\nb\n")
    assert hygiene.require_clean(tmp_path, [clean])["outcome"] == "clean"
