# Forja

**Um LLM de engenharia de software em português, do treino à produção.**

Um modelo pequeno é treinado, adaptado, avaliado e servido para uma tarefa real: **explicar código e revisar pull requests em português**. Cada repositório entrega algo que o próximo usa.

> Status: 🚧 semana 12 — contratos definidos, modelo base em decisão ([ADR 0001](docs/adr/0001-modelo-base.md)).

## Resultados do sistema

| Configuração | Qualidade (forja-evals) | Latência p50 | Custo / 1k requisições |
| --- | --- | --- | --- |
| Modelo grande via API | referência | — | — |
| Modelo base + prompt | — | — | — |
| + SFT (LoRA) | — | — | — |
| + DPO | — | — | — |
| + quantização 4-bit + speculative | — | — | — |

Todo número desta tabela vem de uma execução do `forja-evals`, com link.

## Arquitetura

```
                       ┌──────────────────────────────┐
                       │  forja-evals (a régua)       │
                       └──▲─────────▲─────────▲───────┘
                          │         │         │ evals online
┌────────────────┐   ┌────┴─────────┴──┐   ┌──┴──────────────┐   ┌─────────────────┐
│ forja-pretrain ├──►│ forja-posttrain ├──►│ forja-serve     ├──►│ forja-review    │
└───────┬────────┘   └─────────────────┘   └────────▲────────┘   └─────────────────┘
        └──────── draft model p/ speculative ───────┘
                  decoding (mesmo tokenizer)
```

| Repositório | Papel | Status |
| --- | --- | --- |
| [forja-pretrain](../forja-pretrain) | Transformer do zero; vira o draft model | 🚧 código pronto, falta treinar |
| [forja-evals](../forja-evals) | A régua: evals offline, juiz calibrado, gate no CI | 🚧 v1 offline pronta |
| [forja-posttrain](../forja-posttrain) | SFT → LoRA → QLoRA → DPO no modelo base | 🚧 R1 em CPU: SFT LoRA leva o Qwen 0.5B de 1 a 15/53 bugs num PR de templates nunca vistos, formato 100% válido, sem regressão no seed-v0; ruff sozinho acha 25/53 e ruff + modelo 32/53. DPO on-policy cortou extras (44 → 34) mas também acertos (15 → 11): o gargalo é o dado; E1–E4 aguardam GPU |
| [forja-serve](../forja-serve) | Engine de inferência OpenAI-compatível | v0: benchmark real (batching 2,6×) e gate de qualidade (int8 aprovado, int4 reprovado por loops); speculative aguarda o draft |
| [forja-review](../forja-review) | GitHub App que revisa PRs em português | v0: App completo (webhook, fila, review inline, feedback, traces → eval online). Com Gemma 26B acha 4/4 bugs num PR reservado; Qwen 0.5B base 0/4, pós-treinado 2/8 nos plantados; linha de base com ruff na mesma régua |
| [forja-dados](../forja-dados) | Fundação de dados: bugs reais de repositórios públicos viram datasets versionados de treino e avaliação (bronze → prata → ouro, Dagster + DuckDB) | 🚧 v0: esqueleto completo (Dagster + DuckDB, checks bloqueantes, 71 testes sobre fixtures); falta o piloto com dado real. [Spec](../forja-dados/SPEC.md) |

## O que mora neste repositório

- [`docs/contratos.md`](docs/contratos.md): os contratos que ligam os projetos.
- [`docs/adr/`](docs/adr): decisões de arquitetura (Architecture Decision Records).
- [`contracts/`](contracts): pacote Python `forja-contracts` com os schemas (Pydantic) que todos os repositórios importam.

```bash
# em qualquer repo do Forja
uv add "forja-contracts @ git+https://github.com/<usuario>/forja#subdirectory=contracts"
```

## Regras de qualidade

1. Reprodutibilidade: config, seed, versões e instruções em cada experimento.
2. Toda técnica nova tem baseline.
3. Nunca avaliar com dado de treino; contaminação checada explicitamente.
4. Ablações: uma variável por vez.
5. Limitações explícitas.
6. Resultados honestos, nas mesmas condições.
7. Mesma régua: toda afirmação de qualidade linka uma execução do forja-evals.
