from __future__ import annotations

import base64
import http.client
import json
from pathlib import Path
from urllib.parse import urlparse

ENDPOINT = "https://openrouter.ai/api/v1/audio/transcriptions"


class TranscriptionError(RuntimeError):
    pass


def transcribe_audio(
    audio_path: Path,
    api_key: str,
    model: str,
    language: str,
    timeout: float = 120,
) -> str:
    try:
        audio_data = base64.b64encode(audio_path.read_bytes()).decode("ascii")
    except OSError as exc:
        raise TranscriptionError("No se pudo leer el audio temporal") from exc

    payload = json.dumps(
        {
            "model": model,
            "input_audio": {"data": audio_data, "format": "wav"},
            "language": language,
            "temperature": 0,
        }
    ).encode("utf-8")
    endpoint = urlparse(ENDPOINT)
    connection = http.client.HTTPSConnection(endpoint.netloc, timeout=timeout)
    try:
        connection.request(
            "POST",
            endpoint.path,
            body=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Content-Length": str(len(payload)),
                "HTTP-Referer": "https://github.com/opencode",
                "X-OpenRouter-Title": "Speech Prompt CLI",
            },
        )
        response = connection.getresponse()
        response_body = response.read().decode("utf-8")
        if response.status >= 400:
            raise TranscriptionError(_format_api_error(response_body, response.status))
        response_data = json.loads(response_body)
    except TranscriptionError:
        raise
    except (OSError, TimeoutError) as exc:
        raise TranscriptionError(
            "No se pudo conectar con OpenRouter. Revisa la conexion a internet."
        ) from exc
    except (ValueError, UnicodeDecodeError) as exc:
        raise TranscriptionError("OpenRouter devolvio una respuesta invalida") from exc
    finally:
        connection.close()

    text = response_data.get("text")
    if not isinstance(text, str) or not text.strip():
        raise TranscriptionError("OpenRouter no devolvio una transcripcion util")
    return text.strip()


def _format_api_error(response_body: str, status: int) -> str:
    try:
        error_data = json.loads(response_body)
        message = error_data.get("error", {}).get("message", "Solicitud rechazada")
    except (ValueError, TypeError):
        message = "Solicitud rechazada"
    return f"OpenRouter rechazo la solicitud ({status}): {message}"
