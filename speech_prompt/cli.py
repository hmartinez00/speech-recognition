from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import DEFAULT_FILE, DEFAULT_LANGUAGE, DEFAULT_MODEL, resolve_api_key, resolve_value
from .recorder import record_audio
from .transcriber import TranscriptionError, transcribe_audio
from .writer import append_transcription


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="speech-prompt",
        description="Graba voz, la transcribe con OpenRouter y la anade a prompt.md.",
    )
    parser.add_argument("--file", type=Path, default=None, help="Archivo destino")
    parser.add_argument("--model", help="Modelo STT de OpenRouter")
    parser.add_argument("--language", help="Idioma del audio, por defecto es")
    parser.add_argument("--duration", type=float, help="Duracion fija en segundos")
    parser.add_argument("--yes", action="store_true", help="Escribir sin confirmacion")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar sin modificar archivos")
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def confirm_write(path: Path) -> bool:
    try:
        answer = input(f"\nAnadir esta transcripcion a {path}? [Y/n] ").strip().lower()
    except EOFError:
        return False
    return answer in ("", "y", "yes", "s", "si")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cwd = Path.cwd()
    package_root = Path(__file__).resolve().parent.parent
    destination = args.file or Path(resolve_value(None, "SPEECH_PROMPT_FILE", DEFAULT_FILE))
    if not destination.is_absolute():
        destination = cwd / destination
    model = resolve_value(args.model, "SPEECH_PROMPT_MODEL", DEFAULT_MODEL)
    language = resolve_value(args.language, "SPEECH_PROMPT_LANGUAGE", DEFAULT_LANGUAGE)

    if args.duration is not None and args.duration <= 0:
        print("Error: --duration debe ser mayor que cero.", file=sys.stderr)
        return 1

    api_key = resolve_api_key(cwd, package_root)
    if not api_key:
        print(
            "Error: no se encontro la clave de OpenRouter. Define "
            "OPENROUTER_API_KEY o usa .opencode-secrets.",
            file=sys.stderr,
        )
        return 1

    audio_path: Path | None = None
    try:
        audio_path = record_audio(args.duration)
        print(f"Transcribiendo con {model}...")
        text = transcribe_audio(audio_path, api_key, model, language)
        print("\nTexto reconocido:\n")
        print(text)

        if args.dry_run:
            print("\nModo dry-run: no se modifico ningun archivo.")
            return 0
        if not args.yes and not confirm_write(destination):
            print("Operacion cancelada; no se modifico ningun archivo.")
            return 2
        append_transcription(destination, text)
        print(f"Texto anadido a {destination}.")
        return 0
    except KeyboardInterrupt:
        print("\nOperacion cancelada.", file=sys.stderr)
        return 2
    except (RuntimeError, ValueError, TranscriptionError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        if audio_path is not None:
            audio_path.unlink(missing_ok=True)
