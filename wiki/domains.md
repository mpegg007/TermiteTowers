<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: wiki/domains.md % -->
<!-- %ccm_git_object_id: wiki/domains.md@200 % -->
<!-- %ccm_git_commit_date: 2026-11-09 10:16:57 -0500 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: zoo.261109 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!-- %git_commit_history: 2026-10-31 mpegg feat(nginx): expose wordbank and soundbank, make analacres hosts gate-ready -->
<!-- %git_commit_history: 2026-09-25 mpegg chore(homarr): retire Homarr - configured but never used day to day -->
 <!-- %git_commit_history: 2025-10-10 mpegg  big update  -->
<!--
-->

# Domain Strategy

TermiteTowers infrastructure spans multiple domains with distinct purposes and architectural philosophies.

## Primary Domain: termitetowers.ca

**Purpose:** General infrastructure, web services, home automation, media, productivity tools

**Naming Pattern:** `<service>.termitetowers.ca`

**Philosophy:** 
- User-facing services
- Home automation and daily-use tools
- Content management and collaboration
- Media and entertainment
- General-purpose infrastructure

**Current Services:**
- `webai.termitetowers.ca` - Open WebUI (port 3000)
- `lobe.termitetowers.ca` - LobeChat (port 3100)
- `search.termitetowers.ca` - SearXNG metasearch (port 3130)
- `wiki.termitetowers.ca` - Wiki.js documentation (port 3200)
- ~~`home.termitetowers.ca`~~ - Homarr dashboard — RETIRED 2026-09-26 (port 3310 freed)
- `kitchenowl.termitetowers.ca` - Kitchen/grocery management (port 3300)
- `llmapi.termitetowers.ca` - LLM server API (port 3350)
- `kuma.termitetowers.ca` - Uptime monitoring (port 3700)
- `asset.termitetowers.ca` - Snipe-IT asset tracking (port 3900)
- Many others... (see `ports.md`)

## Secondary Domain: analacres.ca

**Full Name:** Analytical Acres

**Purpose:** High-compute analytical processing, AI/ML workloads, data-intensive operations

**Naming Pattern:** `<workload>.analacres.ca`

**Philosophy:**
- **Analytical processing** - Not "anal" as in pervert, as in **analytical**
- **Acres** - Represents massive datacenter-scale compute power
- Dedicated to compute-intensive tasks
- AI/ML model training and inference
- Large-scale data processing
- LLM fine-tuning and experimentation
- GPU-accelerated workloads
- Research and development environments

**Rationale:**
- This massive PC was built for **analytical processing**
- LLMs, model training, data science require "acres" of compute
- Separates heavy compute workloads from daily-use services
- Clear mental model: termitetowers.ca = services, analacres.ca = processing power

## Current Services for analacres.ca

Unlike the planned list below, these four exist or are being built now. All are
proxied by nginx on monolith over **one shared TLS listener, port 3261**
(selected by SNI), each with its own per-host certificate issued through the
GoDaddy DNS-01 hooks:

- `memorylab.analacres.ca` - Immich photo library
- `wordbank.analacres.ca` - AudioBookshelf audiobook library
- `soundbank.analacres.ca` - Navidrome music library
- `filebank.analacres.ca` - Nextcloud file sync and sharing. Named for the
  family grammar (`-bank` = a store of things), not after the software, so the
  public URL does not advertise what to probe. Internally still "nextcloud":
  container, ZFS dataset and database keep that name.
- `auth.analacres.ca` - Authelia SSO portal (planned, Phase 2)

All three service hostnames are **ungated** today, but their vhosts are already
wired for an Authelia forward-auth gate that can be switched on without editing
any vhost: the gate lives in one included snippet. See `runbook-authelia.md`.

Note the listener choice: the analacres.ca family does not arrive on 443. Ports
on the reverse proxy are therefore not a per-service allocation here — one
forward, many hostnames.

## Planned Services for analacres.ca

**AI/ML Workloads:**
- `train.analacres.ca` - Model training interfaces
- `notebook.analacres.ca` - Jupyter notebooks for data science
- `tensorboard.analacres.ca` - Training visualization
- `mlflow.analacres.ca` - ML experiment tracking
- `comfy.analacres.ca` - ComfyUI (Stable Diffusion)

**Data Processing:**
- `spark.analacres.ca` - Apache Spark cluster
- `dask.analacres.ca` - Distributed computing
- `airflow.analacres.ca` - Workflow orchestration

**Research & Development:**
- `lab.analacres.ca` - Experimental deployments
- `sandbox.analacres.ca` - Testing environments
- `bench.analacres.ca` - Performance benchmarking

**LLM Infrastructure:**
- `ollama.analacres.ca` - Primary LLM inference (move from termitetowers.ca)
- `vllm.analacres.ca` - vLLM high-throughput inference
- `textgen.analacres.ca` - Text generation web UI
- `embedding.analacres.ca` - Embedding model services

## Domain Separation Benefits

**Clear Purpose Separation:**
- termitetowers.ca = "What I use daily"
- analacres.ca = "What I compute with"

**Resource Management:**
- Heavy workloads on analacres.ca clearly identified
- Easy to monitor/prioritize compute-intensive services
- Can apply different resource limits/quotas per domain

**Mental Model:**
- TermiteTowers = Home infrastructure (small, manageable)
- Analytical Acres = Data center power (massive, scalable)

**DNS Organization:**
- Separate CNAME records per domain
- Different SSL cert management if needed
- Flexibility for future infrastructure splits

## Implementation Notes

**Current State (2025-10-09):**
- termitetowers.ca fully operational with 15+ services
- analacres.ca domain registered but not yet configured
- nginx configs follow termitetowers.ca pattern
- All services currently on termitetowers.ca

**Migration Strategy:**
1. Add analacres.ca DNS zone
2. Create nginx configs for analacres.ca services
3. Migrate compute-heavy services (Ollama, etc.)
4. Keep user-facing interfaces on termitetowers.ca
5. Add new AI/ML workloads to analacres.ca

**DNS Setup:**
- Both domains point to same host IP (for now)
- nginx server_name distinguishes routing
- Future: Could split to different physical hosts

## Nginx Configuration Pattern

Both domains follow same nginx structure:

```nginx
# termitetowers.ca example
server {
    listen 443 ssl http2;
    server_name service.termitetowers.ca;
    proxy_pass http://localhost:XXXX/;
}

# analacres.ca example  
server {
    listen 443 ssl http2;
    server_name workload.analacres.ca;
    proxy_pass http://localhost:YYYY/;
}
```

## Port Allocation

**termitetowers.ca services:** 3000-3999 range (current allocation)
**analacres.ca services:** 4000-4999 range (future allocation)

This provides clear separation at infrastructure level.

---

**Remember:** It's **Analytical Acres** - the massive compute power (acres) for analytical processing. Not perverted, just powerful. 💪🔬

Updated: 2025-10-09
