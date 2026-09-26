<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_object_id: infra/mcp/home-assistant/README.md:160 % -->
<!-- %ccm_git_author: mpegg % -->
<!-- %ccm_git_author_email: mpegg@hotmail.com % -->
<!-- %ccm_git_blob_sha: 21dda113cad94f8305c3c7c55a199dc35f773e6d % -->
<!-- %ccm_git_commit_id: 3a0dc6d000abbf72c8996a230bc72454f05c9f1b % -->
<!-- %ccm_git_commit_count: 160 % -->
<!-- %ccm_git_commit_date: 2026-09-25 21:30:36 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_email: mpegg@hotmail.com % -->
<!-- %ccm_git_commit_message: cleanup % -->
<!-- %ccm_git_modify_date: 2026-09-25 21:30:37 % -->
<!-- %ccm_git_file_last_modified: 2026-08-27 19:26:25 % -->
<!-- %ccm_git_file_name: README.md % -->
<!-- %ccm_git_path: infra/mcp/home-assistant/README.md % -->
<!-- %ccm_git_language_mode: markdown % -->
<!-- %ccm_git_file_type: text/plain % -->
<!-- %ccm_git_file_encoding: utf-8 % -->
<!-- %ccm_git_file_eol: CRLF % -->
<!-- %ccm_git_exec: no % -->
<!-- %ccm_git_size: 6757 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
 <!-- %git_commit_history: 1970-01-01 unknown  unknown  --> 
# Home Assistant MCP Server

A Model Context Protocol (MCP) server that lets an AI agent (GitHub Copilot in
VS Code) inspect and operate an existing Home Assistant instance, while staging
every scene/script/automation authoring change as a reviewable proposal.

## Safety model

| Capability | Allowed | Gate |
| --- | --- | --- |
| Read/inspect (info, entities, states, routines) | Yes | Authentication only |
| Operate existing routines (scenes, scripts, automations) | Yes | Allowlist of service domains |
| Generic service calls | Yes | Allowlist; protected domains refused |
| Create/update/delete routines | No by default | `HA_WRITES_ENABLED=true` **and** explicit `confirm=true` |
| Security domains (locks, alarms) | Never | Hard refusal in client, independent of config |

Two-step authoring: `propose_routine` only creates a local draft (with a
rendered preview and protected-reference warnings). `apply_proposal` writes to
Home Assistant only when the user has explicitly confirmed. Drafts are stored
locally under `HA_PROPOSAL_DIR` (default `/tmp/ha-mcp/proposals`) for audit.

## Architecture

```
Copilot (VS Code) -> [stdio MCP] -> server.py -> [REST + Bearer token] -> Home Assistant
                                          |
                                          +-> YAML config files (propose/apply only)
```

The server follows the repository MCP pattern in
[wiki/how-to-add-mcp-server.md](../../../wiki/how-to-add-mcp-server.md): it runs
on the host and communicates over stdio, like `infra/mcp/searxng`.

## Prerequisites

1. A running Home Assistant instance reachable from this machine
   (default `http://homeassistant.local:8123`).
2. A **dedicated** Home Assistant user plus a long-lived access token
   (Settings -> People -> create a user; then its Security tab -> Long-lived
   access tokens). Do not reuse the owner account token.
3. Python 3.10+ with the dependencies from `requirements.txt` installed.

## Setup

```bash
cd /home/mpegg-adm/source/TermiteTowers/infra/mcp/home-assistant
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp config.example.json config.json
# Edit config.json: set ha_url, token, ha_config_dir, keep writes_enabled=false
```

`config.json` and `proposals/` are git-ignored. Never commit the token.

## First-run probe (version-specific proof)

Always run this before enabling writes. It verifies the token, reports the Home
Assistant version, lists existing routines, and shows which YAML files are
reachable through `ha_config_dir`.

```bash
source .venv/bin/activate
python probe_ha.py
```

Review the output, then set `"writes_enabled": true` (or
`HA_WRITES_ENABLED=true`) only after you have a sandbox to test against.

## Register with VS Code / Copilot

Use the VS Code MCP server registration. You can point it at `config.json` by
setting environment variables, or use `mcp-config.json` as a starting template:

```json
{
  "mcpServers": {
    "home-assistant": {
      "command": "python",
      "args": ["/home/mpegg-adm/source/TermiteTowers/infra/mcp/home-assistant/server.py"],
      "env": {
        "HA_URL": "http://homeassistant.local:8123",
        "HA_TOKEN": "<token>",
        "HA_CONFIG_DIR": "/path/to/homeassistant/config",
        "HA_WRITES_ENABLED": "false"
      }
    }
  }
}
```

Use the full path to the venv interpreter (e.g.
`.../home-assistant/.venv/bin/python`) as the `command` so the MCP SDK and
PyYAML resolve.

## Configuration reference

Environment variables override `config.json`, which overrides defaults.

| Variable | Default | Purpose |
| --- | --- | --- |
| `HA_URL` | `http://homeassistant.local:8123` | Base URL of the HA instance |
| `HA_TOKEN` | *(none)* | Long-lived access token (required) |
| `HA_CONFIG_DIR` | *(none)* | Path to HA config dir (enables YAML read/write) |
| `HA_WRITES_ENABLED` | `false` | Master switch for applying proposals |
| `HA_VERIFY_TLS` | `true` | Verify TLS certificates |
| `HA_TIMEOUT` | `15` | Request timeout in seconds |
| `HA_PROPOSAL_DIR` | `/tmp/ha-mcp/proposals` | Local proposal store |

`protected_domains` (default `lock`, `alarm_control_panel`),
`protected_entities`, and `allowed_service_domains` are configured in
`config.json`.

## Tools

- `get_ha_info` — version, state, components, write capability.
- `list_entities` — states filtered by domain and/or query.
- `get_state` — one entity's state and attributes.
- `list_routines` / `get_routine` — scenes, scripts, automations (with YAML when files are accessible).
- `activate_scene`, `run_script`, `set_automation_enabled` — operate routines.
- `call_service` — allowlisted generic service call.
- `propose_routine` — draft a routine change (no HA mutation).
- `apply_proposal` — apply a confirmed proposal and reload the domain.
- `list_proposals` — list local drafts and their applied state.

## Write path details

`apply_proposal` merges into the existing YAML file (`automations.yaml`,
`scenes.yaml`, `scripts.yaml`) and reloads the matching domain. It will **not**
create a new config file and will **not** touch UI-managed (`config/.storage`)
automations: those must be created in the Home Assistant UI or migrated to YAML
first. This is why the probe output matters before enabling writes.

## Testing

```bash
source .venv/bin/activate
python -m unittest test_server -v
```

Tests use mocked Home Assistant responses and do not require a live instance.

## Related documentation

- `probe_ha.py` — version-specific capability check.
- `wiki/how-to-add-mcp-server.md` — repository MCP conventions.
- `wiki/how-to-extend-voice-assistant.md` — existing voice/webhook path (fixed commands only).
- `wiki/runbook-ha-hal-bridge.md` — current webhook bridge (needs separate hardening).
