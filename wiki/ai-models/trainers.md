<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: wiki/ai-models/trainers.md % -->
<!-- %ccm_git_object_id: wiki/ai-models/trainers.md@195 % -->
<!-- %ccm_git_commit_date: 2026-10-29 21:42:03 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: mkdocs updates % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!-- # %git_commit_history: 2025-09-06 mpegg  hook final alpha v0.1  %  -->
# The Trainers (The Universities) 🎓

In our analogy, the **Trainer** is the organization or "University" that taught the model.
Different organizations have different philosophies, safety standards and training
methodologies. Trainers change rarely; the model names they ship change constantly — so the
left-hand columns below are the durable part and the right-hand column is disposable.

Model names reflect a live catalog pull on **2026-10-30** from the providers configured on this
host. Read them as a dated snapshot, not a permanent claim.

| Trainer (University) | Philosophy | Known For | Style / Analogy | Current line (2026-10) |
| :--- | :--- | :--- | :--- | :--- |
| **OpenAI** (Ivy League) | Scale, capability, product polish | GPT-6.x, o-series reasoning, Codex variants | "Ivy League". Closed, polished, most heavily tooled. | `gpt-6.1-sol` / `-terra` / `-luna` (+`-pro`), `gpt-5.6-*`, `gpt-5.1-codex-max` |
| **Anthropic** (Ethics Comm) | Safety, careful edits, long-form judgement | Claude 5.x, trustworthy refactors | "Ethics Board". Cautious; least likely to break what it touches. | `claude-opus-5.5`, `claude-sonnet-5.5`, `claude-haiku-5.5`, `claude-fable-5.1` |
| **Google** (Mega-Campus) | Multimodal, integration, long context | Gemini and Gemma | "Biggest Library". Deepest context, native video/audio. | `gemini-4-argon`, `gemini-3.8-flash`, `gemini-3.1-pro-preview`, `gemma-4-31b-it` |
| **Alibaba / Qwen** (CS Lab) | Open weights, coding and math, multilingual | Qwen 2.5 → 3.8 | "CS Majors". Punch above their weight class; terse. | `qwen3.8-max-prime`, `qwen3.8-27b`, `qwen3-coder` |
| **DeepSeek** (Math Dept) | RL reasoning, efficiency, price | V3 / R1 → V4.x | "Math Prodigies". Cheap, logical, quietly strong. | `deepseek-flash`, `deepseek-v4-pro` (direct); `deepseek-v4.1-flash` (aggregators) |
| **Z.ai / Zhipu** (State Lab) | Open weights, tiered pricing | GLM 4.x → 5.3 | "State Lab". Broad family, aggressive price ladder. | `glm-5.3`, `glm-5.3-prime`, `glm-5.3-flash`, `glm-5.2` |
| **Moonshot** (Night School) | Long context, code, China-market UX | Kimi K2 → K3 | "Night School". 1M context at mid price. | `kimi-k3`, `kimi-k3.1-pro`, `kimi-k2.7-code`, `kimi-k2.6` |
| **Meta** (The Dean) | Open weights, general knowledge | Llama 3.1 / 4, Muse families | "Dean's List". Standard, well-rounded, polite. | `llama-4-maverick`, `llama-3.3-70b`, `muse-spark-1.3`, `muse-wonder` |
| **xAI** (Private Incubator) | Speed, edge, real-time flavour | Grok 4.x | "Private Lab". Fast, less filtered, historically news-aware. | `grok-4.20` (2M context), `grok-4.3` … `grok-4.7` |
| **Mistral AI** (European Inst) | Efficiency, open weights, EU hosting | Large 4, Codestral, Magistral | "French Powerhouse". High capability per parameter. | `mistral-large-4`, `magistral-medium`, `codestral-2508`, `ministral-14b` |
| **MiniMax** (Cram School) | MoE efficiency, low cost | M-series | "Cram School". Cheap, fast, improving each release. | `minimax-m3`, `minimax-m3.1-flash`, `minimax-m2.7` |
| **Nous Research** (Rebel Prof) | Uncensored, instruction-following | Hermes series | "Art School / Rebel". Unlocks models to do exactly what is asked. | `hermes-3-llama-3.1-405b` (hosted), `Hermes-3-8B-Instruct` (local) |
| **Microsoft** (Research Inst) | Small models, "textbook quality" data | Phi series | "Efficiency Experts". Tiny and logical. | `phi-4` |
| **BigCode** (Vocational) | Permissive licences only, transparency | StarCoder | "Vocational School". Narrow by design, legal-safe. | `StarCoder2-3B` (local only) |
| **Cohere** (Consultancy) | Enterprise retrieval, RAG | Command series | "Consultancy". Retrieval-first; modest context. | `command-a-plus` (192K) |
| **NVIDIA** (Hardware School) | Fine-tunable open models, GPU-native | Nemotron | "Hardware School". Ships with the hardware. | `nemotron-3.5-super-vl`, `nemotron-3.5-lightning` |

## Retired from this host's reachable set

These appear in older revisions of this page and are **no longer served** by any configured
provider key, though some survive as local Ollama weights:

| Trainer | Retired model | Status |
| :--- | :--- | :--- |
| Anthropic | Claude 3 / 3.5 line | Gone — the API starts at `claude-opus-4-5-20251101` |
| OpenAI | `o1-preview`, `gpt-4o` (as current) | `o1-preview` absent; `gpt-4o` still listed but superseded |
| Google | Gemini 1.5 Pro | Gone — the catalog starts at 2.5 |
| xAI | Grok-2 / Grok-3 | Superseded by 4.20 and the 4.3–4.7 line |
| Microsoft | Phi-3.5 | Superseded by Phi-4; the old Ollama tag is gone |
| Meta | Llama 3 / 3.2 | Superseded; `Llama-3.1-8B` remains installed locally |

## Related

- **[The Subjects (The Focus)](subjects.md)**: what the model majored in.
- **[The Bases (The Students)](bases.md)**: the underlying architecture, where one is visible.
