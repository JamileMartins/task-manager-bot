from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


def _require(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"Variável de ambiente obrigatória não definida: {name}")
    return value


TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")
AUTHORIZED_CHAT_ID: int = int(_require("AUTHORIZED_CHAT_ID"))
DATABASE_URL: str = _require("DATABASE_URL")
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
DEFAULT_TIMEZONE: str = os.environ.get("DEFAULT_TIMEZONE", "America/Fortaleza")
