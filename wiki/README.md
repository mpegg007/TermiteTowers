<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: https://github.com/mpegg007/TermiteTowers.git %
  %ccm_git_branch: main %
  %ccm_git_object_id: wiki/README.md:97 %
  %ccm_git_author: CCM Maintainer %
  %ccm_git_author_email: ccm@test %
  %ccm_git_blob_sha: c6e37f823b5cd0fac36e29c3b4e5002867697277 %
  %ccm_git_commit_id: f8d51ae7fe101541b1ccd2f91922878ece0bb306 %
  %ccm_git_commit_count: 97 %
  %ccm_git_commit_date: 2025-10-10 20:55:46 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: big update %
  %ccm_git_modify_date: 2025-08-29 07:37:53 %
  %ccm_git_file_last_modified: 2025-08-29 07:37:52 %
  %ccm_git_file_name: CCM_HEADER_TEMPLATE.txt %
  %ccm_git_path: CCM_HEADER_TEMPLATE.txt %
  %ccm_git_language_mode:  %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 659 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
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

- `runbook-openwebui.md`, `runbook-lobechat.md`, `runbook-tortoise.md`, `runbook-whisper.md`, `runbook-wikijs.md`, `runbook-kitchenowl.md`, `runbook-uptime-kuma.md`, `runbook-dozzle.md`, `runbook-homarr.md`, `runbook-ha-hal-bridge.md`, `runbook-piper.md`

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
