#!/usr/bin/env python3
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/mcp/home-assistant/server.py:160 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: c4bb270b2b62373654d66cd35311ebab8c399324 %
#  %ccm_git_commit_id: 3a0dc6d000abbf72c8996a230bc72454f05c9f1b %
#  %ccm_git_commit_count: 160 %
#  %ccm_git_commit_date: 2026-09-25 21:30:36 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: cleanup %
#  %ccm_git_modify_date: 2026-09-25 21:30:37 %
#  %ccm_git_file_last_modified: 2026-08-28 18:17:06 %
#  %ccm_git_file_name: server.py %
#  %ccm_git_path: infra/mcp/home-assistant/server.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 16308 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""
Home Assistant MCP Server.

Exposes read, operate, and proposal-gated write capabilities to MCP clients
(such as GitHub Copilot in VS Code) via stdio.

Usage:
    HA_URL=http://homeassistant.local:8123 \
    HA_TOKEN=... \
    HA_CONFIG_DIR=/path/to/ha/config \
    HA_WRITES_ENABLED=false \
    python server.py

See README.md for the full configuration matrix and safety model.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Annotated, Any, Literal

try:
    import yaml as _yaml
    YAML_AVAILABLE = True
except ImportError:  # pragma: no cover
    _yaml = None
    YAML_AVAILABLE = False

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from ha_client import (
    HAError,
    HAPolicyError,
    HAWriteError,
    HomeAssistantClient,
    load_config,
)

# ---------------------------------------------------------------------------
# Logging - stderr only, never on stdio.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/tmp/mcp-home-assistant.log"),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger("mcp-home-assistant")

CONFIG = load_config()
CLIENT = HomeAssistantClient(CONFIG)
PROPOSAL_DIR = os.getenv("HA_PROPOSAL_DIR", "/tmp/ha-mcp/proposals")

app = MCPServer(name="home-assistant", version="0.1.0")

# Never log the token.
logger.info(
    "Home Assistant MCP server starting "
    f"(base_url={CONFIG.base_url_clean}, writes={CONFIG.writes_enabled})"
)


def _json_text(payload: Any) -> str:
    return json.dumps(payload, indent=2, default=str)


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

def _safe(name: str, args: dict[str, Any]) -> str:
    """Dispatch a tool and convert any error into a readable JSON string."""
    logger.info(f"Tool called: {name}")
    try:
        return _dispatch(name, args)
    except HAPolicyError as exc:
        logger.warning(f"Policy refusal for {name}: {exc}")
        return _json_text({"refused": True, "reason": str(exc)})
    except (HAError, HAWriteError) as exc:
        logger.error(f"HA error for {name}: {exc}")
        return _json_text({"error": True, "message": str(exc)})
    except Exception as exc:  # noqa: BLE001 - fail safe for the LLM
        logger.exception(f"Unexpected error for {name}")
        return _json_text({"error": True, "message": f"Unexpected error: {exc}"})


@app.tool(
    name="get_ha_info",
    description=(
        "Read Home Assistant instance information: version, state, components, "
        "and whether configuration-file writes are enabled for this agent. "
        "Use this first to understand the environment."
    ),
)
def get_ha_info() -> str:
    return _safe("get_ha_info", {})


@app.tool(
    name="list_entities",
    description=(
        "List Home Assistant entities with their current states. Optionally "
        "filter by domain (e.g. 'light') and/or by a substring match on "
        "entity_id or friendly name."
    ),
)
def list_entities(
    domain: Annotated[str | None, Field(description="Optional domain filter, e.g. 'light', 'switch', 'climate'.")] = None,
    query: Annotated[str | None, Field(description="Optional substring to match against entity_id or friendly name.")] = None,
) -> str:
    return _safe("list_entities", {"domain": domain, "query": query})


@app.tool(
    name="get_state",
    description=(
        "Get the full state object (state + attributes) for a single entity by entity_id."
    ),
)
def get_state(
    entity_id: Annotated[str, Field(description="Entity id, e.g. 'light.office'.")],
) -> str:
    return _safe("get_state", {"entity_id": entity_id})


@app.tool(
    name="list_routines",
    description=(
        "List existing scenes, scripts, and/or automations. Returns names/ids, "
        "current state (for entities), and the full YAML definition when "
        "configuration files are accessible."
    ),
)
def list_routines(
    kind: Annotated[Literal["automation", "scene", "script"], Field(description="Which routine type to list.")],
) -> str:
    return _safe("list_routines", {"kind": kind})


@app.tool(
    name="get_routine",
    description=(
        "Get the full definition (YAML) of a single scene, script, or automation by id or alias."
    ),
)
def get_routine(
    kind: Annotated[Literal["automation", "scene", "script"], Field(description="Routine type.")],
    definition_id: Annotated[str, Field(description="The id or alias of the routine.")],
) -> str:
    return _safe("get_routine", {"kind": kind, "definition_id": definition_id})


@app.tool(name="activate_scene", description=("Activate an existing scene (scene.turn_on)."))
def activate_scene(
    scene_id: Annotated[str, Field(description="Scene id or entity_id, e.g. 'evening' or 'scene.evening'.")],
) -> str:
    return _safe("activate_scene", {"scene_id": scene_id})


@app.tool(name="run_script", description=("Run an existing script (script.turn_on)."))
def run_script(
    script_id: Annotated[str, Field(description="Script id or entity_id, e.g. 'good_morning' or 'script.good_morning'.")],
) -> str:
    return _safe("run_script", {"script_id": script_id})


@app.tool(
    name="set_automation_enabled",
    description=(
        "Enable or disable an existing automation. Does not delete or modify its definition."
    ),
)
def set_automation_enabled(
    automation_id: Annotated[str, Field(description="Automation id or entity_id.")],
    enabled: Annotated[bool, Field(description="true to turn on, false to turn off.")],
) -> str:
    return _safe("set_automation_enabled", {"automation_id": automation_id, "enabled": enabled})


@app.tool(
    name="call_service",
    description=(
        "Call an allowlisted Home Assistant service (e.g. light.turn_on, "
        "switch.toggle, media_player.media_pause). Security domains (locks, "
        "alarms) are always refused."
    ),
)
def call_service(
    domain: Annotated[str, Field(description="Service domain, e.g. 'light'.")],
    service: Annotated[str, Field(description="Service name, e.g. 'turn_on'.")],
    entity_id: Annotated[str | None, Field(description="Optional target entity_id.")] = None,
    data: Annotated[dict | None, Field(description="Optional service data payload.")] = None,
) -> str:
    return _safe("call_service", {"domain": domain, "service": service, "entity_id": entity_id, "data": data})


@app.tool(
    name="propose_routine",
    description=(
        "DRAFT a new or updated scene/script/automation as YAML without changing "
        "Home Assistant. Returns a proposal id plus a rendered preview and any "
        "protected-reference warnings. Use apply_proposal to actually apply it "
        "after user approval."
    ),
)
def propose_routine(
    kind: Annotated[Literal["automation", "scene", "script"], Field(description="Routine type.")],
    yaml_text: Annotated[str, Field(description="The routine definition as YAML (a single mapping, or a list for multiple).")],
) -> str:
    return _safe("propose_routine", {"kind": kind, "yaml_text": yaml_text})


@app.tool(
    name="apply_proposal",
    description=(
        "Apply a previously created proposal to the Home Assistant configuration "
        "files and reload the affected domain. Requires confirm=true AND writes "
        "to be enabled. Never call this before the user has explicitly approved "
        "the proposal."
    ),
)
def apply_proposal(
    proposal_id: Annotated[str, Field(description="The proposal id returned by propose_routine.")],
    confirm: Annotated[bool, Field(description="Must be explicitly true to apply.")],
) -> str:
    return _safe("apply_proposal", {"proposal_id": proposal_id, "confirm": confirm})


@app.tool(
    name="list_proposals",
    description=(
        "List pending and applied proposals stored locally on the machine running this MCP server."
    ),
)
def list_proposals() -> str:
    return _safe("list_proposals", {})


def _dispatch(name: str, args: dict[str, Any]) -> str:
    if name == "get_ha_info":
        info = CLIENT.get_info()
        info["writes_enabled"] = CONFIG.writes_enabled
        info["config_dir_configured"] = bool(CONFIG.config_dir)
        info["yaml_available"] = YAML_AVAILABLE
        info["protected_domains"] = CONFIG.protected_domains
        info["allowed_service_domains"] = CONFIG.allowed_service_domains
        return _json_text(info)

    if name == "list_entities":
        domain = (args.get("domain") or "").strip().lower()
        query = (args.get("query") or "").strip().lower()
        states = CLIENT.list_states()
        rows = []
        for state in states:
            entity_id = state.get("entity_id", "")
            if domain and entity_id.split(".", 1)[0] != domain:
                continue
            if query:
                friendly = str(state.get("attributes", {}).get("friendly_name", "")).lower()
                if query not in entity_id.lower() and query not in friendly:
                    continue
            rows.append(
                {
                    "entity_id": entity_id,
                    "state": state.get("state"),
                    "friendly_name": state.get("attributes", {}).get("friendly_name"),
                }
            )
        return _json_text({"count": len(rows), "entities": rows})

    if name == "get_state":
        entity_id = args["entity_id"]
        return _json_text(CLIENT.get_state(entity_id))

    if name == "list_routines":
        kind = args["kind"]
        definitions = []
        if CONFIG.config_dir and YAML_AVAILABLE:
            definitions = CLIENT.list_definitions(kind)
        else:
            states = CLIENT.list_states()
            definitions = [
                {
                    "id": s["entity_id"].split(".", 1)[1],
                    "entity_id": s["entity_id"],
                    "alias": s.get("attributes", {}).get("friendly_name", s["entity_id"]),
                    "state": s.get("state"),
                    "definition_available": False,
                }
                for s in states
                if s.get("entity_id", "").startswith(f"{kind}.")
            ]
        return _json_text(
            {
                "kind": kind,
                "count": len(definitions),
                "definitions": definitions,
                "definitions_from_files": bool(CONFIG.config_dir and YAML_AVAILABLE),
            }
        )

    if name == "get_routine":
        kind = args["kind"]
        definition_id = args["definition_id"]
        definition = CLIENT.get_definition(kind, definition_id)
        if definition is None:
            return _json_text(
                {"found": False, "kind": kind, "definition_id": definition_id}
            )
        return _json_text({"found": True, "kind": kind, "definition": definition})

    if name == "activate_scene":
        result = CLIENT.activate_scene(args["scene_id"])
        return _json_text({"ok": True, "result": result})

    if name == "run_script":
        result = CLIENT.run_script(args["script_id"])
        return _json_text({"ok": True, "result": result})

    if name == "set_automation_enabled":
        result = CLIENT.set_automation_enabled(
            args["automation_id"], bool(args["enabled"])
        )
        return _json_text({"ok": True, "result": result})

    if name == "call_service":
        result = CLIENT.call_service(
            args["domain"],
            args["service"],
            args.get("entity_id"),
            args.get("data"),
        )
        return _json_text({"ok": True, "result": result})

    if name == "propose_routine":
        kind = args["kind"]
        yaml_text = args["yaml_text"]
        if not YAML_AVAILABLE:
            raise HAWriteError("PyYAML is not installed; cannot parse YAML proposals.")
        try:
            payload = _yaml.safe_load(yaml_text)
        except _yaml.YAMLError as exc:
            raise HAError(f"Invalid YAML: {exc}") from exc
        if payload is None:
            raise HAError("YAML was empty; provide a definition.")

        proposal = CLIENT.propose(kind, payload, PROPOSAL_DIR)
        return _json_text(
            {
                "proposal_id": proposal.id,
                "kind": proposal.kind,
                "target_file": proposal.target_file,
                "replace_ids": proposal.replace_ids,
                "protected_hits": proposal.protected_hits,
                "preview_yaml": _yaml.safe_dump(
                    proposal.payload, sort_keys=False, default_flow_style=False
                ),
                "note": (
                    "Draft only. Nothing was changed in Home Assistant. "
                    "Share this with the user and call apply_proposal only after "
                    "explicit approval."
                ),
            }
        )

    if name == "apply_proposal":
        proposal_id = args["proposal_id"]
        confirm = bool(args.get("confirm"))
        proposal = CLIENT.load_proposal(PROPOSAL_DIR, proposal_id)
        result = CLIENT.apply_proposal(proposal, confirm=confirm)
        CLIENT._save_proposal(proposal, PROPOSAL_DIR)  # record applied state
        return _json_text(result)

    if name == "list_proposals":
        os.makedirs(PROPOSAL_DIR, exist_ok=True)
        rows = []
        for fname in sorted(os.listdir(PROPOSAL_DIR)):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(PROPOSAL_DIR, fname)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    record = json.load(fh)
            except (OSError, ValueError):
                continue
            rows.append(
                {
                    "proposal_id": record.get("id"),
                    "kind": record.get("kind"),
                    "target_file": record.get("target_file"),
                    "protected_hits": record.get("protected_hits", []),
                    "applied": record.get("applied", False),
                    "created_at": record.get("created_at"),
                }
            )
        return _json_text({"proposals": rows})

    raise HAError(f"Unknown tool: {name}")


async def main() -> None:
    logger.info("Starting Home Assistant MCP server")
    try:
        info = CLIENT.get_info()
        logger.info(
            f"Connected to Home Assistant {info.get('version')} at "
            f"{CONFIG.base_url_clean}"
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Could not reach Home Assistant at startup: {exc}")
        logger.warning("Server will start anyway; calls will fail until HA is reachable.")

    await app.run_stdio_async()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Server error: {exc}", exc_info=True)
        sys.exit(1)
