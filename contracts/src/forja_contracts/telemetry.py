"""Contrato de telemetria: traces OpenTelemetry do forja-review consumidos pelo forja-evals (evals online).

O forja-review exporta spans; o forja-evals lê os spans, sorteia uma amostra e avalia com o juiz.
Os nomes seguem as convenções semânticas GenAI do OpenTelemetry onde existem (`gen_ai.*`) e o prefixo
`forja.*` para o resto. Mudou um nome aqui? Sobe a versão do pacote: os dois lados quebram juntos.

Formato em disco: JSONL, um span por linha, no formato de `ReadableSpan.to_json()` do SDK Python
(`name`, `context.trace_id`, `context.span_id`, `parent_id`, `attributes`, `start_time`, `end_time`).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

SERVICE_REVIEW = "forja-review"

# Spans
SPAN_REVIEW = "forja.review"  # um PR num commit: pai das chamadas ao modelo
SPAN_LLM = "forja.review.llm"  # uma chamada ao modelo (um arquivo ou um pedaço dele)
SPAN_FEEDBACK = "forja.review.feedback"  # reações 👍/👎 num comentário publicado

# Atributos GenAI (OpenTelemetry semconv)
ATTR_MODEL = "gen_ai.request.model"
ATTR_INPUT_TOKENS = "gen_ai.usage.input_tokens"
ATTR_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
ATTR_FINISH = "gen_ai.response.finish_reasons"
ATTR_INPUT_MESSAGES = "gen_ai.input.messages"  # JSON: [{"role": ..., "content": ...}]
ATTR_OUTPUT_TEXT = "gen_ai.output.text"  # texto bruto da resposta

# Atributos do Forja
ATTR_REPO = "forja.repo"  # "dono/repo" (ou "local")
ATTR_PR = "forja.pr"
ATTR_SHA = "forja.head_sha"
ATTR_FILE = "forja.file"
ATTR_CHUNK = "forja.chunk"  # índice do pedaço quando o arquivo não coube numa chamada
ATTR_COMMENTS = "forja.comments"  # JSON: comentários que sobreviveram à ancoragem
ATTR_PROBLEMS = "forja.problems"  # JSON: ["json_invalido", "linha_fora_do_diff", ...]
ATTR_COMMENT_ID = "forja.comment_id"
ATTR_LINE = "forja.line"
ATTR_REVIEW_TRACE = "forja.review_trace_id"  # liga o feedback (que chega depois) ao trace da review
ATTR_FEEDBACK_UP = "forja.feedback.up"
ATTR_FEEDBACK_DOWN = "forja.feedback.down"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ReviewComment(_Frozen):
    arquivo: str
    linha: int
    severidade: str
    comentario: str


class LLMInteraction(_Frozen):
    """Uma chamada ao modelo reconstruída a partir de um span `forja.review.llm`."""

    trace_id: str
    span_id: str
    repo: str
    pr: int | None = None
    arquivo: str
    modelo: str
    mensagens: list[dict[str, str]] = Field(default_factory=list)
    saida: str = ""
    comentarios: list[ReviewComment] = Field(default_factory=list)
    problemas: list[str] = Field(default_factory=list)
    input_tokens: int | None = None
    output_tokens: int | None = None
    duracao_s: float | None = None


class Feedback(_Frozen):
    review_trace_id: str
    comment_id: int
    arquivo: str
    linha: int
    up: int
    down: int


def iter_spans(path: str | Path) -> Iterator[dict[str, Any]]:
    """Spans de um ou mais JSONL (arquivo ou diretório)."""
    p = Path(path)
    files = sorted(p.glob("*.jsonl")) if p.is_dir() else [p]
    for f in files:
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    yield json.loads(line)


def _hex(v: str) -> str:
    return v[2:] if v.startswith("0x") else v


def _duration(span: dict[str, Any]) -> float | None:
    from datetime import datetime

    try:
        a = datetime.fromisoformat(span["start_time"].replace("Z", "+00:00"))
        b = datetime.fromisoformat(span["end_time"].replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        return None
    return (b - a).total_seconds()


def load_interactions(path: str | Path) -> tuple[list[LLMInteraction], list[Feedback]]:
    """Reconstrói chamadas ao modelo e feedback humano a partir dos spans exportados."""
    calls: list[LLMInteraction] = []
    # O feedback é re-emitido a cada mudança; vale o último por comentário.
    fb: dict[int, Feedback] = {}
    for s in iter_spans(path):
        a = s.get("attributes") or {}
        if s.get("name") == SPAN_LLM:
            calls.append(
                LLMInteraction(
                    trace_id=_hex(s["context"]["trace_id"]),
                    span_id=_hex(s["context"]["span_id"]),
                    repo=a.get(ATTR_REPO, ""),
                    pr=a.get(ATTR_PR),
                    arquivo=a.get(ATTR_FILE, ""),
                    modelo=a.get(ATTR_MODEL, ""),
                    mensagens=json.loads(a.get(ATTR_INPUT_MESSAGES) or "[]"),
                    saida=a.get(ATTR_OUTPUT_TEXT, ""),
                    comentarios=json.loads(a.get(ATTR_COMMENTS) or "[]"),
                    problemas=json.loads(a.get(ATTR_PROBLEMS) or "[]"),
                    input_tokens=a.get(ATTR_INPUT_TOKENS),
                    output_tokens=a.get(ATTR_OUTPUT_TOKENS),
                    duracao_s=_duration(s),
                )
            )
        elif s.get("name") == SPAN_FEEDBACK:
            f = Feedback(
                review_trace_id=a[ATTR_REVIEW_TRACE],
                comment_id=int(a[ATTR_COMMENT_ID]),
                arquivo=a.get(ATTR_FILE, ""),
                linha=int(a.get(ATTR_LINE, 0)),
                up=int(a.get(ATTR_FEEDBACK_UP, 0)),
                down=int(a.get(ATTR_FEEDBACK_DOWN, 0)),
            )
            fb[f.comment_id] = f
    return calls, list(fb.values())
