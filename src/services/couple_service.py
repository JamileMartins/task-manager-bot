"""Lógica de domínio do pareamento de casal (Fase C2) — sem dependência do Telegram.

Pareamento por código de convite: um usuário cria um convite (`create_invite`) e
o parceiro entra com o código (`accept_invite`). O `telegram_chat_id` já é a
identidade autenticada; o convite apenas vincula dois usuários num `Couple`.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select

from src.db.models import Couple, CoupleMember, Invite, User
from src.db.session import get_session

# Código sem caracteres ambíguos (sem O/0, I/1).
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_LENGTH = 6
INVITE_TTL_HOURS = 24


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _gen_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))


def _aware(dt: datetime) -> datetime:
    """Garante timezone-aware (SQLite devolve naive)."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Resultados tipados
# ---------------------------------------------------------------------------

@dataclass
class InviteResult:
    status: str  # "ok" | "no_user" | "already_paired"
    code: Optional[str] = None


@dataclass
class AcceptResult:
    status: str  # "ok" | "no_user" | "invalid" | "expired" | "used"
                 # | "already_paired" | "own_invite" | "full"
    partner_name: Optional[str] = None


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

def _user_by_chat(session, chat_id: int) -> Optional[User]:
    return session.scalar(select(User).where(User.telegram_chat_id == chat_id))


def _membership(session, user_id) -> Optional[CoupleMember]:
    return session.scalar(select(CoupleMember).where(CoupleMember.user_id == user_id))


def _member_count(session, couple_id) -> int:
    return session.scalar(
        select(func.count()).select_from(CoupleMember).where(CoupleMember.couple_id == couple_id)
    ) or 0


def get_couple_id(chat_id: int) -> Optional[str]:
    """Retorna o couple_id (str) do usuário, ou None se não pareado."""
    with get_session() as session:
        user = _user_by_chat(session, chat_id)
        if user is None:
            return None
        m = _membership(session, user.id)
        return str(m.couple_id) if m else None


def get_partner(chat_id: int) -> Optional[dict]:
    """Retorna {'name', 'chat_id'} do parceiro, ou None se sem casal/sem parceiro."""
    with get_session() as session:
        user = _user_by_chat(session, chat_id)
        if user is None:
            return None
        m = _membership(session, user.id)
        if m is None:
            return None
        partner_member = session.scalar(
            select(CoupleMember).where(
                CoupleMember.couple_id == m.couple_id,
                CoupleMember.user_id != user.id,
            )
        )
        if partner_member is None:
            return None
        partner = session.get(User, partner_member.user_id)
        if partner is None:
            return None
        return {"name": partner.name, "chat_id": partner.telegram_chat_id}


def partner_chat_id(chat_id: int) -> Optional[int]:
    """Atalho para o chat_id do parceiro (usado nas notificações da C4)."""
    partner = get_partner(chat_id)
    return partner["chat_id"] if partner else None


def member_names(chat_id: int) -> dict:
    """Mapa user_id -> nome dos membros do casal (para rotular o dono das tarefas)."""
    with get_session() as session:
        user = _user_by_chat(session, chat_id)
        if user is None:
            return {}
        m = _membership(session, user.id)
        if m is None:
            return {}
        rows = session.execute(
            select(CoupleMember.user_id, User.name)
            .join(User, User.id == CoupleMember.user_id)
            .where(CoupleMember.couple_id == m.couple_id)
        ).all()
        return {uid: name for uid, name in rows}


# ---------------------------------------------------------------------------
# Criar convite
# ---------------------------------------------------------------------------

def create_invite(chat_id: int) -> InviteResult:
    """Cria (ou reaproveita) um casal de 1 membro e gera um código de convite."""
    with get_session() as session:
        user = _user_by_chat(session, chat_id)
        if user is None:
            return InviteResult(status="no_user")

        m = _membership(session, user.id)
        if m is not None:
            # Já está num casal completo (2 membros) → não pode convidar.
            if _member_count(session, m.couple_id) >= 2:
                return InviteResult(status="already_paired")
            couple_id = m.couple_id
        else:
            couple = Couple(created_at=_now())
            session.add(couple)
            session.flush()
            session.add(
                CoupleMember(
                    couple_id=couple.id,
                    user_id=user.id,
                    role="member",
                    joined_at=_now(),
                )
            )
            couple_id = couple.id

        # Gera um código único (colisão é improvável, mas garantimos).
        code = _gen_code()
        while session.get(Invite, code) is not None:
            code = _gen_code()

        session.add(
            Invite(
                code=code,
                couple_id=couple_id,
                created_by=user.id,
                created_at=_now(),
                expires_at=_now() + timedelta(hours=INVITE_TTL_HOURS),
            )
        )
        return InviteResult(status="ok", code=code)


# ---------------------------------------------------------------------------
# Aceitar convite
# ---------------------------------------------------------------------------

def accept_invite(chat_id: int, code: str) -> AcceptResult:
    """Valida o código e vincula o usuário ao casal do convite."""
    code = (code or "").strip().upper()
    with get_session() as session:
        user = _user_by_chat(session, chat_id)
        if user is None:
            return AcceptResult(status="no_user")

        invite = session.get(Invite, code)
        if invite is None:
            return AcceptResult(status="invalid")
        # own_invite antes de membership: o criador já é membro do próprio casal,
        # então sem esta ordem ele cairia sempre em "already_paired".
        if invite.created_by == user.id:
            return AcceptResult(status="own_invite")
        if invite.used_by is not None:
            return AcceptResult(status="used")
        if _aware(invite.expires_at) < _now():
            return AcceptResult(status="expired")
        if _membership(session, user.id) is not None:
            return AcceptResult(status="already_paired")
        if _member_count(session, invite.couple_id) >= 2:
            return AcceptResult(status="full")

        session.add(
            CoupleMember(
                couple_id=invite.couple_id,
                user_id=user.id,
                role="member",
                joined_at=_now(),
            )
        )
        invite.used_by = user.id

        creator = session.get(User, invite.created_by)
        return AcceptResult(status="ok", partner_name=creator.name if creator else None)
