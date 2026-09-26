#!/usr/bin/env python3
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/mcp/home-assistant/ha_client.py:160 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 91280f683503b1f922c46aa400db0bf36eaf0915 %
#  %ccm_git_commit_id: 3a0dc6d000abbf72c8996a230bc72454f05c9f1b %
#  %ccm_git_commit_count: 160 %
#  %ccm_git_commit_date: 2026-09-25 21:30:36 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: cleanup %
#  %ccm_git_modify_date: 2026-09-25 21:30:37 %
#  %ccm_git_file_last_modified: 2026-08-27 19:26:25 %
#  %ccm_git_file_name: ha_client.py %
#  %ccm_git_path: infra/mcp/home-assistant/ha_client.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 21382 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""
Home Assistant REST client with safety-policy enforcement.

This module is intentionally free of MCP dependencies so it can be unit
tested and reused by both the MCP server and the probe script.

Design principles:
- Read/inspect operations are always allowed once authenticated.
- Operation of ordinary routines is allowed within an allowlist.
- Security domains (locks, alarms, ...) are protected and refused by default.
- Configuration authoring is two-step: propose (draft/diff only) then apply
  (requires explicit confirmation, writes_enabled, and a writable config dir).
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

import requests

try:
    import yaml as _yaml
    YAML_AVAILABLE = True
except ImportError:  # pragma: no cover - environment dependent
    _yaml = None
    YAML_AVAILABLE = False

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_HA_URL = "http://homeassistant.local:8123"

# Entities under these domains are never operated on or written by the agent.
DEFAULT_PROTECTED_DOMAINS = [
    "lock",
    "alarm_control_panel",
]

# Service domains the agent is permitted to call via the generic `call_service`
# tool. Scenes, scripts, and automations are always allowed for their dedicated
# tools regardless of this list.
DEFAULT_ALLOWED_SERVICE_DOMAINS = [
    "scene",
    "script",
    "automation",
    "light",
    "switch",
    "fan",
    "climate",
    "media_player",
    "input_boolean",
    "button",
    "number",
    "select",
    "vacuum",
    "humidifier",
    "cover",
]

ENTITY_ID_RE = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")

# Mapping of definition kind -> YAML filename within HA config dir.
YAML_FILENAMES = {
    "automation": "automations.yaml",
    "scene": "scenes.yaml",
    "script": "scripts.yaml",
}

# Mapping of definition kind -> service domain used to reload after write.
RELOAD_SERVICE = {
    "automation": "automation",
    "scene": "scene",
    "script": "script",
}


class HAError(Exception):
    """Base error for Home Assistant client failures."""


class HAAuthError(HAError):
    """Authentication or authorization failure against Home Assistant."""


class HAPolicyError(HAError):
    """A request was refused by the local safety policy."""


class HAWriteError(HAError):
    """A configuration write could not be completed safely."""


@dataclass
class HAConfig:
    base_url: str = DEFAULT_HA_URL
    token: str = ""
    config_dir: Optional[str] = None
    allowed_service_domains: list[str] = field(
        default_factory=lambda: list(DEFAULT_ALLOWED_SERVICE_DOMAINS)
    )
    protected_domains: list[str] = field(
        default_factory=lambda: list(DEFAULT_PROTECTED_DOMAINS)
    )
    protected_entities: list[str] = field(default_factory=list)
    writes_enabled: bool = False
    verify_tls: bool = True
    timeout: float = 15.0

    @property
    def base_url_clean(self) -> str:
        return self.base_url.rstrip("/")


@dataclass
class Proposal:
    id: str
    kind: str
    payload: Any
    target_file: str
    replace_ids: list[str]
    protected_hits: list[str]
    created_at: float
    applied: bool = False
    applied_at: Optional[float] = None


def load_config(path: Optional[str] = None) -> HAConfig:
    """Load configuration from an optional JSON file merged with environment.

    Precedence (highest first):
      1. Environment variables (HA_URL, HA_TOKEN, HA_CONFIG_DIR,
         HA_WRITES_ENABLED, HA_VERIFY_TLS, HA_TIMEOUT).
      2. JSON file values (default: ./config.json next to this module).
      3. Built-in defaults.
    """
    cfg_file = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    data: dict[str, Any] = {}
    if os.path.isfile(cfg_file):
        with open(cfg_file, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
        if isinstance(loaded, dict):
            data = loaded

    def _pick(env_key: str, file_key: str, default: Any) -> Any:
        if os.getenv(env_key):
            return os.getenv(env_key)
        return data.get(file_key, default)

    def _bool(value: Any, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("1", "true", "yes", "on")

    config = HAConfig(
        base_url=str(_pick("HA_URL", "ha_url", DEFAULT_HA_URL)),
        token=str(_pick("HA_TOKEN", "token", "")),
        config_dir=_pick("HA_CONFIG_DIR", "ha_config_dir", None) or None,
        allowed_service_domains=list(
            data.get("allowed_service_domains", DEFAULT_ALLOWED_SERVICE_DOMAINS)
        ),
        protected_domains=list(
            data.get("protected_domains", DEFAULT_PROTECTED_DOMAINS)
        ),
        protected_entities=list(data.get("protected_entities", [])),
        writes_enabled=_bool(
            _pick("HA_WRITES_ENABLED", "writes_enabled", False), False
        ),
        verify_tls=_bool(
            _pick("HA_VERIFY_TLS", "verify_tls", True), True
        ),
        timeout=float(_pick("HA_TIMEOUT", "timeout", 15.0)),
    )
    return config


class HomeAssistantClient:
    """Thin, policy-enforcing client for the Home Assistant REST API."""

    def __init__(self, config: HAConfig) -> None:
        self.config = config

    # -- HTTP plumbing -----------------------------------------------------

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.token}",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[dict[str, Any]] = None,
    ) -> Any:
        url = f"{self.config.base_url_clean}{path}"
        try:
            response = requests.request(
                method,
                url,
                headers=self._headers,
                json=json_body,
                timeout=self.config.timeout,
                verify=self.config.verify_tls,
            )
        except requests.exceptions.RequestException as exc:
            raise HAError(f"Unable to reach Home Assistant at {url}: {exc}") from exc

        if response.status_code in (401, 403):
            raise HAAuthError(
                f"Home Assistant rejected the token for {method} {path} "
                f"(HTTP {response.status_code}). Check HA_TOKEN."
            )
        if response.status_code >= 400:
            detail = response.text[:400] if response.text else "(no body)"
            raise HAError(
                f"Home Assistant returned HTTP {response.status_code} for "
                f"{method} {path}: {detail}"
            )

        if not response.text:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text

    # -- Read / inspect ----------------------------------------------------

    def get_info(self) -> dict[str, Any]:
        """Return API heartbeat plus config (version, components, paths)."""
        heartbeat = self._request("GET", "/api/") or {}
        config = self._request("GET", "/api/config") or {}
        return {
            "message": heartbeat.get("message", ""),
            "version": config.get("version"),
            "state": config.get("state"),
            "config_dir": config.get("config_dir"),
            "components": config.get("components", []),
            "time_zone": config.get("time_zone"),
            "external_url": config.get("external_url"),
            "internal_url": config.get("internal_url"),
        }

    def list_states(self) -> list[dict[str, Any]]:
        """Return all entity states."""
        return self._request("GET", "/api/states") or []

    def get_state(self, entity_id: str) -> dict[str, Any]:
        """Return a single entity's state."""
        if not ENTITY_ID_RE.match(entity_id or ""):
            raise HAError(f"Invalid entity_id: {entity_id!r}")
        return self._request("GET", f"/api/states/{entity_id}") or {}

    # -- Operation ----------------------------------------------------------

    def _assert_entity_allowed(self, entity_id: Optional[str]) -> None:
        if not entity_id:
            return
        domain = entity_id.split(".", 1)[0]
        if domain in self.config.protected_domains:
            raise HAPolicyError(
                f"Refused: domain '{domain}' is protected "
                f"({', '.join(self.config.protected_domains)})."
            )
        if entity_id in self.config.protected_entities:
            raise HAPolicyError(f"Refused: entity '{entity_id}' is protected.")

    def _assert_service_domain_allowed(self, domain: str) -> None:
        if domain in self.config.protected_domains:
            raise HAPolicyError(
                f"Refused: service domain '{domain}' is protected."
            )
        if domain not in self.config.allowed_service_domains:
            raise HAPolicyError(
                f"Refused: service domain '{domain}' is not in the allowed list."
            )

    def call_service(
        self,
        domain: str,
        service: str,
        entity_id: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Call a Home Assistant service within the safety policy."""
        self._assert_service_domain_allowed(domain)
        self._assert_entity_allowed(entity_id)

        body: dict[str, Any] = {}
        if entity_id:
            body["entity_id"] = entity_id
        if data:
            body.update(data)

        return self._request(
            "POST", f"/api/services/{domain}/{service}", json_body=body or None
        )

    def activate_scene(self, scene_id: str) -> Any:
        entity_id = scene_id if "." in scene_id else f"scene.{scene_id}"
        return self.call_service("scene", "turn_on", entity_id)

    def run_script(self, script_id: str) -> Any:
        entity_id = script_id if "." in script_id else f"script.{script_id}"
        return self.call_service("script", "turn_on", entity_id)

    def set_automation_enabled(self, automation_id: str, enabled: bool) -> Any:
        entity_id = (
            automation_id if "." in automation_id else f"automation.{automation_id}"
        )
        service = "turn_on" if enabled else "turn_off"
        return self.call_service("automation", service, entity_id)

    # -- Configuration file access -----------------------------------------

    def _config_path(self, kind: str) -> str:
        if not self.config.config_dir:
            raise HAWriteError(
                "HA_CONFIG_DIR is not set; configuration files are not accessible."
            )
        filename = YAML_FILENAMES[kind]
        return os.path.join(self.config.config_dir, filename)

    def read_definitions(self, kind: str) -> Any:
        """Read the YAML definitions file for a kind (may return None)."""
        if not YAML_AVAILABLE:
            raise HAWriteError("PyYAML is not installed; cannot parse YAML files.")
        path = self._config_path(kind)
        if not os.path.isfile(path):
            return None
        with open(path, "r", encoding="utf-8") as fh:
            return _yaml.safe_load(fh) or None

    def list_definitions(self, kind: str) -> list[dict[str, Any]]:
        """Return definitions of a kind as a normalized list of mappings."""
        raw = self.read_definitions(kind)
        if raw is None:
            return []
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
        if isinstance(raw, dict):
            # scripts.yaml is traditionally a mapping keyed by alias/id.
            items = []
            for key, value in raw.items():
                if isinstance(value, dict):
                    entry = dict(value)
                    if "id" not in entry:
                        entry["id"] = key
                    if "alias" not in entry:
                        entry["alias"] = key
                    items.append(entry)
                else:
                    items.append({"id": key, "alias": key, "value": value})
            return items
        return []

    def get_definition(self, kind: str, definition_id: str) -> Optional[dict[str, Any]]:
        """Return one definition by id or alias, or None."""
        for item in self.list_definitions(kind):
            if item.get("id") == definition_id or item.get("alias") == definition_id:
                return item
        return None

    # -- Proposal / apply ----------------------------------------------------

    def scan_protected(self, payload: Any) -> list[str]:
        """Return a list of protected references found inside a definition."""
        hits: list[str] = []
        if not YAML_AVAILABLE:
            return hits
        text = _yaml.safe_dump(payload, sort_keys=False, default_flow_style=False)
        domains = "|".join(re.escape(d) for d in self.config.protected_domains)
        if not domains:
            return hits
        for match in re.finditer(rf"\b({domains})\.", text):
            hits.append(match.group(0))
        for match in re.finditer(
            rf"(domain\s*:\s*)({domains})", text
        ):
            hits.append(match.group(2))
        for entity in self.config.protected_entities:
            if entity and entity in text:
                hits.append(entity)
        # De-duplicate while preserving order.
        seen: list[str] = []
        for hit in hits:
            if hit not in seen:
                seen.append(hit)
        return seen

    def _merge_definitions(self, existing: Any, additions: list[dict[str, Any]]) -> Any:
        if existing is None:
            existing = []
        if isinstance(existing, list):
            merged = list(existing)
            by_id = {
                item.get("id"): idx
                for idx, item in enumerate(merged)
                if isinstance(item, dict) and item.get("id")
            }
            for addition in additions:
                key = addition.get("id")
                if key and key in by_id:
                    merged[by_id[key]] = addition
                else:
                    merged.append(addition)
            return merged
        if isinstance(existing, dict):
            merged = dict(existing)
            for addition in additions:
                key = addition.get("id") or addition.get("alias")
                if key:
                    merged[key] = addition
            return merged
        # Unsupported existing form; do not touch it.
        raise HAWriteError(
            "Existing definitions file has an unsupported structure; refusing to write."
        )

    def propose(self, kind: str, payload: Any, proposal_dir: str) -> Proposal:
        """Create and persist a proposal. Does NOT modify Home Assistant."""
        if kind not in YAML_FILENAMES:
            raise HAError(f"Unknown definition kind: {kind!r}")

        if isinstance(payload, dict):
            payload_list = [payload]
        elif isinstance(payload, list):
            payload_list = payload
        else:
            raise HAError("Definition must be a YAML mapping or list of mappings.")

        protected_hits = self.scan_protected(payload_list)
        replace_ids = [
            item.get("id") for item in payload_list if isinstance(item, dict) and item.get("id")
        ]

        proposal = Proposal(
            id=uuid.uuid4().hex[:12],
            kind=kind,
            payload=payload_list,
            target_file=self._config_path(kind),
            replace_ids=replace_ids,
            protected_hits=protected_hits,
            created_at=time.time(),
        )
        self._save_proposal(proposal, proposal_dir)
        return proposal

    @staticmethod
    def _proposal_path(proposal_dir: str, proposal_id: str) -> str:
        return os.path.join(proposal_dir, f"{proposal_id}.json")

    def _save_proposal(self, proposal: Proposal, proposal_dir: str) -> None:
        os.makedirs(proposal_dir, exist_ok=True)
        path = self._proposal_path(proposal_dir, proposal.id)
        payload_text = (
            _yaml.safe_dump(proposal.payload, sort_keys=False)
            if YAML_AVAILABLE
            else json.dumps(proposal.payload, indent=2)
        )
        record = {
            "id": proposal.id,
            "kind": proposal.kind,
            "payload": proposal.payload,
            "payload_yaml": payload_text,
            "target_file": proposal.target_file,
            "replace_ids": proposal.replace_ids,
            "protected_hits": proposal.protected_hits,
            "created_at": proposal.created_at,
            "applied": proposal.applied,
            "applied_at": proposal.applied_at,
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2)

    def load_proposal(self, proposal_dir: str, proposal_id: str) -> Proposal:
        path = self._proposal_path(proposal_dir, proposal_id)
        if not os.path.isfile(path):
            raise HAWriteError(f"Unknown proposal id: {proposal_id!r}")
        with open(path, "r", encoding="utf-8") as fh:
            record = json.load(fh)
        proposal = Proposal(
            id=record["id"],
            kind=record["kind"],
            payload=record["payload"],
            target_file=record["target_file"],
            replace_ids=record.get("replace_ids", []),
            protected_hits=record.get("protected_hits", []),
            created_at=record["created_at"],
            applied=record.get("applied", False),
            applied_at=record.get("applied_at"),
        )
        return proposal

    def apply_proposal(
        self,
        proposal: Proposal,
        *,
        confirm: bool,
    ) -> dict[str, Any]:
        """Apply a proposal to the YAML config file and reload the domain."""
        if not confirm:
            raise HAPolicyError(
                "Confirmation required. Re-run apply with confirm=true only after "
                "reviewing the proposal."
            )
        if not self.config.writes_enabled:
            raise HAWriteError(
                "Writes are disabled (HA_WRITES_ENABLED=false). Enable them only "
                "after reviewing the probe output and configuring a sandbox."
            )
        if proposal.applied:
            raise HAWriteError(f"Proposal {proposal.id} was already applied.")

        if proposal.protected_hits:
            raise HAPolicyError(
                "Proposal references protected domains/entities and cannot be "
                f"applied: {', '.join(proposal.protected_hits)}"
            )

        if not YAML_AVAILABLE:
            raise HAWriteError("PyYAML is not installed; cannot write YAML files.")

        path = proposal.target_file
        if not os.path.isfile(path):
            raise HAWriteError(
                f"Target file does not exist: {path}. Create it (and the matching "
                f"!include in configuration.yaml) manually first; the agent will "
                "not create new config files."
            )

        with open(path, "r", encoding="utf-8") as fh:
            existing = _yaml.safe_load(fh)

        merged = self._merge_definitions(existing, proposal.payload)

        # Atomic write: temp file in same directory, then replace.
        temp_path = f"{path}.tmp-{proposal.id}"
        with open(temp_path, "w", encoding="utf-8") as fh:
            _yaml.safe_dump(merged, fh, sort_keys=False, default_flow_style=False)
        os.replace(temp_path, path)

        reload_service = RELOAD_SERVICE[proposal.kind]
        result = self._request(
            "POST",
            f"/api/services/{reload_service}/reload",
            json_body=None,
        )

        proposal.applied = True
        proposal.applied_at = time.time()

        return {
            "applied": True,
            "proposal_id": proposal.id,
            "kind": proposal.kind,
            "target_file": path,
            "replace_ids": proposal.replace_ids,
            "reload_result": result,
        }
