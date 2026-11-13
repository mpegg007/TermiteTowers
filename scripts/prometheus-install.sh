#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/prometheus-install.sh@218 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 152581d7bf257fcc043f12ff1fed71e541817038 %
#  %ccm_git_commit_id: 72c0eae6bb7ccad09a6031b8cf1fff35b571a7e4 %
#  %ccm_git_commit_count: 218 %
#  %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: changes 261113 %
#  %ccm_git_modify_date: 2026-11-13 14:50:47 %
#  %ccm_git_file_last_modified: 2026-11-13 14:49:39 %
#  %ccm_git_file_name: prometheus-install.sh %
#  %ccm_git_path: scripts/prometheus-install.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 5544 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# TermiteTowers — one-command install/update of the Prometheus stack (dev1).
#
#   sudo scripts/prometheus-install.sh
#
# Idempotent: safe to re-run. Does everything the manual runbook listed:
#   dirs, htpasswd, nginx, both containers, docker metrics, systemd timers,
#   one metrics emission, then validate -> reload -> verify.
#
# Flags:
#   --check                 report what would change, make no changes
#   --restart-docker        also restart Docker (needed for metrics-addr; stops
#                           every container on the host, so opt-in)
#
# Nothing here writes secrets into the repo. The htpasswd file lives in /etc.

set -Eeuo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STORAGE=/mnt/ai_storage/prometheus
TEXTFILE="${STORAGE}/textfile"
HTPASSWD=/etc/nginx/htpasswd-prometheus
USER_ID=2001
GROUP_ID=1006
CHECK=0
RESTART_DOCKER=0

for arg in "$@"; do
    case "$arg" in
        --check) CHECK=1 ;;
        --restart-docker) RESTART_DOCKER=1 ;;
        -h|--help) sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown flag: $arg" >&2; exit 2 ;;
    esac
done

say()  { printf '\n==> %s\n' "$*"; }
note() { printf '    %s\n' "$*"; }
run()  { if [ "$CHECK" -eq 1 ]; then note "[check] $*"; else "$@"; fi; }

[ "$CHECK" -eq 1 ] || [ "$(id -u)" -eq 0 ] || { echo "run with sudo (or --check)" >&2; exit 1; }
command -v docker >/dev/null || { echo "docker not found" >&2; exit 1; }
docker network inspect monitor-apps-net-dev1 >/dev/null 2>&1 \
    || { echo "network monitor-apps-net-dev1 missing; apply infra/docker/networks-dev1.yml first" >&2; exit 1; }

say "1/8 directories"
run install -d -o "$USER_ID" -g "$GROUP_ID" -m 0755 "$STORAGE" "$STORAGE/data"
run install -d -o "$USER_ID" -g "$GROUP_ID" -m 0755 "$TEXTFILE"
note "$STORAGE/data (TSDB), $TEXTFILE (textfile collector)"

say "2/8 htpasswd for the vhost"
if [ -f "$HTPASSWD" ]; then
    note "exists, leaving untouched: $HTPASSWD"
elif [ "$CHECK" -eq 1 ]; then
    note "[check] would prompt for a password and create $HTPASSWD"
else
    read -rsp "password for prometheus UI user 'prometheus': " pw; echo
    printf '%s\n' "$pw" | htpasswd -ci "$HTPASSWD" prometheus >/dev/null
    unset pw
    chown root:www-data "$HTPASSWD"; chmod 0640 "$HTPASSWD"
    note "created $HTPASSWD (root:www-data 0640)"
fi

say "3/8 nginx vhost"
run ln -sf "${REPO}/infra/nginx/sites-available/prometheus.conf" /etc/nginx/sites-enabled/prometheus
if [ "$CHECK" -eq 0 ]; then
    nginx -t && systemctl reload nginx
    note "nginx reloaded"
fi

say "4/8 containers"
run docker compose -f "${REPO}/infra/docker/prometheus-dev1.yml" up -d
run docker compose -f "${REPO}/infra/docker/node-exporter-dev1.yml" up -d

say "5/8 docker engine metrics"
if [ "$CHECK" -eq 1 ]; then
    "${REPO}/scripts/system/enable-docker-metrics.sh" --check || true
elif grep -qs 'metrics-addr' /etc/docker/daemon.json; then
    note "metrics-addr already present"
else
    if [ "$RESTART_DOCKER" -eq 1 ]; then
        "${REPO}/scripts/system/enable-docker-metrics.sh"
        say "   restarting docker (stops every container)"
        systemctl restart docker
        sleep 10
        docker ps --format '{{.Names}}' | wc -l | xargs -I{} sh -c 'echo "    {} containers running"'
    else
        note "not enabled. Re-run with --restart-docker to enable it (bounces all containers)"
    fi
fi

say "6/8 systemd timers"
for unit in tt-prometheus-alerts.service tt-prometheus-alerts.timer \
            tt-prometheus-metrics.service tt-prometheus-metrics.timer; do
    run install -m 0644 "${REPO}/infra/systemd/${unit}" "/etc/systemd/system/${unit}"
done
if [ "$CHECK" -eq 0 ]; then
    systemctl daemon-reload
    systemctl enable --now tt-prometheus-alerts.timer tt-prometheus-metrics.timer
    note "timers enabled"
    if [ ! -f /etc/tt-secrets/dev1/env/prometheus-alerts.env ]; then
        note "WARNING: /etc/tt-secrets/dev1/env/prometheus-alerts.env is missing;"
        note "         alert delivery will fail until it contains ALERT_TO=..."
    fi
fi

say "7/8 first metrics emission"
[ "$CHECK" -eq 0 ] && runuser -u mpegg-adm -- "${REPO}/scripts/emit-backup-metrics.sh" || note "[check] would emit backup metrics"

say "8/8 validate, reload, verify"
if [ "$CHECK" -eq 0 ]; then
    "${REPO}/scripts/deploy-prometheus.sh"
fi

say "done"
note "https://prometheus.termitetowers.ca (auth_basic)"
note "if the docker job is down, enable metrics: sudo $0 --restart-docker"
