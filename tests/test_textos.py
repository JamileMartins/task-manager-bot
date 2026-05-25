"""Testes das mensagens centralizadas (utils/textos.py)."""
from __future__ import annotations

import pytest

from src.utils import textos


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
])
def test_constante_nao_vazia(constante):
    valor = getattr(textos, constante)
    assert isinstance(valor, str)
    assert valor.strip() != ""


def test_ajuda_menciona_comandos_essenciais():
    for cmd in ["/agora", "/listas", "/inbox", "/ping", "/reiniciar"]:
        assert cmd in textos.MSG_AJUDA, f"Comando {cmd} ausente em MSG_AJUDA"


def test_boas_vindas_menciona_comandos_iniciais():
    for cmd in ["/agora", "/listas", "/ajuda"]:
        assert cmd in textos.MSG_BOAS_VINDAS, f"Comando {cmd} ausente em MSG_BOAS_VINDAS"
