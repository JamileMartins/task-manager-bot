#!/usr/bin/env python3
"""Valida as três conexões necessárias antes de iniciar o desenvolvimento."""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Força UTF-8 no terminal Windows (reconfigure existe em TextIOWrapper mas não no stub TextIO)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]


def _load_env() -> None:
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


_load_env()

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def _fail(msg: str) -> None:
    print(f"  {RED}✗{RESET} {msg}")


def _section(title: str) -> None:
    print(f"\n{BOLD}{title}{RESET}")


def check_telegram() -> bool:
    _section("Telegram Bot API")
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        _fail("TELEGRAM_BOT_TOKEN não definido no .env")
        return False

    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        if data.get("ok"):
            bot = data["result"]
            _ok(f"Bot conectado: @{bot['username']} — {bot['first_name']}")
            chat_id = os.environ.get("AUTHORIZED_CHAT_ID", "")
            if chat_id:
                _ok(f"AUTHORIZED_CHAT_ID configurado: {chat_id}")
            else:
                _fail("AUTHORIZED_CHAT_ID não definido — restrição de acesso não vai funcionar")
            return True
        _fail(f"Resposta inesperada da API: {data}")
        return False
    except urllib.error.HTTPError as exc:
        _fail(f"HTTP {exc.code}: token inválido ou revogado")
        return False
    except Exception as exc:
        _fail(f"Erro de rede: {exc}")
        return False


def check_gemini() -> bool:
    _section("Google Gemini API")
    api_key = os.environ.get("GEMINI_API_KEY", "")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    if not api_key:
        _fail("GEMINI_API_KEY não definido no .env")
        _fail("Obtenha sua chave gratuita em: aistudio.google.com/apikey")
        return False

    try:
        from google import genai  # type: ignore[import]
    except ImportError:
        _fail("Pacote 'google-genai' não instalado — execute: pip install google-genai")
        return False

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents="Responda apenas a palavra: ok",
        )
        resposta = response.text.strip()
        _ok(f"API conectada — modelo: {model}")
        _ok(f"Resposta de teste: \"{resposta}\"")
        return True
    except Exception as exc:
        msg = str(exc)
        if "API_KEY_INVALID" in msg or "401" in msg:
            _fail("Chave inválida — verifique GEMINI_API_KEY no .env")
        elif "quota" in msg.lower() or "429" in msg:
            _fail("Cota excedida — aguarde ou verifique os limites do free tier")
        else:
            _fail(f"Erro: {exc}")
        return False


def check_database() -> bool:
    _section("Banco de dados (Supabase / PostgreSQL)")
    database_url = os.environ.get("DATABASE_URL", "")

    if not database_url:
        _fail("DATABASE_URL não definida no .env")
        return False

    if "sslmode=require" not in database_url:
        print(f"  {YELLOW}!{RESET} DATABASE_URL sem sslmode=require — conexão insegura")

    try:
        from sqlalchemy import create_engine, text  # type: ignore[import]
    except ImportError:
        _fail("Pacote 'sqlalchemy' não instalado — execute: pip install sqlalchemy psycopg2-binary")
        return False

    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            version: str = conn.execute(text("SELECT version()")).scalar()
            _ok(f"Conexão SSL estabelecida")
            _ok(f"Servidor: {version.split(',')[0]}")
        return True
    except Exception as exc:
        _fail(f"Erro de conexão: {exc}")
        return False


def main() -> None:
    print(f"\n{BOLD}=== Verificação de Conexões — Bot Foco ==={RESET}")

    results = {
        "Telegram": check_telegram(),
        "Google Gemini": check_gemini(),
        "Banco de dados": check_database(),
    }

    print(f"\n{BOLD}Resumo{RESET}")
    all_ok = all(results.values())
    for service, status in results.items():
        icon = f"{GREEN}✓{RESET}" if status else f"{RED}✗{RESET}"
        print(f"  {icon} {service}")

    if all_ok:
        print(f"\n{GREEN}{BOLD}Tudo pronto! Você pode iniciar a implementação da F1.{RESET}\n")
        sys.exit(0)
    else:
        print(f"\n{YELLOW}{BOLD}Corrija os erros acima antes de continuar.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
