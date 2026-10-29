# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: ttmail/tests/test_cli.py@194 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: f00dac0d87dccfcac31c1fa4fb1ab2e2612eed64 %
#  %ccm_git_commit_id: 2dece6d3d0a2907a11acbbacea79fb55ab8ce3ce %
#  %ccm_git_commit_count: 194 %
#  %ccm_git_commit_date: 2026-10-28 20:22:38 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: misc updates %
#  %ccm_git_modify_date: 2026-10-28 20:22:39 %
#  %ccm_git_file_last_modified: 2026-10-28 20:22:02 %
#  %ccm_git_file_name: test_cli.py %
#  %ccm_git_path: ttmail/tests/test_cli.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 4599 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""ttmail CLI tests: argument handling and delegation. No network."""

from __future__ import annotations

import awmail.cli
import pytest

import ttmail.cli as cli


@pytest.fixture
def seen(monkeypatch):
    """Record what ttmail told awmail, without reaching awmail's real CLI."""
    calls: list[list[str]] = []

    def fake_main(argv=None) -> int:
        calls.append(list(argv or []))
        return 0

    monkeypatch.setattr(awmail.cli, "main", fake_main)
    return calls


@pytest.fixture
def envs(monkeypatch):
    """Record load_env() arguments instead of touching the filesystem."""
    calls: list[object] = []
    monkeypatch.setattr(cli, "load_env", lambda path=None, **kw: calls.append(path))
    return calls


# -- delegation -------------------------------------------------------------
def test_passes_argv_through_unchanged(seen, envs):
    assert cli.main(["send", "me@example.com", "--subject", "hi", "--body", "-"]) == 0
    assert seen == [["send", "me@example.com", "--subject", "hi", "--body", "-"]]


def test_no_argv_uses_sys_argv(seen, envs, monkeypatch):
    monkeypatch.setattr(cli.sys, "argv", ["ttmail", "doctor"])
    assert cli.main() == 0
    assert seen == [["doctor"]]


def test_exit_code_propagates(monkeypatch, envs):
    monkeypatch.setattr(awmail.cli, "main", lambda argv=None: 2)
    assert cli.main(["send", "x@y.z"]) == 2


def test_loads_env_before_delegating(monkeypatch, seen):
    order: list[str] = []
    monkeypatch.setattr(cli, "load_env", lambda path=None, **kw: order.append("env"))
    monkeypatch.setattr(awmail.cli, "main",
                        lambda argv=None: (order.append("awmail"), 0)[1])
    cli.main(["doctor"])
    assert order == ["env", "awmail"]


# -- --env-file -------------------------------------------------------------
def test_env_file_is_taken_out_of_argv(seen, envs):
    cli.main(["--env-file", "/tmp/custom.env", "send", "me@example.com"])
    assert envs == ["/tmp/custom.env"]
    assert seen == [["send", "me@example.com"]]


def test_env_file_equals_form(seen, envs):
    cli.main(["--env-file=/tmp/custom.env", "doctor"])
    assert envs == ["/tmp/custom.env"]
    assert seen == [["doctor"]]


def test_env_file_after_subcommand_still_works(seen, envs):
    cli.main(["send", "me@example.com", "--env-file", "/tmp/e"])
    assert envs == ["/tmp/e"]
    assert seen == [["send", "me@example.com"]]


def test_no_env_file_flag_passes_none(seen, envs):
    cli.main(["doctor"])
    assert envs == [None]


def test_missing_env_file_is_a_clean_error(seen, envs, monkeypatch, capsys):
    """cron runs this: a traceback instead of a message is the bug."""
    def boom(path=None, **kw):
        raise RuntimeError(f"env file not found: {path}")

    monkeypatch.setattr(cli, "load_env", boom)
    assert cli.main(["--env-file", "/nope/missing.env", "send", "me@example.com"]) == 1
    captured = capsys.readouterr()
    assert "env file not found: /nope/missing.env" in captured.err
    assert "Traceback" not in captured.err
    assert seen == []                      # never reached awmail


def test_awmails_own_flags_are_not_eaten(seen, envs):
    """awmail has no --env-file, but its other flags must survive intact."""
    argv = ["send", "a@b.c", "d@e.f", "--subject", "x", "--body", "y"]
    cli.main(argv)
    assert seen == [argv]
    assert envs == [None]


# -- the real delegation target exists --------------------------------------
def test_awmail_exposes_a_main():
    """If upstream renames main, ttmail fails here rather than at 3am."""
    assert callable(awmail.cli.main)
