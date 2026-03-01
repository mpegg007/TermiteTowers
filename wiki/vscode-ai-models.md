<!-- # %git_commit_history: 2025-09-06 mpegg  hook final alpha v0.1  %  -->
<!-- %git_commit_history: 2025-12-15 mpegg  monday drop  % -->
<!-- %git_commit_history: friday checkin % -->
# AI Models Available in GitHub Copilot (VS Code)

## Models Available Through GitHub Copilot Extension

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

## Local Models (Via Ollama or Other Extensions)

| Model | DL | Released | Context | Trainer | Focus | Base | VRAM | Fits | Rec? | Speed | Code | Und. | Auto | Strengths | Weaknesses |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- | :---: | :---: | :--- | :---: | :---: | :---: | :--- | :--- |
| **DeepSeek-R1 (8B)** | ✅ | 2025 | 128K | DeepSeek-R1 | Liberal Arts | Llama 3.1 | 6GB | ✅ | ✅ | Fast | ✅ | ✅✅ | ❌ | Great reasoning + natural language | Less code-specialized than Qwen |
| **DeepSeek-R1 (7B)** | ✅ | 2025 | 128K | DeepSeek-R1 | STEM | Qwen 2.5 | 5GB | ✅ | ✅ | Fast | ✅ | ✅✅ | ❌ | Excellent logic & math reasoning | Can be terse |
| **Qwen2.5-Coder (32B)** | ❌ | 2024 | 128K | Qwen | Coding | Qwen 2.5 | 20GB | ❌ | ❌ | Slow | ✅ | ✅ | ❌ | Strong code generation | Too big for 16GB VRAM |
| **Qwen2.5-Coder (14B)** | ✅ | 2024 | 128K | Qwen | Coding | Qwen 2.5 | 10GB | ✅ | ✅ | Medium | ✅ | ✅ | ❌ | Good balance of speed/capability | Mid-tier performance |
| **Qwen2.5-Coder (7B)** | ❌ | 2024 | 128K | Qwen | Coding | Qwen 2.5 | 6GB | ✅ | ⚠️ | Fast | ✅ | ✅ | ❌ | Efficient, fast | Less capable than 14B |
| **Qwen2.5-Coder (1.5B)**| ❌ | 2024 | 128K | Qwen | Coding | Qwen 2.5 | 2GB | ✅ | ❌ | V.Fast | ⚠️ | ⚠️ | ❌ | Very fast | Weak code quality |
| **Qwen2.5 (32B)** | ✅ | 2024 | 128K | Qwen | STEM | Qwen 2.5 | 20GB | ❌ | ❌ | Slow | ✅ | ✅ | ❌ | Very smart, large knowledge base | Too big for 16GB VRAM |
| **DeepSeek-Coder-V2 (236B)**| ❌ | 2024 | 128K | DeepSeek | Coding | DeepSeek-V2 | 150GB+| ❌ | ❌ | V.Slow | ✅✅ | ✅✅ | ❌ | Near GPT-4 level | Massive hardware reqs |
| **DeepSeek-Coder-V2 (16B)** | ✅ | 2024 | 128K | DeepSeek | Coding | DeepSeek-V2 | 12GB | ✅ | ✅ | Medium | ✅✅ | ✅ | ❌ | Strong code, fill-in-middle | No tool calling |
| **DeepSeek-Coder-V2 (6.7B)**| ❌ | 2024 | 128K | DeepSeek | Coding | DeepSeek-V2 | 5GB | ✅ | ⚠️ | Fast | ✅ | ✅ | ❌ | Fast, efficient | Less capable than 16B |
| **DeepSeek-Coder-V2 (1.3B)**| ❌ | 2024 | 128K | DeepSeek | Coding | DeepSeek-V2 | 2GB | ✅ | ❌ | V.Fast | ⚠️ | ⚠️ | ❌ | Very fast | Weak code quality |
| **CodeLlama (70B)** | ❌ | 2023 | 100K | Meta | Coding | Llama 2 | 48GB+ | ❌ | ❌ | V.Slow | ✅ | ✅ | ❌ | Strong capabilities | Very high hardware reqs |
| **CodeLlama (34B)** | ❌ | 2023 | 100K | Meta | Coding | Llama 2 | 22GB | ❌ | ❌ | Slow | ✅ | ✅ | ❌ | Better than 13B | High hardware reqs |
| **CodeLlama (13B)** | ❌ | 2023 | 100K | Meta | Coding | Llama 2 | 9GB | ✅ | ✅ | Medium | ✅ | ✅ | ❌ | Good code completion | Older model |
| **CodeLlama (7B)** | ❌ | 2023 | 100K | Meta | Coding | Llama 2 | 5GB | ✅ | ⚠️ | Fast | ✅ | ✅ | ❌ | Fast, efficient | Less capable than 13B |
| **StarCoder2 (15B)** | ❌ | 2024 | 16K | BigCode | Coding | StarCoder2 | 10GB | ✅ | ✅ | Medium | ✅ | ✅ | ❌ | Better than 7B | Limited context |
| **StarCoder2 (7B)** | ❌ | 2024 | 16K | BigCode | Coding | StarCoder2 | 5GB | ✅ | ⚠️ | Fast | ✅ | ✅ | ❌ | Fast, efficient | Limited capabilities |
| **StarCoder2 (3B)** | ❌ | 2024 | 16K | BigCode | Coding | StarCoder2 | 3GB | ✅ | ❌ | V.Fast | ⚠️ | ✅ | ❌ | Very fast | Limited capabilities |
| **Phi-3.5 (3.8B)** | ❌ | 2024 | 128K | Microsoft | Math/Logic | Phi-3 | 4GB | ✅ | ❌ | V.Fast | ⚠️ | ✅ | ❌ | Lightweight, CPU friendly | Limited capabilities |
| **Llama 3.1 (70B)** | ❌ | 2024 | 128K | Meta | General | Llama 3.1 | 48GB+ | ❌ | ❌ | V.Slow | ⚠️ | ✅ | ❌ | Strong reasoning | Not code-specialized |
| **Llama 3.1 (8B)** | ✅ | 2024 | 128K | Meta | General | Llama 3.1 | 6GB | ✅ | ⚠️ | Fast | ⚠️ | ✅ | ❌ | General purpose | Not code-specialized |
| **Hermes 3 (8B)** | ✅ | 2024 | 128K | Nous Research | Creative/Roleplay | Llama 3.1 | 6GB | ✅ | ✅ | Fast | ⚠️ | ✅ | ❌ | Uncensored, creative, follows instructions | Can hallucinate on strict logic |

## Column Definitions

### Online Models
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
| **Complex Debugging / CSS** | **Gemini 3 Pro** | Strong structural reasoning, analyzes hierarchy (DOM) rather than just guessing properties. |
| **Refactoring / Cleanup** | **Claude Sonnet 4.5** | Very careful, preserves logic, excellent at "do no harm". |
| **New Feature / Boilerplate** | **GPT-4o / GPT-5** | Fast, standard patterns, good at generating large chunks of code. |
| **Large Context / Repo-wide** | **Gemini 3 Pro** | Massive 2M+ context window allows seeing the whole picture. |

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
To install the models mentioned above, run the following commands in your terminal (assuming you have Ollama installed):

*   **DeepSeek-R1-Distill-Llama-8B**: `ollama run deepseek-r1:8b`
*   **Meta Llama 3.1 8B**: `ollama run llama3.1`
*   **Hermes 3 (8B)**: `ollama run hermes3`

## The Extension vs. The Model: An Analogy

It is important to distinguish between the **Model** (the intelligence) and the **Extension** (the tool you use to access it).

### 1. The Model = The Brain 🧠

- **Examples:** Gemini 1.5 Pro, GPT-4o, Claude 3.5 Sonnet, DeepSeek R1.
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
  - **Limitation:** "Get what you pay for." The free models are smaller and less capable than GPT-4 or Claude 3.5 Sonnet. They are great for boilerplate but may struggle with complex logic or deep reasoning compared to the paid "Senior Engineers."

#### 📚 Sourcegraph Cody (The Librarian)

- **Analogy:** The **Head Librarian** with a photographic memory.
- **Capabilities:**
  - **Deep Context:** Its superpower is understanding the *entire* codebase, not just open files. It uses Sourcegraph's code graph to find definitions and references across massive repositories.
  - **Retrieval:** Excellent at answering "Where is this defined?" or "How does the auth system work?" by pulling context from everywhere.
  - **Enterprise Grade:** Often shines in very large, complex corporate environments where finding the right code is half the battle.
