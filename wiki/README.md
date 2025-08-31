<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2025-08-31 12:26:15 %
% ccm_author: mpegg %
% ccm_author_email: mpegg@hotmail.com %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: wiki/README.md:0 %
% ccm_commit_id: unknown %
% ccm_commit_count: 0 %
% ccm_commit_message: unknown %
% ccm_commit_author: unknown %
% ccm_commit_email: unknown %
% ccm_commit_date: 1970-01-01 00:00:00 +0000 %
% ccm_file_last_modified: 2025-08-31 12:26:15 %
% ccm_file_name: README.md %
% ccm_file_type: text/plain %
% ccm_file_encoding: us-ascii %
% ccm_file_eol: CRLF %
% ccm_path: wiki/README.md %
% ccm_blob_sha: c3908269e34275c258ef17b3a20f9b920807ceb1 %
% ccm_exec: no %
% ccm_size: 2090 %
% ccm_tag:  %
tt-ccm.header.end
-->

# TermiteTowers Ops Docs

These Markdown pages are ready to import into Wiki.js. They capture the storage/permissions model and Docker Compose conventions we implemented.

- Storage model: `storage-model.md`
- Compose conventions: `compose-conventions.md`
- Service runbooks: `runbook-openwebui.md`, `runbook-lobechat.md`, `runbook-tortoise.md`, `runbook-whisper.md`, `runbook-wikijs.md`, `runbook-kitchenowl.md`, `runbook-uptime-kuma.md`, `runbook-dozzle.md`
- Quick refs: `env-variables.md`, `paths-and-symlinks.md`, `ports.md`

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
