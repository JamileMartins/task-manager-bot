"""Fixtures compartilhadas — banco SQLite em memória para testes unitários."""
from __future__ import annotations

import os

# Env mínimo para permitir importar src.config nos testes (sem .env real).
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("AUTHORIZED_CHAT_ID", "12345")
# URL Postgres dummy: create_engine é lazy (não conecta); os testes fazem
# patch de get_session, então o engine real nunca é usado.
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/test")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import Base


@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False, expire_on_commit=False)
    session = Session()
    yield session
    session.close()
