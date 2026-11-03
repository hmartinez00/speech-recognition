from pathlib import Path

from speech_prompt.config import read_secret_file, resolve_api_key


def test_reads_first_non_empty_secret_line(tmp_path: Path):
    secret_file = tmp_path / ".opencode-secrets"
    secret_file.write_text("\n  test-key  \nignored\n", encoding="utf-8")
    assert read_secret_file(secret_file) == "test-key"


def test_current_directory_secret_has_priority_over_environment(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "environment-key")
    (tmp_path / ".opencode-secrets").write_text("file-key\n", encoding="utf-8")
    assert resolve_api_key(tmp_path, tmp_path) == "file-key"


def test_environment_key_is_used_without_current_directory_secret(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "environment-key")
    assert resolve_api_key(tmp_path, tmp_path / "package") == "environment-key"


def test_reads_key_from_current_directory(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    (tmp_path / ".opencode-secrets").write_text("file-key\n", encoding="utf-8")
    assert resolve_api_key(tmp_path, tmp_path / "package") == "file-key"
