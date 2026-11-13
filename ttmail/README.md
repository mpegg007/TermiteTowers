<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: ttmail/README.md % -->
<!-- %ccm_git_object_id: ttmail/README.md@218 % -->
<!-- %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: changes 261113 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!-- tt-secrets.skip -->

# ttmail

A `.env` layer over the [`awmail`](https://pypi.org/project/awmail/) package.

`awmail` does the actual work: SMTP/IMAP, the recipient allow-list, rate caps,
loop detection, and the ACCEPTED / REFUSED / UNKNOWN verdict. `ttmail` adds two
things:

1. **A `.env` loader.** awmail reads `AWMAIL_*` from the process environment
   only; it has no dotenv support. A file keeps the bridge password out of
   systemd unit files and shell history, which matters for anything running
   unattended.
2. **A `ttmail` command** — awmail's own CLI with that `.env` loaded first, so
   scripts do not have to export anything. It is delegation, not a reimplementation.

Everything else — sending, receiving, allow-listing, rate limiting, reply-loop
refusal — stays in `awmail`. If you find yourself reimplementing one of those
here, it belongs upstream instead.

## Install

```bash
cd ttmail
cp env.example .env
chmod 600 .env
"$EDITOR" .env            # set AWMAIL_PASSWORD

../.venv/bin/pip install -e .
```

## Use

```python
from ttmail import bridge_from_env

m = bridge_from_env()                     # reads ./.env or ./ttmail/.env
result = m.send(to="me@example.com", subject="hi", body="hello")

if result.ok:                             # True only for ACCEPTED
    print(result.message_id)
else:
    print(result.status, result.detail)   # refused / unknown, and why
```

Read `result.status`, not just truthiness. `unknown` means the message may have
been delivered — retrying can duplicate it.

Check configuration without sending anything:

```python
m = bridge_from_env()
print(m.doctor())   # per-probe "ok" / "failed" / "unknown", never a bare bool
```

## Command line

`pip install -e .` puts a `ttmail` command on the path. It is awmail's command
line with `.env` loaded in front of it — same subcommands, same flags, same exit
codes. ttmail adds nothing but the `.env` load and its own `--env-file`.

```bash
ttmail send me@example.com --subject "backup failed" --body "see /var/log/x"
ttmail send me@example.com --subject "errors" --body -        # body from stdin
journalctl -p err -n 50 | ttmail send me@example.com --subject errors --body -
ttmail inbox --limit 5
ttmail reply <uid> --body "on it"
```

`--body -` reads the body from stdin. Without `--body` the body is empty, so
pipe into `--body -` explicitly rather than expecting stdin to be picked up.

Pick the `.env` file when the working directory is not the repo. On this host the
real path is the per-tier secrets root — the `.env` in `ttmail/` is a development
leftover and should not be used, because it keeps a live mail password inside the
checkout:

```bash
ttmail --env-file /etc/tt-secrets/dev1/env/ttmail.env send me@example.com --subject hi
TTMAIL_ENV_FILE=/etc/tt-secrets/dev1/env/ttmail.env ttmail send me@example.com --subject hi
```

This matters for cron and systemd, which do not run in the repo directory. With
no `.env` reachable, `load_env()` finds nothing, awmail refuses to build a
`Mailer`, and you get exit `1` with the unset variable names — not a silent
no-op.

An explicit `--env-file` that does not exist is a hard error (`ttmail: env file
not found: ...`, exit `1`) rather than a fall back to the search path. A typo in
a unit file should not quietly send as whatever the default file happens to say.

### Exit codes

Straight from awmail; scripts should branch on these, not on stdout text.

| Code | Meaning |
|---|---|
| `0` | accepted — the server took the message |
| `1` | not accepted; read the printed status |
| `2` | refused by the guard (allowlist or rate cap) — nothing was sent |

Exit `1` covers both a hard failure and `unknown`. `unknown` means the message
*may* have been delivered, so a retry loop can duplicate it. Alert on it once and
let a human look, rather than retrying.

## Alerting from scripts

The `hal@` mailbox is the intended sender for unattended notifications:

```bash
#!/usr/bin/env bash
# /usr/local/bin/hal-notify
set -uo pipefail
/opt/ttmail/.venv/bin/ttmail --env-file /etc/ttmail/prod.env \
    send "$ALERT_TO" --subject "hal: $1" --body -
```

```bash
# cron: only mail on failure
0 3 * * * /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1 || \
          echo "backup exited $?" | hal-notify "backup failed"

# systemd: OnFailure=hal-notify@%n.service
```

Two things to keep in mind for unattended use:

- awmail's rate caps (60/hour, 250/day by default) are the thing that stops a
  crash loop from filling the mailbox. Leave them on; a script that mails once
  per retry needs a guard upstream, not a higher cap.
- `AWMAIL_ALLOW` is the blast radius. `*` means a bug in a notification script
  can mail anyone. Narrow it to your own address once the setup is trusted.

## Doctor is not a connectivity check

`awmail 0.1.0` intercepts `doctor` with a generated *stack* report: it prints
which `aw*` packages are installed and pairs with awmail. It does **not** touch
SMTP, the bridge, or the allowlist, and it exits `0` even with no configuration
at all. `ttmail doctor` inherits that behaviour.

So `ttmail doctor` is not a health check for this deployment. To verify the real
send path, send yourself one message and read the status word:

```bash
echo test | ttmail send hal@termitetowers.ca --subject "[ttmail] test" --body -
# accepted accepted=hal@termitetowers.ca ...
```

`accepted` means the relay took it; delivery is decided later and elsewhere. Any
other verdict is a real problem.


Standard awmail names. None are renamed or remapped.

| Variable | Meaning |
|---|---|
| `AWMAIL_FROM` | address mail is sent as (**required**) |
| `AWMAIL_PASSWORD` | Proton **Bridge** password, not your login (**required**) |
| `AWMAIL_ALLOW` | comma-separated recipient patterns (**required**) |
| `AWMAIL_USER` | mailbox username, defaults to `AWMAIL_FROM` |
| `AWMAIL_HOST` / `AWMAIL_PORT` / `AWMAIL_IMAP_PORT` | bridge endpoint |
| `AWMAIL_SECURITY` | `starttls` (default), `ssl`, or `plain` |
| `TTMAIL_ENV_FILE` | explicit path to the `.env` file |

An **empty** `AWMAIL_ALLOW` is a refusal, not "send anywhere". awmail raises
rather than defaulting to permissive, and ttmail does not paper over that
with `*`.

Variables already exported in the environment win over the file, so a real
`export` always beats `.env`. Pass `override=True` to `load_env()` to invert
that.

`AWMAIL_HOST` and `AWMAIL_PORT` are read by `awmail.Mailer.from_env()`, not by
`Mailer.bridge()`. To point the transport elsewhere, pass `host=`/`smtp_port=`
to `bridge_from_env()`; the file alone will not move it.

## Known hazard: repr() leaks the password

awmail 0.1.0's `SmtpTransport` is a plain `@dataclass`, so `repr()` includes the
password:

```python
>>> print(m.transport)
SmtpTransport(host='127.0.0.1', ..., password='<the bridge password>', ...)
```

Never `print()`, log, or f-string a `Mailer` or its transport.
`tests/test_ttmail.py` pins this behaviour so it is noticed if upstream fixes it.

## Layout

```
ttmail/
├── src/ttmail/__init__.py   # the .env layer
├── src/ttmail/cli.py        # `ttmail` - awmail's CLI, .env loaded first
├── tests/test_ttmail.py     # 23 tests, no network
├── tests/test_cli.py        # 10 tests, no network
├── env.example
└── pyproject.toml
```

Uses the `src/` layout deliberately: with a flat layout the `ttmail/` project
directory shadows the `ttmail` package during pytest collection.
