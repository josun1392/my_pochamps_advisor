from __future__ import annotations

import os

from config.env_loader import load_dotenv


def test_load_dotenv_sets_missing_values(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "# local settings",
                "GEMINI_API_KEY='abc123'",
                'GEMINI_MODEL="gemini-2.5-flash"',
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    load_dotenv(env_path)

    assert os.environ["GEMINI_API_KEY"] == "abc123"
    assert os.environ["GEMINI_MODEL"] == "gemini-2.5-flash"


def test_load_dotenv_does_not_override_existing_env(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("GEMINI_MODEL=gemini-2.5-flash\n", encoding="utf-8")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-existing")

    load_dotenv(env_path)

    assert os.environ["GEMINI_MODEL"] == "gemini-existing"
