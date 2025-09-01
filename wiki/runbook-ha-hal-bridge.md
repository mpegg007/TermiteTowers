<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2025-09-01 15:47:12 %
% ccm_author: mpegg %
% ccm_author_email: mpegg@hotmail.com %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: wiki/runbook-ha-hal-bridge.md:0 %
% ccm_commit_id: unknown %
% ccm_commit_count: 0 %
% ccm_commit_message: unknown %
% ccm_commit_author: unknown %
% ccm_commit_email: unknown %
% ccm_commit_date: 1970-01-01 00:00:00 +0000 %
% ccm_file_last_modified: 2025-08-31 17:32:02 %
% ccm_file_name: runbook-ha-hal-bridge.md %
% ccm_file_type: text/plain %
% ccm_file_encoding: us-ascii %
% ccm_file_eol: CRLF %
% ccm_path: wiki/runbook-ha-hal-bridge.md %
% ccm_blob_sha: 3203ff349afb032be37d7bfd9874a6311e0ecf0a %
% ccm_exec: no %
% ccm_size: 2464 %
% ccm_tag:  %
tt-ccm.header.end
-->

# Runbook: HAL Flask Home Assistant Bridge

Service that parses natural language into a compact command and triggers Home Assistant webhooks.

## Source
- `llm-server/llm_server/handlers/home_assistant.py` (Flask app)
- Startup controlled by `TermiteTowers/scripts/system/startup.sh`

## Endpoint
- POST `http://<host>:5000/hal`
  - Body: `{ "prompt": "turn on the office light" }`
  - Response: `{ "command": "turn_on_office_light", "success": true }`

## Dependencies
- LM Studio running the OpenAI-compatible API at `http://localhost:1234/v1/chat/completions`
- Home Assistant accessible at `http://homeassistant.local:8123`
- HA automations mapping webhooks to services

## Start / Stop
- Start: via global startup
  - `bash /home/mpegg-adm/source/TermiteTowers/startup.sh`
- Manual start (dev):
  - `python3 /home/mpegg-adm/source/llm-server/llm_server/handlers/home_assistant.py`
- Stop:
  - `pkill -f llm_server/handlers/home_assistant.py`

## Logs
- `$HOME/startup.log` (startup script appends output)

## Health
- Port 5000 should be open
- Sample test:
```bash
curl -sS -X POST http://localhost:5000/hal \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"turn on the office light"}' | jq
```

## Common issues
- 5000 closed: process not started; rerun startup or manual start
- LM Studio not running: Flask returns errors calling LLM; start LM Studio and verify :1234
- Webhook 404: HA webhook not defined; add automation for `api/webhook/<command>`

## Hardening ideas
- Add API key / IP allowlist to `/hal`
- Emit JSON instruction (action/entity/params) instead of opaque command names
- Migrate to the FastAPI server and deprecate standalone Flask
