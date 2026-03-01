<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: scripts/system/SERVICE_STARTUP_FIX.md:111 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 50adf5c5d97ecbea2b0870f6df7972db77a70c2e %
  %ccm_git_commit_id: c95decaaa02c45bee627cd315be8d2b7aefd7fc5 %
  %ccm_git_commit_count: 111 %
  %ccm_git_commit_date: 2025-10-29 19:12:44 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: docker updates %
  %ccm_git_modify_date: 2025-10-29 19:12:45 %
  %ccm_git_file_last_modified: 2025-10-11 10:54:22 %
  %ccm_git_file_name: SERVICE_STARTUP_FIX.md %
  %ccm_git_path: scripts/system/SERVICE_STARTUP_FIX.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 3257 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# Whisper & Piper Auto-Startup Fix

## Date: October 11, 2025

## Problem
After reboot, Whisper and Piper services were failing to start automatically even though systemd services existed and were enabled.

## Root Causes Identified

### 1. Whisper Service (wyoming-faster-whisper-dev1.service)
- **Issue**: Missing required `--data-dir` argument in ExecStart command
- **Error**: `__main__.py: error: the following arguments are required: --data-dir`
- **Fix**: Added `--data-dir /srv/dev1/whisper/data` to the ExecStart command

### 2. Piper Service (wyoming-piper-dev1.service)
- **Issue 1**: Attempting to execute bash script `/srv/dev1/piper/script/run` directly (it's a bash script, not Python)
- **Issue 2**: Missing piper binary at `/srv/dev1/piper/piper`
- **Error**: `FileNotFoundError: [Errno 2] No such file or directory: '/srv/dev1/piper/piper'`
- **Fix**: 
  - Service file now correctly uses bash script (not python interpreter)
  - Created symlink: `/srv/dev1/piper/piper` → `/home/mpegg-adm/piper/piper`

## Changes Made

### Updated Service Files (saved to `/etc/systemd/system/`)
1. `/home/mpegg-adm/source/TermiteTowers/scripts/system/wyoming-faster-whisper-dev1.service`
2. `/home/mpegg-adm/source/TermiteTowers/scripts/system/wyoming-piper-dev1.service`

### Created Symlink
```bash
ln -s /home/mpegg-adm/piper/piper /srv/dev1/piper/piper
```

### Commands Executed
```bash
sudo cp /home/mpegg-adm/source/TermiteTowers/scripts/system/wyoming-faster-whisper-dev1.service /etc/systemd/system/
sudo cp /home/mpegg-adm/source/TermiteTowers/scripts/system/wyoming-piper-dev1.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart wyoming-faster-whisper-dev1.service
sudo systemctl restart wyoming-piper-dev1.service
```

## Verification

### Service Status
```bash
✅ wyoming-faster-whisper-dev1.service - Active (running)
✅ wyoming-piper-dev1.service - Active (running)
```

### Port Listening
```bash
✅ Port 10300 - Whisper STT (listening)
✅ Port 10200 - Piper TTS (listening)
```

### Boot Startup
```bash
✅ wyoming-faster-whisper-dev1.service - enabled
✅ wyoming-piper-dev1.service - enabled
```

## Result
Both services now start automatically on boot and are functioning correctly. No need to manually run `startup.sh` anymore.

## Updated startup.sh Script

The `startup.sh` script has been converted from a service launcher to a **health check utility**:
- All manual service startup code has been commented out
- Health checks remain active to verify services are running
- Script now serves as a diagnostic tool rather than a startup script

Run it anytime to check service health:
```bash
bash ~/source/TermiteTowers/scripts/system/startup.sh
# Output will show:
# ✅ Port 10300 is open  (Whisper)
# ✅ Port 10200 is open  (Piper)
# ✅ Port 5000 is open   (Havoc/HAL Bridge)
```

## Complete Service Inventory

After reboot, these services auto-start via systemd:
1. **Whisper STT** - Port 10300 - `wyoming-faster-whisper-dev1.service`
2. **Piper TTS** - Port 10200 - `wyoming-piper-dev1.service`
3. **Havoc (HAL Bridge)** - Port 5000 - Auto-starts via systemd
4. **llm-server** - Port 8000 - Auto-starts via systemd/Docker
5. **Open WebUI** - Port 8080 - Auto-starts via systemd/Docker
