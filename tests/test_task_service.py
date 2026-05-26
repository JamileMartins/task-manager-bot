"""Testes unitários de task_service sem dependência do Telegram."""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select

from src.db.models import Config, Reminder, Task, TaskList, User
from src.services import task_service


# ---------------------------------------------------------------------------
# Infraestrutura de patch
# ---------------------------------------------------------------------------

@contextmanager
def _test_session(session):
    """Substitui get_session() usando a sessão de teste em andamento."""
    try:
        yield session
        session.flush()
    except Exception:
        session.rollback()
        raise


@pytest.fixture
def svc(db_session):
    """Injeta db_session nas funções de serviço via patch de get_session.

    Usa side_effect para criar um novo context manager a cada chamada,
    permitindo que um único teste invoque múltiplas funções de serviço.
    """
    with patch(
        "src.services.task_service.get_session",
        side_effect=lambda: _test_session(db_session),
    ):
        yield db_session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(session, chat_id: int = 12345, name: str = "Jamile") -> User:
    user = User(
        telegram_chat_id=chat_id,
        name=name,
        timezone="America/Fortaleza",
        created_at=datetime.now(timezone.utc),
    )
    session.add(user)
    session.flush()
    return user


def _task(session, user: User, *, title: str = "Tarefa", status: str = "aberta",
          list_id=None) -> Task:
    now = datetime.now(timezone.utc)
    t = Task(
        user_id=user.id,
        list_id=list_id,
        title=title,
        status=status,
        sort_order=0,
        created_at=now,
        last_touched_at=now,
    )
    session.add(t)
    session.flush()
    return t


def _list(session, user: User, *, name: str = "Minha Lista", is_couple: bool = False,
          sort_order: int = 0) -> TaskList:
    lst = TaskList(
        user_id=user.id,
        name=name,
        slug=task_service._slugify(name),
        is_couple=is_couple,
        sort_order=sort_order,
    )
    session.add(lst)
    session.flush()
    return lst


# ---------------------------------------------------------------------------
# Slugify
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("entrada,esperado", [
    ("Trabalho", "trabalho"),
    ("Saúde", "saude"),
    ("Casa (solo)", "casa-solo"),
    ("Casa (casal)", "casa-casal"),
    ("Projetos Pessoais", "projetos-pessoais"),
    ("Idéias & Inspiração", "ideias-inspiracao"),
])
def test_slugify(entrada, esperado):
    assert task_service._slugify(entrada) == esperado


# ---------------------------------------------------------------------------
# Criação de listas iniciais
# ---------------------------------------------------------------------------

def test_listas_iniciais_quantidade(db_session):
    user = _user(db_session)
    task_service._create_initial_lists(db_session, user)
    db_session.flush()

    listas = db_session.scalars(select(TaskList).where(TaskList.user_id == user.id)).all()
    assert len(listas) == 6


def test_listas_iniciais_nomes(db_session):
    user = _user(db_session)
    task_service._create_initial_lists(db_session, user)
    db_session.flush()

    nomes = {
        lst.name
        for lst in db_session.scalars(select(TaskList).where(TaskList.user_id == user.id)).all()
    }
    assert {"Trabalho", "Projetos", "Casa (solo)", "Casa (casal)", "Saúde", "Ideias"} == nomes


def test_listas_iniciais_casal_marcada(db_session):
    user = _user(db_session)
    task_service._create_initial_lists(db_session, user)
    db_session.flush()

    casal = db_session.scalar(
        select(TaskList).where(TaskList.user_id == user.id, TaskList.slug == "casa-casal")
    )
    assert casal is not None
    assert casal.is_couple is True


def test_listas_iniciais_apenas_casal_is_couple(db_session):
    user = _user(db_session)
    task_service._create_initial_lists(db_session, user)
    db_session.flush()

    couples = db_session.scalars(
        select(TaskList).where(TaskList.user_id == user.id, TaskList.is_couple.is_(True))
    ).all()
    assert len(couples) == 1


def test_listas_iniciais_cria_config_com_defaults(db_session):
    user = _user(db_session)
    task_service._create_initial_lists(db_session, user)
    db_session.flush()

    cfg = db_session.get(Config, user.id)
    assert cfg is not None
    assert cfg.stale_days == 7
    assert cfg.stale_waiting_days == 14


# ---------------------------------------------------------------------------
# get_or_create_user
# ---------------------------------------------------------------------------

def test_get_or_create_user_cria_novo(svc):
    chat_id = 55555
    user = task_service.get_or_create_user(chat_id, "Maria")

    assert user.telegram_chat_id == chat_id
    assert user.name == "Maria"
    # Deve criar listas iniciais
    listas = svc.scalars(select(TaskList).where(TaskList.user_id == user.id)).all()
    assert len(listas) == 6


def test_get_or_create_user_idempotente(svc):
    chat_id = 55556
    u1 = task_service.get_or_create_user(chat_id, "Maria")
    u2 = task_service.get_or_create_user(chat_id, "Outro Nome")

    assert u1.id == u2.id
    assert u2.name == "Maria"  # nome original preservado


# ---------------------------------------------------------------------------
# Captura na Inbox
# ---------------------------------------------------------------------------

def test_create_task_in_inbox(svc):
    user = _user(svc)
    task = task_service.create_task_in_inbox(user.telegram_chat_id, "Ligar pro dentista")

    assert task.title == "Ligar pro dentista"
    assert task.list_id is None
    assert task.status == "aberta"


def test_create_task_timestamps_preenchidos(svc):
    user = _user(svc)
    antes = datetime.now(timezone.utc)
    task = task_service.create_task_in_inbox(user.telegram_chat_id, "Teste")
    depois = datetime.now(timezone.utc)

    # Normaliza para UTC antes de comparar (SQLite pode retornar naive)
    criado = task.created_at.replace(tzinfo=timezone.utc) if task.created_at.tzinfo is None else task.created_at
    assert antes <= criado <= depois
    assert task.last_touched_at is not None


def test_create_task_cria_usuario_na_primeira_vez(svc):
    chat_id = 99999
    task = task_service.create_task_in_inbox(chat_id, "Primeira tarefa", "Novo Usuário")

    assert task.title == "Primeira tarefa"
    user = svc.scalar(select(User).where(User.telegram_chat_id == chat_id))
    assert user is not None
    assert user.name == "Novo Usuário"


# ---------------------------------------------------------------------------
# Conclusão de tarefa
# ---------------------------------------------------------------------------

def test_complete_task_muda_status(svc):
    user = _user(svc)
    task = _task(svc, user)

    resultado = task_service.complete_task(task.id)

    assert resultado is True
    svc.refresh(task)
    assert task.status == "concluida"
    assert task.completed_at is not None


def test_complete_task_preenche_completed_at(svc):
    user = _user(svc)
    task = _task(svc, user)
    antes = datetime.now(timezone.utc)

    task_service.complete_task(task.id)
    depois = datetime.now(timezone.utc)

    svc.refresh(task)
    concluido = task.completed_at.replace(tzinfo=timezone.utc) if task.completed_at.tzinfo is None else task.completed_at
    assert antes <= concluido <= depois


def test_complete_task_ja_concluida_e_idempotente(svc):
    user = _user(svc)
    task = _task(svc, user, status="concluida")

    resultado = task_service.complete_task(task.id)

    assert resultado is False  # não altera tarefa já concluída


def test_complete_task_inexistente_retorna_false(svc):
    assert task_service.complete_task(uuid.uuid4()) is False


def test_complete_task_aceita_string_uuid(svc):
    user = _user(svc)
    task = _task(svc, user)

    resultado = task_service.complete_task(str(task.id))

    assert resultado is True


# ---------------------------------------------------------------------------
# Deleção de tarefa
# ---------------------------------------------------------------------------

def test_delete_task(svc):
    user = _user(svc)
    task = _task(svc, user)
    task_id = task.id

    resultado = task_service.delete_task(task_id)

    assert resultado is True
    assert svc.get(Task, task_id) is None


def test_delete_task_aceita_string_uuid(svc):
    user = _user(svc)
    task = _task(svc, user)
    task_id = task.id

    resultado = task_service.delete_task(str(task_id))

    assert resultado is True
    assert svc.get(Task, task_id) is None


def test_delete_task_inexistente_retorna_false(svc):
    assert task_service.delete_task(uuid.uuid4()) is False


# ---------------------------------------------------------------------------
# Listas — CRUD
# ---------------------------------------------------------------------------

def test_create_list(svc):
    user = _user(svc)
    lst = task_service.create_list(user.telegram_chat_id, "Projetos Pessoais")

    assert lst is not None
    assert lst.name == "Projetos Pessoais"
    assert lst.slug == "projetos-pessoais"


def test_create_list_sort_order_incrementa(svc):
    user = _user(svc)
    task_service._create_initial_lists(svc, user)  # cria 6 listas (sort_order 0–5)
    svc.flush()

    lst = task_service.create_list(user.telegram_chat_id, "Nova")

    assert lst is not None
    assert lst.sort_order > 5


def test_create_list_usuario_inexistente_retorna_none(svc):
    lst = task_service.create_list(chat_id=999888, name="Sem usuário")
    assert lst is None


def test_rename_list(svc):
    user = _user(svc)
    lst = _list(svc, user, name="Nome Antigo")

    resultado = task_service.rename_list(lst.id, "Nome Novo")

    assert resultado is not None
    assert resultado.name == "Nome Novo"
    assert resultado.slug == "nome-novo"


def test_rename_list_inexistente_retorna_none(svc):
    assert task_service.rename_list(uuid.uuid4(), "Qualquer") is None


def test_archive_list(svc):
    user = _user(svc)
    lst = _list(svc, user, name="Lista Ativa")

    nome = task_service.archive_list(lst.id)

    assert nome == "Lista Ativa"
    svc.refresh(lst)
    assert lst.archived is True


def test_archive_list_inexistente_retorna_none(svc):
    assert task_service.archive_list(uuid.uuid4()) is None


def test_get_user_lists_retorna_apenas_ativas(svc):
    user = _user(svc)
    task_service._create_initial_lists(svc, user)
    svc.flush()

    casal = svc.scalar(
        select(TaskList).where(TaskList.user_id == user.id, TaskList.slug == "casa-casal")
    )
    casal.archived = True
    svc.flush()

    listas = task_service.get_user_lists(user.telegram_chat_id)

    slugs = [l.slug for l in listas]
    assert "casa-casal" not in slugs
    assert len(listas) == 5


def test_get_user_lists_contagem_tarefas_abertas(svc):
    user = _user(svc)
    lst = _list(svc, user)
    _task(svc, user, list_id=lst.id)
    _task(svc, user, list_id=lst.id)
    _task(svc, user, list_id=lst.id, status="concluida")  # não deve contar

    listas = task_service.get_user_lists(user.telegram_chat_id)
    info = next(l for l in listas if l.id == lst.id)

    assert info.open_task_count == 2


# ---------------------------------------------------------------------------
# Tarefas — consultas
# ---------------------------------------------------------------------------

def test_get_inbox_tasks_retorna_apenas_inbox(svc):
    user = _user(svc)
    lst = _list(svc, user)
    _task(svc, user, title="Inbox 1")
    _task(svc, user, title="Inbox 2")
    _task(svc, user, title="Na lista", list_id=lst.id)

    tasks = task_service.get_inbox_tasks(user.telegram_chat_id)

    assert len(tasks) == 2
    assert all(t.list_id is None for t in tasks)


def test_get_inbox_tasks_nao_inclui_concluidas(svc):
    user = _user(svc)
    _task(svc, user, title="Aberta")
    _task(svc, user, title="Concluída", status="concluida")

    tasks = task_service.get_inbox_tasks(user.telegram_chat_id)

    assert len(tasks) == 1
    assert tasks[0].title == "Aberta"


def test_get_tasks_for_list_retorna_apenas_abertas(svc):
    user = _user(svc)
    lst = _list(svc, user)
    _task(svc, user, title="Aberta 1", list_id=lst.id)
    _task(svc, user, title="Aberta 2", list_id=lst.id)
    _task(svc, user, title="Concluída", list_id=lst.id, status="concluida")

    tasks = task_service.get_tasks_for_list(lst.id)

    assert len(tasks) == 2
    assert all(t.status == "aberta" for t in tasks)


def test_get_inbox_count(svc):
    user = _user(svc)
    _task(svc, user)
    _task(svc, user)
    _task(svc, user, status="concluida")

    count = task_service.get_inbox_count(user.telegram_chat_id)

    assert count == 2


# ---------------------------------------------------------------------------
# Isolamento multi-usuário
# ---------------------------------------------------------------------------

def test_inbox_isolado_por_usuario(svc):
    """Tarefas de um usuário não aparecem na inbox do outro."""
    u1 = _user(svc, chat_id=11111, name="Usuária 1")
    u2 = _user(svc, chat_id=22222, name="Usuária 2")
    _task(svc, u1, title="Tarefa U1")
    _task(svc, u1, title="Tarefa U1 B")
    _task(svc, u2, title="Tarefa U2")

    tasks_u1 = task_service.get_inbox_tasks(u1.telegram_chat_id)
    tasks_u2 = task_service.get_inbox_tasks(u2.telegram_chat_id)

    assert len(tasks_u1) == 2
    assert len(tasks_u2) == 1
    assert all(t.title.startswith("Tarefa U1") for t in tasks_u1)
    assert tasks_u2[0].title == "Tarefa U2"


def test_listas_isoladas_por_usuario(svc):
    """Listas de um usuário não aparecem para o outro."""
    u1 = _user(svc, chat_id=33333, name="Usuária 1")
    u2 = _user(svc, chat_id=44444, name="Usuária 2")
    _list(svc, u1, name="Lista da U1")
    _list(svc, u2, name="Lista da U2")

    listas_u1 = task_service.get_user_lists(u1.telegram_chat_id)
    listas_u2 = task_service.get_user_lists(u2.telegram_chat_id)

    assert all(l.name == "Lista da U1" for l in listas_u1)
    assert all(l.name == "Lista da U2" for l in listas_u2)
    assert len(listas_u1) == 1
    assert len(listas_u2) == 1


def test_inbox_count_isolado_por_usuario(svc):
    u1 = _user(svc, chat_id=55551, name="U1")
    u2 = _user(svc, chat_id=55552, name="U2")
    _task(svc, u1)
    _task(svc, u1)
    _task(svc, u2)

    assert task_service.get_inbox_count(u1.telegram_chat_id) == 2
    assert task_service.get_inbox_count(u2.telegram_chat_id) == 1


def test_get_or_create_user_nao_conflita_entre_usuarios(svc):
    u1 = task_service.get_or_create_user(66661, "Primeiro")
    u2 = task_service.get_or_create_user(66662, "Segundo")

    assert u1.id != u2.id
    assert u1.name == "Primeiro"
    assert u2.name == "Segundo"


# ---------------------------------------------------------------------------
# Tarefas preservadas após arquivar lista
# ---------------------------------------------------------------------------

def test_tarefas_preservadas_apos_arquivar_lista(svc):
    """Arquivar uma lista não deleta as tarefas dela."""
    user = _user(svc)
    lst = _list(svc, user, name="Temporária")
    t1 = _task(svc, user, title="Tarefa 1", list_id=lst.id)
    t2 = _task(svc, user, title="Tarefa 2", list_id=lst.id)

    task_service.archive_list(lst.id)

    assert svc.get(Task, t1.id) is not None
    assert svc.get(Task, t2.id) is not None
    svc.refresh(t1)
    assert t1.list_id == lst.id  # vínculo mantido


def test_lista_arquivada_some_de_get_user_lists(svc):
    user = _user(svc)
    lst = _list(svc, user, name="Para arquivar")
    _task(svc, user, title="Tarefa", list_id=lst.id)

    task_service.archive_list(lst.id)
    listas = task_service.get_user_lists(user.telegram_chat_id)

    assert not any(l.id == lst.id for l in listas)


def test_lista_arquivada_nao_conta_no_open_task_count(svc):
    """Após arquivar lista A, as contagens de outras listas não são afetadas."""
    user = _user(svc)
    lst_a = _list(svc, user, name="Lista A", sort_order=0)
    lst_b = _list(svc, user, name="Lista B", sort_order=1)
    _task(svc, user, title="T1", list_id=lst_a.id)
    _task(svc, user, title="T2", list_id=lst_b.id)
    _task(svc, user, title="T3", list_id=lst_b.id)

    task_service.archive_list(lst_a.id)
    listas = task_service.get_user_lists(user.telegram_chat_id)

    info_b = next(l for l in listas if l.id == lst_b.id)
    assert info_b.open_task_count == 2


# ---------------------------------------------------------------------------
# Casos extremos — entradas incomuns
# ---------------------------------------------------------------------------

def test_create_task_titulo_com_espacos_extras(svc):
    """O título é preservado como fornecido pelo serviço (sem truncagem silenciosa)."""
    user = _user(svc)
    task = task_service.create_task_in_inbox(user.telegram_chat_id, "  comprar café  ")

    assert task is not None
    assert "café" in task.title


def test_create_list_nomes_duplicados_criam_listas_separadas(svc):
    user = _user(svc)
    l1 = task_service.create_list(user.telegram_chat_id, "Duplicada")
    l2 = task_service.create_list(user.telegram_chat_id, "Duplicada")

    assert l1 is not None
    assert l2 is not None
    assert l1.id != l2.id


def test_get_tasks_for_list_lista_vazia_retorna_lista_vazia(svc):
    user = _user(svc)
    lst = _list(svc, user)

    tasks = task_service.get_tasks_for_list(lst.id)

    assert tasks == []


def test_get_inbox_tasks_usuario_sem_tarefas_retorna_lista_vazia(svc):
    user = _user(svc)

    tasks = task_service.get_inbox_tasks(user.telegram_chat_id)

    assert tasks == []


def test_complete_task_sets_last_touched_at(svc):
    user = _user(svc)
    task = _task(svc, user)
    before = task.last_touched_at

    task_service.complete_task(task.id)
    svc.refresh(task)

    after = task.last_touched_at.replace(tzinfo=timezone.utc) if task.last_touched_at.tzinfo is None else task.last_touched_at
    before_utc = before.replace(tzinfo=timezone.utc) if before.tzinfo is None else before
    assert after >= before_utc


# ---------------------------------------------------------------------------
# Helper F3 — tarefa com atributos de priorização
# ---------------------------------------------------------------------------

def _task_f3(
    session,
    user: User,
    *,
    title: str = "Tarefa",
    status: str = "aberta",
    estimate_min: int | None = None,
    energy: str | None = None,
    quadrant: int | None = None,
    due_at: datetime | None = None,
    sort_order: int = 0,
    list_id=None,
) -> Task:
    now = datetime.now(timezone.utc)
    t = Task(
        user_id=user.id,
        list_id=list_id,
        title=title,
        status=status,
        estimate_min=estimate_min,
        energy=energy,
        quadrant=quadrant,
        due_at=due_at,
        sort_order=sort_order,
        created_at=now,
        last_touched_at=now,
    )
    session.add(t)
    session.flush()
    return t


# ---------------------------------------------------------------------------
# F3 — get_task_for_agora (US-12)
# ---------------------------------------------------------------------------

def test_agora_retorna_tarefa_compativel(svc):
    user = _user(svc)
    t = _task_f3(svc, user, title="Revisar e-mails", estimate_min=15, energy="baixa")

    result = task_service.get_task_for_agora(user.telegram_chat_id, tempo_min=30, energia="media")

    assert result is not None
    assert result.id == t.id


def test_agora_filtra_tarefa_que_excede_tempo(svc):
    user = _user(svc)
    _task_f3(svc, user, title="Longa", estimate_min=60, energy="baixa")

    result = task_service.get_task_for_agora(user.telegram_chat_id, tempo_min=15, energia="alta")

    assert result is None


def test_agora_aceita_tarefa_sem_estimate(svc):
    """Tarefa sem estimate_min deve aparecer para qualquer tempo disponível."""
    user = _user(svc)
    t = _task_f3(svc, user, title="Sem estimativa", energy="baixa")

    result = task_service.get_task_for_agora(user.telegram_chat_id, tempo_min=5, energia="alta")

    assert result is not None
    assert result.id == t.id


def test_agora_nao_sugere_energia_alta_para_baixa(svc):
    user = _user(svc)
    _task_f3(svc, user, title="Pesada", estimate_min=10, energy="alta")

    result = task_service.get_task_for_agora(user.telegram_chat_id, tempo_min=60, energia="baixa")

    assert result is None


def test_agora_aceita_energia_baixa_para_media(svc):
    user = _user(svc)
    t = _task_f3(svc, user, title="Leve", estimate_min=10, energy="baixa")

    result = task_service.get_task_for_agora(user.telegram_chat_id, tempo_min=30, energia="media")

    assert result is not None
    assert result.id == t.id


def test_agora_aceita_tarefa_sem_energia_definida(svc):
    """Tarefa sem energy definida deve aparecer para qualquer nível de energia."""
    user = _user(svc)
    t = _task_f3(svc, user, title="Neutra", estimate_min=10)

    result = task_service.get_task_for_agora(user.telegram_chat_id, tempo_min=30, energia="baixa")

    assert result is not None
    assert result.id == t.id


def test_agora_respeita_excluidos(svc):
    user = _user(svc)
    t1 = _task_f3(svc, user, title="Primeira", estimate_min=10, energy="baixa", sort_order=0)
    t2 = _task_f3(svc, user, title="Segunda", estimate_min=10, energy="baixa", sort_order=1)

    result = task_service.get_task_for_agora(
        user.telegram_chat_id, tempo_min=30, energia="alta", excluir_ids=[t1.id]
    )

    assert result is not None
    assert result.id == t2.id


def test_agora_prefere_quadrante_menor(svc):
    user = _user(svc)
    t4 = _task_f3(svc, user, title="Q4", estimate_min=10, energy="baixa", quadrant=4, sort_order=0)
    t1 = _task_f3(svc, user, title="Q1", estimate_min=10, energy="baixa", quadrant=1, sort_order=1)

    result = task_service.get_task_for_agora(user.telegram_chat_id, tempo_min=30, energia="alta")

    assert result is not None
    assert result.id == t1.id


def test_agora_ignora_tarefas_concluidas(svc):
    user = _user(svc)
    _task_f3(svc, user, title="Concluída", estimate_min=5, energy="baixa", status="concluida")

    result = task_service.get_task_for_agora(user.telegram_chat_id, tempo_min=30, energia="alta")

    assert result is None


def test_agora_ignora_tarefas_aguardando(svc):
    user = _user(svc)
    _task_f3(svc, user, title="Bloqueada", estimate_min=5, energy="baixa", status="aguardando")

    result = task_service.get_task_for_agora(user.telegram_chat_id, tempo_min=30, energia="alta")

    assert result is None


def test_agora_sem_candidatos_retorna_none(svc):
    user = _user(svc)

    result = task_service.get_task_for_agora(user.telegram_chat_id, tempo_min=30, energia="media")

    assert result is None


def test_agora_usuario_inexistente_retorna_none(svc):
    result = task_service.get_task_for_agora(chat_id=999777, tempo_min=30, energia="media")

    assert result is None


# ---------------------------------------------------------------------------
# F3 — get_lightest_task (US-12 fallback)
# ---------------------------------------------------------------------------

def test_lightest_retorna_tarefa_mais_leve(svc):
    user = _user(svc)
    _task_f3(svc, user, title="Pesada", estimate_min=60)
    t_leve = _task_f3(svc, user, title="Leve", estimate_min=5)

    result = task_service.get_lightest_task(user.telegram_chat_id)

    assert result is not None
    assert result.id == t_leve.id


def test_lightest_respeita_excluidos(svc):
    user = _user(svc)
    t1 = _task_f3(svc, user, title="Leve", estimate_min=5)
    t2 = _task_f3(svc, user, title="Media", estimate_min=30)

    result = task_service.get_lightest_task(user.telegram_chat_id, excluir_ids=[t1.id])

    assert result is not None
    assert result.id == t2.id


def test_lightest_todas_excluidas_retorna_none(svc):
    user = _user(svc)
    t = _task_f3(svc, user, title="Única", estimate_min=5)

    result = task_service.get_lightest_task(user.telegram_chat_id, excluir_ids=[t.id])

    assert result is None


def test_lightest_sem_tarefas_retorna_none(svc):
    user = _user(svc)

    result = task_service.get_lightest_task(user.telegram_chat_id)

    assert result is None


def test_lightest_prefere_sem_estimate_por_ultimo(svc):
    """Tarefa com estimate_min=None aparece depois das que têm valor."""
    user = _user(svc)
    t_none = _task_f3(svc, user, title="Sem estimativa", sort_order=0)
    t5 = _task_f3(svc, user, title="5 min", estimate_min=5, sort_order=1)

    result = task_service.get_lightest_task(user.telegram_chat_id)

    assert result is not None
    assert result.id == t5.id


# ---------------------------------------------------------------------------
# F3 — update_task_attrs (US-07, 08, 09, 10)
# ---------------------------------------------------------------------------

def test_update_task_quadrant(svc):
    user = _user(svc)
    t = _task_f3(svc, user)

    task_service.update_task_attrs(t.id, quadrant=2)
    svc.refresh(t)

    assert t.quadrant == 2


def test_update_task_energy(svc):
    user = _user(svc)
    t = _task_f3(svc, user)

    task_service.update_task_attrs(t.id, energy="baixa")
    svc.refresh(t)

    assert t.energy == "baixa"


def test_update_task_estimate_min(svc):
    user = _user(svc)
    t = _task_f3(svc, user)

    task_service.update_task_attrs(t.id, estimate_min=30)
    svc.refresh(t)

    assert t.estimate_min == 30


def test_update_task_due_at(svc):
    user = _user(svc)
    t = _task_f3(svc, user)
    prazo = datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc)

    task_service.update_task_attrs(t.id, due_at=prazo)
    svc.refresh(t)

    assert t.due_at is not None


def test_update_task_due_at_none_remove_prazo(svc):
    user = _user(svc)
    prazo = datetime(2026, 12, 31, tzinfo=timezone.utc)
    t = _task_f3(svc, user, due_at=prazo)

    task_service.update_task_attrs(t.id, due_at=None)
    svc.refresh(t)

    assert t.due_at is None


def test_update_task_list_id_move_para_lista(svc):
    user = _user(svc)
    lst = _list(svc, user, name="Trabalho")
    t = _task_f3(svc, user)

    task_service.update_task_attrs(t.id, list_id=lst.id)
    svc.refresh(t)

    assert t.list_id == lst.id


def test_update_task_list_id_none_move_para_inbox(svc):
    user = _user(svc)
    lst = _list(svc, user)
    t = _task_f3(svc, user, list_id=lst.id)

    task_service.update_task_attrs(t.id, list_id=None)
    svc.refresh(t)

    assert t.list_id is None


def test_update_task_atualiza_last_touched_at(svc):
    user = _user(svc)
    t = _task_f3(svc, user)
    before = t.last_touched_at

    task_service.update_task_attrs(t.id, quadrant=3)
    svc.refresh(t)

    after = t.last_touched_at.replace(tzinfo=timezone.utc) if t.last_touched_at.tzinfo is None else t.last_touched_at
    before_utc = before.replace(tzinfo=timezone.utc) if before.tzinfo is None else before
    assert after >= before_utc


def test_update_task_inexistente_retorna_none(svc):
    result = task_service.update_task_attrs(uuid.uuid4(), quadrant=1)

    assert result is None


def test_update_task_ignora_campo_nao_permitido(svc):
    user = _user(svc)
    t = _task_f3(svc, user, title="Original")

    task_service.update_task_attrs(t.id, title="Alterado", quadrant=1)
    svc.refresh(t)

    assert t.title == "Original"
    assert t.quadrant == 1


# ---------------------------------------------------------------------------
# F3 — reorder_task (US-11)
# ---------------------------------------------------------------------------

def test_reorder_up_troca_com_anterior(svc):
    user = _user(svc)
    lst = _list(svc, user)
    t1 = _task_f3(svc, user, list_id=lst.id, sort_order=0)
    t2 = _task_f3(svc, user, list_id=lst.id, sort_order=1)

    result = task_service.reorder_task(t2.id, "up")
    svc.refresh(t1)
    svc.refresh(t2)

    assert result is True
    assert t2.sort_order == 0
    assert t1.sort_order == 1


def test_reorder_down_troca_com_proxima(svc):
    user = _user(svc)
    lst = _list(svc, user)
    t1 = _task_f3(svc, user, list_id=lst.id, sort_order=0)
    t2 = _task_f3(svc, user, list_id=lst.id, sort_order=1)

    result = task_service.reorder_task(t1.id, "down")
    svc.refresh(t1)
    svc.refresh(t2)

    assert result is True
    assert t1.sort_order == 1
    assert t2.sort_order == 0


def test_reorder_up_primeira_retorna_false(svc):
    user = _user(svc)
    lst = _list(svc, user)
    t = _task_f3(svc, user, list_id=lst.id, sort_order=0)

    result = task_service.reorder_task(t.id, "up")

    assert result is False


def test_reorder_down_ultima_retorna_false(svc):
    user = _user(svc)
    lst = _list(svc, user)
    t = _task_f3(svc, user, list_id=lst.id, sort_order=0)

    result = task_service.reorder_task(t.id, "down")

    assert result is False


def test_reorder_inexistente_retorna_false(svc):
    result = task_service.reorder_task(uuid.uuid4(), "up")

    assert result is False


def test_reorder_nao_cruza_lista_diferente(svc):
    """Tarefas de listas distintas não interferem na reordenação."""
    user = _user(svc)
    lst_a = _list(svc, user, name="Lista A", sort_order=0)
    lst_b = _list(svc, user, name="Lista B", sort_order=1)
    t_a = _task_f3(svc, user, list_id=lst_a.id, sort_order=0)
    t_b = _task_f3(svc, user, list_id=lst_b.id, sort_order=1)

    result = task_service.reorder_task(t_a.id, "up")

    assert result is False
    svc.refresh(t_b)
    assert t_b.sort_order == 1


# ---------------------------------------------------------------------------
# F2 — save_classified_tasks
# ---------------------------------------------------------------------------

def test_save_classified_tasks_cria_tarefas(svc):
    user = _user(svc)
    task_service._create_initial_lists(svc, user)
    svc.flush()

    tarefas = [{"titulo": "Ligar pro cliente", "lista_sugerida": "Trabalho",
                "quadrante_sugerido": 2, "estimativa_min": 10, "energia": "media",
                "impedimento": None, "impedimento_externo": False, "proximo_passo": None,
                "prazo_sugerido": None}]

    salvas = task_service.save_classified_tasks(user.telegram_chat_id, tarefas)

    assert len(salvas) == 1
    assert salvas[0].title == "Ligar pro cliente"
    assert salvas[0].status == "aberta"


def test_save_classified_tasks_externo_vira_aguardando(svc):
    user = _user(svc)
    task_service._create_initial_lists(svc, user)
    svc.flush()

    tarefas = [{"titulo": "Aguardar retorno", "lista_sugerida": "Trabalho",
                "quadrante_sugerido": None, "estimativa_min": None, "energia": "media",
                "impedimento": "pessoa", "impedimento_externo": True, "proximo_passo": None,
                "prazo_sugerido": None}]

    salvas = task_service.save_classified_tasks(user.telegram_chat_id, tarefas)

    assert salvas[0].status == "aguardando"
    assert salvas[0].waiting_since is not None


def test_save_classified_tasks_lista_inexistente_vai_para_inbox(svc):
    user = _user(svc)
    task_service._create_initial_lists(svc, user)
    svc.flush()

    tarefas = [{"titulo": "Sem lista", "lista_sugerida": "Lista Fantasma",
                "quadrante_sugerido": None, "estimativa_min": None, "energia": None,
                "impedimento": None, "impedimento_externo": False, "proximo_passo": None,
                "prazo_sugerido": None}]

    salvas = task_service.save_classified_tasks(user.telegram_chat_id, tarefas)

    assert salvas[0].list_id is None


# ---------------------------------------------------------------------------
# F4 — archive_task
# ---------------------------------------------------------------------------

def test_archive_task_muda_status_para_arquivada(svc):
    user = _user(svc)
    t = _task(svc, user)

    assert task_service.archive_task(t.id) is True
    svc.refresh(t)
    assert t.status == "arquivada"


def test_archive_task_aceita_string_uuid(svc):
    user = _user(svc)
    t = _task(svc, user)

    assert task_service.archive_task(str(t.id)) is True


def test_archive_task_inexistente_retorna_false(svc):
    assert task_service.archive_task(uuid.uuid4()) is False


# ---------------------------------------------------------------------------
# F4 — reschedule_task
# ---------------------------------------------------------------------------

def test_reschedule_task_define_due_at_futuro(svc):
    user = _user(svc)
    t = _task(svc, user)
    antes = datetime.now(timezone.utc)

    task_service.reschedule_task(t.id, 7)
    svc.refresh(t)

    due = t.due_at.replace(tzinfo=timezone.utc) if t.due_at.tzinfo is None else t.due_at
    assert due > antes


def test_reschedule_task_atualiza_last_touched_at(svc):
    user = _user(svc)
    t = _task(svc, user)
    before = t.last_touched_at

    task_service.reschedule_task(t.id, 1)
    svc.refresh(t)

    after = t.last_touched_at.replace(tzinfo=timezone.utc) if t.last_touched_at.tzinfo is None else t.last_touched_at
    before_utc = before.replace(tzinfo=timezone.utc) if before.tzinfo is None else before
    assert after >= before_utc


def test_reschedule_task_inexistente_retorna_none(svc):
    assert task_service.reschedule_task(uuid.uuid4(), 3) is None


# ---------------------------------------------------------------------------
# F4 — set_blocker / set_waiting / unblock_task
# ---------------------------------------------------------------------------

def test_set_blocker_salva_tipo_interno(svc):
    user = _user(svc)
    t = _task(svc, user)

    task_service.set_blocker(t.id, "vaga_grande")
    svc.refresh(t)

    assert t.blocker_type == "vaga_grande"
    assert t.blocker_is_external is False


@pytest.mark.parametrize("tipo", ["pessoa", "recurso_info", "data_externa"])
def test_set_blocker_tipos_externos_inferem_flag(svc, tipo):
    user = _user(svc)
    t = _task(svc, user)

    task_service.set_blocker(t.id, tipo)
    svc.refresh(t)

    assert t.blocker_is_external is True


@pytest.mark.parametrize("tipo", ["vaga_grande", "decisao_pendente", "aversiva_energia", "obsoleta"])
def test_set_blocker_tipos_internos_flag_false(svc, tipo):
    user = _user(svc)
    t = _task(svc, user)

    task_service.set_blocker(t.id, tipo)
    svc.refresh(t)

    assert t.blocker_is_external is False


def test_set_waiting_muda_status_e_registra_waiting_since(svc):
    user = _user(svc)
    t = _task(svc, user)
    antes = datetime.now(timezone.utc)

    task_service.set_waiting(t.id)
    svc.refresh(t)

    assert t.status == "aguardando"
    ws = t.waiting_since.replace(tzinfo=timezone.utc) if t.waiting_since.tzinfo is None else t.waiting_since
    assert ws >= antes


def test_set_waiting_com_due_at_define_prazo(svc):
    user = _user(svc)
    t = _task(svc, user)
    prazo = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)

    task_service.set_waiting(t.id, due_at=prazo)
    svc.refresh(t)

    assert t.status == "aguardando"
    assert t.due_at is not None


def test_unblock_task_volta_para_aberta_e_limpa_campos(svc):
    user = _user(svc)
    t = _task(svc, user)
    t.status = "aguardando"
    t.waiting_since = datetime.now(timezone.utc)
    t.blocker_type = "pessoa"
    t.blocker_is_external = True
    svc.flush()

    task_service.unblock_task(t.id)
    svc.refresh(t)

    assert t.status == "aberta"
    assert t.waiting_since is None
    assert t.blocker_type is None
    assert t.blocker_is_external is None


def test_unblock_task_inexistente_retorna_none(svc):
    assert task_service.unblock_task(uuid.uuid4()) is None


# ---------------------------------------------------------------------------
# F4 — get_stale_tasks / get_stale_waiting_tasks
# ---------------------------------------------------------------------------

def test_get_stale_tasks_retorna_antigas_e_ignora_recentes(svc):
    user = _user(svc)
    task_service._create_initial_lists(svc, user)
    svc.flush()
    cfg = svc.scalar(select(Config).where(Config.user_id == user.id))
    cfg.stale_days = 7
    svc.flush()

    t_velha = _task(svc, user, title="Velha")
    t_velha.last_touched_at = datetime.now(timezone.utc) - timedelta(days=10)
    t_recente = _task(svc, user, title="Recente")
    svc.flush()

    stale = task_service.get_stale_tasks(user.telegram_chat_id)

    ids = [t.id for t in stale]
    assert t_velha.id in ids
    assert t_recente.id not in ids


def test_get_stale_tasks_ignora_nao_abertas(svc):
    user = _user(svc)
    task_service._create_initial_lists(svc, user)
    svc.flush()
    cfg = svc.scalar(select(Config).where(Config.user_id == user.id))
    cfg.stale_days = 7
    svc.flush()

    old = datetime.now(timezone.utc) - timedelta(days=15)
    t_c = _task(svc, user, title="Concluída", status="concluida")
    t_c.last_touched_at = old
    t_w = _task(svc, user, title="Aguardando", status="aguardando")
    t_w.last_touched_at = old
    svc.flush()

    stale = task_service.get_stale_tasks(user.telegram_chat_id)

    titles = [t.title for t in stale]
    assert "Concluída" not in titles
    assert "Aguardando" not in titles


def test_get_stale_waiting_retorna_esperas_longas(svc):
    user = _user(svc)
    task_service._create_initial_lists(svc, user)
    svc.flush()
    cfg = svc.scalar(select(Config).where(Config.user_id == user.id))
    cfg.stale_waiting_days = 14
    svc.flush()

    t_longa = _task(svc, user, title="Espera Longa", status="aguardando")
    t_longa.waiting_since = datetime.now(timezone.utc) - timedelta(days=20)
    t_recente = _task(svc, user, title="Espera Recente", status="aguardando")
    t_recente.waiting_since = datetime.now(timezone.utc) - timedelta(days=5)
    svc.flush()

    stale = task_service.get_stale_waiting_tasks(user.telegram_chat_id)

    ids = [t.id for t in stale]
    assert t_longa.id in ids
    assert t_recente.id not in ids


def test_get_stale_waiting_ignora_tarefas_abertas(svc):
    user = _user(svc)
    task_service._create_initial_lists(svc, user)
    svc.flush()
    cfg = svc.scalar(select(Config).where(Config.user_id == user.id))
    cfg.stale_waiting_days = 7
    svc.flush()

    t_aberta = _task(svc, user, title="Aberta Velha", status="aberta")
    t_aberta.last_touched_at = datetime.now(timezone.utc) - timedelta(days=30)
    svc.flush()

    stale = task_service.get_stale_waiting_tasks(user.telegram_chat_id)

    assert not any(t.title == "Aberta Velha" for t in stale)


# ---------------------------------------------------------------------------
# F4 — get_config / update_config (US-20)
# ---------------------------------------------------------------------------

def test_get_config_retorna_none_sem_usuario(svc):
    assert task_service.get_config(chat_id=999888) is None


def test_get_config_retorna_defaults(svc):
    user = _user(svc)
    task_service._create_initial_lists(svc, user)
    svc.flush()

    cfg = task_service.get_config(user.telegram_chat_id)

    assert cfg is not None
    assert cfg.stale_days == 7
    assert cfg.stale_waiting_days == 14
    assert cfg.daily_summary_time is None
    assert cfg.couple_group_chat_id is None


def test_update_config_salva_horario_diario(svc):
    from datetime import time as dtime
    user = _user(svc)
    task_service._create_initial_lists(svc, user)
    svc.flush()

    task_service.update_config(user.telegram_chat_id, daily_summary_time=dtime(7, 30))
    cfg = task_service.get_config(user.telegram_chat_id)

    assert cfg.daily_summary_time.hour == 7
    assert cfg.daily_summary_time.minute == 30


def test_update_config_salva_grupo_casal(svc):
    user = _user(svc)
    task_service._create_initial_lists(svc, user)
    svc.flush()

    task_service.update_config(user.telegram_chat_id, couple_group_chat_id=-100123456)
    cfg = task_service.get_config(user.telegram_chat_id)

    assert cfg.couple_group_chat_id == -100123456


def test_update_config_ignora_campo_nao_permitido(svc):
    user = _user(svc)
    task_service._create_initial_lists(svc, user)
    svc.flush()

    task_service.update_config(user.telegram_chat_id, campo_inventado=999)
    cfg = task_service.get_config(user.telegram_chat_id)

    assert cfg.stale_days == 7  # não alterado


# ---------------------------------------------------------------------------
# F4 — recorrência (US-18)
# ---------------------------------------------------------------------------

def test_complete_task_com_recorrencia_cria_proxima_ocorrencia(svc):
    user = _user(svc)
    prazo = datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc)
    t = _task_f3(svc, user, title="Tarefa Semanal", due_at=prazo)
    t.recurrence = "weekly"
    svc.flush()

    task_service.complete_task(t.id)

    todas = svc.scalars(select(Task).where(Task.user_id == user.id)).all()
    concluidas = [x for x in todas if x.status == "concluida"]
    abertas = [x for x in todas if x.status == "aberta"]
    assert len(concluidas) == 1
    assert len(abertas) == 1


def test_complete_task_recorrencia_diaria_due_at_correto(svc):
    user = _user(svc)
    prazo = datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc)
    t = _task_f3(svc, user, title="Diária", due_at=prazo)
    t.recurrence = "daily"
    svc.flush()

    task_service.complete_task(t.id)

    proxima = svc.scalar(
        select(Task).where(Task.user_id == user.id, Task.status == "aberta")
    )
    assert proxima is not None
    due = proxima.due_at.replace(tzinfo=timezone.utc) if proxima.due_at.tzinfo is None else proxima.due_at
    assert due == prazo + timedelta(days=1)


def test_complete_task_recorrencia_mensal_avanca_30_dias(svc):
    user = _user(svc)
    prazo = datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc)
    t = _task_f3(svc, user, title="Mensal", due_at=prazo)
    t.recurrence = "monthly"
    svc.flush()

    task_service.complete_task(t.id)

    proxima = svc.scalar(
        select(Task).where(Task.user_id == user.id, Task.status == "aberta")
    )
    assert proxima is not None
    due = proxima.due_at.replace(tzinfo=timezone.utc) if proxima.due_at.tzinfo is None else proxima.due_at
    assert due == prazo + timedelta(days=30)


def test_complete_task_sem_recorrencia_nao_cria_proxima(svc):
    user = _user(svc)
    t = _task(svc, user, title="Única")

    task_service.complete_task(t.id)

    todas = svc.scalars(select(Task).where(Task.user_id == user.id)).all()
    assert len(todas) == 1
    assert todas[0].status == "concluida"


def test_complete_task_recorrencia_preserva_atributos(svc):
    user = _user(svc)
    lst = _list(svc, user)
    prazo = datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc)
    t = _task_f3(svc, user, title="Com Atributos", list_id=lst.id, quadrant=2,
                 energy="alta", estimate_min=30, due_at=prazo)
    t.recurrence = "weekly"
    svc.flush()

    task_service.complete_task(t.id)

    proxima = svc.scalar(
        select(Task).where(Task.user_id == user.id, Task.status == "aberta")
    )
    assert proxima.quadrant == 2
    assert proxima.energy == "alta"
    assert proxima.estimate_min == 30
    assert proxima.list_id == lst.id
    assert proxima.recurrence == "weekly"


# ---------------------------------------------------------------------------
# F4 — lembretes: _sync_reminder / get_due_reminders / mark_reminder_sent (US-17)
# ---------------------------------------------------------------------------

def test_update_due_at_cria_lembrete(svc):
    user = _user(svc)
    t = _task(svc, user)
    prazo = datetime(2099, 12, 1, 10, 0, tzinfo=timezone.utc)

    task_service.update_task_attrs(t.id, due_at=prazo)

    lembrete = svc.scalar(select(Reminder).where(Reminder.task_id == t.id))
    assert lembrete is not None
    assert lembrete.sent is False


def test_update_due_at_none_remove_lembrete(svc):
    user = _user(svc)
    prazo = datetime(2099, 12, 1, 10, 0, tzinfo=timezone.utc)
    t = _task_f3(svc, user, due_at=prazo)
    svc.add(Reminder(task_id=t.id, remind_at=prazo))
    svc.flush()

    task_service.update_task_attrs(t.id, due_at=None)

    lembrete = svc.scalar(
        select(Reminder).where(Reminder.task_id == t.id, Reminder.sent.is_(False))
    )
    assert lembrete is None


def test_update_due_at_atualiza_lembrete_existente(svc):
    user = _user(svc)
    prazo1 = datetime(2099, 6, 1, tzinfo=timezone.utc)
    prazo2 = datetime(2099, 7, 1, tzinfo=timezone.utc)
    t = _task_f3(svc, user, due_at=prazo1)
    svc.add(Reminder(task_id=t.id, remind_at=prazo1))
    svc.flush()

    task_service.update_task_attrs(t.id, due_at=prazo2)

    lembretes = svc.scalars(
        select(Reminder).where(Reminder.task_id == t.id, Reminder.sent.is_(False))
    ).all()
    assert len(lembretes) == 1
    remind = lembretes[0].remind_at
    remind = remind.replace(tzinfo=timezone.utc) if remind.tzinfo is None else remind
    assert remind == prazo2


def test_get_due_reminders_retorna_vencidos(svc):
    user = _user(svc)
    t = _task(svc, user)
    passado = datetime(2020, 1, 1, tzinfo=timezone.utc)
    r = Reminder(task_id=t.id, remind_at=passado)
    svc.add(r)
    svc.flush()

    due = task_service.get_due_reminders()

    assert any(lem.id == r.id for lem, _, _ in due)


def test_get_due_reminders_nao_retorna_futuros(svc):
    user = _user(svc)
    t = _task(svc, user)
    futuro = datetime(2099, 12, 31, tzinfo=timezone.utc)
    r = Reminder(task_id=t.id, remind_at=futuro)
    svc.add(r)
    svc.flush()

    due = task_service.get_due_reminders()

    assert not any(lem.id == r.id for lem, _, _ in due)


def test_get_due_reminders_nao_retorna_ja_enviados(svc):
    user = _user(svc)
    t = _task(svc, user)
    passado = datetime(2020, 1, 1, tzinfo=timezone.utc)
    r = Reminder(task_id=t.id, remind_at=passado, sent=True)
    svc.add(r)
    svc.flush()

    due = task_service.get_due_reminders()

    assert not any(lem.id == r.id for lem, _, _ in due)


def test_get_due_reminders_inclui_chat_id_correto(svc):
    user = _user(svc, chat_id=77777)
    t = _task(svc, user)
    passado = datetime(2020, 1, 1, tzinfo=timezone.utc)
    r = Reminder(task_id=t.id, remind_at=passado)
    svc.add(r)
    svc.flush()

    due = task_service.get_due_reminders()

    match = next((entry for entry in due if entry[0].id == r.id), None)
    assert match is not None
    assert match[2] == 77777


def test_mark_reminder_sent_marca_enviado(svc):
    user = _user(svc)
    t = _task(svc, user)
    r = Reminder(task_id=t.id, remind_at=datetime(2020, 1, 1, tzinfo=timezone.utc))
    svc.add(r)
    svc.flush()

    task_service.mark_reminder_sent(r.id)
    svc.refresh(r)

    assert r.sent is True


# ---------------------------------------------------------------------------
# F5 — get_couple_tasks (US-19)
# ---------------------------------------------------------------------------

def test_get_couple_tasks_retorna_tarefas_da_lista_casal(svc):
    user = _user(svc)
    task_service._create_initial_lists(svc, user)
    svc.flush()
    casal = svc.scalar(
        select(TaskList).where(TaskList.user_id == user.id, TaskList.is_couple.is_(True))
    )
    _task(svc, user, title="Comprar pão", list_id=casal.id)
    _task(svc, user, title="Pagar aluguel", list_id=casal.id)
    _task(svc, user, title="Na inbox")

    tasks, group_id = task_service.get_couple_tasks(user.telegram_chat_id)

    assert len(tasks) == 2
    assert all(t.list_id == casal.id for t in tasks)
    assert group_id is None


def test_get_couple_tasks_retorna_group_id_configurado(svc):
    user = _user(svc)
    task_service._create_initial_lists(svc, user)
    svc.flush()
    task_service.update_config(user.telegram_chat_id, couple_group_chat_id=-100999)

    _, group_id = task_service.get_couple_tasks(user.telegram_chat_id)

    assert group_id == -100999


def test_get_couple_tasks_ignora_concluidas(svc):
    user = _user(svc)
    task_service._create_initial_lists(svc, user)
    svc.flush()
    casal = svc.scalar(
        select(TaskList).where(TaskList.user_id == user.id, TaskList.is_couple.is_(True))
    )
    _task(svc, user, title="Aberta", list_id=casal.id)
    _task(svc, user, title="Concluída", list_id=casal.id, status="concluida")

    tasks, _ = task_service.get_couple_tasks(user.telegram_chat_id)

    assert len(tasks) == 1
    assert tasks[0].title == "Aberta"


def test_get_couple_tasks_lista_vazia_retorna_lista_vazia(svc):
    user = _user(svc)
    task_service._create_initial_lists(svc, user)
    svc.flush()

    tasks, _ = task_service.get_couple_tasks(user.telegram_chat_id)

    assert tasks == []


def test_get_couple_tasks_usuario_inexistente(svc):
    tasks, group_id = task_service.get_couple_tasks(999888)

    assert tasks == []
    assert group_id is None


# ---------------------------------------------------------------------------
# F5 — search_tasks (US-22)
# ---------------------------------------------------------------------------

def test_search_tasks_encontra_por_titulo(svc):
    user = _user(svc)
    t = _task(svc, user, title="Reuniao de planejamento")
    _task(svc, user, title="Comprar cafe")

    resultado = task_service.search_tasks(user.telegram_chat_id, "reuniao")

    assert len(resultado) == 1
    assert resultado[0].id == t.id


def test_search_tasks_parcial_no_titulo(svc):
    user = _user(svc)
    t = _task(svc, user, title="Preparar apresentacao do projeto")

    resultado = task_service.search_tasks(user.telegram_chat_id, "apresentacao")

    assert len(resultado) == 1
    assert resultado[0].id == t.id


def test_search_tasks_nao_retorna_concluidas(svc):
    user = _user(svc)
    _task(svc, user, title="Fazer relatorio", status="concluida")

    resultado = task_service.search_tasks(user.telegram_chat_id, "relatorio")

    assert resultado == []


def test_search_tasks_nao_retorna_arquivadas(svc):
    user = _user(svc)
    _task(svc, user, title="Fazer relatorio", status="arquivada")

    resultado = task_service.search_tasks(user.telegram_chat_id, "relatorio")

    assert resultado == []


def test_search_tasks_retorna_aguardando(svc):
    user = _user(svc)
    t = _task(svc, user, title="Aguardando aprovacao", status="aguardando")

    resultado = task_service.search_tasks(user.telegram_chat_id, "aprovacao")

    assert len(resultado) == 1
    assert resultado[0].id == t.id


def test_search_tasks_sem_resultado_retorna_lista_vazia(svc):
    user = _user(svc)
    _task(svc, user, title="Outra coisa")

    resultado = task_service.search_tasks(user.telegram_chat_id, "inexistente")

    assert resultado == []


def test_search_tasks_usuario_inexistente_retorna_lista_vazia(svc):
    assert task_service.search_tasks(999888, "qualquer") == []


def test_search_tasks_respeita_limite_20(svc):
    user = _user(svc)
    for i in range(25):
        _task(svc, user, title=f"Tarefa reuniao {i}")

    resultado = task_service.search_tasks(user.telegram_chat_id, "reuniao")

    assert len(resultado) <= 20


def test_search_tasks_encontra_por_notas(svc):
    user = _user(svc)
    now = datetime.now(timezone.utc)
    t = Task(
        user_id=user.id,
        title="Tarefa generica",
        notes="Detalhe importante sobre o projeto",
        status="aberta",
        sort_order=0,
        created_at=now,
        last_touched_at=now,
    )
    svc.add(t)
    svc.flush()

    resultado = task_service.search_tasks(user.telegram_chat_id, "projeto")

    assert len(resultado) == 1
    assert resultado[0].id == t.id


# ---------------------------------------------------------------------------
# v1.10.0 — get_all_open_tasks: oculta recorrentes futuras (bug /tudo)
# ---------------------------------------------------------------------------

def test_get_all_open_tasks_oculta_recorrente_futura(svc):
    """/tudo não deve mostrar medicação de amanhã (próxima ocorrência recorrente)."""
    user = _user(svc)
    lst = _list(svc, user, name="Saude")
    now = datetime.now(timezone.utc)
    amanha = now + timedelta(days=1)

    # Tarefa recorrente com due_at amanhã (já foi concluída hoje, nova ocorrência criada)
    t_rec = _task_f3(svc, user, title="Remedio amanha", list_id=lst.id,
                     due_at=amanha, status="aberta")
    t_rec.recurrence = "daily"
    svc.flush()
    _task_f3(svc, user, title="Tarefa sem recorrencia", list_id=lst.id)

    groups = task_service.get_all_open_tasks(user.telegram_chat_id)

    titulos = [t.title for g in groups for t in g.tasks]
    assert "Remedio amanha" not in titulos
    assert "Tarefa sem recorrencia" in titulos


def test_get_all_open_tasks_mostra_recorrente_hoje(svc):
    """Tarefa recorrente com due_at hoje deve aparecer no /tudo."""
    user = _user(svc)
    lst = _list(svc, user, name="Saude")
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("America/Fortaleza")
    hoje_meio_dia = datetime.now(tz).replace(hour=12, minute=0, second=0, microsecond=0)

    t = _task_f3(svc, user, title="Remedio hoje", list_id=lst.id, due_at=hoje_meio_dia)
    t.recurrence = "daily"
    svc.flush()

    groups = task_service.get_all_open_tasks(user.telegram_chat_id)

    titulos = [task.title for g in groups for task in g.tasks]
    assert "Remedio hoje" in titulos


def test_get_all_open_tasks_mostra_nao_recorrente_com_prazo_futuro(svc):
    """Tarefa normal (sem recorrência) com prazo futuro ainda aparece no /tudo."""
    user = _user(svc)
    lst = _list(svc, user, name="Trabalho")
    futuro = datetime.now(timezone.utc) + timedelta(days=7)

    _task_f3(svc, user, title="Entrega semana que vem", list_id=lst.id, due_at=futuro)

    groups = task_service.get_all_open_tasks(user.telegram_chat_id)

    titulos = [t.title for g in groups for t in g.tasks]
    assert "Entrega semana que vem" in titulos


# ---------------------------------------------------------------------------
# v1.10.0 — get_due_waiting_tasks: desbloqueio automático por data
# ---------------------------------------------------------------------------

def test_get_due_waiting_tasks_retorna_aguardando_vencida(svc):
    user = _user(svc)
    passado = datetime(2020, 1, 1, tzinfo=timezone.utc)
    t = _task(svc, user)
    t.status = "aguardando"
    t.due_at = passado
    t.waiting_since = passado
    svc.flush()

    result = task_service.get_due_waiting_tasks()

    ids = [task.id for task, _ in result]
    assert t.id in ids


def test_get_due_waiting_tasks_nao_retorna_futuras(svc):
    user = _user(svc)
    futuro = datetime(2099, 12, 31, tzinfo=timezone.utc)
    t = _task(svc, user)
    t.status = "aguardando"
    t.due_at = futuro
    t.waiting_since = datetime.now(timezone.utc)
    svc.flush()

    result = task_service.get_due_waiting_tasks()

    ids = [task.id for task, _ in result]
    assert t.id not in ids


def test_get_due_waiting_tasks_nao_retorna_sem_due_at(svc):
    user = _user(svc)
    t = _task(svc, user)
    t.status = "aguardando"
    t.waiting_since = datetime(2020, 1, 1, tzinfo=timezone.utc)
    svc.flush()

    result = task_service.get_due_waiting_tasks()

    ids = [task.id for task, _ in result]
    assert t.id not in ids


def test_get_due_waiting_tasks_nao_retorna_tarefas_abertas(svc):
    user = _user(svc)
    passado = datetime(2020, 1, 1, tzinfo=timezone.utc)
    t = _task(svc, user)
    t.status = "aberta"
    t.due_at = passado
    svc.flush()

    result = task_service.get_due_waiting_tasks()

    ids = [task.id for task, _ in result]
    assert t.id not in ids


def test_get_due_waiting_tasks_inclui_chat_id(svc):
    user = _user(svc, chat_id=88888)
    passado = datetime(2020, 6, 1, tzinfo=timezone.utc)
    t = _task(svc, user)
    t.status = "aguardando"
    t.due_at = passado
    t.waiting_since = passado
    svc.flush()

    result = task_service.get_due_waiting_tasks()

    match = next((entry for entry in result if entry[0].id == t.id), None)
    assert match is not None
    assert match[1] == 88888


# ---------------------------------------------------------------------------
# v1.10.0 — find_list_by_term: /ver <lista>
# ---------------------------------------------------------------------------

def test_find_list_by_term_slug_exato(svc):
    user = _user(svc)
    _list(svc, user, name="Trabalho")

    result = task_service.find_list_by_term(user.telegram_chat_id, "trabalho")

    assert result is not None
    assert result.name == "Trabalho"


def test_find_list_by_term_nome_parcial(svc):
    user = _user(svc)
    _list(svc, user, name="Casa (solo)")

    result = task_service.find_list_by_term(user.telegram_chat_id, "solo")

    assert result is not None
    assert "solo" in result.name.lower()


def test_find_list_by_term_case_insensitive(svc):
    user = _user(svc)
    _list(svc, user, name="Saúde")

    result = task_service.find_list_by_term(user.telegram_chat_id, "SAÚDE")

    assert result is not None
    assert result.name == "Saúde"


def test_find_list_by_term_sem_acento(svc):
    user = _user(svc)
    _list(svc, user, name="Saúde")

    result = task_service.find_list_by_term(user.telegram_chat_id, "saude")

    assert result is not None
    assert result.name == "Saúde"


def test_find_list_by_term_nao_encontrado_retorna_none(svc):
    user = _user(svc)
    _list(svc, user, name="Trabalho")

    result = task_service.find_list_by_term(user.telegram_chat_id, "inexistente")

    assert result is None


def test_find_list_by_term_usuario_inexistente_retorna_none(svc):
    result = task_service.find_list_by_term(999888, "qualquer")

    assert result is None


def test_find_list_by_term_nao_retorna_arquivada(svc):
    user = _user(svc)
    lst = _list(svc, user, name="Arquivada")
    lst.archived = True
    svc.flush()

    result = task_service.find_list_by_term(user.telegram_chat_id, "arquivada")

    assert result is None


# ---------------------------------------------------------------------------
# Notas em tarefa (Sugestao 2)
# ---------------------------------------------------------------------------

def test_update_task_attrs_salva_nota(svc):
    user = _user(svc)
    task = _task(svc, user)

    result = task_service.update_task_attrs(task.id, notes="Protocolo 12345")

    svc.refresh(task)
    assert result is not None
    assert task.notes == "Protocolo 12345"


def test_update_task_attrs_apaga_nota(svc):
    user = _user(svc)
    task = _task(svc, user)
    task.notes = "Nota existente"
    svc.flush()

    task_service.update_task_attrs(task.id, notes=None)

    svc.refresh(task)
    assert task.notes is None


def test_update_task_attrs_sobrescreve_nota(svc):
    user = _user(svc)
    task = _task(svc, user)
    task.notes = "Nota antiga"
    svc.flush()

    task_service.update_task_attrs(task.id, notes="Nota nova")

    svc.refresh(task)
    assert task.notes == "Nota nova"


# ---------------------------------------------------------------------------
# Conquistas (Sugestao 3)
# ---------------------------------------------------------------------------

def test_conquistas_sem_tarefas_retorna_zeros(svc):
    user = _user(svc)

    stats = task_service.get_conquistas(user.telegram_chat_id)

    assert stats["hoje"] == 0
    assert stats["ontem"] == 0
    assert stats["semana"] == 0
    assert stats["dias_ativos"] == 0


def test_conquistas_usuario_inexistente_retorna_zeros(svc):
    stats = task_service.get_conquistas(999888777)

    assert stats["semana"] == 0


def test_conquistas_conta_tarefa_concluida_hoje(svc):
    user = _user(svc)
    task = _task(svc, user)
    task.status = "concluida"
    task.completed_at = datetime.now(timezone.utc)
    svc.flush()

    stats = task_service.get_conquistas(user.telegram_chat_id)

    assert stats["hoje"] == 1
    assert stats["semana"] == 1
    assert stats["dias_ativos"] == 1


def test_conquistas_conta_tarefa_concluida_ontem(svc):
    user = _user(svc)
    task = _task(svc, user)
    task.status = "concluida"
    task.completed_at = datetime.now(timezone.utc) - timedelta(days=1)
    svc.flush()

    stats = task_service.get_conquistas(user.telegram_chat_id)

    assert stats["hoje"] == 0
    assert stats["ontem"] == 1
    assert stats["semana"] == 1


def test_conquistas_ignora_tarefa_mais_de_7_dias(svc):
    user = _user(svc)
    task = _task(svc, user)
    task.status = "concluida"
    task.completed_at = datetime.now(timezone.utc) - timedelta(days=8)
    svc.flush()

    stats = task_service.get_conquistas(user.telegram_chat_id)

    assert stats["semana"] == 0


def test_conquistas_dias_ativos_varios_no_mesmo_dia(svc):
    user = _user(svc)
    agora = datetime.now(timezone.utc)
    for _ in range(3):
        t = _task(svc, user)
        t.status = "concluida"
        t.completed_at = agora
        svc.flush()

    stats = task_service.get_conquistas(user.telegram_chat_id)

    assert stats["semana"] == 3
    assert stats["dias_ativos"] == 1
