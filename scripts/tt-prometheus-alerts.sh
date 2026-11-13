#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/tt-prometheus-alerts.sh@218 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 57279394ca206b61a1b6c1aebf7b2d85dcfb483c %
#  %ccm_git_commit_id: 72c0eae6bb7ccad09a6031b8cf1fff35b571a7e4 %
#  %ccm_git_commit_count: 218 %
#  %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: changes 261113 %
#  %ccm_git_modify_date: 2026-11-13 14:50:47 %
#  %ccm_git_file_last_modified: 2026-11-13 14:49:39 %
#  %ccm_git_file_name: tt-prometheus-alerts.sh %
#  %ccm_git_path: scripts/tt-prometheus-alerts.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 8200 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# TermiteTowers — deliver firing Prometheus alerts by mail.
#
# WHY THIS EXISTS INSTEAD OF ALERTMANAGER
#   Prometheus evaluates rules and exposes their state as the ALERTS series, but
#   it cannot send mail. Alertmanager is the usual answer and is a whole service
#   to configure, run and learn for one job: turn a firing alert into a message.
#
#   ttmail already does that job properly — allow-list, rate caps, loop
#   detection, and a verdict that distinguishes accepted from unknown. So this
#   script reads Prometheus's own alert state and hands delivery to ttmail. One
#   script instead of one more daemon, and alerts stay defined where they
#   belong, in the rule files.
#
# DEDUPLICATION
#   A timer runs this every 5 minutes, so the same firing alert is seen over and
#   over. State is kept in $STATE_DIR/alerts.state, one key per firing alert:
#     - new key      -> one mail
#     - vanished key -> one "resolved" mail
#     - unchanged    -> nothing
#   State is only advanced after the mail is accepted, so a failed send is
#   retried next run rather than lost. A duplicate critical alert is a better
#   failure than a missing one.
#
# USAGE
#   scripts/tt-prometheus-alerts.sh              # deliver
#   scripts/tt-prometheus-alerts.sh --dry-run    # print what would be sent
#
# ENVIRONMENT
#   ALERT_TO          required, recipient (from EnvironmentFile)
#   TTMAIL_ENV_FILE   default /etc/tt-secrets/dev1/env/ttmail.env
#   TTMAIL_BIN        default: first ttmail found (see resolve_ttmail)
#   PROM_URL          default http://127.0.0.1:3720
#   STATE_DIR         default /var/lib/tt-prometheus
#
# EXIT
#   0  state reconciled (nothing to send, or everything accepted)
#   1  query or delivery failed; state left unchanged so the alert re-fires

set -Eeuo pipefail

PROM_URL="${PROM_URL:-http://127.0.0.1:3720}"
STATE_DIR="${STATE_DIR:-/var/lib/tt-prometheus}"
STATE_FILE="${STATE_DIR}/alerts.state"
ALERT_TO="${ALERT_TO:-}"
TTMAIL_ENV_FILE="${TTMAIL_ENV_FILE:-/etc/tt-secrets/dev1/env/ttmail.env}"
TTMAIL_BIN="${TTMAIL_BIN:-}"
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

log() { printf '%s\n' "$*" >&2; }
die() { log "error: $*"; exit 1; }

resolve_ttmail() {
    [ -n "$TTMAIL_BIN" ] && { printf '%s' "$TTMAIL_BIN"; return; }
    local cand
    for cand in \
        "$(command -v ttmail 2>/dev/null || true)" \
        "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.venv/bin/ttmail" \
        /opt/ttmail/.venv/bin/ttmail
    do
        [ -n "$cand" ] && [ -x "$cand" ] && { printf '%s' "$cand"; return; }
    done
    die "ttmail not found; set TTMAIL_BIN in ${TTMAIL_ENV_FILE%/*}/prometheus-alerts.env"
}

command -v curl >/dev/null || die "curl not found"
command -v python3 >/dev/null || die "python3 not found"
if [ "$DRY_RUN" -eq 0 ] && [ -z "$ALERT_TO" ]; then
    die "ALERT_TO is not set (the systemd EnvironmentFile should provide it)"
fi

# systemd's StateDirectory= creates this. A manual run as a normal user cannot
# create /var/lib entries, which must not read as a mysterious install(1) error.
mkdir -p "$STATE_DIR" 2>/dev/null || true
[ -d "$STATE_DIR" ] && [ -w "$STATE_DIR" ] || die \
    "STATE_DIR ${STATE_DIR} is missing or not writable; systemd StateDirectory= creates it, or set STATE_DIR=/tmp/tt-prometheus for a manual run"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

# ---------------------------------------------------------------- current state
# Emit one TSV row per firing alert: key, alertname, instance, severity,
# summary, activeSince. Key is alertname|instance because that is the identity a
# human cares about and the one that persists across restarts.
#
# /api/v1/alerts is used rather than querying the ALERTS series: the series
# carries the rule's LABELS only, so annotations (summary, description) would
# come back empty and every mail would have a blank body.
curl -fsS "${PROM_URL}/api/v1/alerts" \
    | python3 -c '
import json, sys

doc = json.load(sys.stdin)
if doc.get("status") != "success":
    print("query failed:", doc.get("error"), file=sys.stderr)
    sys.exit(1)

for a in doc["data"]["alerts"]:
    if a.get("state") != "firing":
        continue
    labels = a.get("labels", {})
    ann = a.get("annotations", {})
    name = labels.get("alertname", "unknown")
    inst = labels.get("instance", labels.get("job", "-"))
    sev = labels.get("severity", "warning")
    summary = (ann.get("summary") or "").replace("\t", " ")
    since = a.get("activeAt", "")
    print("\t".join([f"{name}|{inst}", name, inst, sev, summary, since]))
' > "$work/current.tsv" || die "cannot query ${PROM_URL}; is prometheus-dev1 running?"

cut -f1 "$work/current.tsv" 2>/dev/null | sort > "$work/current.keys" || : > "$work/current.keys"
touch "$STATE_FILE"
sort "$STATE_FILE" > "$work/prev.keys"

comm -13 "$work/prev.keys" "$work/current.keys" > "$work/new.keys"
comm -23 "$work/prev.keys" "$work/current.keys" > "$work/resolved.keys"

new_count=$(wc -l < "$work/new.keys")
res_count=$(wc -l < "$work/resolved.keys")
log "firing=$(wc -l < "$work/current.keys"), new=${new_count}, resolved=${res_count}"

field_of() { # key, column
    awk -F'\t' -v k="$1" -v c="$2" '$1 == k { print $c; exit }' "$work/current.tsv"
}

send() { # subject, body
    local subject="$1" body="$2"
    if [ "$DRY_RUN" -eq 1 ]; then
        log "--- would send: ${subject}"
        printf '%s\n' "$body" >&2
        return 0
    fi
    printf '%s\n' "$body" \
        | "$TTMAIL_BIN" --env-file "$TTMAIL_ENV_FILE" \
              send "$ALERT_TO" --subject "$subject" --body -
}

failed=0

while IFS= read -r key; do
    [ -n "$key" ] || continue
    name="$(field_of "$key" 2)"
    inst="$(field_of "$key" 3)"
    sev="$(field_of "$key" 4)"
    summary="$(field_of "$key" 5)"
    body="$(printf 'Alert:    %s\nTarget:   %s\nSeverity: %s\n\n%s\n\nFiring since: %s\n\nSource: %s/#alerts\n' \
        "$name" "$inst" "$sev" "$summary" "$(field_of "$key" 6)" "$PROM_URL")"
    log "notify: ${name} on ${inst}"
    if ! send "[${sev^^}] ${name} on ${inst}" "$body"; then
        log "warn: delivery failed for ${name}; leaving state unchanged so it retries"
        failed=1
        break
    fi
done < "$work/new.keys"

# Resolutions are only attempted once every new alert has been delivered. If a
# send failed above we bail out before touching state, so nothing is marked as
# handled that a human never saw.
if [ "$failed" -eq 0 ]; then
    while IFS= read -r key; do
        [ -n "$key" ] || continue
        name="${key%%|*}"
        inst="${key#*|}"
        body="$(printf 'Alert:  %s\nTarget: %s\n\nThe condition is no longer firing.\n\nSource: %s/#alerts\n' \
            "$name" "$inst" "$PROM_URL")"
        log "resolved: ${name} on ${inst}"
        send "[resolved] ${name} on ${inst}" "$body" || { failed=1; break; }
    done < "$work/resolved.keys"
fi

if [ "$failed" -ne 0 ]; then
    log "delivery incomplete; state NOT advanced"
    exit 1
fi

if [ "$DRY_RUN" -eq 0 ]; then
    cp "$work/current.keys" "$STATE_FILE.new"
    mv "$STATE_FILE.new" "$STATE_FILE"
fi

log "done (state now holds $(wc -l < "$work/current.keys") firing alert(s))"
