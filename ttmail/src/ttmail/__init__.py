# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: ttmail/src/ttmail/__init__.py@218 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: f6171e6a10905b2abdcb1ad3760ef92a2e8e2a5c %
#  %ccm_git_commit_id: 72c0eae6bb7ccad09a6031b8cf1fff35b571a7e4 %
#  %ccm_git_commit_count: 218 %
#  %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: changes 261113 %
#  %ccm_git_modify_date: 2026-11-13 14:50:48 %
#  %ccm_git_file_last_modified: 2026-11-13 14:49:15 %
#  %ccm_git_file_name: __init__.py %
#  %ccm_git_path: ttmail/src/ttmail/__init__.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/plain %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 5802 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""ttmail -- a `.env` layer over the `awmail` package.

tt-secrets.skip

awmail does the actual work: SMTP/IMAP, the recipient allow-list, rate caps,
loop detection, and the ACCEPTED/REFUSED/UNKNOWN verdict. This module adds two
things and nothing else:

  A `.env` loader. awmail reads AWMAIL_* from the process environment only; it
  has no dotenv support. Cron jobs and systemd units are much easier with a
  file, and a file keeps the bridge password out of unit files and shell
  history.

  A `ttmail` command (`ttmail.cli`). It loads that `.env`, then hands the whole
  command line to awmail's own CLI -- same subcommands, flags and exit codes.

Deliberately NOT wrapped: sending, receiving, allow-listing, rate limiting, and
reply-loop refusal all stay in awmail. If you find yourself reimplementing one
of those here, it belongs upstream instead.

    from ttmail import bridge_from_env

    m = bridge_from_env()                     # reads ./.env, or $TTMAIL_ENV_FILE
    result = m.send(to="me@example.com", subject="hi", body="hello")
    if result.ok:                             # True only for ACCEPTED
        print(result.message_id)
    else:
        print(result.status, result.detail)   # refused / unknown, and why
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from awmail import Limits, Mailer  # re-exported for callers

__all__ = ["bridge_from_env", "load_env", "Limits", "Mailer"]

log = logging.getLogger("ttmail")


def load_env(path: str | os.PathLike[str] | None = None, *,
             override: bool = False) -> Path | None:
    """Load KEY=value pairs from a .env file into os.environ.

    Resolution order: explicit ``path``, then ``$TTMAIL_ENV_FILE``, then
    ``./.env``, then ``./ttmail/.env``. It never walks up parent directories, so
    an unrelated ``/.env`` cannot be picked up.

    Variables already present in the environment win unless ``override=True``,
    so a real export always beats the file.

    A file missing at an explicitly given path raises; a file missing from the
    fallback locations is not an error.
    """
    resolved = _resolve(path)
    if resolved is None:
        log.debug("no .env file found")
        return None

    try:
        text = resolved.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"cannot read env file {resolved}: {exc}") from exc

    loaded = 0
    for key, value in _parse_dotenv(text):
        if override or key not in os.environ:
            os.environ[key] = value
            loaded += 1
    log.debug("loaded %d variable(s) from %s", loaded, resolved)
    return resolved


def _resolve(path: str | os.PathLike[str] | None) -> Path | None:
    if path is not None:
        candidate = Path(path).expanduser()
        if not candidate.is_file():
            raise RuntimeError(f"env file not found: {candidate}")
        return candidate

    explicit = os.environ.get("TTMAIL_ENV_FILE", "").strip()
    if explicit:
        candidate = Path(explicit).expanduser()
        if not candidate.is_file():
            raise RuntimeError(f"TTMAIL_ENV_FILE points at a missing file: {candidate}")
        return candidate

    cwd = Path.cwd()
    for candidate in (cwd / ".env", cwd / "ttmail" / ".env"):
        if candidate.is_file():
            return candidate
    return None


def _parse_dotenv(text: str):
    """Yield (key, value). Supports export, comments, and quoted values."""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not key:
            continue
        # Quoting is decided BEFORE comment-stripping: a '#' inside quotes is
        # part of the value, and a trailing comment after closing quotes is not.
        if value[:1] in {"'", '"'}:
            quote, rest = value[0], value[1:]
            end = rest.find(quote)
            if end == -1:                 # unterminated: take the rest literally
                value = rest
            else:
                value = rest[:end]
                if quote == '"':
                    value = value.encode("utf-8").decode("unicode_escape")
        else:
            value = value.split(" #", 1)[0].rstrip()
        yield key, value


def bridge_from_env(env_file: str | os.PathLike[str] | None = None, **overrides) -> Mailer:
    """Build an awmail Mailer for the local Proton Bridge, reading .env first.

    Args:
        env_file: Explicit .env path; otherwise the usual search applies.
        **overrides: Passed through to ``Mailer.bridge``, e.g. ``allow=["*"]``
            or ``receive=False``.

    Raises:
        awmail.MailError: configuration is incomplete (notably a missing
            AWMAIL_ALLOW or password). awmail names which variables are unset.
    """
    path = load_env(env_file)
    if path is not None:
        log.debug("configuration read from %s", path)

    allow = overrides.pop("allow", None)
    if allow is None:
        raw = os.environ.get("AWMAIL_ALLOW", "").strip()
        # awmail fails closed on an empty allowlist; do not paper over it by
        # inventing "*". A missing allowlist must look like a missing allowlist.
        allow = [p.strip() for p in raw.split(",") if p.strip()]

    return Mailer.bridge(
        sender=os.environ.get("AWMAIL_FROM", "").strip(),
        username=(os.environ.get("AWMAIL_USER") or
                  os.environ.get("AWMAIL_FROM", "")).strip(),
        password=os.environ.get("AWMAIL_PASSWORD", ""),
        allow=allow,
        **overrides,
    )
