# ADR 0001: Base model and tokenizer

- **Status:** accepted with plan B. The 0.5B is the model used in post-training (R1 and R2, see [forja-posttrain](https://github.com/josuekuhim/forja-posttrain)); the 1.5B is still planned (E2–E4)
- **Date:** 2026-11-18

## Context

The base model defines the tokenizer, and the tokenizer locks three things:

1. **forja-pretrain**, which needs the same vocabulary to serve as the draft model;
2. **forja-posttrain**, which adapts this model;
3. **forja-serve**, which runs speculative decoding with both.

Requirements: 0.5 to 1.5B parameters, permissive license, good at code, a reasonable tokenizer for Portuguese, fits on Kaggle/Colab's T4/P100 for LoRA and QLoRA.

## Options

| Model | Params | License | Vocab | Note |
| --- | --- | --- | --- | --- |
| Qwen2.5-Coder-0.5B-Instruct | 0.5B | Apache 2.0 | 151,665 | Cheapest, full SFT fits on a free GPU |
| **Qwen2.5-Coder-1.5B-Instruct** | 1.5B | Apache 2.0 | 151,665 | Better at code; same tokenizer as the 0.5B |
| SmolLM2-1.7B-Instruct | 1.7B | Apache 2.0 | 49,152 | Small vocab (good for the draft), but weak in Portuguese |

> Check on the Hub before locking: current license, whether there is a newer generation with the same license, and the exact `vocab_size` in `config.json` (Qwen's embedding is allocated with 151,936 rows, above the real vocab).

## Proposed decision

**Qwen2.5-Coder-1.5B-Instruct** as the production model, with the **0.5B as plan B** (same tokenizer, so nothing upstream changes if the 1.5B does not fit).

## Important consequence for forja-pretrain

With ~152k tokens in the vocabulary, **the embedding table dominates a small model**:

| d_model | Embedding (tied) | For 10–50M in total... |
| --- | --- | --- |
| 256 | 38.9M | almost nothing is left for the blocks |
| 384 | 58.4M | already over 50M in the embedding alone |
| 512 | 77.8M | — |

That is why forja-pretrain reports **non-embedding parameters** (the Kaplan et al./Chinchilla convention) and targets **10–50M non-embedding**, with the embedding tied to the `lm_head`. This is a limitation to document in the README, not a bug: it is the price of reusing the tokenizer for speculative decoding.

Alternative discarded for now: training with a reduced vocabulary and mapping IDs. It breaks token verification in speculative decoding and adds complexity with no gain for the portfolio.

## Open items

- [ ] Confirm license and vocab on the Hub. _Partial (2026-11-18): the `Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF` repository is Apache 2.0 and not gated; the `vocab_size` in the original model's `config.json` is still to be checked._
- [ ] Run the base model + prompt on 20 cases per category (zero baseline). _Partial (2026-11-18): run on `forja-seed-v0` (16 cases, no judge), score 0.273; refusal 0/3 and bug detection 0/4. See `forja-evals/baselines/`._
- [ ] Measure tokenizer fertility (tokens per word) in Portuguese vs. English.
