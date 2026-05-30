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


def _parse_chat_ids(raw: str) -> set[int]:
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part:
            ids.add(int(part))
    return ids


TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")
AUTHORIZED_CHAT_ID: int = int(_require("AUTHORIZED_CHAT_ID"))
# Allowlist de chats autorizados. AUTHORIZED_CHAT_ID sempre incluído (retrocompat).
# Demais ids opcionais via ALLOWED_CHAT_IDS (CSV), ex.: "123,456".
ALLOWED_CHAT_IDS: set[int] = {AUTHORIZED_CHAT_ID} | _parse_chat_ids(
    os.environ.get("ALLOWED_CHAT_IDS", "")
)
DATABASE_URL: str = _require("DATABASE_URL")
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
DEFAULT_TIMEZONE: str = os.environ.get("DEFAULT_TIMEZONE", "America/Fortaleza")
