<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: wiki/README.md % -->
<!-- %ccm_git_object_id: wiki/README.md@194 % -->
<!-- %ccm_git_commit_date: 2026-10-28 20:22:38 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: misc updates % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!-- %git_commit_history: 2025-10-10 mpegg big update -->
<!--
-->

# TermiteTowers Ops Docs

These Markdown pages are ready to import into Wiki.js. They capture the storage/permissions model and Docker Compose conventions we implemented.

## Infrastructure Docs

- **Domain strategy**: `domains.md` - termitetowers.ca vs analacres.ca domain architecture
- **Storage model**: `storage-model.md`
- **Compose conventions**: `compose-conventions.md`
- **Quick refs**: `env-variables.md`, `paths-and-symlinks.md`, `ports.md`, `how-to-add-docker-app.md`, `how-to-add-mcp-server.md`

## Service Runbooks

- `runbook-openwebui.md`, `runbook-lobechat.md`, `runbook-tortoise.md`, `runbook-whisper.md`, `runbook-wikijs.md`, `runbook-kitchenowl.md`, `runbook-uptime-kuma.md`, `runbook-dozzle.md`, `runbook-homarr.md`, `runbook-ha-hal-bridge.md`, `runbook-piper.md`, `runbook-ha-mcp.md`

## Vision & Architecture

- **HAL Vision**: `vision-hal-enterprise-computer.md` - End-state HAL 9000/Enterprise Computer system goals

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
