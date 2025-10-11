<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: https://github.com/mpegg007/TermiteTowers.git %
  %ccm_git_branch: main %
  %ccm_git_object_id: wiki/domains.md:97 %
  %ccm_git_author: CCM Maintainer %
  %ccm_git_author_email: ccm@test %
  %ccm_git_blob_sha: c6e37f823b5cd0fac36e29c3b4e5002867697277 %
  %ccm_git_commit_id: f8d51ae7fe101541b1ccd2f91922878ece0bb306 %
  %ccm_git_commit_count: 97 %
  %ccm_git_commit_date: 2025-10-10 20:55:46 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: big update %
  %ccm_git_modify_date: 2025-08-29 07:37:53 %
  %ccm_git_file_last_modified: 2025-08-29 07:37:52 %
  %ccm_git_file_name: CCM_HEADER_TEMPLATE.txt %
  %ccm_git_path: CCM_HEADER_TEMPLATE.txt %
  %ccm_git_language_mode:  %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 659 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
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
- `home.termitetowers.ca` - Homarr dashboard (port 3310)
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
