<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: wiki/runbook-ha-mcp.md % -->
<!-- %ccm_git_object_id: wiki/runbook-ha-mcp.md@194 % -->
<!-- %ccm_git_commit_date: 2026-10-28 20:22:38 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: misc updates % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
# Runbook: HA-MCP (Home Assistant MCP server)

Containerised Home Assistant MCP server exposing 78 `ha_*` tools to MCP clients (Zoo Code, Cline, VS Code native MCP) over Streamable HTTP.

## Source
- Compose: `infra/docker/ha-mcp-dev1.yml`
- Environment: `infra/docker/env/ha-mcp.env` (secrets, git-ignored; template at `ha-mcp.env.example`)
- Runtime data: `/mnt/ai_storage/ha-mcp/data`

## Endpoint
- Streamable HTTP MCP endpoint: `POST http://<host>:3340/private_<TOKEN>`
  - GET on the same path returns `405 Method Not Allowed` — this is expected and is a useful health signal.
  - A wrong or missing token returns `404`, not `403`.
- Web settings UI: `http://<host>:3340/private_<TOKEN>/settings` (enable/disable tools, approvals, backups)
  - The "full URL in the startup logs" reference in tool output means this path — the token is the settings path.

Published mapping is `0.0.0.0:3340 -> 8086/tcp`. Port 3340 is registered in [`ports.md`](ports.md).

## Dependencies
- Home Assistant at `http://192.168.4.85:8123` (observed version 2026.10.4), reached via `HAMCP_*` values in the env file
- Docker network `app-services-net-dev1` (external)
- `/mnt/ai_storage/ha-mcp/data` must be writable by uid 999

## Start / Stop
```bash
cd /srv/dev1/ha-mcp/docker

# Start / update
docker compose -f ha-mcp-dev1.yml up -d

# Status
docker ps --filter name=ha-mcp-dev1 --format '{{.Names}} | {{.Status}} | {{.Ports}}'

# Stop
docker compose -f ha-mcp-dev1.yml down
```

## Logs
```bash
docker logs --tail 100 -f ha-mcp-dev1
```

## Health
Two checks, in order — they separate routing problems from protocol problems.

```bash
TOKEN=private_<TOKEN>

# 1) Bind + route + token path. Expect 405. 404 = bad token/path. 000 = nothing listening.
curl -sS -o /dev/null -w '%{http_code}\n' "http://127.0.0.1:3340/$TOKEN"

# 2) MCP handshake. Expect 200, content-type text/event-stream, and a serverInfo payload.
curl -sS -D- -X POST "http://127.0.0.1:3340/$TOKEN" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}'
```

Confirm the server is up and identify its build from the handshake response, which reports `serverInfo.name` and `serverInfo.version`.

## Client configuration

The transport token is client-specific. Using the wrong one causes a **silent skip**, not a visible error.

| Client | `type` value | Config root key | Config path |
|---|---|---|---|
| Zoo Code | `streamable-http` | `mcpServers` | `~/.config/Code/User/globalStorage/zoocodeorganization.zoo-code/settings/mcp_settings.json` |
| Cline | `streamableHttp` | `mcpServers` | `~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json` |
| VS Code native | `http` | `servers` | `~/.config/Code/User/mcp.json` or `profiles/<id>/mcp.json` |

Zoo Code entry:

```json
"hal-mcp": {
  "url": "http://127.0.0.1:3340/private_<TOKEN>",
  "type": "streamable-http",
  "disabled": false,
  "autoApprove": []
}
```

Zoo Code watches the settings file and reloads on change — no window reload required.

## Token handling

The `private_<TOKEN>` path segment is the only authentication on this endpoint. Treat it as a credential.

- It currently appears in three live config files plus VS Code local-history copies. There is no single source of truth; `infra/docker/env/ha-mcp.env` is the intended one.
- To rotate: stop the container, update the token in the env file, recreate the container, then update every client config. Clients will show `404` until updated.
- Prefer the `headers` field for auth where a client supports it, so the secret is not in the URL path (URLs leak into logs and history).
- Do not commit the token. `infra/docker/env/` is git-ignored except `.example` files.

Relevant hardening note: the publish is `0.0.0.0`, so the endpoint is reachable from the whole LAN. If no client connects from another host, narrowing the publish to `127.0.0.1:3340:8086` removes LAN exposure entirely.

## Upgrades
The image is `ghcr.io/homeassistant-ai/ha-mcp:latest`. The health check reports the running version and whether a newer release exists; a version mismatch between that report and the pulled image means the container predates the last pull.

```bash
docker compose -f ha-mcp-dev1.yml pull
docker compose -f ha-mcp-dev1.yml up -d
```

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| `No connection found for server: hal-mcp` in the client | `type` token not in the client's accepted set; entry skipped during schema validation | Use `streamable-http` for Zoo Code. A validation error also appears in the client's MCP output panel |
| `404` on health check | Wrong or rotated token | Re-read the token from the env file |
| `000` from curl, connection refused | Container down, or client resolving `localhost` to `::1` against an IPv4-only publish | Start the container; use `127.0.0.1` explicitly |
| Tools listed but calls fail with auth errors | `HAMCP_*` values in env file stale | Refresh the HA token in `ha-mcp.env`, recreate the container |
| Handshake returns 200 but no tools | Wrong HA instance reachable, or tools disabled in settings UI | Check the settings UI and the container log |

## Verification performed

On 2026-10-28 this endpoint was confirmed working: GET returned `405`, `initialize` returned `200` with `Content-Type: text/event-stream`, and `ha_get_overview` returned Home Assistant 2026.10.4 in state `RUNNING`.

Version history observed on this host:

| Version | `tools/list` count | Notable change |
|---|---|---|
| 8.4.3 | 78 | baseline |
| 9.0.0 | 77 | `ha_get_blueprint` and `ha_import_blueprint` consolidated into `ha_manage_blueprints` |

Because the image tracks `:latest`, a version bump can rename or merge tools without any signal beyond the count changing. MCP clients cache tool schemas for the lifetime of a session, so after an upgrade reload the client window before trusting the tool list — a stale cached name fails with an unknown-tool error even though the server itself is healthy. For reproducibility, pinning an image digest (or an explicit tag) instead of `:latest` makes upgrades a deliberate act.
