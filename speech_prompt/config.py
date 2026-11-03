from __future__ import annotations

import os
from pathlib import Path

DEFAULT_MODEL = "nvidia/nemotron-3.5-transcribe"
DEFAULT_LANGUAGE = "es"
DEFAULT_FILE = "prompt.md"
SECRETS_FILE = ".opencode-secrets"


def read_secret_file(path: Path) -> str | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    for line in lines:
        value = line.strip()
        if value:
            if "=" in value:
                name, value = value.split("=", 1)
                if name.strip() != "OPENROUTER_API_KEY":
                    continue
                value = value.strip().strip('"').strip("'")
            return value
    return None


def resolve_api_key(cwd: Path, package_root: Path) -> str | None:
    current_directory_key = read_secret_file(cwd / SECRETS_FILE)
    if current_directory_key:
        return current_directory_key

    environment_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if environment_key:
        return environment_key

    return read_secret_file(package_root / SECRETS_FILE)


def resolve_value(argument: str | None, environment_name: str, default: str) -> str:
    if argument:
        return argument
    return os.getenv(environment_name, default).strip() or default
