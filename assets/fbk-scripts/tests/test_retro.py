import pytest
from pathlib import Path
try:
    from fbk.retro import append_section
except ImportError:
    append_section = None


@pytest.mark.skipif(append_section is None, reason="fbk.retro not yet implemented")
def test_second_append_preserves_first(tmp_path):
    """append_section reads before writing; a second stage append preserves the first."""
    retro = tmp_path / "retrospective.md"
    append_section(str(retro), "Intent", "Intent stage content.")
    append_section(str(retro), "Design", "Design stage content.")
    text = retro.read_text()
    assert "Intent" in text, "first stage section was overwritten"
    assert "Design" in text, "second stage section missing"
    assert "Intent stage content." in text
    assert "Design stage content." in text
