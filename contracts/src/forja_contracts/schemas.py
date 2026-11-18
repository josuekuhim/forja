from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class Categoria(StrEnum):
    EXPLICACAO = "explicacao"
    DETECCAO_BUG = "deteccao_bug"
    CORRECAO = "correcao"
    API = "api"
    RECUSA = "recusa"


class OrigemPar(StrEnum):
    JUIZ = "juiz"
    HUMANO = "humano"
    JUIZ_HUMANO = "juiz+humano"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvalCase(_Frozen):
    id: str = Field(pattern=r"^[a-z_]+-\d{4,}$")
    categoria: Categoria
    input: str = Field(min_length=1)
    referencia: str | None = None
    metadados: dict[str, Any] = Field(default_factory=dict)


class PreferencePair(_Frozen):
    prompt: str = Field(min_length=1)
    escolhida: str = Field(min_length=1)
    rejeitada: str = Field(min_length=1)
    origem: OrigemPar

    def to_trl(self) -> dict[str, str]:
        """Formato esperado pelo DPOTrainer do TRL."""
        return {"prompt": self.prompt, "chosen": self.escolhida, "rejected": self.rejeitada}


class EvalRunRef(_Frozen):
    run_id: str
    dataset_hash: str
    modelo: str
    criado_em: datetime
    url: str | None = None


M = TypeVar("M", bound=BaseModel)


def _canonical(obj: BaseModel) -> str:
    return json.dumps(obj.model_dump(mode="json"), sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def dataset_hash(items: Iterable[BaseModel]) -> str:
    """Hash independente da ordem das linhas: o dataset é um conjunto, não uma lista."""
    lines = sorted(_canonical(i) for i in items)
    h = hashlib.sha256()
    for line in lines:
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def write_jsonl(path: str | Path, items: Iterable[BaseModel]) -> None:
    with Path(path).open("w", encoding="utf-8", newline="\n") as f:
        for item in items:
            f.write(_canonical(item) + "\n")


def read_jsonl(path: str | Path, model: type[M]) -> list[M]:
    with Path(path).open(encoding="utf-8") as f:
        return [model.model_validate_json(line) for line in f if line.strip()]
