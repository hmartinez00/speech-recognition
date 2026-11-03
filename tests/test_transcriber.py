import base64
import json
from pathlib import Path

import pytest

from speech_prompt.transcriber import TranscriptionError, transcribe_audio


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps({"text": "texto de prueba"}).encode()


def test_transcriber_sends_audio(monkeypatch, tmp_path: Path):
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"RIFF test")
    captured = {}

    class FakeConnection:
        def __init__(self, host, timeout):
            captured["host"] = host
            captured["timeout"] = timeout

        def request(self, method, path, body, headers):
            captured["method"] = method
            captured["path"] = path
            captured["body"] = body
            captured["headers"] = headers

        def getresponse(self):
            return FakeResponse()

        def close(self):
            pass

    monkeypatch.setattr("speech_prompt.transcriber.http.client.HTTPSConnection", FakeConnection)
    assert transcribe_audio(audio, "secret", "model", "es") == "texto de prueba"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["method"] == "POST"
    assert captured["path"] == "/api/v1/audio/transcriptions"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["headers"]["Content-Type"] == "application/json"
    assert json.loads(captured["body"]) == {
        "model": "model",
        "input_audio": {
            "data": base64.b64encode(b"RIFF test").decode("ascii"),
            "format": "wav",
        },
        "language": "es",
        "temperature": 0,
    }
    assert captured["timeout"] == 120


def test_transcriber_rejects_empty_text(monkeypatch, tmp_path: Path):
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"audio")

    class EmptyResponse(FakeResponse):
        def read(self):
            return b'{"text": ""}'

    class EmptyConnection:
        def __init__(self, host, timeout):
            pass

        def request(self, method, path, body, headers):
            pass

        def getresponse(self):
            return EmptyResponse()

        def close(self):
            pass

    monkeypatch.setattr(
        "speech_prompt.transcriber.http.client.HTTPSConnection", EmptyConnection
    )
    with pytest.raises(TranscriptionError):
        transcribe_audio(audio, "secret", "model", "es")
