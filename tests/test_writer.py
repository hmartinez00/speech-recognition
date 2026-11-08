from pathlib import Path
from datetime import datetime

from speech_prompt.writer import append_transcription, format_entry


def test_formats_markdown_entry():
    timestamp = datetime(2026, 11, 2, 16, 10)
    assert format_entry("  Hola  ", timestamp) == "## 2026-11-02 16:10\n\nHola\n"


def test_prepends_without_overwriting(tmp_path: Path):
    target = tmp_path / "prompt.md"
    target.write_text("contenido anterior\n", encoding="utf-8")
    append_transcription(target, "nuevo texto")
    content = target.read_text(encoding="utf-8")
    assert content.startswith("## ")
    assert "nuevo texto\n\ncontenido anterior\n" in content
