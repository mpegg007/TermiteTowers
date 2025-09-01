<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2025-09-01 15:47:12 %
% ccm_author: mpegg %
% ccm_author_email: mpegg@hotmail.com %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: wiki/how-to-extend-voice-assistant.md:0 %
% ccm_commit_id: unknown %
% ccm_commit_count: 0 %
% ccm_commit_message: unknown %
% ccm_commit_author: unknown %
% ccm_commit_email: unknown %
% ccm_commit_date: 1970-01-01 00:00:00 +0000 %
% ccm_file_last_modified: 2025-08-31 17:32:02 %
% ccm_file_name: how-to-extend-voice-assistant.md %
% ccm_file_type: text/plain %
% ccm_file_encoding: us-ascii %
% ccm_file_eol: CRLF %
% ccm_path: wiki/how-to-extend-voice-assistant.md %
% ccm_blob_sha: 198f4eb58f003ce8c5001679b2c2b3e9f4dd74c5 %
% ccm_exec: no %
% ccm_size: 3055 %
% ccm_tag:  %
tt-ccm.header.end
-->

# How to Extend the Voice Assistant

Goal: add new spoken capabilities end-to-end using the current LLM + HA flow.

## Current patterns

- Webhook command naming
  - LLM outputs an opaque command string (e.g., `turn_on_office_light`)
  - HA automation triggers on `api/webhook/<command>`

- FastAPI server (llm-server)
  - Endpoint `/parse` dispatches `domain` to handlers
  - Handlers return structured JSON (action/target/etc.) for potential direct HA service calls

## Option A: extend Flask HAL bridge (quickest)

1) Improve prompting in `llm_server/handlers/home_assistant.py` to cover new intents.
2) Define new HA webhooks and automations matching the new outputs.
3) Add tests in `llm-server/tests/test_home_assistant.py` for the new phrasing.

Pros: minimal changes, leverages current startup. Cons: opaque command strings; logic split from FastAPI.

## Option B: unify under FastAPI (recommended)

1) Add an endpoint `/hal` to `llm_server/main.py` mirroring the Flask behavior.
2) Move the LM Studio call into a shared util and return structured JSON (action/entity/params).
3) Create an HA automation to call a generic webhook that reads JSON and calls appropriate services.
4) Update `scripts/system/startup.sh` to start the FastAPI app instead of Flask.

Pros: single server, typed models, unit-testable. Cons: one-time migration.

## HA integration tips

- Map actions to services (light.turn_on, climate.set_temperature, media.*)
- Prefer device_class/entity_id naming in the LLM output to reduce ambiguity
- Consider a middleware in HA that converts simple JSON instructions to service calls

## Dev checklist

- Start stack: `TermiteTowers/startup.sh` (STT/TTS + Flask)
- Verify LM Studio on :1234
- Run unit tests in llm-server
- Add tests for new intents
- Wire HA webhooks and automations

## Example HA automation (webhook)

Trigger: Webhook `turn_on_office_light`
Action:
```
service: light.turn_on
target:
  entity_id: light.office
```

## Next steps (proposal)

- Implement Option B migration plan with a feature flag to switch endpoints
- Add a small HA custom component or blueprint to call the FastAPI `/parse` and execute services
- Monitor: add health endpoints and logs aggregation for `/parse` and `/hal`
