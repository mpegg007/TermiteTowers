<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/webai-comfyui-integration.md:139 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: b92ecd7cbbb2a20d6c046ea10141721222f3d24b %
  %ccm_git_commit_id: 4b7c4d5292241b4ba1eb82f1b2ec0509b8fd544f %
  %ccm_git_commit_count: 139 %
  %ccm_git_commit_date: 2026-03-22 09:03:20 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: march updates %
  %ccm_git_modify_date: 2026-03-22 09:03:23 %
  %ccm_git_file_last_modified: 2026-02-15 16:28:27 %
  %ccm_git_file_name: webai-comfyui-integration.md %
  %ccm_git_path: wiki/webai-comfyui-integration.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 4662 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# WebAI (OpenWebUI) + ComfyUI Image Generation Integration

## Overview
WebAI (OpenWebUI) is now integrated with ComfyUI for AI-powered image generation using Stable Diffusion models. This allows you to generate images directly from chat conversations.

## Integration Status: ✅ ACTIVE

**Components:**
- **WebAI (OpenWebUI)**: Chat interface on port 3101
  - URL: https://webai.termitetowers.ca
  - Docker container: `openwebui-dev1`
- **ComfyUI**: Image generation backend on port 3830
  - URL: https://comfyui.termitetowers.ca
  - Systemd service: `comfyui-dev1`
  - Installation: `/srv/dev1/comfyui/ComfyUI`

## Configuration

### OpenWebUI Environment Variables
Added to [infra/docker/openwebui-dev1.yml](../infra/docker/openwebui-dev1.yml):
```yaml
- ENABLE_IMAGE_GENERATION=true
- IMAGE_GENERATION_ENGINE=comfyui
- COMFYUI_BASE_URL=http://host.docker.internal:3830
```

### Network Connectivity
- OpenWebUI container communicates with ComfyUI via `host.docker.internal:3830`
- ComfyUI runs as native systemd service on host
- Both services use shared model storage at `/mnt/ai_storage`

## How to Use

### Method 1: Image Generation in Chat
1. Open WebAI at https://webai.termitetowers.ca
2. In any chat, use an image generation prompt:
   - "Generate an image of a sunset over mountains"
   - "Create a picture of a futuristic city"
   - "/imagine a cat wearing sunglasses"
3. OpenWebUI will send the request to ComfyUI
4. Generated image will appear in the chat

### Method 2: Direct ComfyUI Access
1. Open ComfyUI directly at https://comfyui.termitetowers.ca
2. Use the node-based workflow interface
3. Load models, configure parameters, and generate images
4. More advanced control over the generation process

## Testing the Integration

### Quick Health Checks
```bash
# Check OpenWebUI is running
curl http://localhost:3101/api/version

# Check ComfyUI is responding
curl -I http://localhost:3830

# Check OpenWebUI can reach ComfyUI from inside container
docker exec openwebui-dev1 curl -I http://host.docker.internal:3830
```

### Test Image Generation
1. Navigate to https://webai.termitetowers.ca
2. Start a new chat with any LLM model
3. Type: "Generate an image of a blue robot"
4. Wait for ComfyUI to process the request
5. Image should appear in chat thread

## Troubleshooting

### Image Generation Not Working
```bash
# Check ComfyUI service status
sudo systemctl status comfyui-dev1

# Restart ComfyUI if needed
sudo systemctl restart comfyui-dev1

# Check ComfyUI logs
sudo journalctl -u comfyui-dev1 -f
```

### OpenWebUI Cannot Connect to ComfyUI
```bash
# Test connectivity from inside OpenWebUI container
docker exec openwebui-dev1 curl -v http://host.docker.internal:3830

# Verify host.docker.internal resolves correctly
docker exec openwebui-dev1 getent hosts host.docker.internal

# Restart OpenWebUI to reload config
docker compose -f infra/docker/openwebui-dev1.yml restart
```

### Models Not Loading in ComfyUI
```bash
# Check model storage
ls -la /mnt/ai_storage/comfyui/models/

# Verify permissions
sudo chown -R comfyui:comfyui /mnt/ai_storage/comfyui/

# Download Stable Diffusion models if missing
# (Follow ComfyUI documentation for model installation)
```

## Architecture

```mermaid
flowchart LR
    User[User Browser] --> WebAI[WebAI<br/>OpenWebUI:3101<br/>Docker]
    WebAI --> Ollama[Ollama:11434<br/>Host Service]
    WebAI -.image generation.-> ComfyUI[ComfyUI:3830<br/>Host Service]
    
    Ollama --> Models1[/mnt/ai_storage/<br/>models/ollama]
    ComfyUI --> Models2[/mnt/ai_storage/<br/>comfyui/models]
    
    WebAI --> Storage[/mnt/ai_storage/<br/>openwebui/data]
```

## Configuration Completed: 2026-02-15

### Changes Made:
1. ✅ Added image generation environment variables to openwebui-dev1.yml
2. ✅ Configured COMFYUI_BASE_URL to point to host service
3. ✅ Restarted OpenWebUI container with new configuration
4. ✅ Updated wiki/ports.md to mark ComfyUI as **INTEGRATED**
5. ✅ Updated wiki/runbook-openwebui.md with integration details
6. ✅ Created this integration documentation

### Next Steps (Optional Enhancements):
- Configure default Stable Diffusion models in ComfyUI
- Create custom ComfyUI workflows for better image quality
- Set up automatic model downloads
- Configure image generation parameters (resolution, steps, sampler)
- Add GPU optimization settings for faster generation

## References
- [OpenWebUI Documentation](https://github.com/open-webui/open-webui)
- [ComfyUI Documentation](https://github.com/comfyanonymous/ComfyUI)
- [TermiteTowers Setup Script](../scripts/system/setup-comfyui-dev1.sh)
- [OpenWebUI Compose File](../infra/docker/openwebui-dev1.yml)
