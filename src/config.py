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
# Tokens de bot para o modo casal com "um bot por pessoa" (C4). O token principal
# entra sempre; tokens extras (CSV em BOT_TOKENS) sobem Applications adicionais
# no mesmo processo. Com um token só, os dois parceiros usam o mesmo bot.
BOT_TOKENS: list[str] = [TELEGRAM_BOT_TOKEN] + [
    t.strip() for t in os.environ.get("BOT_TOKENS", "").split(",")
    if t.strip() and t.strip() != TELEGRAM_BOT_TOKEN
]
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

# Google Calendar (C6) — opcional. A sincronização só liga quando estes estiverem
# definidos E as bibliotecas do Google instaladas (ver docs/08 §6 e docs/10).
GOOGLE_OAUTH_CLIENT_ID: str = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET: str = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REDIRECT_URI: str = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "")


def google_calendar_enabled() -> bool:
    """True se as credenciais OAuth do Google estão configuradas."""
    return bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET and GOOGLE_OAUTH_REDIRECT_URI)
