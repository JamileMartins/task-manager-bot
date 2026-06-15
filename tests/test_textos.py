"""Testes das mensagens centralizadas (utils/textos.py)."""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from src.utils import textos
from src.version import __version__


def _mock_task(**kwargs):
    defaults = {
        "title": "Tarefa teste",
        "task_list": None,
        "quadrant": None,
        "energy": None,
        "estimate_min": None,
        "status": "aberta",
        "blocker_type": None,
        "blocker_is_external": None,
        "due_at": None,
        "recurrence": None,
        "next_step": None,
        "notes": None,
        "completed_at": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# Variantes sorteadas — testa todas as possibilidades via monkeypatching
# ---------------------------------------------------------------------------

_VARIANTES_CAPTURA = {"Anotado ✅", "Guardado. Pode esquecer que eu lembro 🧠", "Tá na lista ✅"}
_VARIANTES_CONCLUSAO = {"Feito ✅", "Boa! Menos uma 💪", "Concluído ✅ Tá indo bem.", "Pronto ✅ Pode comemorar essa."}


@pytest.mark.parametrize("indice", range(len(_VARIANTES_CAPTURA)))
def test_captura_confirmacao_cobre_todas_variantes(monkeypatch, indice):
    variantes = sorted(_VARIANTES_CAPTURA)
    monkeypatch.setattr("src.utils.textos.random.choice", lambda seq: seq[indice % len(seq)])
    resultado = textos.msg_captura_confirmacao()
    assert resultado in _VARIANTES_CAPTURA


def test_captura_confirmacao_nunca_vazia():
    for _ in range(20):
        assert textos.msg_captura_confirmacao().strip() != ""


@pytest.mark.parametrize("indice", range(len(_VARIANTES_CONCLUSAO)))
def test_conclusao_cobre_todas_variantes(monkeypatch, indice):
    monkeypatch.setattr("src.utils.textos.random.choice", lambda seq: seq[indice % len(seq)])
    resultado = textos.msg_conclusao()
    assert resultado in _VARIANTES_CONCLUSAO


def test_conclusao_contem_confirmacao_visual():
    """Toda variante deve ter ✅ ou 💪 para reforço visual."""
    for _ in range(50):
        msg = textos.msg_conclusao()
        assert "✅" in msg or "💪" in msg


# ---------------------------------------------------------------------------
# msg_ping
# ---------------------------------------------------------------------------

def test_ping_contem_timestamp():
    resultado = textos.msg_ping("25/05 14:32")
    assert "25/05 14:32" in resultado
    assert "✅" in resultado


def test_ping_formato_completo():
    resultado = textos.msg_ping("01/01 00:00")
    assert resultado == "Funcionando ✅ — 01/01 00:00"


# ---------------------------------------------------------------------------
# msg_inbox_titulo — singular e plural
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("n,esperado", [
    (1, "📥 Caixa de entrada (1 item):"),
    (2, "📥 Caixa de entrada (2 itens):"),
    (10, "📥 Caixa de entrada (10 itens):"),
    (0, "📥 Caixa de entrada (0 itens):"),
])
def test_inbox_titulo_singular_plural(n, esperado):
    assert textos.msg_inbox_titulo(n) == esperado


# ---------------------------------------------------------------------------
# lista_emoji
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("slug,emoji", [
    ("trabalho", "💼"),
    ("projetos", "📁"),
    ("casa-solo", "🏠"),
    ("casa-casal", "🏠"),
    ("saude", "💚"),
    ("ideias", "💡"),
])
def test_lista_emoji_slugs_conhecidos(slug, emoji):
    assert textos.lista_emoji(slug) == emoji


def test_lista_emoji_slug_desconhecido_retorna_default():
    assert textos.lista_emoji("qualquer-coisa") == "📋"
    assert textos.lista_emoji("") == "📋"


# ---------------------------------------------------------------------------
# Mensagens de template com .format()
# ---------------------------------------------------------------------------

def test_msg_lista_vazia_substitui_nome():
    resultado = textos.MSG_LISTA_VAZIA.format(nome="Trabalho")
    assert "Trabalho" in resultado


def test_msg_lista_criada_substitui_nome():
    resultado = textos.MSG_LISTA_CRIADA.format(nome="Projetos")
    assert "Projetos" in resultado
    assert "✅" in resultado


def test_msg_lista_renomeada_substitui_nome():
    resultado = textos.MSG_LISTA_RENOMEADA.format(nome="Novo Nome")
    assert "Novo Nome" in resultado


def test_msg_lista_arquivada_menciona_tarefas_mantidas():
    resultado = textos.MSG_LISTA_ARQUIVADA.format(nome="Saúde")
    assert "Saúde" in resultado
    assert "mantidas" in resultado.lower() or "mantidas" in resultado


def test_msg_confirmar_arquivar_explica_consequencia():
    resultado = textos.MSG_CONFIRMAR_ARQUIVAR.format(nome="Ideias")
    assert "Ideias" in resultado
    assert "tarefas" in resultado.lower()


# ---------------------------------------------------------------------------
# Constantes obrigatórias existem e são não-vazias
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("constante", [
    "MSG_BOAS_VINDAS",
    "MSG_AJUDA",
    "MSG_NAO_AUTORIZADO",
    "MSG_ERRO_GENERICO",
    "MSG_CAPTURA_FALLBACK",
    "MSG_DESFAZER_OK",
    "MSG_SUAS_LISTAS",
    "MSG_INBOX_VAZIA",
    "MSG_CANCELADO",
    "MSG_REINICIANDO",
    "MSG_CLASSIFICANDO",
    "MSG_AGORA_NADA",
    "MSG_DIARIO_VAZIO",
    "MSG_REVISAO_NADA",
    "MSG_CASAL_VAZIA",
    "MSG_CASAL_SEM_GRUPO",
    "MSG_BUSCA_SEM_TERMO",
    "MSG_BUSCA_VAZIA",
])
def test_constante_nao_vazia(constante):
    valor = getattr(textos, constante)
    assert isinstance(valor, str)
    assert valor.strip() != ""


def test_ajuda_menciona_comandos_essenciais():
    for cmd in ["/agora", "/listas", "/inbox", "/ping", "/reiniciar", "/casal", "/buscar"]:
        assert cmd in textos.MSG_AJUDA, f"Comando {cmd} ausente em MSG_AJUDA"


def test_boas_vindas_menciona_comandos_iniciais():
    for cmd in ["/agora", "/listas", "/ajuda"]:
        assert cmd in textos.MSG_BOAS_VINDAS, f"Comando {cmd} ausente em MSG_BOAS_VINDAS"


# ---------------------------------------------------------------------------
# F2 — msg_classificacao_resumo
# ---------------------------------------------------------------------------

def test_classificacao_resumo_contem_titulo():
    tarefas = [{"titulo": "Ligar pro dentista", "lista_sugerida": "Saúde",
                "quadrante_sugerido": 2, "estimativa_min": 15, "energia": "baixa",
                "impedimento": None, "impedimento_externo": False, "proximo_passo": None}]
    resultado = textos.msg_classificacao_resumo(tarefas)
    assert "Ligar pro dentista" in resultado


def test_classificacao_resumo_conta_tarefas_no_header():
    tarefas = [
        {"titulo": "T1", "lista_sugerida": None, "quadrante_sugerido": None,
         "estimativa_min": None, "energia": None, "impedimento": None,
         "impedimento_externo": False, "proximo_passo": None},
        {"titulo": "T2", "lista_sugerida": None, "quadrante_sugerido": None,
         "estimativa_min": None, "energia": None, "impedimento": None,
         "impedimento_externo": False, "proximo_passo": None},
    ]
    resultado = textos.msg_classificacao_resumo(tarefas)
    assert "2 tarefas" in resultado


def test_classificacao_resumo_singular_uma_tarefa():
    tarefas = [{"titulo": "Única", "lista_sugerida": None, "quadrante_sugerido": None,
                "estimativa_min": None, "energia": None, "impedimento": None,
                "impedimento_externo": False, "proximo_passo": None}]
    resultado = textos.msg_classificacao_resumo(tarefas)
    assert "1 tarefa" in resultado


def test_classificacao_resumo_mostra_lista():
    tarefas = [{"titulo": "Tarefa", "lista_sugerida": "Trabalho",
                "quadrante_sugerido": None, "estimativa_min": None, "energia": None,
                "impedimento": None, "impedimento_externo": False, "proximo_passo": None}]
    resultado = textos.msg_classificacao_resumo(tarefas)
    assert "Trabalho" in resultado


def test_classificacao_resumo_inbox_quando_sem_lista():
    tarefas = [{"titulo": "Tarefa", "lista_sugerida": None,
                "quadrante_sugerido": None, "estimativa_min": None, "energia": None,
                "impedimento": None, "impedimento_externo": False, "proximo_passo": None}]
    resultado = textos.msg_classificacao_resumo(tarefas)
    assert "Inbox" in resultado


def test_classificacao_resumo_mostra_indicador_aguardando():
    tarefas = [{"titulo": "Depende de alguém", "lista_sugerida": None,
                "quadrante_sugerido": None, "estimativa_min": None, "energia": None,
                "impedimento": "pessoa", "impedimento_externo": True, "proximo_passo": None}]
    resultado = textos.msg_classificacao_resumo(tarefas)
    assert "aguardando" in resultado.lower()


def test_classificacao_resumo_mostra_proximo_passo_vaga_grande():
    tarefas = [{"titulo": "Grande projeto", "lista_sugerida": None,
                "quadrante_sugerido": None, "estimativa_min": None, "energia": None,
                "impedimento": "vaga_grande", "impedimento_externo": False,
                "proximo_passo": "Abrir documento e escrever o título"}]
    resultado = textos.msg_classificacao_resumo(tarefas)
    assert "Abrir documento" in resultado


# ---------------------------------------------------------------------------
# F3 — msg_agora_tarefa / msg_agora_adiada
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("days,esperado", [
    (1, "amanhã"),
    (3, "3 dias"),
    (7, "próxima semana"),
])
def test_agora_adiada_menciona_prazo(days, esperado):
    resultado = textos.msg_agora_adiada(days)
    assert esperado in resultado.lower()


def test_agora_tarefa_contem_titulo():
    task = _mock_task(title="Preparar apresentação")
    resultado = textos.msg_agora_tarefa(task)
    assert "Preparar apresentação" in resultado


def test_agora_tarefa_mostra_lista():
    lista = SimpleNamespace(name="Trabalho")
    task = _mock_task(title="Reunião", task_list=lista)
    resultado = textos.msg_agora_tarefa(task)
    assert "Trabalho" in resultado


def test_agora_tarefa_fallback_mostra_mensagem_gentil():
    task = _mock_task(title="Tarefa")
    resultado = textos.msg_agora_tarefa(task, fallback=True)
    assert "perfeito" in resultado.lower() or "que tal" in resultado.lower()


def test_agora_tarefa_sem_lista_mostra_inbox():
    task = _mock_task(title="Tarefa", task_list=None)
    resultado = textos.msg_agora_tarefa(task)
    assert "Inbox" in resultado


# ---------------------------------------------------------------------------
# F4 — msg_diario_focos / msg_revisao_* / msg_config_status
# ---------------------------------------------------------------------------

def test_diario_focos_contem_titulos():
    t1 = SimpleNamespace(title="Reunião", estimate_min=30)
    t2 = SimpleNamespace(title="Relatório", estimate_min=None)
    resultado = textos.msg_diario_focos([t1], [t2])
    assert "Reunião" in resultado
    assert "Relatório" in resultado


def test_diario_focos_mostra_estimativa_quando_presente():
    t = SimpleNamespace(title="Tarefa", estimate_min=45)
    resultado = textos.msg_diario_focos([t], [])
    assert "45min" in resultado


def test_diario_focos_sem_estimativa_nao_quebra():
    t = SimpleNamespace(title="Tarefa", estimate_min=None)
    resultado = textos.msg_diario_focos([], [t])
    assert "Tarefa" in resultado


def test_revisao_abertura_contem_contagem():
    resultado = textos.msg_revisao_abertura(5)
    assert "5" in resultado


def test_revisao_abertura_singular():
    resultado = textos.msg_revisao_abertura(1)
    assert "1 tarefa" in resultado


def test_revisao_tarefa_contem_titulo_e_dias():
    task = SimpleNamespace(title="Projeto parado")
    resultado = textos.msg_revisao_tarefa(task, 14)
    assert "Projeto parado" in resultado
    assert "14" in resultado


def test_revisao_espera_contem_titulo_e_dias():
    task = SimpleNamespace(title="Aguardando retorno")
    resultado = textos.msg_revisao_espera(task, 20)
    assert "Aguardando retorno" in resultado
    assert "20" in resultado


@pytest.mark.parametrize("stats,esperado", [
    ({"reagendadas": 2}, "reagendou 2"),
    ({"arquivadas": 1}, "arquivou 1"),
    ({"destravadas": 3}, "destravou 3"),
    ({}, "Tudo mantido"),
])
def test_revisao_encerramento_menciona_acao(stats, esperado):
    resultado = textos.msg_revisao_encerramento(stats)
    assert esperado.lower() in resultado.lower()


def test_config_status_desativado_sem_config():
    resultado = textos.msg_config_status(None)
    assert "desativado" in resultado
    assert "desativada" in resultado


def test_config_status_mostra_horario_diario():
    from datetime import time
    cfg = SimpleNamespace(
        daily_summary_time=time(7, 30),
        weekly_review_dow=None,
        weekly_review_time=None,
        couple_group_chat_id=None,
    )
    resultado = textos.msg_config_status(cfg)
    assert "07:30" in resultado


def test_config_status_mostra_dia_revisao():
    from datetime import time
    cfg = SimpleNamespace(
        daily_summary_time=None,
        weekly_review_dow=4,  # sexta
        weekly_review_time=time(19, 0),
        couple_group_chat_id=None,
    )
    resultado = textos.msg_config_status(cfg)
    assert "sexta" in resultado.lower()
    assert "19:00" in resultado


def test_config_status_mostra_grupo_configurado():
    cfg = SimpleNamespace(
        daily_summary_time=None,
        weekly_review_dow=None,
        weekly_review_time=None,
        couple_group_chat_id=-100123456,
    )
    resultado = textos.msg_config_status(cfg)
    assert "configurado" in resultado.lower()


def test_config_status_mostra_grupo_nao_configurado():
    cfg = SimpleNamespace(
        daily_summary_time=None,
        weekly_review_dow=None,
        weekly_review_time=None,
        couple_group_chat_id=None,
    )
    resultado = textos.msg_config_status(cfg)
    assert "não configurado" in resultado.lower()


# ---------------------------------------------------------------------------
# F5 — msg_casal / msg_busca
# ---------------------------------------------------------------------------

def test_msg_casal_contem_titulos():
    t1 = _mock_task(title="Comprar pão")
    t2 = _mock_task(title="Pagar aluguel")
    resultado = textos.msg_casal([t1, t2])
    assert "Comprar pão" in resultado
    assert "Pagar aluguel" in resultado


def test_msg_casal_contem_contagem():
    tasks = [_mock_task(title=f"T{i}") for i in range(3)]
    resultado = textos.msg_casal(tasks)
    assert "3 tarefas" in resultado


def test_msg_casal_singular():
    resultado = textos.msg_casal([_mock_task(title="Única")])
    assert "1 tarefa" in resultado


def test_msg_casal_mostra_estimativa():
    task = _mock_task(title="Comprar legumes", estimate_min=20)
    resultado = textos.msg_casal([task])
    assert "20min" in resultado


def test_msg_casal_mostra_criador_e_data():
    import uuid
    criador = uuid.uuid4()
    task = _mock_task(
        title="Comprar tinta",
        created_by=criador,
        created_at=datetime(2026, 6, 12, 17, 30, tzinfo=timezone.utc),  # 14:30 BRT
    )
    resultado = textos.msg_casal([task], names={criador: "Jamile Martins"})
    assert "Comprar tinta" in resultado
    assert "Jamile" in resultado          # primeiro nome do criador
    assert "12/06 às 14:30" in resultado  # data/hora em BRT


def test_msg_casal_sem_criador_mostra_so_data():
    task = _mock_task(
        title="Tarefa antiga",
        created_by=None,
        created_at=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),  # 09:00 BRT
    )
    resultado = textos.msg_casal([task])
    assert "01/06 às 09:00" in resultado


def test_msg_task_detail_exibe_recorrencia_quinzenal():
    t = _mock_task(title="Pagar fatura", recurrence="quinzenal", blocker_note=None, category=None)
    resultado = textos.msg_task_detail(t)
    assert "Quinzenal" in resultado


def test_periodo_label_mensal():
    label = textos.periodo_label("mes", 0)
    # Ex.: "junho/2026" — contém uma barra e um nome de mês em PT-BR.
    assert "/" in label
    assert any(m in label for m in textos._MESES_PT)


def test_periodo_label_diaria_contem_dia_da_semana():
    label = textos.periodo_label("dia", 0)
    assert "/" in label
    assert "(" in label and ")" in label


def test_periodo_label_semanal_tem_intervalo():
    label = textos.periodo_label("semana", 0)
    assert "semana de" in label
    assert "–" in label


def test_msg_casal_compartilhou_com_titulo():
    m = textos.msg_casal_compartilhou("Jamile Martins", 1, "Comprar tinta")
    assert "Comprar tinta" in m


def test_msg_casal_compartilhou_sem_titulo_mantem_generico():
    m = textos.msg_casal_compartilhou("Jamile", 1)
    assert m == "💞 Jamile compartilhou uma tarefa de casal com você."


def test_msg_casal_compartilhou_plural():
    m = textos.msg_casal_compartilhou("Jamile", 3)
    assert "3 tarefas" in m


def test_msg_casal_removeu_e_neutro_e_identifica_tarefa():
    m = textos.msg_casal_removeu("Jamile", "Trocar prateleira")
    assert "Trocar prateleira" in m
    assert "tirou" in m  # linguagem de remoção, não de conclusão
    assert "não foi concluída" in m  # deixa claro que NÃO foi feita


def test_msg_tarefa_removida_identifica_e_nao_conta_como_concluida():
    m = textos.msg_tarefa_removida("Comprar tinta")
    assert "Comprar tinta" in m
    assert "não contou" in m.lower()


def test_msg_confirmar_remover_tem_titulo():
    m = textos.msg_confirmar_remover("Pagar luz")
    assert "Pagar luz" in m


def test_msg_busca_contem_titulo_e_termo():
    t = _mock_task(title="Reunião mensal")
    resultado = textos.msg_busca([t], "reunião")
    assert "Reunião mensal" in resultado
    assert "reunião" in resultado


def test_msg_busca_contem_contagem():
    tasks = [_mock_task(title=f"T{i}") for i in range(2)]
    resultado = textos.msg_busca(tasks, "algo")
    assert "2 tarefas" in resultado


def test_msg_busca_singular():
    resultado = textos.msg_busca([_mock_task(title="Única")], "única")
    assert "1 tarefa" in resultado


def test_msg_busca_mostra_lista_da_tarefa():
    lista = SimpleNamespace(name="Trabalho")
    task = _mock_task(title="Preparar doc", task_list=lista)
    resultado = textos.msg_busca([task], "doc")
    assert "Trabalho" in resultado


def test_msg_busca_inbox_quando_sem_lista():
    task = _mock_task(title="Tarefa", task_list=None)
    resultado = textos.msg_busca([task], "tarefa")
    assert "Inbox" in resultado


def test_msg_busca_aguardando_mostra_icone():
    task = _mock_task(title="Aguardando", status="aguardando", task_list=None)
    resultado = textos.msg_busca([task], "aguardando")
    assert "⏳" in resultado


# ---------------------------------------------------------------------------
# /hoje e /amanha
# ---------------------------------------------------------------------------

def _mock_task_due(title, due_str=None, estimate_min=None, task_list=None):
    from datetime import datetime, timezone
    due = datetime.fromisoformat(due_str).replace(tzinfo=timezone.utc) if due_str else None
    return SimpleNamespace(
        title=title,
        due_at=due,
        estimate_min=estimate_min,
        task_list=task_list,
        quadrant=None,
    )


def test_msg_hoje_exibe_tarefas_com_prazo():
    t = _mock_task_due("Ligar pro dentista", "2026-05-26T12:00:00-03:00", estimate_min=15)
    resultado = textos.msg_hoje([t], [])
    assert "Ligar pro dentista" in resultado
    assert "Com prazo" in resultado
    assert "15min" in resultado


def test_msg_hoje_exibe_focos():
    t = _mock_task_due("Estudar para prova", estimate_min=60)
    resultado = textos.msg_hoje([], [t])
    assert "Estudar para prova" in resultado
    assert "Q1/Q2" in resultado


def test_msg_hoje_menciona_agora():
    resultado = textos.msg_hoje([], [_mock_task_due("T")])
    assert "/agora" in resultado


def test_msg_hoje_vazia_nao_e_chamada_aqui():
    assert textos.MSG_HOJE_VAZIO.strip() != ""
    assert "/agora" in textos.MSG_HOJE_VAZIO


def test_msg_amanha_exibe_tarefas():
    t = _mock_task_due("Reunião", "2026-05-27T14:00:00-03:00", estimate_min=60)
    resultado = textos.msg_amanha([t])
    assert "Reunião" in resultado
    assert "Amanhã" in resultado
    assert "60min" in resultado


def test_msg_amanha_singular():
    t = _mock_task_due("Única")
    resultado = textos.msg_amanha([t])
    assert "1 tarefa" in resultado


def test_msg_amanha_plural():
    tasks = [_mock_task_due(f"T{i}") for i in range(3)]
    resultado = textos.msg_amanha(tasks)
    assert "3 tarefas" in resultado


def test_msg_amanha_exibe_lista():
    lista = SimpleNamespace(name="Trabalho")
    t = _mock_task_due("Entregar relatório", task_list=lista)
    resultado = textos.msg_amanha([t])
    assert "Trabalho" in resultado


def test_msg_amanha_vazio_nao_e_vazia():
    assert textos.MSG_AMANHA_VAZIO.strip() != ""


@pytest.mark.parametrize("constante", ["MSG_HOJE_VAZIO", "MSG_AMANHA_VAZIO"])
def test_constantes_hoje_amanha_nao_vazias(constante):
    valor = getattr(textos, constante)
    assert isinstance(valor, str) and valor.strip() != ""


# ---------------------------------------------------------------------------
# Versão
# ---------------------------------------------------------------------------

def test_versao_no_ajuda():
    assert __version__ in textos.MSG_AJUDA


def test_versao_no_reiniciando():
    assert __version__ in textos.MSG_REINICIANDO


def test_versao_formato_semver():
    partes = __version__.split(".")
    assert len(partes) == 3
    assert all(p.isdigit() for p in partes)


# ---------------------------------------------------------------------------
# F6 — msg_medicacoes / msg_med_ok
# ---------------------------------------------------------------------------

def _mock_med(title, recurrence="daily", notes=None, completed_at=None):
    return SimpleNamespace(
        title=title,
        recurrence=recurrence,
        notes=notes,
        completed_at=completed_at,
    )


def test_medicacoes_lista_daily():
    t = _mock_med("Puran T4")
    resultado = textos.msg_medicacoes([t], [])
    assert "Puran T4" in resultado
    assert "Hoje" in resultado


def test_medicacoes_exibe_horario():
    t = _mock_med("Atentah", notes="08:00")
    resultado = textos.msg_medicacoes([t], [])
    assert "08:00" in resultado
    assert "⏰" in resultado


def test_medicacoes_sem_horario_nao_exibe_relogio():
    t = _mock_med("Citobê")
    resultado = textos.msg_medicacoes([t], [])
    assert "⏰" not in resultado


def test_medicacoes_semanal_sem_dia():
    t = _mock_med("Citobê", recurrence="weekly")
    resultado = textos.msg_medicacoes([], [t])
    assert "Citobê" in resultado
    assert "Semanal" in resultado


def test_medicacoes_semanal_com_dia():
    t = _mock_med("Citobê", recurrence="weekly:1")  # Terça
    resultado = textos.msg_medicacoes([], [t])
    assert "Terça" in resultado


@pytest.mark.parametrize("dow,nome", [
    (0, "Segunda"), (1, "Terça"), (2, "Quarta"),
    (3, "Quinta"), (4, "Sexta"), (5, "Sábado"), (6, "Domingo"),
])
def test_medicacoes_semanal_todos_os_dias(dow, nome):
    t = _mock_med("Med", recurrence=f"weekly:{dow}")
    resultado = textos.msg_medicacoes([], [t])
    assert nome in resultado


def test_medicacoes_tomadas_hoje_exibe_horario():
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("America/Fortaleza")
    completed = datetime(2026, 5, 26, 11, 30, tzinfo=timezone.utc)
    t = _mock_med("Puran T4", completed_at=completed)
    resultado = textos.msg_medicacoes([], [], completed_hoje=[t])
    assert "Tomadas hoje" in resultado
    assert "Puran T4" in resultado


def test_medicacoes_vazia_sem_secao_tomadas():
    resultado = textos.msg_medicacoes([], [], completed_hoje=None)
    assert "Tomadas hoje" not in resultado


def test_med_ok_diaria_sem_horario():
    resultado = textos.msg_med_ok("Puran T4", "daily")
    assert "diária" in resultado
    assert "✅" in resultado


def test_med_ok_diaria_com_horario():
    resultado = textos.msg_med_ok("Puran T4", "daily", med_time="08:00")
    assert "08:00" in resultado


def test_med_ok_semanal_com_dia():
    resultado = textos.msg_med_ok("Citobê", "weekly:1", dow=1)
    assert "Terça" in resultado
    assert "semanal" in resultado.lower()


@pytest.mark.parametrize("constante", [
    "MSG_MED_VAZIA",
    "MSG_MED_PEDIR_NOME",
    "MSG_MED_PEDIR_HORARIO",
    "MSG_MED_PEDIR_FREQ",
    "MSG_MED_PEDIR_DIA",
])
def test_constantes_medicacoes_nao_vazias(constante):
    valor = getattr(textos, constante)
    assert isinstance(valor, str)
    assert valor.strip() != ""
