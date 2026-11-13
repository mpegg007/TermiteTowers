#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/system/enable-docker-metrics.sh@218 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 779d4cba02175aa6198cce8b3a84eefbadf402e7 %
#  %ccm_git_commit_id: 72c0eae6bb7ccad09a6031b8cf1fff35b571a7e4 %
#  %ccm_git_commit_count: 218 %
#  %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: changes 261113 %
#  %ccm_git_modify_date: 2026-11-13 14:50:47 %
#  %ccm_git_file_last_modified: 2026-11-13 14:49:39 %
#  %ccm_git_file_name: enable-docker-metrics.sh %
#  %ccm_git_path: scripts/system/enable-docker-metrics.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 5181 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# TermiteTowers — enable Docker engine metrics for Prometheus.
#
# WHAT IT CHANGES
#   Adds "metrics-addr": "172.17.0.1:9323" to /etc/docker/daemon.json, which is
#   what the `docker` scrape job in infra/docker/prometheus/prometheus.yml
#   expects. Without it that job is permanently down and no container alert can
#   ever fire.
#
# WHY 172.17.0.1 AND NOT 0.0.0.0
#   The endpoint has no authentication. 172.17.0.1 is the docker0 gateway, so it
#   is reachable from containers on any bridge and is NOT reachable from the LAN.
#   Binding 0.0.0.0 would publish container inventory to every device on the
#   network.
#
# WHAT IT DOES NOT DO
#   It does not restart Docker. A restart stops every container on the host, so
#   that decision stays with a human: the script prints the command and exits.
#
# USAGE
#   scripts/system/enable-docker-metrics.sh --check    # report only, no writes
#   sudo scripts/system/enable-docker-metrics.sh       # write daemon.json
#
# EXIT
#   0  already configured, or written successfully
#   1  prerequisites failed
#   2  usage error
#
# daemon.json is backed up to /etc/docker/daemon.json.bak-<timestamp> before any
# write, and the resulting file is validated with dockerd --validate when the
# flag is supported.

set -Eeuo pipefail

DAEMON_JSON="/etc/docker/daemon.json"
METRICS_ADDR="172.17.0.1:9323"
CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1
[ -z "${1:-}" ] || [ "$1" = "--check" ] || { echo "usage: $0 [--check]" >&2; exit 2; }

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
log() { printf '%s\n' "$*" >&2; }

command -v python3 >/dev/null || die "python3 not found"

current_addr="$(python3 - "$DAEMON_JSON" <<'PY'
import json, os, sys

path = sys.argv[1]
if not os.path.exists(path):
    print("")
    raise SystemExit
try:
    with open(path) as fh:
        doc = json.load(fh)
except (OSError, json.JSONDecodeError) as exc:
    print(f"__invalid__:{exc}")
    raise SystemExit
print((doc or {}).get("metrics-addr", ""))
PY
)"

case "$current_addr" in
    __invalid__*)
        die "${DAEMON_JSON} is not valid JSON (${current_addr#__invalid__:}); fix it by hand first"
        ;;
esac

if [ "$current_addr" = "$METRICS_ADDR" ]; then
    log "already configured: metrics-addr = ${METRICS_ADDR}"
    log ""
    log "Verify with:"
    log "  curl -s http://${METRICS_ADDR}/metrics | head"
    log "  scripts/deploy-prometheus.sh verify"
    exit 0
fi

if [ -n "$current_addr" ]; then
    log "metrics-addr is currently '${current_addr}' (expected '${METRICS_ADDR}')"
else
    log "metrics-addr is not set"
fi

if [ "$CHECK_ONLY" -eq 1 ]; then
    log ""
    log "--check: no changes made. Re-run with sudo to apply."
    exit 0
fi

[ "$(id -u)" -eq 0 ] || die "must run as root to write ${DAEMON_JSON}"

backup="${DAEMON_JSON}.bak-$(date +%Y%m%d-%H%M%S)"
if [ -f "$DAEMON_JSON" ]; then
    cp -a "$DAEMON_JSON" "$backup"
    log "backed up to ${backup}"
else
    install -d -m 0755 /etc/docker
    log "created ${DAEMON_JSON} (it did not exist)"
fi

python3 - "$DAEMON_JSON" "$METRICS_ADDR" <<'PY'
import json, os, sys

path, addr = sys.argv[1], sys.argv[2]
doc = {}
if os.path.exists(path) and os.path.getsize(path):
    with open(path) as fh:
        doc = json.load(fh)
doc["metrics-addr"] = addr
tmp = path + ".tmp"
with open(tmp, "w") as fh:
    json.dump(doc, fh, indent=2)
    fh.write("\n")
os.replace(tmp, path)
PY

log "wrote metrics-addr = ${METRICS_ADDR} to ${DAEMON_JSON}"

# Validate before the human restarts. Old dockerd versions lack --validate, so a
# failure to support the flag is not treated as a config failure.
if dockerd --validate --config-file "$DAEMON_JSON" >/dev/null 2>&1; then
    log "dockerd --validate: OK"
else
    log "dockerd --validate unavailable or reported a problem; check ${DAEMON_JSON} before restarting"
fi

log ""
log "Docker must be restarted to apply. This stops EVERY container on the host:"
log "  sudo systemctl restart docker"
log ""
log "Then:"
log "  docker ps --format '{{.Names}}' | wc -l     # confirm everything came back"
log "  scripts/deploy-prometheus.sh verify"
