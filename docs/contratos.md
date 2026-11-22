# Forja contracts

The contracts are the glue of the system. Changed a contract? Bump `forja_contracts.__version__` and record it in the CHANGELOG.

The reference implementation is in [`contracts/src/forja_contracts`](../contracts/src/forja_contracts). Repositories import these models instead of redefining fields. Field names are in Portuguese, the project's target language; their meaning is given below.

## 1. Model API

OpenAI-compatible: `POST /v1/chat/completions`, with `stream: true` over SSE. Produced by forja-serve, vLLM and external APIs; consumed by forja-evals and forja-review.

**Golden rule:** since everything speaks this API, forja-evals evaluates anything with the same yardstick.

## 2. Evaluation cases (`EvalCase`)

JSONL, one case per line. The dataset is **immutable**: its version is the SHA-256 hash of the canonical content.

| Field | Type | Description |
| --- | --- | --- |
| `id` | str | Stable across versions (`explicacao-0001`) |
| `categoria` | enum | Category: `explicacao` (explanation), `deteccao_bug` (bug detection), `correcao` (fix), `api`, `recusa` (refusal) |
| `input` | str | What the user sends (code + question) |
| `referencia` | str \| null | Reference answer, when there is one |
| `metadados` | dict | Metadata: `linguagem`, `origem`, `licenca`, `testes` (for verifiable fixes) |

## 3. Preference pairs (`PreferencePair`)

| Field | Type | Description |
| --- | --- | --- |
| `prompt` | str | |
| `escolhida` | str | Chosen answer |
| `rejeitada` | str | Rejected answer |
| `origem` | enum | Source: `juiz` (judge), `humano` (human), `juiz+humano` |

Maps directly to TRL `DPOTrainer`'s `prompt/chosen/rejected`. **Never** generated from the final evaluation set (see risks: circularity).

## 4. Models

safetensors on the Hugging Face Hub, with a model card containing: link to the eval run, config, seed, code commit.

## 5. Results (`EvalRunRef`)

Every forja-evals run has an ID. Model cards and READMEs link that ID.

## 6. Configuration

Versioned YAML + seed + lockfile (`uv.lock`). Every experiment saves the resolved config alongside its artifacts.

## 7. Online traces (`forja_contracts.telemetry`)

OpenTelemetry spans that **forja-review** emits and **forja-evals** consumes (`forja-evals online`). On disk: JSONL, one span per line, in the `ReadableSpan.to_json()` format; they can also go over OTLP to a collector.

| Span | When | Main attributes |
| --- | --- | --- |
| `forja.review` | one PR at one commit (parent of the calls) | `forja.repo`, `forja.pr`, `forja.head_sha`, `gen_ai.request.model` |
| `forja.review.llm` | one model call (one file or chunk) | `forja.file`, `gen_ai.input.messages`, `gen_ai.output.text`, `gen_ai.usage.*`, `forja.comments`, `forja.problems` |
| `forja.review.feedback` | a comment's 👍/👎 changed | `forja.review_trace_id`, `forja.comment_id`, `forja.file`, `forja.line`, `forja.feedback.up/down` |

`gen_ai.*` follows OpenTelemetry's GenAI semantic conventions. Feedback arrives days after the review, in its own trace; `forja.review_trace_id` is what links the two. With `FORJA_REVIEW_CAPTURAR_CONTEUDO=0` (private repos), the diff and the answer stay out of the trace, and the call is left out of the online-eval sample.
