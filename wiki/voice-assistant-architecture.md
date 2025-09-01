<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2025-09-01 15:47:12 %
% ccm_author: mpegg %
% ccm_author_email: mpegg@hotmail.com %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: wiki/voice-assistant-architecture.md:0 %
% ccm_commit_id: unknown %
% ccm_commit_count: 0 %
% ccm_commit_message: unknown %
% ccm_commit_author: unknown %
% ccm_commit_email: unknown %
% ccm_commit_date: 1970-01-01 00:00:00 +0000 %
% ccm_file_last_modified: 2025-08-31 17:32:02 %
% ccm_file_name: voice-assistant-architecture.md %
% ccm_file_type: text/plain %
% ccm_file_encoding: utf-8 %
% ccm_file_eol: CRLF %
% ccm_path: wiki/voice-assistant-architecture.md %
% ccm_blob_sha: 919119b085f6e3711cb9a325a9f5976de3fae6a5 %
% ccm_exec: no %
% ccm_size: 3621 %
% ccm_tag:  %
tt-ccm.header.end
-->

# Voice Assistant Architecture (dev1)

This documents the current voice stack across TermiteTowers and llm-server.

## Components

- STT: Wyoming Faster-Whisper server
  - Port 10300 (TCP)
  - Started by `scripts/system/startup.sh`
- TTS: Wyoming Piper server
  - Port 10200 (TCP)
  - Started by `scripts/system/startup.sh`
- LLM parse/skills: Flask “HAL” Home Assistant bridge
  - File: `llm-server/llm_server/handlers/home_assistant.py`
  - Port 5000 (HTTP, /hal)
- LLM backend: LM Studio (OpenAI-compatible API)
  - Port 1234 (HTTP)
  - URL used: `http://localhost:1234/v1/chat/completions`
- Home Assistant
  - Receives actions via webhook: `http://homeassistant.local:8123/api/webhook/<command>`
  - Note: `home-assistant-config/custom_components/llm_server/` is currently empty (no HA custom component); integration is via webhooks.

## Data flows

1) Voice command via HA (Assist)
- HA captures audio and can use Wyoming services:
  - STT -> tcp://<host>:10300 (Whisper)
  - TTS -> tcp://<host>:10200 (Piper)
- Today’s LLM “skills” bridge is separate (Flask on :5000). To use it from HA, send the transcript to `/hal` and trigger webhooks in HA.

2) LLM-to-HA webhook bridge (current)
- Client submits `{prompt: "turn on the office light"}` to `POST /hal` (Flask)
- Flask calls LM Studio to get a compact command string (e.g., `turn_on_office_light`)
- Flask posts to `http://homeassistant.local:8123/api/webhook/turn_on_office_light`
- HA automations map that webhook to services (e.g., `light.turn_on` on `light.office`)

## Ports and health

- 10300 Whisper STT (Wyoming)
- 10200 Piper TTS (Wyoming)
- 5000 Flask HAL bridge (/hal)
- 1234 LM Studio (OpenAI-compatible)
- `scripts/system/startup.sh` checks 10300, 10200, and 5000

## Startup

- Entry: `TermiteTowers/startup.sh` forwards to `scripts/system/startup.sh`
- That script:
  - Starts Whisper STT and Piper TTS (prefers $HOME installs, falls back to `/srv/dev1/...`)
  - Starts the Flask HA integration (`/home/mpegg-adm/source/llm-server/llm_server/handlers/home_assistant.py`)
  - Performs simple port checks; logs to `$HOME/startup.log`

## Notes and constraints

- The Flask bridge and FastAPI app (`llm_server/main.py`) are separate. The FastAPI app routes `domain` to handlers (home_assistant/media) but is not started by `startup.sh`.
- HA custom component directory exists but is empty; behavior relies on HA webhooks, not a component.
- LM Studio model name and prompt engineering live inside the Flask handler file.

## Opportunities

- Unify Flask into FastAPI (single service) and expose `/parse` + `/hal` in one process.
- Add a minimal HA custom component to emit transcripts to `/hal` and map responses to HA services.
- Replace webhook naming scheme with a small JSON instruction schema (action/entity/params).
