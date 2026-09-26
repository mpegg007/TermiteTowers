#!/usr/bin/env python3
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/mcp/home-assistant/probe_ha.py:160 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 65af92ea3cef0972fb58657eeedcac4be8b5fe83 %
#  %ccm_git_commit_id: 3a0dc6d000abbf72c8996a230bc72454f05c9f1b %
#  %ccm_git_commit_count: 160 %
#  %ccm_git_commit_date: 2026-09-25 21:30:36 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: cleanup %
#  %ccm_git_modify_date: 2026-09-25 21:30:37 %
#  %ccm_git_file_last_modified: 2026-08-28 18:41:13 %
#  %ccm_git_file_name: probe_ha.py %
#  %ccm_git_path: infra/mcp/home-assistant/probe_ha.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 5710 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""
Version-specific capability probe for a running Home Assistant instance.

Run this BEFORE enabling writes. It verifies:

1. Token authentication against the REST API.
2. The Home Assistant version and core configuration.
3. Which routine types (automation/scene/script) currently exist.
4. Whether configuration files (automations.yaml, scenes.yaml, scripts.yaml)
   are reachable through HA_CONFIG_DIR and therefore writable by the agent.
5. Which service domains are available.

Exit code 0 on success, non-zero on any blocking failure.

Usage:
    HA_URL=http://homeassistant.local:8123 \
    HA_TOKEN=... \
    HA_CONFIG_DIR=/path/to/ha/config \
    python probe_ha.py
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter

from ha_client import (
    HAConfig,
    HAError,
    HomeAssistantClient,
    load_config,
    YAML_FILENAMES,
)

try:
    import yaml as _yaml
    YAML_AVAILABLE = True
except ImportError:  # pragma: no cover
    _yaml = None
    YAML_AVAILABLE = False


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> int:
    config = load_config()
    if not config.token:
        print("ERROR: HA_TOKEN is not set (or config.json has no token).")
        return 2

    client = HomeAssistantClient(config)
    print(f"Base URL : {config.base_url_clean}")
    print(f"Token    : {'configured (' + str(len(config.token)) + ' chars)'}")
    print(f"Config dir: {config.config_dir or '(not set)'}")
    print(f"Writes enabled: {config.writes_enabled}")

    try:
        info = client.get_info()
    except HAError as exc:
        print(f"ERROR: could not reach Home Assistant: {exc}")
        return 1

    section("Instance")
    print(f"Version   : {info.get('version')}")
    print(f"State     : {info.get('state')}")
    print(f"Config dir: {info.get('config_dir')}")
    print(f"Components: {len(info.get('components', []))}")

    section("Entities")
    try:
        states = client.list_states()
    except HAError as exc:
        print(f"ERROR listing states: {exc}")
        return 1
    domains = Counter(s.get("entity_id", "?").split(".", 1)[0] for s in states)
    print(f"Total entities: {len(states)}")
    for domain in ("automation", "scene", "script", "light", "switch", "lock", "alarm_control_panel"):
        if domains.get(domain):
            print(f"  {domain:<18} {domains[domain]}")

    section("Routines")
    for kind, filename in YAML_FILENAMES.items():
        count = sum(
            1 for s in states if s.get("entity_id", "").startswith(f"{kind}.")
        )
        print(f"  {kind:<12} entities={count}  file={filename}")

    section("Write path")
    if not YAML_AVAILABLE:
        print("  WARNING: PyYAML not installed; YAML read/write unavailable.")
    if config.config_dir:
        for kind, filename in YAML_FILENAMES.items():
            path = os.path.join(config.config_dir, filename)
            exists = os.path.isfile(path)
            form = "?"
            if exists and YAML_AVAILABLE:
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        raw = _yaml.safe_load(fh)
                    form = "list" if isinstance(raw, list) else (
                        "dict" if isinstance(raw, dict) else type(raw).__name__
                    )
                except Exception as exc:  # noqa: BLE001
                    form = f"unparseable ({exc})"
            print(
                f"  {filename:<18} exists={exists}  form={form}"
            )
        if not config.writes_enabled:
            print("  Writes are DISABLED. Set HA_WRITES_ENABLED=true only after")
            print("  reviewing this output and configuring a sandbox.")
    else:
        print("  HA_CONFIG_DIR is not set; the agent cannot read or write YAML")
        print("  definitions. Only inspect/operate tools will work.")

    section("Service availability")
    try:
        services = client._request("GET", "/api/services") or []
        domains = {
            service.get("domain")
            for service in services
            if isinstance(service, dict) and service.get("domain")
        }
        relevant = [
            domain
            for domain in ("scene", "script", "automation", "light", "switch")
            if domain in domains
        ]
        print(f"  Service domains available: {len(domains)}")
        print(f"  Relevant domains: {', '.join(relevant) or '(none)'}")
    except HAError as exc:
        print(f"  WARNING: could not list services: {exc}")

    print("\nProbe complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
