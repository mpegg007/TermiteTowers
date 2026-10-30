<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: wiki/vscode-ai-models.md % -->
<!-- %ccm_git_object_id: wiki/vscode-ai-models.md@195 % -->
<!-- %ccm_git_commit_date: 2026-10-29 21:42:03 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: mkdocs updates % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!-- %git_commit_history: 2026-03-22 mpegg march updates -->
<!-- # %git_commit_history: 2025-09-06 mpegg  hook final alpha v0.1  %  -->
<!-- %git_commit_history: 2025-12-15 mpegg  monday drop  % -->
<!-- %git_commit_history: friday checkin % -->
# AI Models Available (VS Code)

> **Live status — verified 2026-10-29.** GitHub Copilot is **not currently in use**; the table
> below is retained as reference only. The authoritative inventory is
> [Models Available via API Keys](#models-available-via-api-keys), produced by querying each
> configured provider's `/models` endpoint. The local inventory in
> [Local Models](#local-models-installed-via-ollama) comes from `ollama list`.
>
> **Zoo Code is the agent in use; Cline is being retired.** The two no longer share a key store
> — the Cline store stays readable, Zoo's keys live in encrypted VS Code SecretStorage — so
> provider inventories must be re-derived from Zoo, not carried forward from Cline.

## Models Available Through GitHub Copilot Extension (legacy reference)

| Model Name         | Cost | Context | Code Changes | Understanding | Autopilot | Reasoning Type | Strengths                          | Weaknesses                        |
|--------------------|:----:|:-------:|:------------:|:-------------:|:---------:|:--------------:|------------------------------------|------------------------------------|
| GPT-4.1            | 0x   | 128K    | ✅           | ✅            | ✅        | Pattern Matching | Fast, strong code suggestions, good context | Sometimes less careful with edits  |
| GPT-4o             | 0x   | 128K    | ✅           | ✅            | ✅        | Pattern Matching | Multimodal, fast, versatile        | Can be less thorough              |
| GPT-5 mini         | 0x   | 128K    | ✅           | ✅            | ✅        | Fast Inference | Very fast, efficient               | Less capable than full GPT-5      |
| Grok Code Fast 1   | 0x   | 128K    | ✅           | ✅            | ✅        | Fast Inference | Fast code completion               | Less context, newer/less tested   |
| Raptor mini (Preview) | 0x | 128K   | ✅           | ✅            | ⚠️        | Fast Inference | Fast inference                     | Preview/experimental              |
| Claude Haiku 4.5   | 0.33x | 200K   | ✅           | ✅            | ✅        | Fast Inference | Very fast, efficient, good for quick tasks | Less capable than Sonnet         |
| Claude Opus 4.5 (Preview) | 3x | 200K | ✅         | ✅✅          | ✅        | Deep Reasoning | Most capable Claude model, best reasoning | Slower, expensive, preview        |
| Claude Sonnet 4    | 1x   | 200K    | ✅           | ✅            | ✅        | Balanced       | Balanced speed/capability          | Older version                     |
| Claude Sonnet 4.5  | 1x   | 200K    | ✅✅         | ✅✅          | ✅✅      | Deep Reasoning | **Trustworthy edits, careful, excellent reasoning, great at understanding context** | Can be verbose, uses credits      |
| Gemini 2.5 Pro     | 1x   | 1M+     | ✅           | ✅            | ✅        | Long Context   | Long context (1M+ tokens), multimodal | Less code-specialized             |
| Gemini 3 Pro (Preview) | 1x | 2M+   | ✅           | ✅            | ✅        | Structural     | **Excellent troubleshooting & structural reasoning (e.g. CSS layouts), precise fixes** | Preview/experimental              |
| GPT-5              | 1x   | 128K    | ✅           | ✅            | ✅        | Balanced       | Latest OpenAI flagship             | May be slower                     |
| GPT-5-Codex (Preview) | 1x | 128K   | ✅✅         | ✅            | ✅        | Code Logic     | Code-specialized GPT-5             | Preview/experimental              |
| GPT-5.1 (Preview)  | 1x   | 256K    | ✅           | ✅            | ✅        | Balanced       | Improved GPT-5                     | Preview/experimental              |
| GPT-5.1-Codex (Preview) | 1x | 256K | ✅✅         | ✅            | ✅        | Code Logic     | Code-specialized GPT-5.1           | Preview/experimental              |
| GPT-5.1-Codex-Max (Preview) | 1x | 256K | ✅✅     | ✅✅          | ✅        | Deep Code Logic| Maximum capability Codex variant   | Preview/experimental, slower      |
| GPT-5.1-Codex-Mini (Preview) | 0.33x | 128K | ✅   | ✅            | ✅        | Fast Code Logic| Faster Codex variant               | Preview/experimental              |
| GPT-5.2 (Preview)  | 1x   | 256K    | ✅           | ✅            | ✅        | Balanced       | Latest GPT-5 iteration             | Preview/experimental              |

## Local Models (Installed via Ollama)

Verified with `ollama list` on 2026-10-29. Fourteen models are installed on the host — this is
the complete inventory, not a candidate list. `ollama list` reports no context metadata, so
window sizes are omitted here rather than guessed.

| Name | ID | Size | Age | Role |
| :--- | :--- | ---: | :--- | :--- |
| GPT-OSS-20B:latest | f38aa0c53da5 | 13 GB | ~1 hour | OpenAI open-weight generalist; largest local model |
| Ministral-3-14B-Instruct:latest | 4760c35aeb9d | 9.1 GB | 3 days | Mistral instruct, newest pull after GPT-OSS |
| StarCoder2-3B:latest | 9f4ae0aff61e | 1.7 GB | 3 months | Code completion, small footprint |
| MoonDream-1.7B:latest | 55fc3abd3867 | 1.7 GB | 3 months | Vision / image-captioning |
| Qwen2.5-Coder-7B:latest | dae161e27b0e | 4.7 GB | 4 months | Coding |
| Hermes-3-8B-Instruct:latest | 4f6b83f30b62 | 4.7 GB | 4 months | Creative / uncensored, Llama 3.1 base |
| Mistral-Nemo-12B:latest | e7e06d107c6c | 7.1 GB | 4 months | General |
| Gemma-3-12B:latest | f4031aab637d | 8.1 GB | 4 months | General, multimodal |
| LLaVA-13B:latest | 0d0eb4d7f485 | 8.0 GB | 4 months | Vision |
| Llama-3.1-8B:latest | 46e0c10c039e | 4.9 GB | 4 months | General baseline |
| Qwen2.5-Coder-14B:latest | 9ec8897f747e | 9.0 GB | 4 months | Coding; strongest local coder |
| DeepSeek-Coder-V2-16B:latest | 63fb193b3a9b | 8.9 GB | 4 months | Coding, fill-in-middle |
| DeepSeek-R1-Qwen-8B:latest | 6995872bfe4c | 5.2 GB | 4 months | Reasoning, Qwen base |
| DeepSeek-R1-Llama-7B:latest | 755ced02ce7b | 4.7 GB | 4 months | Reasoning, Llama base |

> **Tag mismatch warning.** These are the *installed* tags and they are capitalised CamelCase
> names, not Ollama Library identifiers. `ollama run deepseek-r1:8b` does **not** resolve to the
> installed `DeepSeek-R1-Qwen-8B:latest`, and `ollama run llama3.1` does not resolve to
> `Llama-3.1-8B:latest`. Use the exact names in the table above.

### Ollama Catalog Reference (not installed)

Kept for hardware sizing only. These are **Ollama Library identifiers, not installed tags**, and
the `DL` (downloaded) column below is the original author's, retained verbatim — it does not
reflect this host. For what is actually installed, see the table above.

| Pull | Model | DL | Released | Context | Trainer | Focus | Base | VRAM | Fits | Rec? | Speed | Code | Und. | Auto | Strengths | Weaknesses |
| :--- | :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- | :---: | :---: | :--- | :---: | :---: | :---: | :--- | :--- |
| deepseek-r1:8b | **DeepSeek-R1 (8B)** | ✅ | 2025 | 128K | DeepSeek-R1 | Liberal Arts | Llama 3.1 | 6GB | ✅ | ✅ | Fast | ✅ | ✅✅ | ❌ | Great reasoning + natural language | Less code-specialized than Qwen |
| deepseek-r1:7b | **DeepSeek-R1 (7B)** | ✅ | 2025 | 128K | DeepSeek-R1 | STEM | Qwen 2.5 | 5GB | ✅ | ✅ | Fast | ✅ | ✅✅ | ❌ | Excellent logic & math reasoning | Can be terse |
| qwen2.5-coder:32b | **Qwen2.5-Coder (32B)** | ❌ | 2024 | 128K | Qwen | Coding | Qwen 2.5 | 20GB | ❌ | ❌ | Slow | ✅ | ✅ | ❌ | Strong code generation | Too big for 16GB VRAM |
| qwen2.5-coder:14b | **Qwen2.5-Coder (14B)** | ✅ | 2024 | 128K | Qwen | Coding | Qwen 2.5 | 10GB | ✅ | ✅ | Medium | ✅ | ✅ | ❌ | Good balance of speed/capability | Mid-tier performance |
| qwen2.5-coder:7b | **Qwen2.5-Coder (7B)** | ❌ | 2024 | 128K | Qwen | Coding | Qwen 2.5 | 6GB | ✅ | ⚠️ | Fast | ✅ | ✅ | ❌ | Efficient, fast | Less capable than 14B |
| qwen2.5-coder:1.5b | **Qwen2.5-Coder (1.5B)** | ❌ | 2024 | 128K | Qwen | Coding | Qwen 2.5 | 2GB | ✅ | ❌ | V.Fast | ⚠️ | ⚠️ | ❌ | Very fast | Weak code quality |
| qwen2.5:32b | **Qwen2.5 (32B)** | ✅ | 2024 | 128K | Qwen | STEM | Qwen 2.5 | 20GB | ❌ | ❌ | Slow | ✅ | ✅ | ❌ | Very smart, large knowledge base | Too big for 16GB VRAM |
| deepseek-coder-v2:236b | **DeepSeek-Coder-V2 (236B)** | ❌ | 2024 | 128K | DeepSeek | Coding | DeepSeek-V2 | 150GB+ | ❌ | ❌ | V.Slow | ✅✅ | ✅✅ | ❌ | Near GPT-4 level | Massive hardware reqs |
| deepseek-coder-v2:16b | **DeepSeek-Coder-V2 (16B)** | ✅ | 2024 | 128K | DeepSeek | Coding | DeepSeek-V2 | 12GB | ✅ | ✅ | Medium | ✅✅ | ✅ | ❌ | Strong code, fill-in-middle | No tool calling |
| deepseek-coder-v2:6.7b | **DeepSeek-Coder-V2 (6.7B)** | ❌ | 2024 | 128K | DeepSeek | Coding | DeepSeek-V2 | 5GB | ✅ | ⚠️ | Fast | ✅ | ✅ | ❌ | Fast, efficient | Less capable than 16B |
| deepseek-coder-v2:1.3b | **DeepSeek-Coder-V2 (1.3B)** | ❌ | 2024 | 128K | DeepSeek | Coding | DeepSeek-V2 | 2GB | ❌ | ❌ | V.Fast | ⚠️ | ⚠️ | ❌ | Very fast | Weak code quality |
| codellama:70b | **CodeLlama (70B)** | ❌ | 2023 | 100K | Meta | Coding | Llama 2 | 48GB+ | ❌ | ❌ | V.Slow | ✅ | ✅ | ❌ | Strong capabilities | Very high hardware reqs |
| codellama:34b | **CodeLlama (34B)** | ❌ | 2023 | 100K | Meta | Coding | Llama 2 | 22GB | ❌ | ❌ | Slow | ✅ | ✅ | ❌ | Better than 13B | High hardware reqs |
| codellama:13b | **CodeLlama (13B)** | ❌ | 2023 | 100K | Meta | Coding | Llama 2 | 9GB | ✅ | ✅ | Medium | ✅ | ✅ | ❌ | Good code completion | Older model |
| codellama:7b | **CodeLlama (7B)** | ❌ | 2023 | 100K | Meta | Coding | Llama 2 | 5GB | ✅ | ⚠️ | Fast | ✅ | ✅ | ❌ | Fast, efficient | Less capable than 13B |
| starcoder2:15b | **StarCoder2 (15B)** | ❌ | 2024 | 16K | BigCode | Coding | StarCoder2 | 10GB | ✅ | ✅ | Medium | ✅ | ✅ | ❌ | Better than 7B | Limited context |
| starcoder2:7b | **StarCoder2 (7B)** | ❌ | 2024 | 16K | BigCode | Coding | StarCoder2 | 5GB | ✅ | ⚠️ | Fast | ✅ | ✅ | ❌ | Fast, efficient | Limited capabilities |
| starcoder2:3b | **StarCoder2 (3B)** | ❌ | 2024 | 16K | BigCode | Coding | StarCoder2 | 3GB | ❌ | ❌ | V.Fast | ⚠️ | ✅ | ❌ | Very fast | Limited capabilities |
| phi3.5:3.8b | **Phi-3.5 (3.8B)** | ❌ | 2024 | 128K | Microsoft | Math/Logic | Phi-3 | 4GB | ❌ | ❌ | V.Fast | ⚠️ | ✅ | ❌ | Lightweight, CPU friendly | Limited capabilities |
| llama3.1:70b | **Llama 3.1 (70B)** | ❌ | 2024 | 128K | Meta | General | Llama 3.1 | 48GB+ | ❌ | ❌ | V.Slow | ⚠️ | ✅ | ❌ | Strong reasoning | Not code-specialized |
| llama3.1:8b | **Llama 3.1 (8B)** | ✅ | 2024 | 128K | Meta | General | Llama 3.1 | 6GB | ⚠️ | ⚠️ | Fast | ⚠️ | ✅ | ❌ | General purpose | Not code-specialized |
| hermes3:8b | **Hermes 3 (8B)** | ✅ | 2024 | 128K | Nous Research | Creative/Roleplay | Llama 3.1 | 6GB | ⚠️ | ⚠️ | Fast | ⚠️ | ✅ | ❌ | Uncensored, creative, follows instructions | Can hallucinate on strict logic |
| gpt-oss:20b | **GPT‑OSS (20B)** | ✅ | 2025 | 128K | OpenAI‑OSS | Generalist | GPT‑4‑OSS | 16GB | ✅ | 👍 | Med | ✅ | ✅ | ❌ | Strong balanced reasoning + broad domain coverage | Heavier than 8B, slower on 16GB GPUs |
| gpt-oss:120b | **GPT‑OSS (120B)** | ❌ | 2025 | 128K | OpenAI‑OSS | Generalist | GPT‑4‑OSS | 60–80GB | ❌ | ❌ | Very Slow | ❌ | ✅ | ❌ | High‑end reasoning potential | Requires massive VRAM; unusable on 16GB GPUs |
| gemma3:1.6b | **Gemma 3 (1.6B)** | ❌ | 2025 | 128K | Google | General | Gemma 3 | 2GB | ✅ | ❌ | V.Fast | ⚠️ | ⚠️ | ❌ | Extremely fast, lightweight, CPU‑friendly | Limited reasoning and coding ability |
| gemma3:4b   | **Gemma 3 (4B)**   | ❌ | 2025 | 128K | Google | General | Gemma 3 | 4–6GB | ✅ | ⚠️ | Fast | ⚠️ | ✅ | ❌ | Good balance of speed and quality for small size | Still weaker than 7B–8B class models |
| gemma3:12b  | **Gemma 3 (12B)**  | ❌ | 2025 | 128K | Google | General | Gemma 3 | 10–12GB | ✅ | 👍 | Med | ⚠️ | ✅ | ❌ | Strongest Gemma 3 model available in Ollama; good reasoning | Heavier and slower than 8B models; not code‑specialized |
| mistral-large | **Mistral Large 3** | ❌ | 2025 | 128K | Mistral | General / Frontier | Mistral Large 3 | 24–32GB | ❌ | ⚠️ | Slow | ⚠️ | ✅ | ❌ | Very strong reasoning and high‑end open‑weight performance | Too large for 16GB VRAM; slow without high‑end GPUs |
| mistral-small | **Mistral Small 3** | ❌ | 2025 | 128K | Mistral | General | Mistral Small 3 | 4–6GB | ✅ | 👍 | Fast | ⚠️ | ✅ | ❌ | Fast, efficient, good general performance | Not as strong as 12B–20B class models |
| mistral-nemo | **Mistral Nemo** | ❌ | 2024 | 128K | Mistral | General | Nemo | 8–10GB | ✅ | 👍 | Med | ⚠️ | ✅ | ❌ | Strong reasoning for its size; efficient | Not as capable as frontier‑scale models |
| mixtral:8x7b | **Mixtral 8×7B** | ❌ | 2023 | 32K | Mistral | General | Mixtral | 16–20GB | ⚠️ | ⚠️ | Med | ⚠️ | ✅ | ❌ | MoE architecture gives high quality for size | VRAM heavy; slower on 16GB GPUs |
| mixtral:8x22b | **Mixtral 8×22B** | ❌ | 2024 | 64K | Mistral | General | Mixtral | 48–64GB | ❌ | ❌ | V.Slow | ⚠️ | ✅ | ❌ | Very strong reasoning and knowledge | Requires massive VRAM; unusable on 16GB GPUs |
| mistral:7b | **Mistral 7B Instruct** | ❌ | 2023 | 32K | Mistral | General | Mistral 7B | 6–8GB | ✅ | 👍 | Fast | ⚠️ | ✅ | ❌ | Strong small model; good reasoning | Older architecture; weaker than newer 8B–12B models |
| llama4 | **Llama 4** | ❌ | 2025 | 128K | Meta | General | Llama 4 | 12–16GB | ⚠️ | 👍 | Med | ⚠️ | ✅ | ❌ | Strong general‑purpose reasoning; modern open‑weight frontier model | Heavier than 8B models; slower on 16GB GPUs; not code‑specialized |
| llama3.2 | **Llama 3.2 (3B)** | ❌ | 2024 | 128K | Meta | General | Llama 3.2 | 4–6GB | ✅ | 👍 | Fast | ⚠️ | ✅ | ❌ | Very fast, efficient, good small‑model reasoning | Not as capable as 8B–12B class |
| llama3.2:1b | **Llama 3.2 (1B)** | ❌ | 2024 | 128K | Meta | General | Llama 3.2 | 2GB | ✅ | ❌ | V.Fast | ⚠️ | ⚠️ | ❌ | Extremely fast, CPU‑friendly | Limited reasoning and coding ability |
| llama3.1:8b | **Llama 3.1 (8B)** | ❌ | 2024 | 128K | Meta | General | Llama 3.1 | 6GB | ⚠️ | 👍 | Fast | ⚠️ | ✅ | ❌ | Strong general model; good balance of speed and quality | Not code‑specialized |
| llama3.1:70b | **Llama 3.1 (70B)** | ❌ | 2024 | 128K | Meta | General | Llama 3.1 | 48GB+ | ❌ | ❌ | V.Slow | ⚠️ | ✅ | ❌ | High‑end reasoning and knowledge | Requires massive VRAM; unusable on 16GB GPUs |
| llama3:8b | **Llama 3 (8B)** | ❌ | 2024 | 128K | Meta | General | Llama 3 | 6GB | ⚠️ | 👍 | Fast | ⚠️ | ✅ | ❌ | Good general reasoning; efficient | Older than 3.1/3.2; weaker coding |
| llama3:70b | **Llama 3 (70B)** | ❌ | 2024 | 128K | Meta | General | Llama 3 | 48GB+ | ❌ | ❌ | V.Slow | ⚠️ | ✅ | ❌ | Strong reasoning | Too large for 16GB VRAM |



## Models Available via API Keys

This inventory is **extension-agnostic in intent**: it records which providers are reachable
from the API keys on this machine, not which agent extension consumes them. Zoo Code is the
extension in active use; Cline is being retired. Keys are *migrated* between them, not shared,
so never assume both clients see the same set.

**No key material is reproduced here** — only provider names, endpoints, model IDs and limits.

### Where the keys live (and why only one store is readable)

| Store | Location | Enumerable? |
| :--- | :--- | :--- |
| Cline | `~/.cline/data/settings/providers.json` | **Yes** — plaintext JSON with a `providers` map |
| Zoo Code / Roo Code | VS Code SecretStorage (`~/.config/Code/User/globalStorage/state.vscdb`) | **No** — encrypted; `grep` finds no `apiKey` string anywhere in Zoo's globalStorage |
| Zoo Code model cache | `~/.config/Code/User/globalStorage/zoocodeorganization.zoo-code/cache/` | **Yes** — cached catalogs only, never keys |

Consequence: the provider query results below come from the **Cline store**, because it is the
only readable one. They are a *floor* for what Zoo can reach, not a ceiling. Because forks keep
keys in SecretStorage by design, a Zoo-only provider cannot be enumerated — only inferred from
what the extension has cached.

**These stores diverge from 2026-10-29 onward.** Both clients held the same key set up to that
date and Zoo is now primary, so treat the Cline table as historical and re-derive from Zoo (its
UI, or its cache) rather than trusting this page for anything Zoo-specific.

### Providers reachable from the Cline key store

Seven distinct providers. Eight entries exist because `openai-compatible` points at the *same*
`inference-api.nousresearch.com` base URL as `nousResearch`; it adds no coverage and can be
removed.

| Provider key | Endpoint | Models returned | Largest context |
| :--- | :--- | ---: | ---: |
| `nousResearch` | `https://inference-api.nousresearch.com/v1` | 382 | 2,000,000 |
| `openai-native` | `https://api.openai.com/v1` | 134 | 1,050,000 * |
| `gemini` | `https://generativelanguage.googleapis.com/v1beta` | 46 | 1,048,576 |
| `mistral` | `https://api.mistral.ai/v1` | 55 | 1,048,576 |
| `moonshot` | `https://api.moonshot.ai/v1` | 6 | 1,048,576 |
| `deepseek` | `https://api.deepseek.com` | 2 | 1,048,576 * |
| `anthropic` | `https://api.anthropic.com/v1` | 14 | 1,000,000 * |
| `openai-compatible` | duplicate of `nousResearch` | 382 | 2,000,000 |

`*` = the provider's own `/models` response carries **no** context field. Those figures come
from the NousResearch catalog metadata for the same model IDs, which is the only cross-check
available here. Gemini, Mistral and Moonshot publish limits directly, as does Zoo's own cache.

### Providers Zoo Code has catalogued (cache is not proof of a key)

Zoo caches a model catalog per provider as it fetches them. Presence proves the extension has
talked to that endpoint; it does **not** prove a key is configured — OpenRouter's catalog, for
one, is public.

| Cached catalog | Models | Largest context | Cache written |
| :--- | ---: | ---: | :--- |
| `openrouter` | 445 | 2,000,000 | 2026-10-29 |
| `nanogpt` | 439 | 10,000,000 † | 2026-10-29 |
| `vercel-ai-gateway` | 321 | 2,000,000 | 2026-10-29 |
| `io-intelligence` | 41 | 1,048,576 | 2026-10-29 |
| `ollama` | 8 of 14 installed | 1,024,000 | 2026-10-28 |
| `moonshot` | 6 | 1,048,576 | 2026-10-28 |
| `deepseek` | 2 | 1,000,000 | 2026-10-28 |

† `pokee-isaac` at 10,000,000 tokens is the single largest figure anywhere in these catalogs. It
is reported by NanoGPT's own metadata and is unverified here — treat it as a special-purpose
long-context model, not a general coding workhorse.

Two things this table settles. First, **DeepSeek is 1,000,000**, stated by the extension's own
provider metadata for `deepseek-flash` and `deepseek-v4-pro` — independent confirmation of the
correction described below. Second, the `ollama` cache covers only 8 of the 14 installed models,
so the extension's view of local models is incomplete; `ollama list` remains authoritative for
those.

### Largest context window you can actually reach

Ordered by ceiling across everything enumerated, direct stores and cached catalogs alike.

| Rank | Source | Model | Context | Notes |
|:--:|---|---|---:|---|
| 1 | `nanogpt` cache | `pokee-isaac` | **10,000,000** | Catalog-reported, unverified † |
| 2 | `nousResearch` | `x-ai/grok-4.20` | **2,000,000** | Also in `openrouter` and `vercel-ai-gateway` |
| 2 | `openrouter` cache | `openrouter/pareto-code`, `x-ai/grok-4.20` | 2,000,000 | |
| 2 | `vercel-ai-gateway` cache | `spacexai/grok-4.20-multi-agent` (+variants) | 2,000,000 | |
| 5 | `openrouter` cache | `meta-llama/llama-4-scout` | 1,310,720 | Only model above 1.05M below the 2M tier |
| 6 | `openai-native` | `gpt-6.1-sol` / `-pro`, `-terra` / `-pro`, `-luna` / `-pro` | 1,050,000 | `*` via aggregator metadata |
| 7 | `gemini` | `gemini-4-argon`, `gemini-3.8-flash`, `gemini-3.1-pro-preview`, `gemini-2.5-pro` | 1,048,576 | 65,536 max output |
| 7 | `mistral` | `mistral-large-4`, `mistral-large-4-0` | 1,048,576 | |
| 7 | `io-intelligence` cache | `moonshotai/Kimi-K3`, `deepseek-ai/DeepSeek-V4-Pro` | 1,048,576 | |
| 7 | `moonshot` | `kimi-k3` | 1,048,576 | See discrepancy note below |
| 7 | `deepseek` | `deepseek-flash`, `deepseek-v4-pro` | 1,048,576 | Confirmed by Zoo's own metadata |
| 12 | `anthropic` | `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`, `claude-fable-5-1` | 1,000,000 | `*` |

Every provider reaches at least 1M, and the aggregators reach 2M. **Window size is no longer a
differentiator** — choose on output ceiling, price per token and cache pricing instead.

**Discrepancy worth knowing:** Moonshot's own API reports 1,048,576 for both `kimi-k3` and
`kimi-k3.1-pro`, but Zoo's cache records `kimi-k3` at 1,048,576 and `kimi-k3.1-pro` at 262,144.
The cache is the older figure and the direct API is authoritative; a 262K limit on the "pro"
variant would be an odd regression, so verify before committing a long prompt to it.

**Model selections below are per-extension.** Each provider's "configured model" line is read
from the Cline store. Zoo's active selection is independent — currently `deepseek-flash` — and
the two will drift as Cline is retired.

### DeepSeek — 2 models

| Model | Context |
| :--- | ---: |
| `deepseek-flash` | 1,048,576 |
| `deepseek-v4-pro` | 1,048,576 |

`deepseek-chat` and `deepseek-reasoner` no longer appear — the public IDs have been retired in
favour of the V4 line. `deepseek-flash` is the model currently driving this chat.

### Anthropic — 14 models

`claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`, `claude-fable-5-1`, `claude-opus-5`,
`claude-sonnet-5`, `claude-fable-5`, `claude-opus-4-8`, `claude-opus-4-7`, `claude-sonnet-4-6`,
`claude-opus-4-6`, `claude-opus-4-5-20251101`, `claude-haiku-4-5-20251001`,
`claude-sonnet-4-5-20250929`.

All 1M per aggregator metadata. Cline's configured model is `claude-sonnet-5`.

### Google Gemini — 46 generateContent models

Text / coding tier (1,048,576 in, 65,536 out unless noted): `gemini-4-argon` (32,768 out),
`gemini-3.8-flash`, `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`,
`gemini-3.5-flash-lite`, `gemini-3.1-pro-preview`, `gemini-3.1-pro-preview-customtools`,
`gemini-3.1-flash-lite`, `gemini-3.1-flash-lite-preview`, `gemini-3-flash-preview`,
`gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-pro-latest`,
`gemini-flash-latest`, `gemini-flash-lite-latest`.

Other tiers: `gemma-4-31b-it` / `gemma-4-26b-a4b-it` (262,144 in / 32,768 out);
`antigravity-preview-latest` and `-05-2026` / `-09-2026` (1,048,576);
`gemini-3-pro-image` family and `nano-banana-pro-preview` (131,072 in / 32,768 out);
image-editing models (65,536); `gemini-3.5-transcribe` (98,304);
`deep-research-*` (131,072); `lyria-3*` music models (1,048,576);
TTS models (8,192 in / 16,384 out); `gemini-robotics-er-2-preview` and
`gemini-2.5-computer-use-preview-10-2025` (131,072).

Cline's configured model is `gemini-3.1-pro-preview`.

### OpenAI — 134 models returned (embeddings, TTS, Whisper and image models included)

Current flagships: `gpt-6.1-sol`, `gpt-6.1-sol-pro`, `gpt-6.1-terra`, `gpt-6.1-terra-pro`,
`gpt-6-sol`, `gpt-6-sol-pro`, `gpt-6-astra`, `gpt-6-astra-pro`, `gpt-6-luna`,
`gpt-6-luna-pro`.

Prior generations still served: `gpt-5.6-{sol,terra,luna}` (+`-pro`), `gpt-5.5` (+`-pro`),
`gpt-5.4` (+`-pro`/`-mini`/`-nano`), `gpt-5.3-codex`, `gpt-5.2` (+`-pro`/`-codex`),
`gpt-5.1` (+`-codex`/`-codex-max`/`-codex-mini`), `gpt-5` (+`-pro`/`-mini`/`-nano`/`-codex`),
`gpt-4.1` (+`-mini`/`-nano`), `gpt-4o` (+`-mini`), `o1`/`o1-pro`, `o3`/`o3-mini`, `o4-mini`.

Specialised: `gpt-realtime-2.1` family, `gpt-audio-1.5` family, `gpt-live-1`,
`gpt-5-search-api`, `gpt-4o-search-preview`, and the `*-chat-latest` aliases.

Cline's configured model is `gpt-5.4`.

### Mistral — 55 models

Frontier: `mistral-large-4`, `mistral-large-4-0` (1,048,576).
Mid: `mistral-medium-latest`, `mistral-medium-3.5`, `mistral-medium-3`, `mistral-medium-2604`
(262,144). Small: `mistral-small-latest`, `mistral-small-2603` (262,144).
Reasoning: `magistral-medium-latest`, `magistral-small-latest` (262,144).
Coding: `codestral-latest`, `codestral-2508`, `mistral-code-latest`, `mistral-code-fim-latest`
(256,000). Edge: `ministral-14b` (262,144), `ministral-8b` (262,144), `ministral-3b` (131,072).
Research: `labs-leanstral-1-5`, `-1-5-1` (262,144).
Audio/OCR/embed: `voxtral-*`, `mistral-ocr-*` (16,384), `codestral-embed` / `mistral-embed`
(8,192), `mistral-moderation-2603`.

Cline's configured model is `mistral-code-latest`.

### Moonshot — 6 models

| Model | Context |
| :--- | ---: |
| `kimi-k3` | 1,048,576 |
| `kimi-k3.1-pro` | 1,048,576 |
| `kimi-k3.1-pro-highspeed` | 1,048,576 |
| `kimi-k2.7-code` | 262,144 |
| `kimi-k2.7-code-highspeed` | 262,144 |
| `kimi-k2.6` | 262,144 |

Cline's configured model is `kimi-k3`.

### NousResearch — 382 models (aggregator)

This endpoint is a multi-vendor aggregator, not a single model family. 173 of its 382 models
offer 1M or more. Context tiers:

| Context | Count | Example models |
| ---: | ---: | :--- |
| 2,000,000 | 1 | `x-ai/grok-4.20` |
| 1,050,000 | 48 | `openai/gpt-6.1-*`, `xiaomi/mimo-v2.6-*` |
| 1,048,756 | 1 | `meituan/longcat-2.0` |
| 1,048,576 | 73 | `google/gemini-*`, `deepseek/deepseek-v4*`, `z-ai/glm-5.3`, `moonshotai/kimi-k3` |
| 1,047,576 | 3 | `openai/gpt-4.1` (+`-mini`/`-nano`) |
| 1,000,000 | 47 | `anthropic/claude-*`, `qwen/qwen3.8-*`, `sakana/fugu-*` |
| 524,288 | 6 | `upstage/solar-pro4`, `thinkingmachines/inkling` |
| 400,000-500,000 | 21 | `x-ai/grok-4.5/4.6/4.7`, `openai/gpt-5.4-*` |
| 262,144 | 59 | `minimax/*`, `bytedance-seed/*`, `elorian/glimpse` |
| ≤ 256,000 | remainder | older Llama/Qwen/Mistral, embeddings, rerankers |

Vendor spread (top): `openai`=80, `qwen`=42, `google`=34, `mistralai`=22, `anthropic`=20,
`z-ai`=20, `deepseek`=17, `moonshotai`=10, `amazon`=8, `minimax`=7, `x-ai`=7.

Catalog conventions: `:batch` = batch-pricing twin of the same model, `:free` = rate-limited
free tier, `:US` = US-region routing, and a `~` prefix (`~openai/gpt-sol-latest`) = a
floating "latest" alias. Cline's configured model here is `deepseek/deepseek-v4.1-flash-1017`.

## Column Definitions

### Online Models

Applies to the Copilot table above, which is legacy reference. The API-key providers in
[Models Available via API Keys](#models-available-via-api-keys) bill per token against your own
keys, so the credit multiplier below does **not** describe their cost.

- **Cost**: Credit multiplier for your GitHub Copilot subscription
  - **0x** = Unlimited usage, no credits consumed
  - **0.33x, 1x, 3x** = Multipliers showing how fast you consume your monthly credit allocation
- **Context**: Maximum tokens the model can process at once (128K = ~96,000 words)
  - **Why it matters**: Larger contexts let the model see more of your codebase simultaneously, improving accuracy for large files or multi-file operations
  - **128K** = Good for most files/functions
  - **200K-256K** = Great for large files or multiple related files
  - **1M-2M+** = Can analyze entire small-to-medium projects at once
- **Code Changes**: How well the model generates/modifies code
  - ✅ = Good, ✅✅ = Excellent
- **Understanding**: How well the model comprehends existing code and context
  - ✅ = Good, ✅✅ = Excellent
- **Autopilot**: Can the model autonomously create/edit files in VS Code
  - ✅ = Yes (via GitHub Copilot Chat agents), ❌ = No
- **Reasoning Type**: The primary cognitive approach the model uses
  - **Pattern Matching**: Relies on common patterns and boilerplate (fast, good for standard tasks)
  - **Deep Reasoning**: Analyzes logic and implications carefully (slower, better for complex refactoring)
  - **Structural**: Understands systems, hierarchies, and dependencies (excellent for debugging and layouts)
  - **Code Logic**: Specialized training on code execution and syntax
  - **Fast Inference**: Optimized for speed over depth

### Local Models

- **DL**: Downloaded (✅ = Installed)
- **Trainer** (Professor): The model creator (e.g., DeepSeek-R1, Meta)
- **Focus** (Subject): The model's specialization (e.g., STEM, Liberal Arts, Coding)
- **Base** (Student): The base architecture (e.g., Qwen, Llama)
- **VRAM**: Minimum GPU memory needed
- **Fits**: Fits 16GB VRAM?
- **Rec?** (Sweet Spot): Recommended for your hardware?
- **Code**: Code Generation capability
- **Und.**: Code Understanding capability
- **Auto**: Autopilot capability (❌ for all local models)

**Notes:**

- **Cost (Credits):**
  - **0x (Unlimited)** = No credit usage with GitHub Copilot subscription—use freely
  - **0.33x, 1x, 3x** = Multipliers consuming your monthly Copilot credits
  - **Free** = Local models requiring no subscription (need Ollama/Continue setup)
- **"Can Make Code Changes (Autopilot)" = ❌** for local models because they lack:
  - Tool calling/function calling capabilities for file operations
  - Deep VS Code Copilot extension integration
  - Multi-step autonomous reasoning and planning
- **Claude Sonnet 4.5** is noted for being especially trustworthy with code changes—users report higher confidence in its edits.
- Models marked **(Preview)** are experimental and may have limited availability or stability.
- **VRAM requirements** assume quantized models (e.g., 4-bit or 8-bit); full precision requires 2-4x more VRAM.
- Local models require Ollama, LM Studio, or similar tools, plus extensions like Continue.

## Understanding the "Lineage" Columns (Trainer, Focus, Base)

Just like people, AI models have a "Nature" (Base) and "Nurture" (Trainer/Focus). We have split the detailed definitions into separate pages for clarity:

*   **[The Trainers (The Universities)](ai-models/trainers.md)**: Who taught the model? (Meta, DeepSeek, Qwen, etc.)
*   **[The Subjects (The Focus)](ai-models/subjects.md)**: What is the model's major? (STEM, Coding, Creative, etc.)
*   **[The Bases (The Students)](ai-models/bases.md)**: What is the underlying architecture? (Llama 3.1, Qwen 2.5, etc.)

## Model Recommendations by Task (Based on Experience)

| Task Type | Recommended Model | Why? |
| :--- | :--- | :--- |
| **Complex Debugging / CSS** | `gemini-3.1-pro-preview` | Structural reasoning; reads the hierarchy instead of guessing properties. |
| **Refactoring / Cleanup** | `claude-sonnet-5.5` | Careful, preserves logic; the "do no harm" choice. |
| **New Feature / Boilerplate** | `gpt-6.1-terra` | Fast, standard patterns, large output budget. |
| **Largest context available** | `x-ai/grok-4.20` (via `nousResearch`) | 2,000,000 tokens — the only 2M model on any configured key. |
| **Repo-wide on a direct provider** | `gemini-4-argon` / `gemini-3.8-flash` | 1,048,576 in, 65,536 out. Gemini is **not** 2M via the direct API. |
| **Long file rewrites** | `gpt-6.1-sol` | 1,050,000 in with the largest output budget of the direct providers. |
| **Cheapest bulk context** | `deepseek-flash` | 1,048,576 at DeepSeek pricing; the current session model. |

## Understanding Model Distillation (The University Analogy)

**The Concept:**
*   **DeepSeek-R1 (The Big 671B Model)** is the **Nobel Prize-Winning Professor**. It has decades of experience and knows *everything*.
*   **The "Reasoning Data"** is the **Curriculum/Textbook** written by that Professor. It contains all the steps on *how* to solve complex problems, not just the answers.
*   **Qwen (The Base Model)** is a **Computer Science Major**. He is naturally good at math, logic, and code.
*   **Llama (The Base Model)** is a **Liberal Arts/General Studies Major**. He is naturally good at language, nuance, and cultural context.

**The Result:**
When **DeepSeek (The University)** forces them both to take the **"Advanced Reasoning"** class taught by the Professor:

1.  **The Qwen Student (DeepSeek-R1-Distill-Qwen)**:
    *   Absorbs the logic and math lessons instantly.
    *   Becomes a **super-coder**.
    *   Result: "I can solve this complex algorithm step-by-step."
    *   *Best for: Coding, Math, Logic Puzzles.*

2.  **The Llama Student (DeepSeek-R1-Distill-Llama)**:
    *   Absorbs the reasoning but applies it with better flow and language.
    *   Becomes a **great writer who can now think logically**.
    *   Result: "I can write a persuasive essay with a perfectly structured logical argument."
    *   *Best for: Creative Writing, Nuanced Explanations, Roleplay.*

## Llama 3.1 Variants Ranking (The "Llama" Class)

Since many models are now based on the Llama 3.1 architecture (the "Student"), here is how they rank against each other based on their "Professor" (Training) and "Subject" (Specialization).

| Rank | Model Name | The "Professor" (Trainer) | The "Subject" (Strength) | Why it Wins / Loses |
| :--- | :--- | :--- | :--- | :--- |
| 🥇 **1st** | **DeepSeek-R1-Distill-Llama-8B** | **DeepSeek (Nobel Prize Winner)** | **Advanced Logic & Reasoning** | Takes the natural language fluency of Llama and adds the deep reasoning capabilities of DeepSeek-R1. Best of both worlds for 8B size. |
| 🥈 **2nd** | **Meta Llama 3.1 70B** | **Meta (The University Dean)** | **General Knowledge (PhD Level)** | Massive knowledge base and very capable, but requires huge hardware (48GB+ VRAM). Wins on raw knowledge, loses on efficiency. |
| 🥉 **3rd** | **Meta Llama 3.1 8B** | **Meta (The University Dean)** | **General Studies (Undergrad)** | The solid baseline. Good at English and basic tasks, but lacks the "advanced reasoning" training of the DeepSeek version. |
| 🏅 **Honorable Mention** | **Hermes 3 (Llama 3.1 8B)** | **Nous Research (The Rebel)** | **Creative Writing & Uncensored** | Unlocked and fine-tuned for roleplay and creative tasks. The "Art Student" of the group. |

### How to Download These Models
The models above are already installed, under different tags. Run these to use the local copies
(the `:latest` suffix is implicit, so it can be omitted):

*   **DeepSeek-R1 (Qwen base, 8B)**: `ollama run DeepSeek-R1-Qwen-8B`
*   **DeepSeek-R1 (Llama base, 7B)**: `ollama run DeepSeek-R1-Llama-7B`
*   **Meta Llama 3.1 8B**: `ollama run Llama-3.1-8B`
*   **Hermes 3 (8B)**: `ollama run Hermes-3-8B-Instruct`

To fetch the upstream Library tags instead, use `ollama pull deepseek-r1:8b`,
`ollama pull llama3.1` or `ollama pull hermes3` — those are separate downloads and will appear
as additional entries in `ollama list`.

> **Correction to the ranking table above.** The installed set inverts the sizes: the Qwen-based
> distillation is the 8B (`DeepSeek-R1-Qwen-8B`) and the Llama-based one is the 7B
> (`DeepSeek-R1-Llama-7B`), so line-for-line size comparisons between the two are not like-for-like.

## The Extension vs. The Model: An Analogy

It is important to distinguish between the **Model** (the intelligence) and the **Extension** (the tool you use to access it).

### 1. The Model = The Brain 🧠

- **Examples:** `gemini-4-argon`, `gpt-6.1-terra`, `claude-sonnet-5.5`, `deepseek-flash`.
- **Function:** This is the raw intelligence. It knows Python, it knows logic, and it can generate text.
- **Limitation:** A brain in a jar cannot type, run commands, or see your file system unless someone connects it.

### 2. The Extension = The Body & Toolbox 🛠️

- **Examples:** GitHub Copilot, Continue, Cline.
- **Function:** This connects the Brain to your VS Code environment. It determines what the Brain can *see* and *do*.

#### 🤖 GitHub Copilot (The Agent)

- **Analogy:** An **Embedded Engineer** sitting at your keyboard.
- **Capabilities:**
  - **Has Hands:** Can run terminal commands (`ls`, `grep`), create files, and edit code directly.
  - **Has Eyes:** Can search your entire workspace to find context automatically.
  - **Action-Oriented:** You say "Fix the bug," and it investigates, plans, and executes the fix.

#### 🗣️ Continue (The Advisor)

- **Analogy:** A **Senior Consultant** behind a glass window.
- **Capabilities:**
  - **Has a Voice:** Can give brilliant advice and write code snippets on a whiteboard (the chat window).
  - **Flexible Brain:** Lets you easily swap the "Brain" (e.g., switch from Gemini to a local Ollama model) instantly.
  - **Passive:** It generally waits for you to show it the code (`@file`) and doesn't typically run commands or explore your file system on its own.

#### 🏗️ Cline (The Contractor)

- **Analogy:** An **Autonomous Contractor**.
- **Capabilities:**
  - **Bring Your Own Tools:** You provide the API key (paying for materials/tokens directly).
  - **Highly Independent:** Can execute complex multi-step tasks, run terminal commands, and edit files with high autonomy.
  - **Cost:** You pay per task (token usage) directly to the model provider (Anthropic/OpenAI), which can get expensive for large refactors.

#### ⚡ Codeium / Tabnine (The Intern)

- **Analogy:** A **Fast Intern** (Free Tier).
- **Capabilities:**
  - **Speed:** Very fast at autocomplete and simple suggestions.
  - **Cost:** Often free for individuals.
  - **Limitation:** "Get what you pay for." The free tier runs smaller models than the paid frontier families (`gpt-6.1-*`, `claude-*-5.5`, `gemini-4-*`). Fine for boilerplate; it may struggle with complex logic or deep reasoning compared with the paid "Senior Engineers."

#### 📚 Sourcegraph Cody (The Librarian)

- **Analogy:** The **Head Librarian** with a photographic memory.
- **Capabilities:**
  - **Deep Context:** Its superpower is understanding the *entire* codebase, not just open files. It uses Sourcegraph's code graph to find definitions and references across massive repositories.
  - **Retrieval:** Excellent at answering "Where is this defined?" or "How does the auth system work?" by pulling context from everywhere.
  - **Enterprise Grade:** Often shines in very large, complex corporate environments where finding the right code is half the battle.
