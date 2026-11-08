from __future__ import annotations

from datetime import datetime
from pathlib import Path


def format_entry(text: str, timestamp: datetime | None = None) -> str:
    moment = timestamp or datetime.now()
    clean_text = text.strip()
    return f"## {moment:%Y-%m-%d %H:%M}\n\n{clean_text}\n"


def append_transcription(path: Path, text: str) -> None:
    if not text.strip():
        raise ValueError("No se puede escribir una transcripcion vacia")

    path.parent.mkdir(parents=True, exist_ok=True)
    existing = ""
    if path.exists():
        existing = path.read_text(encoding="utf-8")

    entry = format_entry(text)
    if existing:
        entry += "\n" + existing

    path.write_text(entry, encoding="utf-8", newline="\n")
