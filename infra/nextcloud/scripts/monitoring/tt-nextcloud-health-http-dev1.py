#!/usr/bin/env python3
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/nextcloud/scripts/monitoring/tt-nextcloud-health-http-dev1.py@200 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: a713698f2724050c6c04a4564c7bc9668e23b29e %
#  %ccm_git_commit_id: 07c638fcfb4804b40c226db94358725a8b6ef636 %
#  %ccm_git_commit_count: 200 %
#  %ccm_git_commit_date: 2026-11-09 10:16:57 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: zoo.261109 %
#  %ccm_git_modify_date: 2026-11-09 10:16:58 %
#  %ccm_git_file_last_modified: 2026-11-09 09:03:55 %
#  %ccm_git_file_name: tt-nextcloud-health-http-dev1.py %
#  %ccm_git_path: infra/nextcloud/scripts/monitoring/tt-nextcloud-health-http-dev1.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 8606 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""
Nextcloud health endpoint for Uptime Kuma. Listens on 127.0.0.1:9002.

Same shape as tt-kea-health-http-dev1.py: a tiny HTTP endpoint that does the
deep checks a plain URL monitor cannot, and answers pass/fail. Kuma polls it.

Checks, each returning pass / warn / fail with a one-line detail:

  container   docker inspect: state running, health status healthy
  web         GET http://127.0.0.1:3230/status.php: installed, not maintenance
  database    config.php dbtype is pgsql -- the one check that proves the instance
              is not quietly back on SQLite
  dataset     ZFS refquota usage on gallery/nextcloud: warn >= 85%, fail >= 95%
  log         application log size: warn > 200 MB (Nextcloud rotates at 100 MB)
  perms       /gallery/nextcloud/data is group tt-ai-storage with setgid, which is
              what makes the files readable by jottad

Responses:
  HTTP 200  nothing failed  (body status "ok" or "degraded")
  HTTP 503  at least one check failed

Body is JSON. A Kuma "keyword" monitor should look for:  "status": "ok"

No third-party dependencies -- stdlib only, so it runs under the distro python3.

Environment overrides:
  NC_HEALTH_BIND          default 127.0.0.1. Set to 10.10.64.1 to let the
                          Uptime Kuma container reach it -- that address is the
                          host side of monitor-apps-net-dev1, so Kuma can
                          connect while the LAN cannot
  NC_HEALTH_PORT          default 9002
  NC_HEALTH_WARN_PCT      default 85
  NC_HEALTH_FAIL_PCT      default 95
  NC_HEALTH_LOG_WARN_MB   default 200
"""

import grp
import json
import os
import stat
import subprocess
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CONTAINER = "nextcloud-dev1"
STATUS_URL = "http://127.0.0.1:3230/status.php"
DATA_DIR = "/gallery/nextcloud/data"
DATASET = "gallery/nextcloud"
LOG_FILE = "/mnt/ai_storage/nextcloud/log/nextcloud.log"
STORAGE_GROUP = "tt-ai-storage"

BIND = os.environ.get("NC_HEALTH_BIND", "127.0.0.1")
PORT = int(os.environ.get("NC_HEALTH_PORT", "9002"))
WARN_PCT = float(os.environ.get("NC_HEALTH_WARN_PCT", "85"))
FAIL_PCT = float(os.environ.get("NC_HEALTH_FAIL_PCT", "95"))
LOG_WARN_MB = float(os.environ.get("NC_HEALTH_LOG_WARN_MB", "200"))

UNITS = {"K": 1 << 10, "M": 1 << 20, "G": 1 << 30, "T": 1 << 40, "P": 1 << 50}


def run(cmd, timeout=15):
    """Run a command, return (rc, stdout+stderr). Never raises."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as exc:  # timeout, missing binary, permission
        return 1, str(exc)


def to_bytes(value):
    """'1.46T' -> bytes. Returns None for '-', 'none', ''."""
    value = (value or "").strip()
    if not value or value in ("-", "none"):
        return None
    suffix = value[-1].upper()
    if suffix in UNITS:
        try:
            return int(float(value[:-1]) * UNITS[suffix])
        except ValueError:
            return None
    try:
        return int(float(value))
    except ValueError:
        return None


def check_container():
    rc, out = run([
        "docker", "inspect", "-f",
        "{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",
        CONTAINER,
    ])
    if rc != 0:
        return "fail", f"cannot inspect {CONTAINER}: {out.strip()[:200]}"
    state, _, health = out.strip().partition("|")
    if state != "running":
        return "fail", f"container state is {state}"
    if health not in ("healthy", "none"):
        return "fail", f"container health is {health}"
    return "pass", f"running, health {health}"


def check_web():
    try:
        with urllib.request.urlopen(STATUS_URL, timeout=10) as resp:
            payload = json.loads(resp.read().decode())
    except Exception as exc:
        return "fail", f"/status.php unreachable: {exc}"
    if not payload.get("installed"):
        return "fail", "instance reports installed=false"
    if payload.get("maintenance"):
        return "fail", "instance is in maintenance mode"
    if payload.get("needsDbUpgrade"):
        return "fail", "instance needs a database upgrade"
    return "pass", f"installed, version {payload.get('versionstring', '?')}"


def check_database():
    php = (
        '$CONFIG=[]; require "/var/www/html/config/config.php";'
        'echo isset($CONFIG["dbtype"]) ? $CONFIG["dbtype"] : "unset";'
    )
    rc, out = run(["docker", "exec", CONTAINER, "php", "-r", php])
    if rc != 0:
        return "fail", f"cannot read config.php: {out.strip()[:200]}"
    dbtype = out.strip()
    if dbtype != "pgsql":
        return "fail", f"dbtype is {dbtype!r}, expected 'pgsql'"
    return "pass", "dbtype pgsql"


def check_dataset():
    rc, out = run(["zfs", "list", "-H", "-o", "used,avail,refquota", DATASET])
    if rc != 0:
        return "fail", f"cannot read {DATASET}: {out.strip()[:200]}"
    parts = out.split()
    if len(parts) < 3:
        return "fail", f"unexpected zfs output: {out.strip()[:120]}"
    used, avail, quota = parts[0], parts[1], parts[2]
    used_b, quota_b = to_bytes(used), to_bytes(quota)
    if used_b is None:
        return "fail", f"unparsable used value {used!r}"
    if quota_b:
        pct = used_b * 100.0 / quota_b
    else:
        # No refquota: fall back to pool headroom so the check still means something.
        avail_b = to_bytes(avail)
        total = used_b + (avail_b or 0)
        if not total:
            return "warn", f"{used} used, pool usage unknown"
        pct = used_b * 100.0 / total
    detail = f"{used} of {quota} used ({pct:.1f}%)"
    if pct >= FAIL_PCT:
        return "fail", detail
    if pct >= WARN_PCT:
        return "warn", detail
    return "pass", detail


def check_log():
    try:
        size = os.stat(LOG_FILE).st_size
    except FileNotFoundError:
        return "warn", "log file not present yet"
    except OSError as exc:
        return "warn", f"cannot stat log: {exc}"
    mb = size / (1 << 20)
    if mb > LOG_WARN_MB:
        return "warn", f"{mb:.1f} MB, above {LOG_WARN_MB:.0f} MB -- rotation may be failing"
    return "pass", f"{mb:.1f} MB"


def check_perms():
    try:
        st = os.stat(DATA_DIR)
    except OSError as exc:
        return "fail", f"cannot stat {DATA_DIR}: {exc}"
    try:
        expected_gid = grp.getgrnam(STORAGE_GROUP).gr_gid
    except KeyError:
        return "fail", f"group {STORAGE_GROUP} does not exist"
    problems = []
    if st.st_gid != expected_gid:
        problems.append(f"group is gid {st.st_gid}, expected {STORAGE_GROUP} ({expected_gid})")
    if not st.st_mode & stat.S_ISGID:
        problems.append("setgid bit is missing")
    if problems:
        return "fail", "; ".join(problems)
    return "pass", f"group {STORAGE_GROUP}, setgid set"


CHECKS = [
    ("container", check_container),
    ("web", check_web),
    ("database", check_database),
    ("dataset", check_dataset),
    ("log", check_log),
    ("perms", check_perms),
]


def collect():
    results = {}
    worst = "pass"
    for name, fn in CHECKS:
        try:
            state, detail = fn()
        except Exception as exc:  # a bug in one check must not blind the others
            state, detail = "fail", f"check raised: {exc}"
        results[name] = {"state": state, "detail": detail}
        if state == "fail":
            worst = "fail"
        elif state == "warn" and worst == "pass":
            worst = "warn"
    status = {"pass": "ok", "warn": "degraded", "fail": "fail"}[worst]
    return status, results


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        status, results = collect()
        body = json.dumps(
            {"status": status, "container": CONTAINER, "checks": results},
            indent=2,
            sort_keys=True,
        ).encode()
        code = 200 if status in ("ok", "degraded") else 503
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Keep the journal readable: one line per request, to stdout.
        sys.stdout.write("%s - %s\n" % (self.address_string(), fmt % args))


def main():
    server = ThreadingHTTPServer((BIND, PORT), Handler)
    sys.stdout.write(f"nextcloud health endpoint on {BIND}:{PORT}\n")
    sys.stdout.flush()
    server.serve_forever()


if __name__ == "__main__":
    main()
