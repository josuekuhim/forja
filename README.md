# Forja

**A software-engineering LLM for Portuguese, from training to production.**

A small model is trained, adapted, evaluated and served for a real task: **explaining code and reviewing pull requests in Portuguese**. Each repository delivers something the next one uses.

> **Status:** the system runs end to end, and its weak link was measured and fixed with data. A PR goes through a webhook, a queue, forja-serve, comments anchored to lines, and traces that become online evals. The model is Qwen2.5-Coder 0.5B ([ADR 0001](docs/adr/0001-modelo-base.md)). Post-training on **real bug-fix commits** (forja-dados → forja-posttrain R2) tripled the real bugs found and cut wrong comments by 3.5×, with no forgetting. Still to do: train forja-pretrain (the speculative-decoding draft) and run the 1.5B.

![forja-review reviewing a real pull request](../forja-review/docs/demo.gif)

*A real run: the post-trained 0.5B, served on a laptop CPU, reviews [a PR with planted bugs](https://github.com/josuekuhim/forja-review-demo/pull/1) through the GitHub App.*

## System results

The PR reviewer, measured with the same yardstick for every model. The yardstick is [forja-evals](../forja-evals)' `review-eval-v0`: 199 bugs from 2025–2026 bug-fix commits plus the 199 already-fixed files, never used in training. The hand-written PRs from [forja-review](../forja-review) and `forja-seed-v0`, which measures forgetting, are also included.

| Configuration | **Real PR: bugs found (199)** | Comment precision | Bug-free files commented on | Hand-written: planted (8) · held-out (4) | Forgetting (seed-v0) | Wall clock on the real PR¹ | Training |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Gemma 4 26B-A4B (ceiling, local) | not measured² | — | — | 7/8 · 4/4 | — | 12–22 min per 5-file PR | — |
| Qwen 0.5B base + prompt | 4 | 3% | 76 | 0/8 · 0/4 | reference | 2h57 | — |
| + synthetic SFT (R1) | 9 | 3% | 149 | 2/8 · 0/4 | ✅ no regression | 1h41 | 3h36 on CPU |
| + synthetic SFT + DPO (R1) | not measured | — | — | 3/8 · 0/4 | ✅ no regression | — | +2h14 on CPU |
| **+ SFT on real data (R2, D2)** | **27** | **23%** | 58 | 0/8 · 0/4 | ✅ no regression | 1h29 | 31 min on a T4 |
| **+ mixed SFT (R2, D3)** | 25 | 21% | **57** | **4/8** · 0/4 | ✅ no regression | 1h28 | 35 min on a T4 |
| `ruff`, no model | 1 | 8% | 5 | 2/8 · 2/4 | — | 7 s | — |

¹ 398 files, forja-serve fp32 on a Ryzen 5 5625U, 4 parallel requests. The trained model is faster than the base because it answers more briefly.
² At 12–22 min per small PR, the 398 files would take days on CPU.

**What this says about the system:**

- **Data was the lever, not the method.** Training on synthetic data made the format perfect but did not help on real code: precision stayed at 3%, the same as the base model. DPO on top only redistributed errors. Only switching to real fixes moved recall and precision together. Details in [forja-posttrain](../forja-posttrain).
- **Linter and model are complementary.** ruff wins on patterns (string-built SQL, mutable defaults) and finds 1 of 199 real bugs. The model catches semantics. The useful product setup is ruff + model.
- **It does not replace human review yet.** 14% recall and 23% precision from a 0.5B running on CPU. Forja's goal was to measure how much each piece moves the number, with the same yardstick, and that is done. Nobody is promising a finished reviewer.
- **Serving:** [forja-serve](../forja-serve)'s continuous batching gives 2.6× throughput with 8 requests. int8 passes the quality gate, and int4 fails it (it loops in half of the answers).

Every number in this table comes from a `forja-evals` run or from a forja-review `--json-out` scored by [`pontua_t4.py`](../forja-posttrain/scripts/pontua_t4.py), with the files in the repository.

## Architecture

```
                       ┌──────────────────────────────┐
                       │  forja-evals (the yardstick) │
                       └──▲─────────▲─────────▲───────┘
                          │         │         │ online evals
┌────────────────┐   ┌────┴─────────┴──┐   ┌──┴──────────────┐   ┌─────────────────┐
│ forja-pretrain ├──►│ forja-posttrain ├──►│ forja-serve     ├──►│ forja-review    │
└───────┬────────┘   └────────▲────────┘   └────────▲────────┘   └─────────────────┘
        │                     │ real bug fixes      │
        │              ┌──────┴──────┐              │
        │              │ forja-dados │              │
        │              └─────────────┘              │
        └──────── draft model for speculative ──────┘
                  decoding (same tokenizer)
```

| Repository | Role | Status |
| --- | --- | --- |
| [forja-pretrain](../forja-pretrain) | Transformer from scratch; becomes the draft model | 🚧 code ready, not trained yet |
| [forja-evals](../forja-evals) | The yardstick: offline evals, calibrated judge, CI gate | 🚧 offline v1 ready |
| [forja-posttrain](../forja-posttrain) | SFT → LoRA → QLoRA → DPO on the base model | 🚧 R2 on a T4: the same LoRA on Qwen 0.5B, trained on 1,500 examples from real bug-fix commits, finds 27/199 real bugs (vs. 9 when trained on synthetic data) with precision going from 3% to 23%; the mixed model finds 25/199 and 4/8 planted bugs with no error; no seed-v0 regression. R1 on CPU: synthetic data did well on the synthetic PR (15/53) and did not generalize. On-policy DPO did not help: the bottleneck was the data |
| [forja-serve](../forja-serve) | OpenAI-compatible inference engine | v0: real benchmark (2.6× from batching) and a quality gate (int8 approved, int4 rejected for loops); speculative decoding waits for the draft |
| [forja-review](../forja-review) | GitHub App that reviews PRs in Portuguese | v0: complete App (webhook, queue, inline review, feedback, traces → online eval). With Gemma 26B it finds 4/4 bugs on a held-out PR; Qwen 0.5B base 0/4, post-trained 4/8 on the planted PR; ruff baseline on the same yardstick |
| [forja-dados](../forja-dados) | Data foundation: real bugs from public repositories become versioned training and evaluation datasets (bronze → silver → gold, Dagster + DuckDB) | v0 ran on real data: 1,500 training examples (750 fixes, up to Sep 2024) and 398 evaluation examples (199 bugs from 2025–2026), Gemma 26B teacher validated by line, labeler with ~80% precision measured by hand. It is the data behind forja-posttrain's R2. [Spec](../forja-dados/SPEC.md) |

## What lives in this repository

- [`docs/contratos.md`](docs/contratos.md): the contracts that connect the projects.
- [`docs/adr/`](docs/adr): Architecture Decision Records.
- [`contracts/`](contracts): the `forja-contracts` Python package with the (Pydantic) schemas every repository imports.

```bash
# in any Forja repo
uv add "forja-contracts @ git+https://github.com/<user>/forja#subdirectory=contracts"
```

## Quality rules

1. Reproducibility: config, seed, versions and instructions for every experiment.
2. Every new technique has a baseline.
3. Never evaluate on training data; contamination is checked explicitly.
4. Ablations: one variable at a time.
5. Explicit limitations.
6. Honest results, under the same conditions.
7. Same yardstick: every quality claim links a forja-evals run.

## A note on language

The product targets Portuguese, so prompts, datasets, model outputs and most code identifiers (`deteccao_bug`, `gabarito`, `pontua_t4.py`) are in Portuguese. The documentation is in English.
