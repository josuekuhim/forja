# ADR 0001: Modelo base e tokenizer

- **Status:** proposto (confirmar na semana 12)
- **Data:** 2026-11-18

## Contexto

O modelo base define o tokenizer, e o tokenizer trava três coisas:

1. o **forja-pretrain**, que precisa do mesmo vocabulário para servir de draft model;
2. o **forja-posttrain**, que adapta esse modelo;
3. o **forja-serve**, que faz speculative decoding com os dois.

Requisitos: 0,5 a 1,5B parâmetros, licença permissiva, bom em código, tokenizer razoável para português, cabe no T4/P100 do Kaggle/Colab para LoRA e QLoRA.

## Opções

| Modelo | Params | Licença | Vocab | Observação |
| --- | --- | --- | --- | --- |
| Qwen2.5-Coder-0.5B-Instruct | 0,5B | Apache 2.0 | 151.665 | Mais barato, SFT completo cabe em GPU gratuita |
| **Qwen2.5-Coder-1.5B-Instruct** | 1,5B | Apache 2.0 | 151.665 | Melhor em código; mesmo tokenizer do 0,5B |
| SmolLM2-1.7B-Instruct | 1,7B | Apache 2.0 | 49.152 | Vocab pequeno (bom pro draft), mas fraco em português |

> Verificar no Hub, antes de travar: licença atual, se há uma geração mais nova com a mesma licença, e o `vocab_size` exato em `config.json` (o embedding do Qwen é alocado com 151.936 linhas, acima do vocab real).

## Decisão proposta

**Qwen2.5-Coder-1.5B-Instruct** como modelo de produção, com o **0.5B como plano B** (mesmo tokenizer, então nada a montante muda se o 1,5B não couber).

## Consequência importante para o forja-pretrain

Com ~152k tokens no vocabulário, **a tabela de embedding domina um modelo pequeno**:

| d_model | Embedding (tied) | Para 10–50M no total... |
| --- | --- | --- |
| 256 | 38,9M | quase nada sobra para os blocos |
| 384 | 58,4M | já passa de 50M só no embedding |
| 512 | 77,8M | — |

Por isso o forja-pretrain passa a reportar **parâmetros não-embedding** (convenção de Kaplan et al./Chinchilla) e mira **10–50M não-embedding**, com embedding amarrado ao `lm_head`. Isso é uma limitação a documentar no README, não um bug: é o preço de reaproveitar o tokenizer para o speculative decoding.

Alternativa descartada por enquanto: treinar com vocabulário reduzido e mapear IDs. Quebra a verificação de tokens no speculative decoding e adiciona complexidade sem ganho para o portfólio.

## Pendências

- [ ] Confirmar licença e vocab no Hub.
- [ ] Rodar o modelo base + prompt em 20 casos de cada categoria (baseline zero).
- [ ] Medir fertilidade do tokenizer (tokens por palavra) em português vs. inglês.
