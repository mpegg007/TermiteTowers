<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/troubleshooting-webai-image-generation.md:139 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 6ad23bf6e5777fba7e3c0ddcb02a32a65c92a41d %
  %ccm_git_commit_id: 4b7c4d5292241b4ba1eb82f1b2ec0509b8fd544f %
  %ccm_git_commit_count: 139 %
  %ccm_git_commit_date: 2026-03-22 09:03:20 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: march updates %
  %ccm_git_modify_date: 2026-03-22 09:03:23 %
  %ccm_git_file_last_modified: 2026-02-15 16:56:00 %
  %ccm_git_file_name: troubleshooting-webai-image-generation.md %
  %ccm_git_path: wiki/troubleshooting-webai-image-generation.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 10224 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# Troubleshooting WebAI (OpenWebUI) Image Generation

## ✅ FIXED: 2026-02-15 16:47

**Root Cause**: Database had wrong model name (`llava:13b` - an LLM model) instead of the Stable Diffusion checkpoint filename.

**Solution Applied**: Updated database to use correct checkpoint: `juggernautXL_v9Rundiffusionphoto2.safetensors`

All backend configuration is now correct:
- Environment variables: ✅ Set
- ComfyUI connectivity: ✅ Working (http://host.docker.internal:3830)
- Models installed: ✅ 2 models (14GB total)
- Database settings: ✅ Fixed and working

## How to Generate Images in OpenWebUI

### Method 1: Using the Image Generation Button (Recommended)

1. **Open WebAI**: https://webai.termitetowers.ca
2. **Start a new chat**
3. **Look for the image icon** in the chat input area
   - Should be near the send button
   - May be labeled with a camera/image icon 📷 or 🖼️
4. **Click the image generation button**
5. **Enter your prompt**: "a beautiful sunset over mountains"
6. **Wait 15-30 seconds** for ComfyUI to generate the image

### Method 2: Using Chat Commands

Try these in regular chat:
```
/imagine a cat wearing sunglasses
Generate an image of a futuristic city
Create a picture of a sunset
```

### Method 3: Direct Prompt (If Enabled for Model)

Some models support inline image generation:
```
Please generate an image showing: a robot in a garden
Draw me a picture of: mountains at sunset
```

## Verifying User Permissions

### Check Your User Role:
1. Go to **Settings** (gear icon, top-right)
2. Navigate to **Admin Panel** (if you're an admin)
3. Go to **Users** section
4. Find your user account
5. Check **Permissions** → **Features** → **Image Generation** is enabled

### If You're NOT an Admin:
Ask an admin user to:
1. Log into WebAI as admin
2. Go to **Admin Panel** → **Settings** → **Features**
3. Enable **Image Generation** for all users
4. Or enable it specifically for your user in **Users** section

## Testing the Integration

### Quick Backend Test (From Terminal):
```bash
# Test ComfyUI is accessible
curl -I http://localhost:3830

# Test from inside OpenWebUI container
docker exec openwebui-dev1 curl -I http://host.docker.internal:3830

# Check OpenWebUI logs for image generation attempts
docker compose -f infra/docker/openwebui-dev1.yml logs -f
```

### Expected Behavior:
1. **Click image button** → Input field appears for prompt
2. **Enter prompt** → Submit
3. **Status indicator** → Shows "Generating..." or progress
4. **Wait 15-60 seconds** → Depends on image complexity
5. **Image appears** → Displayed in chat thread

## Common Issues & Solutions

### "HTTP Error 400: Bad Request" (FIXED)

**Error in logs**: `Error while queuing prompt: HTTP Error 400: Bad Request`

**Root Cause**: The database had `llava:13b` as the model name, but that's an LLM model name, not a Stable Diffusion checkpoint filename. ComfyUI tried to load `llava:13b` as a checkpoint and failed with HTTP 400.

**Fix Applied**:
```bash
# Updated database to correct checkpoint filename
docker exec openwebui-dev1 python3 -c "
import sqlite3, json
conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()
cursor.execute('SELECT id, data FROM config')
for config_id, data_json in cursor.fetchall():
    config = json.loads(data_json)
    if 'image_generation' in config:
        config['image_generation']['model'] = 'juggernautXL_v9Rundiffusionphoto2.safetensors'
        cursor.execute('UPDATE config SET data = ? WHERE id = ?', (json.dumps(config), config_id))
conn.commit()
conn.close()
"

# Restart to apply changes
docker compose -f infra/docker/openwebui-dev1.yml restart
```

**Verify the fix**:
```bash
# Check current model setting
docker exec openwebui-dev1 python3 -c "
import sqlite3, json
conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()
cursor.execute('SELECT data FROM config LIMIT 1')
config = json.loads(cursor.fetchone()[0])
print('Model:', config['image_generation']['model'])
conn.close()
"
# Should output: Model: juggernautXL_v9Rundiffusionphoto2.safetensors
```

### "Image generation not available"

**Cause**: User doesn't have permissions
**Solution**: 
1. Check if you're logged in (not anonymous user)
2. Verify your account has image generation permission
3. Ask admin to enable the feature

### "Error generating image"

**Cause**: ComfyUI connection or model issue
**Solution**:
```bash
# Check ComfyUI is running
sudo systemctl status comfyui-dev1

# Check ComfyUI logs
sudo journalctl -u comfyui-dev1 -f

# Restart ComfyUI if needed
sudo systemctl restart comfyui-dev1
```

### "No models available"

**Cause**: Models not loaded in ComfyUI
**Solution**:
```bash
# Check models exist
ls -lh /mnt/ai_storage/comfyui/models/checkpoints/

# Should show:
# juggernautXL_v9Rundiffusionphoto2.safetensors (6.7GB)
# sd_xl_base_1.0.safetensors (6.5GB)

# If missing, download models:
cd /mnt/ai_storage/comfyui/models/checkpoints/
# Download from Hugging Face or Civitai
```

### Image button not visible

**Cause**: Feature disabled in UI or browser cache
**Solution**:
1. Hard refresh browser: Ctrl+Shift+R (or Cmd+Shift+R on Mac)
2. Clear browser cache for webai.termitetowers.ca
3. Try incognito/private browsing mode
4. Check Admin Panel → Settings → Features → Image Generation

### Slow generation (> 2 minutes)

**Cause**: GPU not being used or high VRAM usage
**Solution**:
```bash
# Check GPU usage
nvidia-smi

# Check ComfyUI is using GPU
sudo journalctl -u comfyui-dev1 | grep -i cuda

# Restart ComfyUI to clear VRAM
sudo systemctl restart comfyui-dev1
```

### Duplicate Images Generated (FIXED: 2026-02-15 21:53)

**Symptoms**: Two identical images appear in chat for each generation request

**Root Cause**: ComfyUI workflow had two output nodes:
- Node 9: `SaveImage` 
- Node 10: `PreviewImage`

OpenWebUI was retrieving images from both nodes, causing duplicates.

**Solution Applied**:
```bash
# Remove node 10 (PreviewImage) from workflow
docker exec openwebui-dev1 python3 -c "
import sqlite3, json
conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()
cursor.execute('SELECT id, data FROM config LIMIT 1')
config_id, data_json = cursor.fetchone()
config = json.loads(data_json)
workflow = json.loads(config['image_generation']['comfyui']['workflow'])
if '10' in workflow:
    del workflow['10']
config['image_generation']['comfyui']['workflow'] = json.dumps(workflow)
cursor.execute('UPDATE config SET data = ? WHERE id = ?', (json.dumps(config), config_id))
conn.commit()
conn.close()
"

# Restart OpenWebUI
docker compose -f infra/docker/openwebui-dev1.yml restart
```

**Result**: Only node 9 (SaveImage) remains, producing a single image per request.

### LLM Responds During Image Generation

**Symptoms**: Image generates successfully, but LLM also responds with text like "I'm sorry, I cannot generate images..."

**Cause**: Typing image requests as regular chat messages sends the prompt to BOTH ComfyUI AND the LLM model.

**Solution**: Use the **dedicated image generation button** (📷 camera icon) in the chat interface:
1. Click the image/camera icon near the send button
2. Enter your prompt in the image generation field
3. This sends the request ONLY to ComfyUI, not the LLM
4. Result: Clean image generation without text responses

## Verified Configuration

### Environment Variables (Inside OpenWebUI Container):
```bash
ENABLE_IMAGE_GENERATION=true
IMAGE_GENERATION_ENGINE=comfyui
COMFYUI_BASE_URL=http://host.docker.internal:3830
```

### Database Settings:
```json
{
  "image_generation": {
    "enable": true,
    "engine": "comfyui",
    "comfyui": {
      "base_url": "http://host.docker.internal:3830"
    }
  }
}
```

### Available Models in ComfyUI:
- `juggernautXL_v9Rundiffusionphoto2.safetensors` (6.7GB) - Main model
- `sd_xl_base_1.0.safetensors` (6.5GB) - Base SDXL model

### Network Connectivity:
```bash
# OpenWebUI → ComfyUI: ✅ Working
docker exec openwebui-dev1 curl -I http://host.docker.internal:3830
# Response: HTTP/1.1 200 OK
```

## Admin Panel Configuration

If you have admin access:

1. **Log in to WebAI** as admin
2. **Click Settings** (gear icon, top-right)
3. **Go to Admin Panel**
4. **Navigate to: Admin Settings → Images → Image Generation**
5. **Verify these settings**:
   - ☑️ Enable Image Generation
   - Engine: `comfyui`
   - ComfyUI Base URL: `http://host.docker.internal:3830`
6. **Click Test Connection** (if available)
7. **Save Settings**

### User Permissions:
Go to **Admin Panel** → **Users** → Select your user → **Edit**
- Ensure **Image Generation** permission is checked under **Features**

## Still Not Working?

### Collect Debug Information:

```bash
# 1. Check all services
sudo systemctl status comfyui-dev1
docker ps | grep openwebui

# 2. Get logs
docker compose -f infra/docker/openwebui-dev1.yml logs --tail=100 > /tmp/openwebui.log
sudo journalctl -u comfyui-dev1 --since "10 minutes ago" > /tmp/comfyui.log

# 3. Test API directly
curl -v http://localhost:3830/system_stats

# 4. Check database settings
docker exec openwebui-dev1 python3 -c "
import sqlite3, json
conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()
cursor.execute('SELECT data FROM config LIMIT 1')
result = cursor.fetchone()
config = json.loads(result[0])
print('Image Gen Enabled:', config.get('image_generation', {}).get('enable'))
print('Engine:', config.get('image_generation', {}).get('engine'))
print('ComfyUI URL:', config.get('image_generation', {}).get('comfyui', {}).get('base_url'))
conn.close()
"
```

### Share These Logs:
- `/tmp/openwebui.log`
- `/tmp/comfyui.log`
- Browser console errors (F12 → Console tab)
- Screenshot of the WebAI interface

## Expected Performance

- **Simple image (512x512, 20 steps)**: 15-30 seconds
- **Complex image (1024x1024, 50 steps)**: 60-120 seconds
- **First generation after restart**: +10-20 seconds (model loading)

## References
- [OpenWebUI Documentation](https://docs.openwebui.com/)
- [ComfyUI Documentation](https://github.com/comfyanonymous/ComfyUI)
- [JuggernautXL Model Info](https://civitai.com/models/133005/juggernaut-xl)
- [Integration Guide](./webai-comfyui-integration.md)
