"""Sincronização com Google Calendar (Fase C6) — fundação.

Estado: o **motor de sincronização** (mapeamento tarefa↔evento, escolha do
calendário, idempotência) está implementado e testado contra um cliente
injetável. A integração ao vivo com a API do Google (cliente real + fluxo OAuth
+ endpoint web de callback) fica desativada por padrão e exige:

  1. Instalar as dependências do Google (não estão no requirements.txt para não
     pesar o MVP): `google-api-python-client`, `google-auth-oauthlib`.
  2. Definir GOOGLE_OAUTH_CLIENT_ID / _SECRET / _REDIRECT_URI (ver config).
  3. Subir um endpoint HTTPS para o callback do OAuth (o bot é long-polling).

Enquanto desativado, `sync_task_for_user` é um no-op seguro. Detalhes de ativação
em docs/08 §6 e docs/10.

Regras de sincronização (mão única, bot → Calendar):
- Só tarefas com `due_at` viram evento. Quadrante/energia não mapeiam.
- Tarefa de casal → calendário compartilhado do casal (fallback: pessoal de quem
  edita). Tarefa pessoal → calendário pessoal do usuário.
- Idempotente: usa `task.gcal_event_id` para criar/atualizar o mesmo evento;
  ao concluir/arquivar/remover prazo, apaga o evento.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional, Protocol, runtime_checkable

from sqlalchemy import select

from src.db.models import Couple, Task, User
from src.db.session import get_session

logger = logging.getLogger(__name__)

# Duração padrão do evento quando a tarefa não tem estimativa (minutos).
DEFAULT_EVENT_MIN = 30


@runtime_checkable
class CalendarClient(Protocol):
    """Contrato mínimo de um cliente de calendário (real ou fake nos testes)."""

    def upsert_event(
        self, calendar_id: str, event_id: Optional[str], summary: str,
        start: datetime, end: datetime,
    ) -> str:
        """Cria (event_id None) ou atualiza o evento. Retorna o id do evento."""
        ...

    def delete_event(self, calendar_id: str, event_id: str) -> None:
        ...


# ---------------------------------------------------------------------------
# Lógica pura (testável sem DB nem Google)
# ---------------------------------------------------------------------------

def _should_have_event(task: Task, calendar_id: Optional[str]) -> bool:
    return calendar_id is not None and task.status == "aberta" and task.due_at is not None


def sync_task(task: Task, client: CalendarClient, calendar_id: Optional[str]) -> Optional[str]:
    """Reconcilia UMA tarefa com o calendário. Retorna o gcal_event_id resultante
    (ou None se o evento foi/está removido). Não persiste — quem chama grava."""
    if _should_have_event(task, calendar_id):
        dur = task.estimate_min or DEFAULT_EVENT_MIN
        end = task.due_at + timedelta(minutes=dur)
        return client.upsert_event(calendar_id, task.gcal_event_id, task.title, task.due_at, end)
    # Não deveria ter evento: apaga se existir.
    if task.gcal_event_id and calendar_id is not None:
        try:
            client.delete_event(calendar_id, task.gcal_event_id)
        except Exception:
            logger.exception("Falha ao apagar evento %s", task.gcal_event_id)
    return None


def target_calendar_id(task: Task, user: User, couple: Optional[Couple]) -> Optional[str]:
    """Escolhe o calendário: casal usa o do casal (fallback pessoal); senão, pessoal."""
    if task.couple_id is not None and couple is not None and couple.gcal_calendar_id:
        return couple.gcal_calendar_id
    return user.google_calendar_id


# ---------------------------------------------------------------------------
# Orquestração com DB (no-op quando o Google não está configurado)
# ---------------------------------------------------------------------------

def get_client_for(user: User) -> Optional[CalendarClient]:
    """Retorna um cliente autenticado para o usuário, ou None se indisponível.

    Por padrão retorna None (Google desativado). A implementação real é injetada
    via `set_client_factory` na ativação — mantém o motor desacoplado da API.
    """
    from src.config import google_calendar_enabled

    if not google_calendar_enabled() or not user.google_refresh_token:
        return None
    if _CLIENT_FACTORY is None:
        logger.info("Google habilitado mas nenhum client factory registrado.")
        return None
    return _CLIENT_FACTORY(user)


# Fábrica de cliente injetável (registrada na ativação do C6).
_CLIENT_FACTORY = None


def set_client_factory(factory) -> None:
    """Registra a fábrica que cria um CalendarClient a partir de um User."""
    global _CLIENT_FACTORY
    _CLIENT_FACTORY = factory


def sync_task_for_user(task_id, chat_id: int) -> Optional[str]:
    """Sincroniza a tarefa com o calendário do usuário, se o Google estiver ativo.

    Seguro de chamar sempre: vira no-op se o Google não estiver configurado.
    Retorna o gcal_event_id resultante (ou None).
    """
    import uuid as _uuid

    uid = _uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        task = session.get(Task, uid)
        if user is None or task is None:
            return None
        client = get_client_for(user)
        if client is None:
            return None  # Google desativado → no-op silencioso.
        couple = session.get(Couple, task.couple_id) if task.couple_id else None
        calendar_id = target_calendar_id(task, user, couple)
        event_id = sync_task(task, client, calendar_id)
        task.gcal_event_id = event_id
        task.gcal_synced_at = datetime.now(tz=task.due_at.tzinfo) if task.due_at else None
        return event_id
