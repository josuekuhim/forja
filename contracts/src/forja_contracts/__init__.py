"""Contratos compartilhados entre os repositórios do Forja."""

from forja_contracts.schemas import (
    Categoria,
    EvalCase,
    EvalRunRef,
    OrigemPar,
    PreferencePair,
    dataset_hash,
    read_jsonl,
    write_jsonl,
)

__version__ = "0.1.0"

__all__ = [
    "Categoria",
    "EvalCase",
    "EvalRunRef",
    "OrigemPar",
    "PreferencePair",
    "dataset_hash",
    "read_jsonl",
    "write_jsonl",
]
