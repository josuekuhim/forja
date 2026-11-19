# Contratos do Forja

Os contratos são a cola do sistema. Mudou um contrato? Sobe a versão em `forja_contracts.__version__` e registra no CHANGELOG.

A implementação de referência está em [`contracts/src/forja_contracts`](../contracts/src/forja_contracts). Os repositórios importam esses modelos em vez de redefinir campos.

## 1. API de modelo

OpenAI-compatível: `POST /v1/chat/completions`, com `stream: true` via SSE. Produzida por forja-serve, vLLM e APIs externas; consumida por forja-evals e forja-review.

**Regra de ouro:** como tudo fala essa API, o forja-evals avalia qualquer coisa com a mesma régua.

## 2. Casos de avaliação (`EvalCase`)

JSONL, um caso por linha. O dataset é **imutável**: a versão é o hash SHA-256 do conteúdo canônico.

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `id` | str | Estável entre versões (`explicacao-0001`) |
| `categoria` | enum | `explicacao`, `deteccao_bug`, `correcao`, `api`, `recusa` |
| `input` | str | O que o usuário manda (código + pergunta) |
| `referencia` | str \| null | Resposta de referência, quando houver |
| `metadados` | dict | `linguagem`, `origem`, `licenca`, `testes` (para correções verificáveis) |

## 3. Pares de preferência (`PreferencePair`)

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `prompt` | str | |
| `escolhida` | str | |
| `rejeitada` | str | |
| `origem` | enum | `juiz`, `humano`, `juiz+humano` |

Mapeia direto para `prompt/chosen/rejected` do `DPOTrainer` do TRL. **Nunca** gerado a partir do conjunto de avaliação final (ver riscos: circularidade).

## 4. Modelos

safetensors no Hugging Face Hub, com model card contendo: link da execução de eval, config, seed, commit do código.

## 5. Resultados (`EvalRunRef`)

Toda execução do forja-evals tem um ID. Model cards e READMEs linkam esse ID.

## 6. Configuração

YAML versionado + seed + lockfile (`uv.lock`). Todo experimento salva a config resolvida junto com os artefatos.

## 7. Traces online (`forja_contracts.telemetry`)

Spans OpenTelemetry que o **forja-review** emite e o **forja-evals** consome (`forja-evals online`). Em disco: JSONL, um span por linha, no formato de `ReadableSpan.to_json()`; também podem ir por OTLP para um coletor.

| Span | Quando | Atributos principais |
| --- | --- | --- |
| `forja.review` | um PR num commit (pai das chamadas) | `forja.repo`, `forja.pr`, `forja.head_sha`, `gen_ai.request.model` |
| `forja.review.llm` | uma chamada ao modelo (um arquivo ou pedaço) | `forja.file`, `gen_ai.input.messages`, `gen_ai.output.text`, `gen_ai.usage.*`, `forja.comments`, `forja.problems` |
| `forja.review.feedback` | mudou o 👍/👎 de um comentário | `forja.review_trace_id`, `forja.comment_id`, `forja.file`, `forja.line`, `forja.feedback.up/down` |

`gen_ai.*` segue as convenções semânticas GenAI do OpenTelemetry. O feedback chega dias depois da review, num trace próprio; `forja.review_trace_id` é o que liga os dois. Com `FORJA_REVIEW_CAPTURAR_CONTEUDO=0` (repos privados), diff e resposta não entram no trace e a chamada fica fora da amostra do eval online.
