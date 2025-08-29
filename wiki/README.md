# TermiteTowers Ops Docs

These Markdown pages are ready to import into Wiki.js. They capture the storage/permissions model and Docker Compose conventions we implemented.

- Storage model: `storage-model.md`
- Compose conventions: `compose-conventions.md`
- Service runbooks: `runbook-openwebui.md`, `runbook-lobechat.md`, `runbook-tortoise.md`, `runbook-whisper.md`, `runbook-wikijs.md`
- Troubleshooting: `troubleshooting.md`
- Quick refs: `env-variables.md`, `paths-and-symlinks.md`

## System architecture (Mermaid)

```mermaid
flowchart LR
	subgraph Users
		Browser
	end

	subgraph Host
		OpenWebUI[Open WebUI:3000]
		LobeChat[Lobe Chat:3100]
		WikiJS[Wiki.js:3200]
		Ollama[(Ollama :11434)]
	end

	subgraph Storage[/mnt/ai_storage/]
		HF[huggingface]
		PIP[pip]
		TORCH[torch]
		WHISPER[models/whisper]
		T_VOICES[tortoise/voices]
		T_OUT[tortoise/outputs]
		W_DB[wiki/postgres-data]
		W_DATA[wiki/wikijs-data]
	end

	Browser --> OpenWebUI
	Browser --> LobeChat
	Browser --> WikiJS

	OpenWebUI -. host.docker.internal .-> Ollama
	LobeChat -. host.docker.internal .-> Ollama

	OpenWebUI --> HF
	OpenWebUI --> PIP
	OpenWebUI --> TORCH

	WHISPER --- HF
	WHISPER --- TORCH

	T_VOICES --- HF
	T_OUT --- TORCH

	WikiJS --> W_DATA
	WikiJS --> W_DB
```
