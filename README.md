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
| forja-posttrain | SFT → LoRA → QLoRA → DPO no modelo base | ⏳ |
| forja-serve | Engine de inferência OpenAI-compatível | v0: KV cache paginado, batching e speculative prontos; falta o benchmark real |
| forja-review | GitHub App que revisa PRs em português | ⏳ |

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
