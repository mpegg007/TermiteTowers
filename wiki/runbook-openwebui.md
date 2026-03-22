<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/runbook-openwebui.md:139 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: a15c6cfc647b1beb0edd022356bfd35e2ab28162 %
  %ccm_git_commit_id: 4b7c4d5292241b4ba1eb82f1b2ec0509b8fd544f %
  %ccm_git_commit_count: 139 %
  %ccm_git_commit_date: 2026-03-22 09:03:20 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: march updates %
  %ccm_git_modify_date: 2026-03-22 09:03:23 %
  %ccm_git_file_last_modified: 2026-02-15 16:28:27 %
  %ccm_git_file_name: runbook-openwebui.md %
  %ccm_git_path: wiki/runbook-openwebui.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 1899 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# Runbook: Open WebUI (dev1)

## Start/Stop
- Start: `docker compose -f /home/mpegg-adm/source/TermiteTowers/docker/openweb-dev1.yml up -d`
- Logs: `docker compose -f /home/mpegg-adm/source/TermiteTowers/docker/openweb-dev1.yml logs -f`
- Stop: `docker compose -f /home/mpegg-adm/source/TermiteTowers/docker/openweb-dev1.yml down`

## Mounts
- `/mnt/ai_storage/openwebui/data:/app/backend/data`
- `/mnt/ai_storage/models/*` to `/cache/*`

## Env
- OLLAMA_BASE_URL, MODEL_PROVIDER, DEFAULT_MODEL, HF_HOME
- Image Generation: ENABLE_IMAGE_GENERATION, IMAGE_GENERATION_ENGINE, COMFYUI_BASE_URL

## Integrations
### Web Search (SearxNG)
- Configured via ENABLE_RAG_WEB_SEARCH, RAG_WEB_SEARCH_ENGINE environment variables
- SearxNG URL: http://searxng-dev1:8080

### Image Generation (ComfyUI)
- Integrated with ComfyUI running on host at port 3830
- Access via host.docker.internal:3830
- ComfyUI service: `sudo systemctl status comfyui-dev1`
- To generate images in chat: Use image generation prompt or /imagine command
- ComfyUI Web UI: https://comfyui.termitetowers.ca

## Health
- URL: http://<host>:3101 or https://webai.termitetowers.ca
- Check can reach Ollama: `curl http://host.docker.internal:11434/api/tags`
- Check can reach ComfyUI: `curl -I http://host.docker.internal:3830`

## Troubleshooting
- Permission errors: verify file owner/group and 664/775 modes
- If Linux host-gateway fails, consider `network_mode: host` (remove ports/extra_hosts)

### Web Search & Tool Calling with Hermes Models
Hermes-class models (Hermes 2, Hermes 3, Nous Hermes, etc.) do not natively support tool calling unless specific configurations are met. If these are missing, the model will hallucinate answers instead of calling SearxNG.

Requirements:
1. Enable **Tools** in OpenWebUI.
2. Enable **Web Search** for that specific model configuration.
3. Use a prompt template that actually triggers the tool.
