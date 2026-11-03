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
    prefix = ""
    if path.exists() and path.stat().st_size:
        prefix = "\n"
    with path.open("a", encoding="utf-8", newline="\n") as destination:
        destination.write(prefix + format_entry(text))
