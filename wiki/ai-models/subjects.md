<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: wiki/ai-models/subjects.md % -->
<!-- %ccm_git_object_id: wiki/ai-models/subjects.md@195 % -->
<!-- %ccm_git_commit_date: 2026-10-29 21:42:03 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: mkdocs updates % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!-- # %git_commit_history: 2025-09-06 mpegg  hook final alpha v0.1  %  -->
# The Subjects (The Focus) 📚

In our analogy, the **Subject** is the model's major or specialisation. Just as a student majors
in Maths, English or Computer Science, models are trained and tuned toward particular work.

The **partition is durable** — these categories have survived four model generations. The
**examples are not**: they reflect a live catalog pull on **2026-10-30** and will be stale long
before the rows are.

| Subject (Focus) | Description | Strengths | Weaknesses | Current examples (2026-10) |
| :--- | :--- | :--- | :--- | :--- |
| **Coding** | Writing, debugging and refactoring code. | Syntax accuracy, library recall, fill-in-the-middle, patch-shaped output. | Weak general world knowledge; may overfit to common idioms. | `qwen3-coder`, `codestral-2508`, `kimi-k2.7-code`, `gpt-5.1-codex-max`, `Qwen2.5-Coder-14B` (local) |
| **STEM / Reasoning** | Hard logic, mathematics, algorithmic thinking. | Multi-step verification, self-correction, formal problems. | Verbose; can over-deliberate on trivial asks. | `deepseek-v4-pro`, `magistral-medium`, `glm-5.3`, `gpt-6.1-sol` (high effort) |
| **Liberal Arts** | Language, culture, history, nuance. | Drafting, summarising, register and tone control. | Struggles with obscure syntax and formal logic versus specialists. | `Llama-3.1-8B`, `llama-4-maverick`, `gemma-4-31b-it`, `muse-wonder` |
| **Creative / Roleplay** | Storytelling, character, dialogue. | Stays in voice; follows unusual instructions without hedging. | Hallucinates more readily when asked for strict facts. | `hermes-3-llama-3.1-405b`, `Hermes-3-8B-Instruct` (local), `grok-4.7` |
| **Long-context analysis** | Whole-repository, whole-contract, whole-transcript reading. | Holds a large corpus in one pass; cross-references far apart. | Retrieval fidelity still decays near the ceiling; price scales with size. | `grok-4.20` (2M), `gemini-4-argon` (1.05M), `kimi-k3` (1M), `deepseek-flash` (1M) |
| **Agentic / tool use** | Driving shells, file edits and multi-step plans. | Reliable structured output, recovers from failed calls, respects schemas. | Cost multiplies — every step resends context. | `claude-sonnet-5.5`, `gpt-6.1-terra`, `gemini-3.1-pro-preview` |
| **Fast inference** | Latency-bound work: autocomplete, classification, routing. | Cheap and quick; good enough for narrow tasks. | Shallow reasoning; fails on multi-file refactors. | `gemini-3.5-flash-lite`, `glm-5.3-flashx`, `minimax-m3.1-flash`, `mistral-small-2603` |
| **Multimodal** | Understanding images, audio and video. | Reads screenshots, diagrams, scans and speech. | Slower; image tokens consume context quickly. | `gemini-4-argon`, `voxtral-small`, `mistral-ocr-4`, `llava` / `moondream` (local) |
| **Embeddings / retrieval** | Turning text into vectors for search and RAG. | Stable similarity, cheap at volume, multilingual. | Not an assistant — cannot reason or converse. | `voyage-4-large`, `codestral-embed`, `mistral-embed`, `sentence-transformers/*` |

## Two subjects that did not exist in the old list

**Long-context analysis** and **agentic tool use** were not separate rows when this page was
first written, because in 2024 no model on this host held more than ~200K tokens and none were
trusted to drive a shell. Both are now primary selection criteria: every configured provider
reaches at least 1M, and Cline/Zoo configs carry explicit `reasoning.effort` budgets that only
matter for agentic loops.

**"Real-Time / Truth" is gone.** It described Grok's X integration as a *capability*. Grok 4.x
is a general frontier family now, and if freshness matters the tool is retrieval — Perplexity
`sonar` or SearXNG — not a model's training cut-off.

## Choosing between subjects

A model is rarely one subject only. `gemini-4-argon` is simultaneously long-context, multimodal
and agentic; `deepseek-v4-pro` is reasoning and cheap. Pick on the subject that dominates *this*
task, then break ties on context ceiling, output limit and cache price — see
[Models Available (VS Code)](../vscode-ai-models.md#models-available-via-api-keys).

## Related

- **[The Trainers (The Universities)](trainers.md)**: who taught the model.
- **[The Bases (The Students)](bases.md)**: the underlying architecture, where one is visible.
