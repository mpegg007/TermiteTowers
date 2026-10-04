<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_object_id: infra/mcp/home-assistant/EVALUATION-2026-08-29.md:160 % -->
<!-- %ccm_git_author: mpegg % -->
<!-- %ccm_git_author_email: mpegg@hotmail.com % -->
<!-- %ccm_git_blob_sha: ca400c6ccac75ffb138b8410648a9c7e9eb9a9fb % -->
<!-- %ccm_git_commit_id: 3a0dc6d000abbf72c8996a230bc72454f05c9f1b % -->
<!-- %ccm_git_commit_count: 160 % -->
<!-- %ccm_git_commit_date: 2026-09-25 21:30:36 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_email: mpegg@hotmail.com % -->
<!-- %ccm_git_commit_message: cleanup % -->
<!-- %ccm_git_modify_date: 2026-09-25 21:30:37 % -->
<!-- %ccm_git_file_last_modified: 2026-08-29 15:03:15 % -->
<!-- %ccm_git_file_name: EVALUATION-2026-08-29.md % -->
<!-- %ccm_git_path: infra/mcp/home-assistant/EVALUATION-2026-08-29.md % -->
<!-- %ccm_git_language_mode: markdown % -->
<!-- %ccm_git_file_type: text/plain % -->
<!-- %ccm_git_file_encoding: us-ascii % -->
<!-- %ccm_git_file_eol: CRLF % -->
<!-- %ccm_git_exec: no % -->
<!-- %ccm_git_size: 13520 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
 <!-- %git_commit_history: 1970-01-01 unknown  unknown  --> 
# Home Assistant MCP Evaluation - 2026-08-29

## Scope

This records an initial read-only evaluation plus a later external Docker
deployment and controlled write test of `homeassistant-ai/ha-mcp`. It is an
operational record, not a credential store. Do not add access tokens, private
MCP URLs, webhook paths, or cloud-model API keys to this document.

## Custom server status

The custom server is implemented in `ha_client.py` and `server.py`. It provides
a deliberately small tool surface and a proposal/apply workflow for authoring
scene, script, and automation YAML.

- Unit tests passed: 14 tests in `test_server.py`.
- A read-only live probe reached Home Assistant 2026.8.3 and initially reported
  1,449 entities, 27 automations, and 3 scenes.
- Later live checks returned 3 scene entities: `scene.mpegg_bedtime_tv`,
  `scene.daytime`, and `scene.good_morning`.
- The custom `list_routines("scene")` returned no definitions because it reads
  configured YAML files, not Home Assistant UI/storage scenes.
- The custom server had writes disabled throughout the evaluation. Its HTTP
  reads cannot restart Home Assistant, reload configuration, or detach VM USB
  devices.

### Confirmed limitation

Home Assistant scenes can originate outside YAML. The custom server only sees
YAML definitions when `HA_CONFIG_DIR` is available and scenes are YAML-managed.
It therefore cannot inspect or edit UI/storage scenes with its present write
path. This is expected from the implementation described in `README.md`.

## HA-MCP evaluation

The evaluated upstream project is [homeassistant-ai/ha-mcp](https://github.com/homeassistant-ai/ha-mcp).
It is an active, MIT-licensed community project, not an official Home Assistant
project. It supports a Home Assistant custom component, add-on, Docker/PyPI,
and local stdio deployments. Its documentation recommends the custom component
or HTTP transport over stdio for durable use.

### Connection and instance facts

- HA-MCP was exposed on a LAN-reachable Home Assistant address. Do not use
  `0.0.0.0` in a client configuration; it is a bind address, not a destination.
- The endpoint accepted MCP protocol version `2025-11-25` over streamable HTTP
  (`application/json` / `text/event-stream`).
- The endpoint intermittently became unavailable or returned a transient
  redirect during evaluation. Treat this as an HA, add-on, or network/proxy
  availability issue; no client action made a mutation.
- A successful `ha_get_overview` reported Home Assistant 2026.8.3, 1,454
  entities, 34 domains, 343 services, and 18 areas.
- The server exposed 39 tools at the time of inspection, with 32 read-oriented
  tools and 7 write/system-management tools.

### Scene inspection results

Only `ha_config_get_scene` was called. It is read-only.

| Scene | Result |
| --- | --- |
| `mpegg_bedtime_tv` | UI/storage scene named `mpegg.bedtime.tv`; configuration covered the Roku TV, bedroom lights, and USB power-strip entities. |
| `daytime` | UI/storage scene named `Daytime`; configuration covered bathroom/stair lights, the office plug, attic lights, and power-strip entities. |
| `good_morning` | SmartThings-provided scene. It exists as `scene.good_morning`, but is not editable Home Assistant storage configuration; edit it in SmartThings. |

This confirms HA-MCP can read UI/storage scene definitions that the custom
YAML-focused server does not see.

### Safety findings

- HA-MCP advertises Read Only Mode, per-tool enable/disable controls, tool
  security policies, and automatic backups for edits.
- Filesystem/YAML tools are opt-in beta features and must remain disabled in an
  initial deployment.
- HA-MCP has powerful system-management tools. Read-only mode must be verified
  in the HA-MCP settings UI before trusting it as a guardrail; it was not proven
  by attempting a refused write during this evaluation.
- A private endpoint path functions as a credential. Store it only in the MCP
  client configuration or a local secret store, never in Git.
- Run only one installation method of HA-MCP for a client. Do not add the
  custom component, add-on, and local stdio version under the same client.

## Superseded HACS recommendation

The initial recommendation below to adopt HA-MCP through its HACS custom
component was superseded by the external Docker deployment after the component
was removed during a period of Home Assistant instability. The removal coincided
with the VM becoming stable; this observation does not establish causality.

The local proposal-first server remains in the repository but is not the active
evaluation path.

## External Docker deployment and write validation

HA-MCP now runs independently on the Linux main server, which hosts Ollama,
Docker workloads, PostgreSQL, nginx, and VS Code. Home Assistant remains in an
Oracle VirtualBox VM on the Windows mini PC at `192.168.4.85`.

- Deployment definition: `infra/docker/ha-mcp-dev1.yml`.
- Host port: `3340`, in the Home Automation range documented in `wiki/ports.md`.
- Docker network: `app-services-net-dev1`; HA-MCP has no dependency on Ollama's
  `ai-services-net-dev1` network.
- Persistent state: `/mnt/ai_storage/ha-mcp/data`, owned by UID/GID `999:999`,
  which matches the upstream container user.
- The deployment uses the stable upstream image and streamable HTTP. The
  private endpoint and Home Assistant token remain only in the ignored runtime
  environment file. Its permissions are `0600`.
- HA-MCP 8.3.0 authenticated to Home Assistant over REST and WebSocket. The
  bundled `home-assistant-best-practices` skill is available through
  `ha_get_skill_guide`.

### Safety and persistence findings

- `READ_ONLY_MODE=true` was verified initially: scene create/delete tools were
  absent from the exposed MCP catalog and write attempts would be blocked.
- Beta filesystem/YAML features and developer mode remain disabled. Secret
  redaction and auto-backup support are enabled. Tool-security-policy middleware
  is enabled, but enabling the middleware alone does not create approval rules;
  no held-approval policy was exercised in the scene test.
- The upstream default auto-backup directory was outside the first data mount.
  The compose definition now explicitly sets `HAMCP_BACKUP_DIR` under the
  mounted HA-MCP directory, so edit backups persist across container recreation.
- The first dedicated HA user token could call the generic API but received
  `401` from the scene-configuration API. Making that dedicated user an
  administrator and recreating HA-MCP resolved the authorization boundary.

### Controlled scene write demonstration

The write path was tested only after the user deliberately set
`READ_ONLY_MODE=false` and recreated the container.

1. Read the bundled scene guidance and supplied the server's required
   best-practice acknowledgement.
2. Confirmed that `ha_mcp_write_demo_20260829` did not exist and read the
   current state of `input_boolean.matt_bedtime_prep` (`on`).
3. Created `scene.ha_mcp_write_demo_20260829` with a name, icon, and that one
   stored helper state. The scene was never activated, so it did not change the
   helper.
4. Read the scene back and confirmed its configuration. The helper remained
   `on`.
5. Recreated HA-MCP to validate persistence, then read the scene back again.
6. Deleted the test scene and verified that it was no longer present. The helper
   remained `on`.
7. Confirmed the persistent pre-delete auto-backup:
   `scene.ha_mcp_write_demo_20260829.20260829_185509.yaml`.

Read-only mode was restored and verified after this test. The user later
deliberately set `READ_ONLY_MODE=false` again and recreated HA-MCP for further
testing. **At the time of this record, write mode is enabled.** Any client that
can reach this shared HA-MCP endpoint can access its currently exposed write
tools.

### Model and client options

The MCP client, not the language model, owns tool discovery and execution. A
model can choose a tool call only after an MCP-capable client presents the tool
schema; that client runs the call against HA-MCP and returns the result to the
model.

| Option | How HA-MCP is used | Constraint and recommendation |
| --- | --- | --- |
| GitHub Copilot in VS Code | VS Code is the MCP client and calls the private LAN endpoint directly. | This is proven working. Standard Copilot configuration does not turn Ollama into a Copilot model; local-model use needs a separate compatible agent/client. |
| Local Ollama model | An MCP-capable local client or gateway, such as an appropriately configured Open WebUI or custom agent loop, runs on the main server and connects to HA-MCP. | Ollama supports function/tool calls and multi-turn loops, but Ollama itself neither speaks MCP nor executes MCP calls. Validate the selected model's tool-call reliability with read-only tools first. Enable HA-MCP's tool-search mode only for clients that cannot defer a large tool catalog. |
| Cloud DeepSeek model/API | An MCP-capable client on the main server sends tool schemas and tool results to DeepSeek, while that same client keeps the HA-MCP connection on the LAN. | DeepSeek is a model/API, not a route into the private LAN by itself. Do not expose port 3340 to the internet or place the MCP secret URL in a cloud prompt. Treat every Home Assistant read result supplied to the cloud model as data leaving the LAN. |

Do not share one write-enabled HA-MCP endpoint casually across Copilot, local
agents, and cloud agents. `READ_ONLY_MODE` and tool visibility are server-wide.
For different trust levels, run separate HA-MCP containers with separate Home
Assistant users/tokens, endpoint secrets, persistent volumes, and tool policies.
The next safest test is a local-model, read-only client test using only
`ha_get_overview`, `ha_search`, and `ha_get_skill_guide`.

## Initial staged-adoption record

1. Take a Home Assistant backup before installing or changing any integration.
2. Install HA-MCP through its HACS custom component and use only the private
   LAN endpoint. Disable remote webhook access unless remote access is needed.
3. Enable and verify Read Only Mode in HA-MCP's settings UI.
4. Initially expose only inspection capabilities: overview, entity/state
   search, scenes/scripts/automations, logs, history, and traces.
5. Keep filesystem/YAML and system-management tools disabled.
6. Retain this custom server while HA-MCP is evaluated. It remains useful as a
   narrow, proposal-first authoring path with protected domains and explicit
   confirmation.
7. Before enabling any authoring tool, establish a reviewable proposal and
   backup workflow. Never rely on model intent alone for write approval.

## Other open-source options considered

| Project | Assessment |
| --- | --- |
| Home Assistant built-in MCP Server | Official Core integration. Best for Assist-exposed, voice-style read/control; it does not author automations, scenes, or YAML. |
| [voska/hass-mcp](https://github.com/voska/hass-mcp) | Actively maintained and feature-rich, but exposes broad service control, restart, and dashboard writes. Use only with strict network and client controls. |
| [tevonsb/homeassistant-mcp](https://github.com/tevonsb/homeassistant-mcp) | Older TypeScript alternative with wide privileges, including add-on and HACS operations. It is not a good default for proposal-first authoring. |
| [allenporter/mcp-server-home-assistant](https://github.com/allenporter/mcp-server-home-assistant) | Archived in 2025; do not adopt. |

## Related repository finding: SearXNG

The `searxng-dev1` container was healthy and had been running for roughly three
weeks. Its local API returned search results. Open WebUI is configured to use
SearXNG directly.

The Python wrapper at `../searxng/server.py` is not running and fails to import
with the installed MCP SDK because `Server` no longer has `list_tools`. Its
`mcp-config.json` instead points to `npx -y mcp-searxng`. The container should be
kept; retire or modernize the obsolete Python wrapper only after confirming no
MCP client references it.

## Follow-up checklist

- [ ] Confirm HA-MCP Read Only Mode in its settings UI.
- [ ] Record the enabled and disabled HA-MCP tools after initial configuration.
- [ ] Exercise read-only inspection of scenes, automations, traces, and logs.
- [ ] Define an explicit user-approval process before enabling authoring.
- [ ] Decide whether HA-MCP complements or replaces the custom server.
- [ ] Confirm clients before removing the legacy SearXNG Python MCP wrapper.
