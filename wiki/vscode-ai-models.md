<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/vscode-ai-models.md:124 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 2fda8c283f97d5dfba32b2481af547afd3315cf1 %
  %ccm_git_commit_id: 8b4b8c60fcc3a47d5432304b72990dd91eef1e93 %
  %ccm_git_commit_count: 124 %
  %ccm_git_commit_date: 2025-12-12 21:43:31 -0500 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: friday checkin %
  %ccm_git_modify_date: 2025-12-12 21:43:36 %
  %ccm_git_file_last_modified: 2025-12-12 21:35:57 %
  %ccm_git_file_name: vscode-ai-models.md %
  %ccm_git_path: wiki/vscode-ai-models.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 11499 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# AI Models Available in GitHub Copilot (VS Code)

## Models Available Through GitHub Copilot Extension

| Model Name         | Cost (Credits) | Can Run Local | Good at Code Changes | Good at Understanding Code | Can Make Code Changes (Autopilot) | Strengths                          | Weaknesses                        |
|--------------------|:--------------:|:-------------:|:--------------------:|:--------------------------:|:----------------------------------:|------------------------------------|------------------------------------|
| GPT-4.1            | 0x (Unlimited) | N             | ✅                   | ✅                         | ✅                                 | Fast, strong code suggestions, good context | Sometimes less careful with edits  |
| GPT-4o             | 0x (Unlimited) | N             | ✅                   | ✅                         | ✅                                 | Multimodal, fast, versatile        | Can be less thorough              |
| GPT-5 mini         | 0x (Unlimited) | N             | ✅                   | ✅                         | ✅                                 | Very fast, efficient               | Less capable than full GPT-5      |
| Grok Code Fast 1   | 0x (Unlimited) | N             | ✅                   | ✅                         | ✅                                 | Fast code completion               | Less context, newer/less tested   |
| Raptor mini (Preview) | 0x (Unlimited) | N          | ✅                   | ✅                         | ⚠️                                 | Fast inference                     | Preview/experimental              |
| Claude Haiku 4.5   | 0.33x          | N             | ✅                   | ✅                         | ✅                                 | Very fast, efficient, good for quick tasks | Less capable than Sonnet         |
| Claude Opus 4.5 (Preview) | 3x       | N             | ✅                   | ✅✅                       | ✅                                 | Most capable Claude model, best reasoning | Slower, expensive, preview        |
| Claude Sonnet 4    | 1x             | N             | ✅                   | ✅                         | ✅                                 | Balanced speed/capability          | Older version                     |
| Claude Sonnet 4.5  | 1x             | N             | ✅✅                 | ✅✅                       | ✅✅                               | **Trustworthy edits, careful, excellent reasoning, great at understanding context** | Can be verbose, uses credits      |
| Gemini 2.5 Pro     | 1x             | N             | ✅                   | ✅                         | ✅                                 | Long context (1M+ tokens), multimodal | Less code-specialized             |
| Gemini 3 Pro (Preview) | 1x         | N             | ✅                   | ✅                         | ✅                                 | Next-gen Google model              | Preview/experimental              |
| GPT-5              | 1x             | N             | ✅                   | ✅                         | ✅                                 | Latest OpenAI flagship             | May be slower                     |
| GPT-5-Codex (Preview) | 1x          | N             | ✅✅                 | ✅                         | ✅                                 | Code-specialized GPT-5             | Preview/experimental              |
| GPT-5.1 (Preview)  | 1x             | N             | ✅                   | ✅                         | ✅                                 | Improved GPT-5                     | Preview/experimental              |
| GPT-5.1-Codex (Preview) | 1x        | N             | ✅✅                 | ✅                         | ✅                                 | Code-specialized GPT-5.1           | Preview/experimental              |
| GPT-5.1-Codex-Max (Preview) | 1x    | N             | ✅✅                 | ✅✅                       | ✅                                 | Maximum capability Codex variant   | Preview/experimental, slower      |
| GPT-5.1-Codex-Mini (Preview) | 0.33x | N            | ✅                   | ✅                         | ✅                                 | Faster Codex variant               | Preview/experimental              |
| GPT-5.2 (Preview)  | 1x             | N             | ✅                   | ✅                         | ✅                                 | Latest GPT-5 iteration             | Preview/experimental              |

## Local Models (Via Ollama or Other Extensions)

| Model Name         | Cost (Credits) | Min RAM/VRAM | Can Run on RTX 5060 Ti (16GB) | Sweet Spot for 16GB | Can Run Local | Good at Code Changes | Good at Understanding Code | Can Make Code Changes (Autopilot) | Strengths                          | Weaknesses                        |
|--------------------|:--------------:|:------------:|:-----------------------------:|:-------------------:|:-------------:|:--------------------:|:--------------------------:|:----------------------------------:|------------------------------------|------------------------------------|
| Qwen2.5-Coder (32B)| Free           | 20GB VRAM    | ❌ (needs 20GB)               | ❌                  | Y             | ✅                   | ✅                         | ❌                                 | Strong code generation, open-source | No tool calling, requires setup   |
| Qwen2.5-Coder (7B) | Free           | 6GB VRAM     | ✅                            | ⚠️ (if speed needed)| Y             | ✅                   | ✅                         | ❌                                 | Efficient, fast, open-source       | Less capable than 14B             |
| Qwen2.5-Coder (14B)| Free           | 10GB VRAM    | ✅                            | ✅ **Recommended**  | Y             | ✅                   | ✅                         | ❌                                 | Good balance of speed/capability   | Mid-tier performance              |
| Qwen2.5-Coder (1.5B-base)| Free    | 2GB VRAM     | ✅                            | ❌ (too limited)    | Y             | ⚠️                   | ⚠️                         | ❌                                 | Very fast, minimal resources       | Weak code quality                 |
| DeepSeek-Coder-V2 (1.3B) | Free     | 2GB VRAM     | ✅                            | ❌ (too limited)    | Y             | ⚠️                   | ⚠️                         | ❌                                 | Very fast, minimal resources       | Weak code quality                 |
| DeepSeek-Coder-V2 (6.7B) | Free     | 5GB VRAM     | ✅                            | ⚠️ (if speed needed)| Y             | ✅                   | ✅                         | ❌                                 | Fast, efficient                    | Less capable than 16B             |
| DeepSeek-Coder-V2 (16B) | Free      | 12GB VRAM    | ✅                            | ✅ **Recommended**  | Y             | ✅✅                 | ✅                         | ❌                                 | Strong code generation, fill-in-middle | No tool calling, requires setup   |
| DeepSeek-Coder-V2 (236B) | Free     | 150GB+ VRAM  | ❌ (needs 150GB+)             | ❌                  | Y             | ✅✅                 | ✅✅                       | ❌                                 | Very capable, near GPT-4 level     | Massive hardware requirements     |
| CodeLlama (7B)     | Free           | 5GB VRAM     | ✅                            | ⚠️ (if speed needed)| Y             | ✅                   | ✅                         | ❌                                 | Fast, efficient                    | Less capable than 13B             |
| CodeLlama (13B)    | Free           | 9GB VRAM     | ✅                            | ✅                  | Y             | ✅                   | ✅                         | ❌                                 | Good code completion, Meta-backed  | Older model                       |
| CodeLlama (34B)    | Free           | 22GB VRAM    | ❌ (needs 22GB)               | ❌                  | Y             | ✅                   | ✅                         | ❌                                 | Better capabilities than 13B       | High hardware requirements        |
| CodeLlama (70B)    | Free           | 48GB+ VRAM   | ❌ (needs 48GB+)              | ❌                  | Y             | ✅                   | ✅                         | ❌                                 | Strong capabilities, open-source   | Very high hardware requirements   |
| StarCoder2 (3B)    | Free           | 3GB VRAM     | ✅                            | ❌ (too limited)    | Y             | ⚠️                   | ✅                         | ❌                                 | Very fast, efficient               | Limited capabilities              |
| StarCoder2 (7B)    | Free           | 5GB VRAM     | ✅                            | ⚠️                  | Y             | ✅                   | ✅                         | ❌                                 | Fast, efficient, open-source       | Limited capabilities              |
| StarCoder2 (15B)   | Free           | 10GB VRAM    | ✅                            | ✅                  | Y             | ✅                   | ✅                         | ❌                                 | Better than 7B, still efficient    | Limited context window            |
| Phi-3.5 (3.8B)     | Free           | 4GB VRAM     | ✅                            | ❌ (too limited)    | Y             | ⚠️                   | ✅                         | ❌                                 | Very lightweight, runs on CPU      | Limited capabilities              |
| Llama 3.1 (8B)     | Free           | 6GB VRAM     | ✅                            | ⚠️                  | Y             | ⚠️                   | ✅                         | ❌                                 | General purpose, decent code skills | Not code-specialized              |
| Llama 3.1 (70B)    | Free           | 48GB+ VRAM   | ❌ (needs 48GB+)              | ❌                  | Y             | ⚠️                   | ✅                         | ❌                                 | General purpose, strong reasoning  | Not code-specialized              |

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
- Local models require Ollama, LM Studio, or similar tools, plus extensions like Continue or Cody.
