"""Testes do serviço de classificação IA (parsing seguro e pós-processamento)."""
from __future__ import annotations

import json

import pytest

from src.services.ai_service import _tarefa_inbox, _normalizar, parse_resposta

_LISTAS = frozenset({"Trabalho", "Saúde", "Casa (solo)", "Casa (casal)", "Ideias", "Projetos"})

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json_tarefa(**kwargs) -> str:
    base = {
        "titulo": "Fazer algo",
        "lista_sugerida": "Trabalho",
        "quadrante_sugerido": 2,
        "prazo_sugerido": None,
        "estimativa_min": 30,
        "energia": "media",
        "impedimento": None,
        "impedimento_externo": False,
        "proximo_passo": None,
        "confianca": 0.9,
    }
    base.update(kwargs)
    return json.dumps({"tarefas": [base]})


# ---------------------------------------------------------------------------
# parse_resposta — JSON válido
# ---------------------------------------------------------------------------

def test_parse_json_valido_retorna_tarefa():
    resposta = _json_tarefa(titulo="Ligar pro dentista", lista_sugerida="Saúde", confianca=0.95)
    resultado = parse_resposta(resposta, "ligar pro dentista", _LISTAS)
    assert len(resultado) == 1
    assert resultado[0]["titulo"] == "Ligar pro dentista"
    assert resultado[0]["lista_sugerida"] == "Saúde"


def test_parse_multiplas_tarefas():
    tarefas = [
        {"titulo": "Comprar café", "lista_sugerida": "Casa (solo)", "confianca": 0.9,
         "quadrante_sugerido": 3, "prazo_sugerido": None, "estimativa_min": 5,
         "energia": "baixa", "impedimento": None, "impedimento_externo": False, "proximo_passo": None},
        {"titulo": "Marcar dentista", "lista_sugerida": "Saúde", "confianca": 0.92,
         "quadrante_sugerido": 2, "prazo_sugerido": None, "estimativa_min": 15,
         "energia": "baixa", "impedimento": None, "impedimento_externo": False, "proximo_passo": None},
    ]
    resposta = json.dumps({"tarefas": tarefas})
    resultado = parse_resposta(resposta, "comprar café, marcar dentista", _LISTAS)
    assert len(resultado) == 2
    assert resultado[0]["titulo"] == "Comprar café"
    assert resultado[1]["titulo"] == "Marcar dentista"


def test_parse_remove_cercas_markdown():
    resposta = "```json\n" + _json_tarefa() + "\n```"
    resultado = parse_resposta(resposta, "fazer algo", _LISTAS)
    assert len(resultado) == 1
    assert resultado[0]["titulo"] == "Fazer algo"


def test_parse_extrai_json_com_texto_ao_redor():
    resposta = "Aqui está:\n" + _json_tarefa() + "\nFim."
    resultado = parse_resposta(resposta, "fazer algo", _LISTAS)
    assert len(resultado) == 1


# ---------------------------------------------------------------------------
# parse_resposta — fallback para Inbox
# ---------------------------------------------------------------------------

def test_parse_json_invalido_retorna_fallback():
    resultado = parse_resposta("isso não é json", "texto original", _LISTAS)
    assert len(resultado) == 1
    assert resultado[0]["titulo"] == "texto original"
    assert resultado[0]["lista_sugerida"] is None
    assert resultado[0]["confianca"] == 0.0


def test_parse_json_sem_chave_tarefas_retorna_fallback():
    resultado = parse_resposta('{"resultado": []}', "texto", _LISTAS)
    assert resultado[0]["titulo"] == "texto"


def test_parse_lista_vazia_retorna_fallback():
    resultado = parse_resposta('{"tarefas": []}', "texto", _LISTAS)
    assert resultado[0]["titulo"] == "texto"


def test_parse_tarefas_sem_titulo_ignoradas_e_fallback():
    resposta = json.dumps({"tarefas": [{"lista_sugerida": "Trabalho", "confianca": 0.9}]})
    resultado = parse_resposta(resposta, "sem título", _LISTAS)
    assert resultado[0]["titulo"] == "sem título"


def test_parse_texto_vazio_retorna_fallback():
    resultado = parse_resposta("", "original", _LISTAS)
    assert resultado[0]["titulo"] == "original"


# ---------------------------------------------------------------------------
# _normalizar — pós-processamento (spec §7)
# ---------------------------------------------------------------------------

def test_normalizar_confianca_baixa_manda_para_inbox():
    t = {"titulo": "Teste", "lista_sugerida": "Trabalho", "confianca": 0.5,
         "quadrante_sugerido": 2, "prazo_sugerido": None, "estimativa_min": None,
         "energia": "media", "impedimento": None, "impedimento_externo": False, "proximo_passo": None}
    resultado = _normalizar(t, _LISTAS)
    assert resultado["lista_sugerida"] is None


def test_normalizar_lista_inexistente_vai_para_inbox():
    t = {"titulo": "Teste", "lista_sugerida": "Lista Fantasma", "confianca": 0.9,
         "quadrante_sugerido": None, "prazo_sugerido": None, "estimativa_min": None,
         "energia": "media", "impedimento": None, "impedimento_externo": False, "proximo_passo": None}
    resultado = _normalizar(t, _LISTAS)
    assert resultado["lista_sugerida"] is None


def test_normalizar_quadrante_invalido_vira_none():
    t = {"titulo": "T", "lista_sugerida": "Trabalho", "confianca": 0.9,
         "quadrante_sugerido": 9, "prazo_sugerido": None, "estimativa_min": None,
         "energia": "media", "impedimento": None, "impedimento_externo": False, "proximo_passo": None}
    resultado = _normalizar(t, _LISTAS)
    assert resultado["quadrante_sugerido"] is None


def test_normalizar_energia_invalida_vira_media():
    t = {"titulo": "T", "lista_sugerida": "Trabalho", "confianca": 0.9,
         "quadrante_sugerido": None, "prazo_sugerido": None, "estimativa_min": None,
         "energia": "extrema", "impedimento": None, "impedimento_externo": False, "proximo_passo": None}
    resultado = _normalizar(t, _LISTAS)
    assert resultado["energia"] == "media"


def test_normalizar_impedimento_invalido_vira_none():
    t = {"titulo": "T", "lista_sugerida": "Trabalho", "confianca": 0.9,
         "quadrante_sugerido": None, "prazo_sugerido": None, "estimativa_min": None,
         "energia": "media", "impedimento": "medo_de_começar", "impedimento_externo": False, "proximo_passo": None}
    resultado = _normalizar(t, _LISTAS)
    assert resultado["impedimento"] is None


def test_normalizar_prazo_invalido_vira_none():
    t = {"titulo": "T", "lista_sugerida": "Trabalho", "confianca": 0.9,
         "quadrante_sugerido": None, "prazo_sugerido": "não-é-data", "estimativa_min": None,
         "energia": "media", "impedimento": None, "impedimento_externo": False, "proximo_passo": None}
    resultado = _normalizar(t, _LISTAS)
    assert resultado["prazo_sugerido"] is None


def test_normalizar_prazo_iso8601_valido_preservado():
    t = {"titulo": "T", "lista_sugerida": "Trabalho", "confianca": 0.9,
         "quadrante_sugerido": None, "prazo_sugerido": "2026-06-01T09:00:00-03:00",
         "estimativa_min": None, "energia": "media", "impedimento": None,
         "impedimento_externo": False, "proximo_passo": None}
    resultado = _normalizar(t, _LISTAS)
    assert resultado["prazo_sugerido"] == "2026-06-01T09:00:00-03:00"


def test_normalizar_campos_ausentes_recebem_defaults():
    t = {"titulo": "Mínimo"}
    resultado = _normalizar(t, _LISTAS)
    assert resultado["energia"] == "media"
    assert resultado["impedimento_externo"] is False
    assert resultado["confianca"] == 0.5
    assert resultado["lista_sugerida"] is None  # confiança 0.5 < 0.6 → Inbox


# ---------------------------------------------------------------------------
# Pós-processamento via parse_resposta
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("impedimento,externo", [
    ("pessoa", True),
    ("recurso_info", True),
    ("data_externa", True),
    ("vaga_grande", False),
    ("decisao_pendente", False),
    ("aversiva_energia", False),
])
def test_parse_impedimento_externo_preservado(impedimento, externo):
    resposta = _json_tarefa(impedimento=impedimento, impedimento_externo=externo, confianca=0.9)
    resultado = parse_resposta(resposta, "texto", _LISTAS)
    assert resultado[0]["impedimento"] == impedimento
    # impedimento_externo vem do JSON, normalizar só zera impedimento inválido
    assert resultado[0]["impedimento_externo"] == externo


def test_parse_proximo_passo_preservado_quando_vaga_grande():
    passo = "Abrir o documento e escrever o título"
    resposta = _json_tarefa(
        impedimento="vaga_grande",
        impedimento_externo=False,
        proximo_passo=passo,
        confianca=0.9,
    )
    resultado = parse_resposta(resposta, "texto", _LISTAS)
    assert resultado[0]["proximo_passo"] == passo


def test_parse_titulo_truncado_em_500_no_fallback():
    longo = "x" * 600
    resultado = parse_resposta("json inválido", longo, _LISTAS)
    assert len(resultado[0]["titulo"]) == 500


# ---------------------------------------------------------------------------
# _tarefa_inbox
# ---------------------------------------------------------------------------

def test_tarefa_inbox_preserva_texto():
    t = _tarefa_inbox("Ligar pro médico")
    assert t["titulo"] == "Ligar pro médico"
    assert t["lista_sugerida"] is None
    assert t["confianca"] == 0.0


def test_tarefa_inbox_trunca_em_500():
    t = _tarefa_inbox("a" * 600)
    assert len(t["titulo"]) == 500
