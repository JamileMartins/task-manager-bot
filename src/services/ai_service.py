"""Classificação de tarefas via Gemini (F2 — US-02)."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

import pytz
from google import genai
from google.genai import types

from src.config import DEFAULT_TIMEZONE, GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Few-shot examples (docs/04_PROMPT_CLASSIFICACAO_IA.md §5)
# ---------------------------------------------------------------------------

_FS_A_USER = (
    'Texto para classificar:\n"""\n'
    "lançar as notas da N1 de sistemas operacionais até sexta, comprar café, "
    "marcar retorno com a dermato, ideia: fazer um quadro kanban pro projeto "
    "integrador, preciso responder o email do coordenador mas to esperando ele "
    "mandar o anexo\n\"\"\""
)
_FS_A_RESP = (
    '{"tarefas":['
    '{"titulo":"Lançar as notas da N1 de Sistemas Operacionais","lista_sugerida":"Trabalho",'
    '"quadrante_sugerido":1,"prazo_sugerido":"2026-05-29T09:00:00-03:00","estimativa_min":60,'
    '"energia":"media","impedimento":null,"impedimento_externo":false,"proximo_passo":null,"confianca":0.95},'
    '{"titulo":"Comprar café","lista_sugerida":"Casa (solo)","quadrante_sugerido":3,'
    '"prazo_sugerido":null,"estimativa_min":5,"energia":"baixa","impedimento":null,'
    '"impedimento_externo":false,"proximo_passo":null,"confianca":0.9},'
    '{"titulo":"Marcar retorno com a dermatologista","lista_sugerida":"Saúde",'
    '"quadrante_sugerido":2,"prazo_sugerido":null,"estimativa_min":15,"energia":"baixa",'
    '"impedimento":null,"impedimento_externo":false,"proximo_passo":null,"confianca":0.92},'
    '{"titulo":"Montar um quadro kanban para o Projeto Integrador","lista_sugerida":"Ideias",'
    '"quadrante_sugerido":4,"prazo_sugerido":null,"estimativa_min":60,"energia":"alta",'
    '"impedimento":"vaga_grande","impedimento_externo":false,'
    '"proximo_passo":"Abrir uma ferramenta de kanban e criar as três colunas: A fazer, Fazendo, Feito",'
    '"confianca":0.8},'
    '{"titulo":"Responder o email do coordenador","lista_sugerida":"Trabalho",'
    '"quadrante_sugerido":2,"prazo_sugerido":null,"estimativa_min":15,"energia":"media",'
    '"impedimento":"pessoa","impedimento_externo":true,"proximo_passo":null,"confianca":0.9}'
    ']}'
)

_FS_B_USER = 'Texto para classificar:\n"""\norganizar as coisas do semestre\n"""'
_FS_B_RESP = (
    '{"tarefas":['
    '{"titulo":"Organizar as coisas do semestre","lista_sugerida":"Trabalho",'
    '"quadrante_sugerido":2,"prazo_sugerido":null,"estimativa_min":120,"energia":"alta",'
    '"impedimento":"vaga_grande","impedimento_externo":false,'
    '"proximo_passo":"Listar em uma nota quais disciplinas e pendências existem neste semestre",'
    '"confianca":0.7}'
    ']}'
)

# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

def _build_system_prompt(listas: list[str], agora: str, timezone: str) -> str:
    lista_str = ", ".join(listas)
    return (
        "Você é um classificador de tarefas de um assistente pessoal de produtividade no Telegram, "
        "voltado a uma pessoa com TDAH. Seu único trabalho é transformar texto livre em tarefas "
        "estruturadas. Você NÃO conversa, NÃO faz perguntas, NÃO comenta: apenas devolve JSON.\n\n"
        "CONTEXTO ATUAL\n"
        f"- Data e hora atuais: {agora}\n"
        f"- Fuso horário: {timezone}\n"
        f"- Listas disponíveis do usuário: {lista_str}\n\n"
        "O QUE FAZER\n"
        "1. Separe o texto em tarefas atômicas. Uma frase pode conter várias tarefas "
        '(separadas por vírgula, "e", quebras de linha, ponto). Cada ação independente é uma tarefa.\n'
        "2. Não invente tarefas que não estão no texto. Não juncte tarefas distintas em uma só.\n"
        '3. Reescreva o título de forma curta, clara e no infinitivo ou imperativo '
        '(ex.: "Ligar para o dentista"), preservando nomes próprios e detalhes essenciais.\n\n'
        "PARA CADA TAREFA, PREENCHA\n"
        "- titulo (string): título curto e acionável.\n"
        f"- lista_sugerida (string): exatamente um dos nomes em {lista_str}. "
        "Se não tiver certeza razoável, use null (irá para a Inbox).\n"
        "- quadrante_sugerido (1 a 4): Matriz de Eisenhower.\n"
        "   1=urgente E importante · 2=importante não urgente · "
        "3=urgente não importante · 4=nem urgente nem importante. Se sem base, null.\n"
        "- prazo_sugerido (string ISO 8601 com fuso, ou null): só se o texto indicar data/hora. "
        "Resolva datas relativas com base na data atual e no fuso. Dia sem hora → 09:00 local.\n"
        "- estimativa_min (inteiro ou null): minutos plausíveis. Valores típicos: 5, 15, 30, 60, 120.\n"
        '- energia (string): "alta", "media" ou "baixa".\n'
        "- impedimento (string ou null): vaga_grande | decisao_pendente | aversiva_energia | "
        "pessoa | recurso_info | data_externa | obsoleta. Se nenhum, null.\n"
        "- impedimento_externo (boolean): true quando pessoa, recurso_info ou data_externa.\n"
        "- proximo_passo (string ou null): quando vaga_grande, menor ação física em ≤2 min, imperativo.\n"
        "- confianca (number 0..1): confiança na classificação de lista e quadrante.\n\n"
        "REGRAS\n"
        "- Responda EXCLUSIVAMENTE com JSON válido. Sem texto antes/depois, sem markdown, sem cercas.\n"
        "- Use null (não string 'null', não '') para campos sem valor.\n"
        f"- Nunca crie nomes de lista fora de: {lista_str}.\n"
        "- Em caso de dúvida entre listas, prefira null e baixe a confianca.\n"
        "- Em português do Brasil.\n\n"
        "FORMATO DE SAÍDA (exato)\n"
        '{"tarefas":[{"titulo":"","lista_sugerida":null,"quadrante_sugerido":null,'
        '"prazo_sugerido":null,"estimativa_min":null,"energia":"media","impedimento":null,'
        '"impedimento_externo":false,"proximo_passo":null,"confianca":0.0}]}'
    )


# ---------------------------------------------------------------------------
# Parsing seguro (spec §6)
# ---------------------------------------------------------------------------

_VALID_BLOCKER_TYPES = frozenset({
    "vaga_grande", "decisao_pendente", "aversiva_energia",
    "pessoa", "recurso_info", "data_externa", "obsoleta",
})
_VALID_ENERGIES = frozenset({"alta", "media", "baixa"})
_VALID_QUADRANTS = frozenset({1, 2, 3, 4})


def _normalizar(t: dict[str, Any], listas_ativas: frozenset[str]) -> dict[str, Any]:
    """Applies defaults and post-processing rules (spec §7)."""
    t.setdefault("titulo", "")
    t.setdefault("lista_sugerida", None)
    t.setdefault("quadrante_sugerido", None)
    t.setdefault("prazo_sugerido", None)
    t.setdefault("estimativa_min", None)
    t.setdefault("energia", "media")
    t.setdefault("impedimento", None)
    t.setdefault("impedimento_externo", False)
    t.setdefault("proximo_passo", None)
    t.setdefault("confianca", 0.5)

    if t["quadrante_sugerido"] not in _VALID_QUADRANTS:
        t["quadrante_sugerido"] = None
    if t["energia"] not in _VALID_ENERGIES:
        t["energia"] = "media"
    if t["impedimento"] not in _VALID_BLOCKER_TYPES:
        t["impedimento"] = None

    # Lista: deve casar exatamente com uma lista ativa
    if t["lista_sugerida"] and t["lista_sugerida"] not in listas_ativas:
        t["lista_sugerida"] = None

    # Confiança baixa ou lista nula → Inbox
    if t["confianca"] < 0.6 or t["lista_sugerida"] is None:
        t["lista_sugerida"] = None

    # Valida ISO 8601
    if t["prazo_sugerido"]:
        try:
            datetime.fromisoformat(t["prazo_sugerido"])
        except ValueError:
            t["prazo_sugerido"] = None

    return t


def _tarefa_inbox(texto_original: str) -> dict[str, Any]:
    return {
        "titulo": texto_original[:500],
        "lista_sugerida": None,
        "quadrante_sugerido": None,
        "prazo_sugerido": None,
        "estimativa_min": None,
        "energia": "media",
        "impedimento": None,
        "impedimento_externo": False,
        "proximo_passo": None,
        "confianca": 0.0,
    }


def parse_resposta(
    texto_resposta: str,
    texto_original: str,
    listas_ativas: frozenset[str],
) -> list[dict[str, Any]]:
    """Faz parsing da resposta da IA. Cai para Inbox em caso de falha (spec §6)."""
    bruto = re.sub(r"```(?:json)?\s*|\s*```", "", texto_resposta).strip()
    dados: Any = None
    try:
        dados = json.loads(bruto)
    except json.JSONDecodeError:
        start, end = bruto.find("{"), bruto.rfind("}")
        if start != -1 and end > start:
            try:
                dados = json.loads(bruto[start : end + 1])
            except json.JSONDecodeError:
                pass

    if not dados or "tarefas" not in dados or not isinstance(dados["tarefas"], list):
        return [_tarefa_inbox(texto_original)]

    resultado = [
        _normalizar(t, listas_ativas)
        for t in dados["tarefas"]
        if isinstance(t, dict) and t.get("titulo")
    ]
    return resultado or [_tarefa_inbox(texto_original)]


# ---------------------------------------------------------------------------
# Classificação principal
# ---------------------------------------------------------------------------

def suggest_next_step(task_title: str) -> str:
    """Sugere o menor próximo passo físico (≤2 min) para uma tarefa vaga/grande."""
    if not GEMINI_API_KEY:
        return "Dar o primeiro passo"

    system = (
        "Você é um assistente de produtividade para uma pessoa com TDAH. "
        "Dada uma tarefa vaga ou grande, sugira O MENOR próximo passo físico possível. "
        "Regras: deve levar ≤ 2 minutos; no imperativo; em português do Brasil; "
        "sem explicações, apenas o passo. "
        'Exemplo: "Abrir o documento e escrever o título"'
    )
    user_msg = f"Tarefa: {task_title}"

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[types.Content(role="user", parts=[types.Part(text=user_msg)])],
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.3,
                max_output_tokens=80,
            ),
        )
        step = (response.text or "").strip().strip('"').strip()
        return step[:200] if step else "Dar o primeiro passo"
    except Exception:
        logger.exception("Erro ao sugerir próximo passo")
        return "Dar o primeiro passo"


def classificar_brain_dump(
    texto: str,
    listas: list[str],
    timezone: str = DEFAULT_TIMEZONE,
) -> list[dict[str, Any]]:
    """Classifica texto livre em tarefas estruturadas via Gemini.

    Retorna sempre uma lista não-vazia. Em caso de erro, retorna uma tarefa
    com o texto original para salvar na Inbox (RNF08).
    """
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY não configurada — fallback para Inbox")
        return [_tarefa_inbox(texto)]

    listas_ativas = frozenset(listas)
    tz = pytz.timezone(timezone)
    agora = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    system_prompt = _build_system_prompt(listas, agora, timezone)
    user_message = f'Texto para classificar:\n"""\n{texto}\n"""'

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        contents = [
            types.Content(role="user", parts=[types.Part(text=_FS_A_USER)]),
            types.Content(role="model", parts=[types.Part(text=_FS_A_RESP)]),
            types.Content(role="user", parts=[types.Part(text=_FS_B_USER)]),
            types.Content(role="model", parts=[types.Part(text=_FS_B_RESP)]),
            types.Content(role="user", parts=[types.Part(text=user_message)]),
        ]
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.1,
                max_output_tokens=2048,
            ),
        )
        return parse_resposta(response.text or "", texto, listas_ativas)
    except Exception:
        logger.exception("Erro na chamada Gemini — fallback para Inbox")
        return [_tarefa_inbox(texto)]
