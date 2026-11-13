# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: ttmail/tests/test_ttmail.py@218 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 5308daa7934bbde273251339286ddb20fc8054b0 %
#  %ccm_git_commit_id: 72c0eae6bb7ccad09a6031b8cf1fff35b571a7e4 %
#  %ccm_git_commit_count: 218 %
#  %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: changes 261113 %
#  %ccm_git_modify_date: 2026-11-13 14:50:48 %
#  %ccm_git_file_last_modified: 2026-11-13 14:50:14 %
#  %ccm_git_file_name: test_ttmail.py %
#  %ccm_git_path: ttmail/tests/test_ttmail.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/plain %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 7272 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""ttmail tests: the .env loader and Mailer construction. No network."""
# tt-secrets.skip

from __future__ import annotations

import os

import pytest

from ttmail import _parse_dotenv, _resolve, bridge_from_env, load_env

CLEAN = ["AWMAIL_FROM", "AWMAIL_USER", "AWMAIL_PASSWORD", "AWMAIL_ALLOW",
         "AWMAIL_HOST", "AWMAIL_PORT", "AWMAIL_SECURITY", "TTMAIL_ENV_FILE"]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Start every test with no awmail config, so order cannot matter."""
    for key in CLEAN:
        monkeypatch.delenv(key, raising=False)


def write_env(tmp_path, body: str):
    env = tmp_path / ".env"
    env.write_text(body, encoding="utf-8")
    return env


GOOD = (
    "AWMAIL_FROM=hal@termitetowers.ca\n"
    "AWMAIL_PASSWORD=bridge-pw\n"
    "AWMAIL_ALLOW=*@example.com\n"
)


# -- parsing ----------------------------------------------------------------
def test_parse_basics():
    pairs = dict(_parse_dotenv("""
# a comment
AWMAIL_FROM=hal@termitetowers.ca
export AWMAIL_ALLOW=*@example.com   # trailing note
QUOTED="a b c"
SINGLE='literal \\n stays'
EMPTY=
NOT A PAIR
""" ))
    assert pairs["AWMAIL_FROM"] == "hal@termitetowers.ca"
    assert pairs["AWMAIL_ALLOW"] == "*@example.com"
    assert pairs["QUOTED"] == "a b c"
    assert pairs["SINGLE"] == "literal \\n stays"
    assert pairs["EMPTY"] == ""
    assert "NOT A PAIR" not in pairs


def test_parse_handles_hash_inside_quotes():
    pairs = dict(_parse_dotenv('PASSWORD="a#b"  # real comment'))
    assert pairs["PASSWORD"] == "a#b"


# -- loading ----------------------------------------------------------------
def test_load_env_reads_file(tmp_path):
    env = write_env(tmp_path, "AWMAIL_FROM=file@example.com\n")
    assert load_env(env) == env
    assert os.environ["AWMAIL_FROM"] == "file@example.com"


def test_existing_environment_wins_by_default(tmp_path, monkeypatch):
    env = write_env(tmp_path, "AWMAIL_FROM=file@example.com\n")
    monkeypatch.setenv("AWMAIL_FROM", "shell@example.com")
    load_env(env)
    assert os.environ["AWMAIL_FROM"] == "shell@example.com"


def test_override_wins_when_asked(tmp_path, monkeypatch):
    env = write_env(tmp_path, "AWMAIL_FROM=file@example.com\n")
    monkeypatch.setenv("AWMAIL_FROM", "shell@example.com")
    load_env(env, override=True)
    assert os.environ["AWMAIL_FROM"] == "file@example.com"


def test_missing_explicit_file_raises(tmp_path):
    with pytest.raises(RuntimeError):
        load_env(tmp_path / "nope.env")


def test_missing_ttmail_env_file_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("TTMAIL_ENV_FILE", str(tmp_path / "gone.env"))
    with pytest.raises(RuntimeError):
        load_env()


def test_no_file_is_not_an_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert load_env() is None


def test_finds_dot_env_in_cwd(tmp_path, monkeypatch):
    write_env(tmp_path, "AWMAIL_FROM=cwd@example.com\n")
    monkeypatch.chdir(tmp_path)
    assert _resolve(None) == tmp_path / ".env"


def test_finds_dot_env_in_ttmail_subdir(tmp_path, monkeypatch):
    (tmp_path / "ttmail").mkdir()
    write_env(tmp_path / "ttmail", "AWMAIL_FROM=sub@example.com\n")
    monkeypatch.chdir(tmp_path)
    assert _resolve(None) == tmp_path / "ttmail" / ".env"


def test_does_not_walk_up_parents(tmp_path, monkeypatch):
    """A parent .env must not be picked up from a child directory."""
    write_env(tmp_path, "AWMAIL_FROM=parent@example.com\n")
    child = tmp_path / "child"
    child.mkdir()
    monkeypatch.chdir(child)
    assert load_env() is None


def test_unreadable_file_raises(tmp_path):
    env = write_env(tmp_path, "AWMAIL_FROM=a@b.ca\n")
    env.chmod(0o000)
    try:
        with pytest.raises(RuntimeError):
            load_env(env)
    finally:
        env.chmod(0o600)


# -- building a Mailer ------------------------------------------------------
def test_bridge_from_env(tmp_path):
    m = bridge_from_env(write_env(tmp_path, GOOD))
    assert m.sender == "hal@termitetowers.ca"
    assert m.transport.username == "hal@termitetowers.ca"
    assert m.transport.password == "bridge-pw"
    assert m.guard.allow == ["*@example.com"]


def test_allow_is_split_on_commas(tmp_path):
    body = GOOD.replace("*@example.com", "a@example.com, b@example.com")
    m = bridge_from_env(write_env(tmp_path, body))
    assert m.guard.allow == ["a@example.com", "b@example.com"]


def test_empty_allowlist_is_not_invented(tmp_path):
    """A missing allowlist must not be papered over with '*'."""
    from awmail import RefusedError

    body = "AWMAIL_FROM=a@b.ca\nAWMAIL_PASSWORD=pw\n"
    m = bridge_from_env(write_env(tmp_path, body))
    assert m.guard.allow == []
    with pytest.raises(RefusedError):
        m.send(to="anyone@example.com", subject="s", body="b")


def test_missing_password_does_not_authenticate(tmp_path):
    body = "AWMAIL_FROM=a@b.ca\nAWMAIL_ALLOW=*\n"
    m = bridge_from_env(write_env(tmp_path, body))
    assert m.transport.password == ""


def test_empty_sender_is_left_empty(tmp_path):
    body = "AWMAIL_PASSWORD=pw\nAWMAIL_ALLOW=*\n"
    m = bridge_from_env(write_env(tmp_path, body))
    assert m.sender == ""


def test_allow_override_beats_env(tmp_path):
    m = bridge_from_env(write_env(tmp_path, GOOD), allow=["me@example.com"])
    assert m.guard.allow == ["me@example.com"]


def test_overrides_reach_the_transport(tmp_path):
    m = bridge_from_env(write_env(tmp_path, GOOD), imap_port=1143)
    assert m.receiver is not None
    assert m.receiver.port == 1143


def test_receive_false_gives_send_only(tmp_path):
    m = bridge_from_env(write_env(tmp_path, GOOD), receive=False)
    assert m.receiver is None
    from awmail import MailError
    with pytest.raises(MailError):
        m.inbox()


def test_host_and_port_come_from_env(tmp_path):
    body = GOOD + "AWMAIL_HOST=127.0.0.1\nAWMAIL_PORT=1026\n"
    # AWMAIL_HOST/PORT are read by from_env(), not bridge(); ttmail passes
    # endpoints as overrides so a file alone cannot move the transport.
    m = bridge_from_env(write_env(tmp_path, body))
    assert m.transport.host == "127.0.0.1"


# -- the password must not leak through repr --------------------------------
def test_upstream_repr_leaks_password_known_hazard():
    """Known awmail 0.1.0 defect, pinned so we notice if upstream fixes it.

    `SmtpTransport` is a plain @dataclass, so repr() includes the password.
    Any log line, f-string or traceback that formats one discloses it. This
    asserts the leak EXISTS; if it starts failing, upstream fixed it.
    """
    from awmail import Mailer, SmtpTransport

    t = SmtpTransport.bridge("u@example.com", "super-secret-value")
    assert "super-secret-value" in repr(t)

    m = Mailer.bridge(sender="u@example.com", username="u@example.com",
                      password="super-secret-value", allow=["*"], receive=False)
    assert "super-secret-value" in repr(m)


def test_ttmail_loads_password_without_echoing_it(tmp_path):
    """load_env returns a path, and its logging names no values."""
    secret = "super-secret-value"
    env = write_env(tmp_path, f"AWMAIL_PASSWORD={secret}\n" + GOOD)
    path = load_env(env)
    assert path == env
    assert os.environ["AWMAIL_PASSWORD"] == secret
    assert secret not in str(path)
