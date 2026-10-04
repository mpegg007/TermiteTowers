#!/usr/bin/env python3
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/mcp/home-assistant/test_server.py:160 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 3cd91b395e2661f6710b4a172456a1d27933b4e7 %
#  %ccm_git_commit_id: 3a0dc6d000abbf72c8996a230bc72454f05c9f1b %
#  %ccm_git_commit_count: 160 %
#  %ccm_git_commit_date: 2026-09-25 21:30:36 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: cleanup %
#  %ccm_git_modify_date: 2026-09-25 21:30:37 %
#  %ccm_git_file_last_modified: 2026-08-27 19:26:25 %
#  %ccm_git_file_name: test_server.py %
#  %ccm_git_path: infra/mcp/home-assistant/test_server.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 7880 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""
Unit tests for the Home Assistant MCP server client.

Uses mocked Home Assistant responses; no live instance is required.
Run: python -m unittest test_server -v
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import patch

import yaml as _yaml

from ha_client import (
    HAConfig,
    HAPolicyError,
    HAWriteError,
    HomeAssistantClient,
)


def make_config(tmpdir: str, **overrides) -> HAConfig:
    kwargs = dict(
        base_url="http://ha.example",
        token="test-token",
        config_dir=tmpdir,
        writes_enabled=False,
    )
    kwargs.update(overrides)
    return HAConfig(**kwargs)


class PolicyTests(unittest.TestCase):
    def test_refuses_protected_service_domain(self):
        client = HomeAssistantClient(make_config(tempfile.mkdtemp()))
        with self.assertRaises(HAPolicyError):
            client.call_service("lock", "lock", "lock.front_door")

    def test_refuses_protected_entity(self):
        client = HomeAssistantClient(make_config(tempfile.mkdtemp()))
        with self.assertRaises(HAPolicyError):
            client.call_service("light", "turn_on", "lock.front_door")

    def test_refuses_unallowed_domain(self):
        client = HomeAssistantClient(make_config(tempfile.mkdtemp()))
        with self.assertRaises(HAPolicyError):
            client.call_service("config", "save")

    def test_allows_normal_service(self):
        client = HomeAssistantClient(make_config(tempfile.mkdtemp()))
        with patch.object(client, "_request", return_value=[{"entity_id": "light.x"}]) as req:
            result = client.call_service("light", "turn_on", "light.office")
            self.assertEqual(result, [{"entity_id": "light.x"}])
            req.assert_called_once()

    def test_protected_entity_config_respected(self):
        cfg = make_config(tempfile.mkdtemp(), protected_entities=["switch.garage_door"])
        client = HomeAssistantClient(cfg)
        with self.assertRaises(HAPolicyError):
            client.call_service("switch", "turn_on", "switch.garage_door")


class ProposalTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.proposal_dir = tempfile.mkdtemp()

    def _client(self, **overrides) -> HomeAssistantClient:
        return HomeAssistantClient(make_config(self.tmpdir, **overrides))

    def test_propose_persists_draft(self):
        client = self._client()
        proposal = client.propose(
            "automation",
            {"id": "abc", "alias": "Test", "trigger": [], "action": []},
            self.proposal_dir,
        )
        self.assertTrue(proposal.id)
        self.assertEqual(proposal.kind, "automation")
        self.assertTrue(
            os.path.isfile(os.path.join(self.proposal_dir, f"{proposal.id}.json"))
        )

    def test_apply_requires_confirm(self):
        client = self._client(writes_enabled=True)
        proposal = client.propose(
            "automation", {"id": "x", "alias": "X", "trigger": [], "action": []},
            self.proposal_dir,
        )
        with self.assertRaises(HAPolicyError):
            client.apply_proposal(proposal, confirm=False)

    def test_apply_requires_writes_enabled(self):
        client = self._client(writes_enabled=False)
        proposal = client.propose(
            "automation", {"id": "x", "alias": "X", "trigger": [], "action": []},
            self.proposal_dir,
        )
        with self.assertRaises(HAWriteError):
            client.apply_proposal(proposal, confirm=True)

    def test_apply_refuses_protected_hits(self):
        client = self._client(writes_enabled=True)
        proposal = client.propose(
            "automation",
            {
                "id": "x",
                "alias": "X",
                "trigger": [],
                "action": [{"service": "lock.lock", "target": {"entity_id": "lock.front"}}],
            },
            self.proposal_dir,
        )
        self.assertTrue(proposal.protected_hits)
        with self.assertRaises(HAPolicyError):
            client.apply_proposal(proposal, confirm=True)

    def test_apply_writes_file_and_reloads(self):
        path = os.path.join(self.tmpdir, "automations.yaml")
        with open(path, "w", encoding="utf-8") as fh:
            _yaml.safe_dump(
                [{"id": "old", "alias": "Old", "trigger": [], "action": []}], fh
            )

        client = self._client(writes_enabled=True)
        proposal = client.propose(
            "automation",
            {"id": "new", "alias": "New", "trigger": [], "action": []},
            self.proposal_dir,
        )

        with patch.object(client, "_request", return_value={}) as req:
            result = client.apply_proposal(proposal, confirm=True)
            self.assertTrue(result["applied"])

        with open(path, "r", encoding="utf-8") as fh:
            merged = _yaml.safe_load(fh)
        ids = {item["id"] for item in merged}
        self.assertEqual(ids, {"old", "new"})

    def test_apply_refuses_when_file_missing(self):
        client = self._client(writes_enabled=True)
        proposal = client.propose(
            "scene", {"id": "s", "name": "S", "entities": {}}, self.proposal_dir
        )
        with self.assertRaises(HAWriteError):
            client.apply_proposal(proposal, confirm=True)


class MergeTests(unittest.TestCase):
    def test_merge_list_replace_by_id(self):
        client = HomeAssistantClient(make_config(tempfile.mkdtemp()))
        existing = [{"id": "a", "alias": "A"}, {"id": "b", "alias": "B"}]
        additions = [{"id": "a", "alias": "A2"}]
        merged = client._merge_definitions(existing, additions)
        aliases = {item["id"]: item.get("alias") for item in merged}
        self.assertEqual(aliases["a"], "A2")
        self.assertIn("b", aliases)

    def test_merge_dict_for_scripts(self):
        client = HomeAssistantClient(make_config(tempfile.mkdtemp()))
        existing = {"morning": {"alias": "Morning", "sequence": []}}
        additions = [{"id": "evening", "alias": "Evening", "sequence": []}]
        merged = client._merge_definitions(existing, additions)
        self.assertIn("morning", merged)
        self.assertIn("evening", merged)


class InfoTests(unittest.TestCase):
    def test_get_info_parses_version(self):
        client = HomeAssistantClient(make_config(tempfile.mkdtemp()))
        with patch.object(
            client,
            "_request",
            side_effect=[
                {"message": "API running."},
                {"version": "2026.7.0", "components": ["light"], "config_dir": "/config"},
            ],
        ):
            info = client.get_info()
        self.assertEqual(info["version"], "2026.7.0")
        self.assertEqual(info["message"], "API running.")


if __name__ == "__main__":
    unittest.main()
