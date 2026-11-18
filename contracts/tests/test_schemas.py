import pytest
from pydantic import ValidationError

from forja_contracts import (
    Categoria,
    EvalCase,
    OrigemPar,
    PreferencePair,
    dataset_hash,
    read_jsonl,
    write_jsonl,
)


def _caso(i: int, texto: str = "def f(): pass") -> EvalCase:
    return EvalCase(id=f"explicacao-{i:04d}", categoria=Categoria.EXPLICACAO, input=texto)


def test_hash_ignora_ordem():
    a, b = _caso(1), _caso(2)
    assert dataset_hash([a, b]) == dataset_hash([b, a])


def test_hash_muda_com_conteudo():
    assert dataset_hash([_caso(1)]) != dataset_hash([_caso(1, "def g(): pass")])


def test_roundtrip_jsonl(tmp_path):
    casos = [_caso(1), _caso(2, "código com acentuação: ção")]
    p = tmp_path / "casos.jsonl"
    write_jsonl(p, casos)
    assert read_jsonl(p, EvalCase) == casos


def test_rejeita_campo_extra_e_id_invalido():
    with pytest.raises(ValidationError):
        EvalCase(id="x", categoria="explicacao", input="a")
    with pytest.raises(ValidationError):
        EvalCase(id="api-0001", categoria="api", input="a", extra=1)


def test_par_para_trl():
    par = PreferencePair(prompt="p", escolhida="boa", rejeitada="ruim", origem=OrigemPar.HUMANO)
    assert par.to_trl() == {"prompt": "p", "chosen": "boa", "rejected": "ruim"}
