# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: ttmail/src/ttmail/cli.py@194 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 8783724abc4346a1a0b686a703ba871354066950 %
#  %ccm_git_commit_id: 2dece6d3d0a2907a11acbbacea79fb55ab8ce3ce %
#  %ccm_git_commit_count: 194 %
#  %ccm_git_commit_date: 2026-10-28 20:22:38 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: misc updates %
#  %ccm_git_modify_date: 2026-10-28 20:22:39 %
#  %ccm_git_file_last_modified: 2026-10-28 20:22:02 %
#  %ccm_git_file_name: cli.py %
#  %ccm_git_path: ttmail/src/ttmail/cli.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 3415 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""ttmail on the command line: awmail's command line, with `.env` in front.

    ttmail doctor
    ttmail send me@example.com --subject "backup failed" --body -
    journalctl -p err -n 50 | ttmail send me@example.com --subject errors --body -

Every subcommand, flag and exit code here is awmail's (`send`, `doctor`,
`inbox`, `reply`). ttmail adds no verbs and no sending behaviour of its own --
the one thing it adds is the `.env` load awmail does not do, so a cron job or a
systemd unit can send mail without the bridge password being exported into it.

Exit codes are awmail's, unchanged:

    0   accepted -- the server took the message
    1   not accepted; read the printed status. `unknown` means it may have been
        delivered, so do not blindly retry it
    2   refused by the guard (allowlist or rate cap); nothing was sent
"""
from __future__ import annotations

import argparse
import sys

from ttmail import load_env

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    """Load `.env`, then hand the rest of the command line to awmail.

    Variables already exported in the environment still win over the file, so
    an explicit ``export`` always beats `.env`.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    env_file, rest = _split_env_file(argv)

    try:
        load_env(env_file)
    except RuntimeError as exc:
        # A missing --env-file is a configuration mistake, not a crash, and this
        # runs from cron: a traceback here is noise in the failure email.
        print("ttmail: " + str(exc), file=sys.stderr)
        return 1

    # Imported late so `ttmail --help` does not pay for awmail's import, and so
    # a broken install names the missing package instead of failing at startup.
    from awmail.cli import main as awmail_main

    return awmail_main(rest)


def _split_env_file(argv: list[str]) -> tuple[str | None, list[str]]:
    """Take ttmail's own ``--env-file`` out of argv, leaving awmail's flags intact."""
    parser = argparse.ArgumentParser(prog="ttmail", add_help=False)
    parser.add_argument("--env-file", default=None, metavar="PATH",
                        help="path to the .env file (default: $TTMAIL_ENV_FILE, "
                             "./.env, ./ttmail/.env)")
    known, rest = parser.parse_known_args(argv)
    return known.env_file, rest


if __name__ == "__main__":
    sys.exit(main())
