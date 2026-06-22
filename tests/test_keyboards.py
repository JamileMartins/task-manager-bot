"""Testes de navegação dos teclados inline (utils/keyboards.py).

Garante que botões de cancelar/voltar dentro do fluxo de uma lista retornam
exatamente um nível (para a lista ou tarefa de origem), e não para o menu
raiz ("Suas listas") — bug original: o submenu de gerenciamento de lista
(⚙️) usava um callback genérico ("cancel_mgmt") que sempre resetava para o
menu raiz, descartando a lista que estava sendo visualizada.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

from src.utils import keyboards


def _buttons(markup):
    """Achata o teclado (lista de linhas) em uma lista única de botões."""
    return [btn for row in markup.inline_keyboard for btn in row]


def _find(markup, text_substring):
    for btn in _buttons(markup):
        if text_substring in btn.text:
            return btn
    raise AssertionError(f"Botão contendo '{text_substring}' não encontrado em {markup}")


def _mock_task(**kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "title": "Tarefa teste",
        "list_id": None,
        "status": "aberta",
        "quadrant": None,
        "energy": None,
        "estimate_min": None,
        "recurrence": None,
        "notes": None,
        "couple_id": None,
        "couple_joint": False,
        "assigned_to": None,
        "category": None,
        "blocked_by_task_id": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# Submenu "⚙️ Gerenciar lista" e seus filhos — Cancelar deve voltar para a
# lista específica, não para o menu raiz de listas.
# ---------------------------------------------------------------------------

def test_gerenciar_lista_cancelar_volta_para_a_lista():
    list_id = uuid.uuid4()
    kb = keyboards.kb_gerenciar_lista(list_id)
    botao = _find(kb, "Cancelar")
    assert botao.callback_data == f"view_list:{list_id}"


def test_janela_tempo_cancelar_volta_para_a_lista():
    list_id = uuid.uuid4()
    kb = keyboards.kb_list_window_edit(list_id, current="dia")
    botao = _find(kb, "Cancelar")
    assert botao.callback_data == f"view_list:{list_id}"


def test_confirmar_arquivar_cancelar_volta_para_a_lista():
    list_id = uuid.uuid4()
    kb = keyboards.kb_confirmar_arquivar(list_id)
    botao = _find(kb, "Cancelar")
    assert botao.callback_data == f"view_list:{list_id}"


def test_submenus_de_gerenciamento_nao_usam_callback_generico_de_cancelamento():
    """Regressão: 'cancel_mgmt' sempre levava ao menu raiz, ignorando a lista atual."""
    list_id = uuid.uuid4()
    teclados = (
        keyboards.kb_gerenciar_lista(list_id),
        keyboards.kb_list_window_edit(list_id, current=None),
        keyboards.kb_confirmar_arquivar(list_id),
    )
    for kb in teclados:
        for btn in _buttons(kb):
            assert btn.callback_data != "cancel_mgmt"


# ---------------------------------------------------------------------------
# Lista (kb_tasks) e Inbox — "Voltar" sai para o menu raiz, que é de fato a
# única origem possível dessas telas (1 nível acima).
# ---------------------------------------------------------------------------

def test_lista_voltar_vai_para_menu_de_listas():
    kb = keyboards.kb_tasks([], list_id=uuid.uuid4())
    botao = _find(kb, "Voltar")
    assert botao.callback_data == "back_to_lists"


def test_inbox_voltar_vai_para_menu_de_listas():
    kb = keyboards.kb_inbox([])
    botao = _find(kb, "Voltar")
    assert botao.callback_data == "back_to_lists"


# ---------------------------------------------------------------------------
# Detalhe de tarefa — "Voltar" retorna para a lista/inbox de origem (1 nível).
# ---------------------------------------------------------------------------

def test_detalhe_tarefa_com_lista_volta_para_a_lista():
    list_id = uuid.uuid4()
    task = _mock_task(list_id=list_id)
    kb = keyboards.kb_task_detail(task, listas=[])
    botao = _find(kb, "Voltar")
    assert botao.callback_data == f"view_list:{list_id}"


def test_detalhe_tarefa_sem_lista_volta_para_inbox():
    task = _mock_task(list_id=None)
    kb = keyboards.kb_task_detail(task, listas=[])
    botao = _find(kb, "Voltar")
    assert botao.callback_data == "view_inbox"


def test_remover_tarefa_cancelar_volta_para_detalhe():
    task_id = uuid.uuid4()
    kb = keyboards.kb_confirmar_remover(task_id)
    botao = _find(kb, "Cancelar")
    assert botao.callback_data == f"task_dt:{task_id}"


def test_mover_tarefa_cancelar_volta_para_detalhe():
    task_id = str(uuid.uuid4())
    kb = keyboards.kb_mover_tarefa(task_id, listas=[])
    botao = _find(kb, "Cancelar")
    assert botao.callback_data == f"task_dt:{task_id}"


def test_nota_cancelar_volta_para_detalhe():
    task_id = str(uuid.uuid4())
    kb = keyboards.kb_nota(task_id, has_notes=False)
    botao = _find(kb, "Cancelar")
    assert botao.callback_data == f"task_note_cancel:{task_id}"


def test_titulo_cancelar_volta_para_detalhe():
    task_id = str(uuid.uuid4())
    kb = keyboards.kb_cancelar(task_id)
    botao = _find(kb, "Cancelar")
    assert botao.callback_data == f"task_title_cancel:{task_id}"


# ---------------------------------------------------------------------------
# /config — "← Voltar" dos submenus de horário/dia volta para o menu de
# configuração (cfg_back), nunca reseta para fora do /config.
# ---------------------------------------------------------------------------

def test_config_submenus_voltam_para_o_menu_de_config():
    for kb in (
        keyboards.kb_config_daily_time(),
        keyboards.kb_config_review_dow(),
        keyboards.kb_config_review_time(),
    ):
        botao = _find(kb, "Voltar")
        assert botao.callback_data == "cfg_back"
