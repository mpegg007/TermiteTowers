<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: infra/docker/PROMETHEUS-TENSORFLOW-SETUP.md:111 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 808742b47eeb834e5b8139c4feb08fabc269a3f5 %
  %ccm_git_commit_id: c95decaaa02c45bee627cd315be8d2b7aefd7fc5 %
  %ccm_git_commit_count: 111 %
  %ccm_git_commit_date: 2025-10-29 19:12:44 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: docker updates %
  %ccm_git_modify_date: 2025-10-29 19:12:44 %
  %ccm_git_file_last_modified: 2025-10-13 10:32:32 %
  %ccm_git_file_name: PROMETHEUS-TENSORFLOW-SETUP.md %
  %ccm_git_path: infra/docker/PROMETHEUS-TENSORFLOW-SETUP.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 4715 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# Prometheus & TensorFlow Setup Summary

## Overview
Created Docker Compose configurations for Prometheus and TensorFlow following the TermiteTowers port allocation strategy from `wiki/ports.md`.

## Services Created

### 1. Prometheus (Monitoring & Alerting)
- **Category**: Monitoring & Ops (3700-3799)
- **Port**: 3720 (host) → 9090 (container)
- **Subdomain**: prometheus.termitetowers.ca
- **Image**: prom/prometheus:latest
- **Purpose**: Time-series database and monitoring solution

**Files Created:**
- `/home/mpegg-adm/source/TermiteTowers/infra/docker/prometheus-dev1.yml`
- `/home/mpegg-adm/source/TermiteTowers/infra/nginx/sites-available/prometheus.conf`

**Data Directories:**
- `/mnt/ai_storage/prometheus/data` - Time-series data
- `/mnt/ai_storage/prometheus/config` - Configuration files

**Features:**
- 30-day data retention
- Web console enabled
- Lifecycle API enabled
- Custom scrape targets support

### 2. TensorFlow Jupyter (ML Development)
- **Category**: AI & Machine Learning (3800-3899)
- **Port**: 3810 (host) → 8888 (container)
- **Subdomain**: tensorflow.termitetowers.ca
- **Image**: tensorflow/tensorflow:latest-gpu-jupyter
- **Purpose**: Machine learning development with Jupyter notebooks

**Files Created:**
- `/home/mpegg-adm/source/TermiteTowers/infra/docker/tensorflow-dev1.yml`
- `/home/mpegg-adm/source/TermiteTowers/infra/docker/env/tensorflow.env.example`
- `/home/mpegg-adm/source/TermiteTowers/infra/nginx/sites-available/tensorflow.conf`

**Data Directories:**
- `/mnt/ai_storage/tensorflow/notebooks` - Jupyter notebooks
- `/mnt/ai_storage/tensorflow/data` - Training data
- `/mnt/ai_storage/tensorflow/models` - ML models

**Features:**
- GPU support (NVIDIA Docker required)
- JupyterLab interface
- WebSocket support for interactive notebooks
- Token-based authentication

## Port Allocation Strategy

Ports are now allocated according to `wiki/ports.md`:

| Range | Category | Services |
|-------|----------|----------|
| 3700-3799 | Monitoring & Ops | Uptime Kuma (3700), Dozzle (3710), **Prometheus (3720)** |
| 3800-3899 | AI & ML | Ollama (3800), **TensorFlow (3810)** |

## Deployment Script

Created: `/home/mpegg-adm/source/TermiteTowers/scripts/deploy-prometheus-tensorflow.sh`

This script automates:
1. Creating data directories with correct permissions (2001:1006)
2. Generating configuration files
3. Creating /srv/dev1 convenience symlinks
4. Starting Docker containers
5. Enabling Nginx sites
6. Verification checks

**Usage:**
```bash
bash /home/mpegg-adm/source/TermiteTowers/scripts/deploy-prometheus-tensorflow.sh
```

## Documentation Updates

### wiki/how-to-add-docker-app.md
Added comprehensive port selection guidance:
- Port range reference table
- Step-by-step port selection process
- Conflict checking commands
- Real example (Prometheus port selection)

**Key addition:** "Always consult wiki/ports.md for the port allocation strategy before choosing a port."

### wiki/ports.md
Updated service allocation table with:
- Prometheus: 3720 (Monitor category)
- TensorFlow: 3810 (AI category)

## Next Steps (Manual)

1. **DNS Configuration:**
   ```bash
   # Add CNAME records:
   prometheus.termitetowers.ca -> imono.termitetowers.ca
   tensorflow.termitetowers.ca -> imono.termitetowers.ca
   ```

2. **Deploy Services:**
   ```bash
   bash /home/mpegg-adm/source/TermiteTowers/scripts/deploy-prometheus-tensorflow.sh
   ```

3. **SSL Certificates:**
   ```bash
   sudo certbot --nginx -d prometheus.termitetowers.ca
   sudo certbot --nginx -d tensorflow.termitetowers.ca
   ```

4. **Add Dashboard Tiles:**
   - Edit: `infra/nginx/www/chat/index.html`
   - Deploy: `bash scripts/deploy-www.sh`

5. **Create Runbooks (Optional):**
   - `wiki/runbook-prometheus.md`
   - `wiki/runbook-tensorflow.md`

## Quick Start Commands

### Prometheus
```bash
# View logs
docker logs -f prometheus-dev1

# Check health
curl http://localhost:3720/-/healthy

# Restart
docker compose -f /srv/dev1/prometheus/docker/prometheus-dev1.yml restart
```

### TensorFlow
```bash
# View logs (includes Jupyter token)
docker logs -f tensorflow-dev1

# Get token
grep JUPYTER_TOKEN /home/mpegg-adm/source/TermiteTowers/infra/docker/env/tensorflow.env

# Restart
docker compose -f /srv/dev1/tensorflow/docker/tensorflow-dev1.yml restart
```

## Benefits of This Approach

✅ **Organized**: Ports grouped by service category  
✅ **Scalable**: Room for growth in each range  
✅ **Discoverable**: Port number indicates service type  
✅ **Conflict-Free**: Clear allocation prevents collisions  
✅ **Documented**: All changes tracked in wiki/ports.md  

---

**Created**: October 13, 2025  
**Author**: GitHub Copilot  
**Status**: Ready for deployment
