"""Fixtures compartilhadas — banco SQLite em memória para testes unitários."""
from __future__ import annotations

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
