<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: wiki/ai-models/bases.md % -->
<!-- %ccm_git_object_id: wiki/ai-models/bases.md@195 % -->
<!-- %ccm_git_commit_date: 2026-10-29 21:42:03 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: mkdocs updates % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!-- # %git_commit_history: 2025-09-06 mpegg  hook final alpha v0.1  %  -->
# The Bases (The Students) 🧑‍🎓

In our analogy, the **Base** is the underlying architecture — the "Student" you send to
different universities. In 2024 this described almost every model on the market: DeepSeek-R1 was
a Llama 3.1 or Qwen 2.5 underneath, Hermes 3 was Llama 3.1, and "which base?" was a question
with a real answer.

**It no longer is.** The frontier split into two unrelated trees, and only one of them has a
visible base.

Model names reflect a live catalog pull on **2026-10-30** from this host's configured providers.

## Tree 1 — open weights: the base is real and traceable

Here the metaphor still works. A base is published, then fine-tuned, distilled or quantised into
variants you can actually name.

| Base (Student) | Lab | Weights | Current hosted line | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Llama 3.1 → 3.3 → 4** | Meta | Open | `llama-4-maverick`, `llama-4-scout`, `llama-3.3-70b` | The classic fine-tune host — still the base under Hermes and the R1-Llama distils |
| **Qwen 2.5 → 3.8** | Alibaba | Open through 3.x; some current tiers hosted-only | `qwen3.8-max-prime`, `qwen3.8-27b`, `qwen3-coder` | The coding/maths lineage; fastest-moving open family |
| **Mistral / Mixtral → Large 4** | Mistral AI | Open for small and mid tiers | `mistral-large-4`, `ministral-14b`, `codestral-2508` | Popularised MoE for open weights |
| **Gemma 3 → 4** | Google | Open | `gemma-4-31b-it`, `gemma-4-26b-a4b-it` | The open counterpart to Gemini |
| **DeepSeek V2 → V4** | DeepSeek | Open through V3 / R1; V4 unverified | `deepseek-v4-pro`, `deepseek-flash` | V2 was the MoE efficiency breakthrough; R1 was the reasoning-distillation source |
| **GLM 4.x → 5.3** | Z.ai (Zhipu) | Open through 4.6; 5.x unverified | `glm-5.3`, `glm-5.3-prime`, `glm-5.3-flash` | Broad family with an aggressive price ladder |
| **Kimi K2 → K3** | Moonshot | K2 published; K3 unverified | `kimi-k3`, `kimi-k3.1-pro`, `kimi-k2.7-code` | Long-context specialist lineage |
| **Phi** | Microsoft | Open | `phi-4` | Textbook-data small models |
| **StarCoder2** | BigCode | Open | `StarCoder2-3B` (local only) | Permissive-licence code only |
| **MiniMax M** | MiniMax | Mixed | `minimax-m3`, `minimax-m3.1-flash` | MoE, cost-driven |
| **Nemotron** | NVIDIA | Open | `nemotron-3.5-super-vl`, `nemotron-3.5-lightning` | GPU-native, fine-tune friendly |

## Tree 2 — closed frontier: there is no visible base

| Family | Lab | Current line | Context |
| :--- | :--- | :--- | ---: |
| **GPT-6.1 / 6 / 5.6** | OpenAI | `gpt-6.1-sol` / `-terra` / `-luna` (+`-pro`), `gpt-5.6-*` | 1,050,000 |
| **Claude 5.5 / 5** | Anthropic | `claude-opus-5.5`, `claude-sonnet-5.5`, `claude-haiku-5.5`, `claude-fable-5.1` | 1,000,000 |
| **Gemini 4 / 3.x** | Google | `gemini-4-argon`, `gemini-3.8-flash`, `gemini-3.1-pro-preview` | 1,048,576 |
| **Grok 4.x** | xAI | `grok-4.20` (2M), `grok-4.3` … `grok-4.7` | 2,000,000 |

For these, any claim about an "underlying base" is speculation. They are not fine-tunes of a
published student; the lineage is a press release.

## Why the old table could not simply be dated

Three mechanisms made the 2024 framing obsolete, and only the first is about model quality:

1. **Distillation stopped being the pipeline.** The old page's centrepiece was DeepSeek-R1 as a
   "Nobel Prize-winning professor" whose reasoning was distilled into Qwen and Llama students.
   That happened — and then the frontier labs stopped publishing students. Scale moved inside
   closed systems.
2. **Context stopped sorting the field.** Every configured provider now reaches ≥1M tokens, so
   "which base holds more" no longer discriminates. See
   [Models Available (VS Code)](../vscode-ai-models.md#models-available-via-api-keys).
3. **Variant suffixes now encode a reasoning budget, not an architecture.** `gpt-6.1-sol` vs
   `-terra` vs `-luna` is not three bases. It is one family at three capability/price points,
   and the client adds an explicit `reasoning.effort` on top.

## Local bases actually installed

These are the only bases you can inspect directly — the weights are on disk.

| Base | Installed tags | Size |
| :--- | :--- | ---: |
| Llama 3.1 | `Llama-3.1-8B`, `Hermes-3-8B-Instruct`, `DeepSeek-R1-Llama-7B` | 4.9 / 4.7 / 4.7 GB |
| Qwen 2.5 | `Qwen2.5-Coder-7B`, `Qwen2.5-Coder-14B`, `DeepSeek-R1-Qwen-8B` | 4.7 / 9.0 / 5.2 GB |
| Mistral | `Mistral-Nemo-12B`, `Ministral-3-14B-Instruct` | 7.1 / 9.1 GB |
| Gemma 3 | `Gemma-3-12B` | 8.1 GB |
| DeepSeek-Coder-V2 | `DeepSeek-Coder-V2-16B` | 8.9 GB |
| GPT-OSS | `GPT-OSS-20B` | 13 GB |
| StarCoder2 | `StarCoder2-3B` | 1.7 GB |
| LLaVA | `LLaVA-13B` | 8.0 GB |
| MoonDream | `MoonDream-1.7B` | 1.7 GB |

## Migration map (old page → current)

| 2024 entry | Replaced by |
| :--- | :--- |
| DeepSeek-V2 | DeepSeek V4 / V4.1 |
| Llama 3.1 (as frontier) | Llama 4 and the Meta `muse-*` families |
| Qwen 2.5 (as frontier) | Qwen 3.8 (`qwen3.8-max-prime`, `qwen3.8-27b`) |
| GPT-4 | GPT-6.1 |
| Claude 3 | Claude 5.5 |
| Gemini 1.5 Pro (1M context) | Gemini 4-argon / 3.8-flash (1,048,576); Grok 4.20 now holds the 2M record |
| Grok-2 | Grok 4.20 and 4.3–4.7 |
| Llama 2 / CodeLlama | Retired — no longer served, not installed |

## Related

- **[The Trainers (The Universities)](trainers.md)**: the labs that trained the base.
- **[The Subjects (The Focus)](subjects.md)**: what the resulting model majored in.
