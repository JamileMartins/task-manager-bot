"""Testes unitários de task_service sem dependência do Telegram."""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select

from src.db.models import Config, Task, TaskList, User
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
