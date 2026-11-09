#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/deploy-analacres-hosts.sh@200 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 6346c31a297a00a24d0d434e6a57498e2a1205ca %
#  %ccm_git_commit_id: 07c638fcfb4804b40c226db94358725a8b6ef636 %
#  %ccm_git_commit_count: 200 %
#  %ccm_git_commit_date: 2026-11-09 10:16:57 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: zoo.261109 %
#  %ccm_git_modify_date: 2026-11-09 10:16:58 %
#  %ccm_git_file_last_modified: 2026-11-08 14:23:56 %
#  %ccm_git_file_name: deploy-analacres-hosts.sh %
#  %ccm_git_path: scripts/deploy-analacres-hosts.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 14231 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
#
# deploy-analacres-hosts.sh — one-shot, idempotent deploy of the analacres.ca
# vhosts (wordbank, soundbank) and the gate-ready nginx snippets.
#
# Run it once, enter your password once:
#
#   ./scripts/deploy-analacres-hosts.sh              # deploy
#   ./scripts/deploy-analacres-hosts.sh --dry-run    # show what it would do
#   ./scripts/deploy-analacres-hosts.sh --force-cert # re-issue certs
#
# If run as a normal user it re-executes itself under sudo, so the password is
# asked exactly once for the whole run. Every later privileged call inside the
# script is already root — the old hand-typed sequence asked for it ~20 times.
#
# What it does, in order:
#   1. Snapshots the current nginx state to /var/backups/tt-nginx/<stamp>/
#   2. Issues a per-host ECDSA cert for wordbank + soundbank (skips existing)
#   3. Symlinks both snippets into /etc/nginx/snippets/
#   4. Symlinks the three vhosts into sites-available + sites-enabled
#   5. nginx -t  — aborts here, WITHOUT reloading, if anything is wrong
#   6. reloads nginx
#   7. publishes the new A records via the ddns unit
#   8. verifies every host over loopback and prints a table
#
# It does NOT touch the Authelia gate: tt-gate.conf stays inert. Phase 2 is a
# separate, single-file change — see wiki/runbook-authelia.md.

set -euo pipefail

# ── resolve paths ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${TT_REPO:-$(dirname "$SCRIPT_DIR")}"

VHOST_DIR="$REPO_DIR/infra/nginx/sites-available"
SNIPPET_DIR="$REPO_DIR/infra/nginx/snippets"
HOOK_DIR="$REPO_DIR/infra/certbot"
GODADDY_ENV="/etc/letsencrypt/godaddy.env"
BACKUP_ROOT="/var/backups/tt-nginx"

# vhost file → /etc/nginx/sites-available name
VHOSTS=(immich library music nextcloud)
# hostnames needing their own certificate in this phase
CERT_HOSTS=(wordbank.analacres.ca soundbank.analacres.ca filebank.analacres.ca)
SNIPPETS=(tt-gate.conf tt-gate-location.conf)

DRY_RUN=0
FORCE_CERT=0
SKIP_CERT=0
SKIP_DDNS=0

# ── args ─────────────────────────────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --dry-run)     DRY_RUN=1 ;;
        --force-cert)  FORCE_CERT=1 ;;
        --skip-cert)   SKIP_CERT=1 ;;
        --skip-ddns)   SKIP_DDNS=1 ;;
        -h|--help)     sed -n '2,30p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown argument: $arg (try --help)" >&2; exit 2 ;;
    esac
done

c_ok()   { printf '\033[32m[ ok ]\033[0m %s\n' "$*"; }
c_info() { printf '\033[36m[info]\033[0m %s\n' "$*"; }
c_warn() { printf '\033[33m[warn]\033[0m %s\n' "$*"; }
c_err()  { printf '\033[31m[fail]\033[0m %s\n' "$*" >&2; }
# For steps performed via run(): never claims success when nothing was executed.
c_done() { if (( DRY_RUN )); then c_info "would do: $*"; else c_ok "$*"; fi; }

run() {
    # Echo every privileged action, and honour --dry-run.
    printf '\033[90m   $ %s\033[0m\n' "$*"
    (( DRY_RUN )) || "$@"
}

# ── elevation: one password prompt for the entire run ────────────────────────
if [[ $EUID -ne 0 ]]; then
    if (( DRY_RUN )); then
        c_warn "not root; --dry-run needs no privileges, continuing read-only"
    elif [[ -x /usr/bin/sudo ]]; then
        c_info "need root for certbot, /etc/nginx and systemd — elevating once"
        exec sudo -- "$0" "$@"
    else
        c_err "not root and sudo not found"; exit 1
    fi
fi

# ── pre-flight ───────────────────────────────────────────────────────────────
c_info "repository: $REPO_DIR"
[[ -d "$VHOST_DIR" ]] || { c_err "vhost dir missing: $VHOST_DIR"; exit 1; }

missing=0
for v in "${VHOSTS[@]}"; do
    [[ -f "$VHOST_DIR/$v.conf" ]] || { c_err "missing vhost: $VHOST_DIR/$v.conf"; missing=1; }
done
for s in "${SNIPPETS[@]}"; do
    [[ -f "$SNIPPET_DIR/$s" ]] || { c_err "missing snippet: $SNIPPET_DIR/$s"; missing=1; }
done
for h in "${CERT_HOSTS[@]}"; do
    [[ -f "$HOOK_DIR/godaddy-auth-hook.sh" ]]   || { c_err "missing hook: godaddy-auth-hook.sh";   missing=1; }
    [[ -f "$HOOK_DIR/godaddy-cleanup-hook.sh" ]] || { c_err "missing hook: godaddy-cleanup-hook.sh"; missing=1; }
done
(( missing == 0 )) || { c_err "pre-flight failed; nothing changed"; exit 1; }
command -v certbot >/dev/null || { c_err "certbot not installed"; exit 1; }
command -v nginx   >/dev/null || { c_err "nginx not installed";   exit 1; }

if [[ ! -f "$GODADDY_ENV" ]]; then
    c_warn "$GODADDY_ENV not found — certificate issuance will fail (DNS-01 needs it)"
fi

# The gate must stay inert in this phase.
if grep -qvE '^\s*(#|$)' "$SNIPPET_DIR/tt-gate.conf"; then
    c_err "tt-gate.conf contains active directives — it must be comments only in Phase 1."
    c_err "Refusing to deploy: some vhost would start requiring Authelia, which is not running."
    exit 1
fi
c_ok "tt-gate.conf is inert (comments only)"

# ── 1. snapshot for rollback ─────────────────────────────────────────────────
STAMP="$(date +%Y%m%d-%H%M%S)"
SNAP="$BACKUP_ROOT/$STAMP"
c_info "snapshotting current nginx state → $SNAP"
run mkdir -p "$SNAP"
run bash -c "nginx -T > '$SNAP/nginx.T' 2>'$SNAP/nginx.T.err' || true"
run bash -c "ls -l /etc/nginx/sites-enabled/ > '$SNAP/sites-enabled.ls' 2>&1 || true"
run bash -c "cp -a /etc/nginx/sites-available/. '$SNAP/sites-available' 2>/dev/null || true"

# ── 2. certificates ──────────────────────────────────────────────────────────
if (( SKIP_CERT )); then
    c_info "skipping certificates (--skip-cert)"
else
    for host in "${CERT_HOSTS[@]}"; do
        if [[ -f "/etc/letsencrypt/live/$host/fullchain.pem" ]] && (( ! FORCE_CERT )); then
            c_ok "certificate already present: $host (use --force-cert to reissue)"
            continue
        fi
        c_info "issuing ECDSA certificate for $host via GoDaddy DNS-01 hooks"
        run certbot certonly --manual --preferred-challenges dns --non-interactive \
            --manual-auth-hook    "$HOOK_DIR/godaddy-auth-hook.sh" \
            --manual-cleanup-hook "$HOOK_DIR/godaddy-cleanup-hook.sh" \
            --key-type ecdsa -d "$host"
    done
fi

# ── 3. snippets into /etc/nginx/snippets ─────────────────────────────────────
run mkdir -p /etc/nginx/snippets
for s in "${SNIPPETS[@]}"; do
    run ln -sfn "$(realpath "$SNIPPET_DIR/$s")" "/etc/nginx/snippets/$s"
    c_done "snippet installed: /etc/nginx/snippets/$s"
done

# ── 4. vhosts into sites-available + sites-enabled ───────────────────────────
for v in "${VHOSTS[@]}"; do
    run ln -sfn "$(realpath "$VHOST_DIR/$v.conf")" "/etc/nginx/sites-available/$v"
    run ln -sfn "/etc/nginx/sites-available/$v"    "/etc/nginx/sites-enabled/$v"
    c_done "vhost enabled: $v"
done

# ── 5. validate — refuse to reload a broken config ───────────────────────────
if (( DRY_RUN )); then
    c_warn "dry-run: skipping nginx -t and reload"
else
    if nginx -t; then
        c_ok "nginx -t passed"
    else
        c_err "nginx -t FAILED — nginx has not been reloaded; the live service is unchanged."
        c_err "Previous state is in $SNAP (nginx.T is the full parsed config)."
        c_err "Rollback:  rm -f /etc/nginx/sites-enabled/{immich,library,music} and re-run after fixing."
        exit 1
    fi
fi

# ── 6. reload ────────────────────────────────────────────────────────────────
run systemctl reload nginx
c_done "nginx reloaded"

# ── 7. DNS records ───────────────────────────────────────────────────────────
if (( SKIP_DDNS )); then
    c_info "skipping ddns (--skip-ddns)"
elif systemctl list-unit-files 2>/dev/null | grep -q '^tt-godaddy-ddns\.service'; then
    if run systemctl start tt-godaddy-ddns.service; then
        c_done "A records published via tt-godaddy-ddns.service"
    else
        c_warn "ddns unit failed — run the updater by hand: $REPO_DIR/infra/dns/godaddy-ddns.sh"
    fi
else
    # Unit not installed. We are already root, so run the updater directly
    # instead of telling the user to do it.
    c_info "tt-godaddy-ddns.service not installed; running the updater directly"
    if run "$REPO_DIR/infra/dns/godaddy-ddns.sh"; then
        c_done "A records published"
    else
        c_warn "A records NOT published — check $GODADDY_ENV, then re-run the updater"
    fi
fi

# ── 8. verify over loopback (no DNS, no hairpin dependency) ──────────────────
echo
if (( DRY_RUN )); then
    c_warn "dry-run: skipping live verification (nothing was deployed)"
else
c_info "verification over loopback (--resolve, so LAN DNS and hairpin are bypassed)"
printf '  %-42s %-6s %s\n' 'ENDPOINT' 'CODE' 'REDIRECT'
printf '  %-42s %-6s %s\n' '--------' '----' '--------'

check() {
    # check <label> <host:port> <path> [insecure]
    local label="$1" hp="$2" path="$3" insecure="${4:-}"
    local host="${hp%:*}" port="${hp##*:}" out code redir
    # Single curl call. -w ends with \n so a failure marker cannot be glued
    # onto a partial -w line (which is what produced "000 000 -" before).
    out="$(curl -sS -o /dev/null --max-time 10 ${insecure:+-k} \
                --resolve "$host:$port:127.0.0.1" \
                -w '%{http_code} %{redirect_url}\n' \
                "https://$host:$port$path" 2>/dev/null)" || out='000 UNREACHABLE'
    code="${out%% *}"
    redir="${out#* }"
    [[ "$redir" == "$out" ]] && redir=''
    printf '  %-42s %-6s %s\n' "$label" "$code" "$redir"
}

check "wordbank root"      wordbank.analacres.ca:3261   /
check "wordbank /api/"     wordbank.analacres.ca:3261   /api/status
check "soundbank root"     soundbank.analacres.ca:3261  /
check "soundbank /rest/"   soundbank.analacres.ca:3261  '/rest/ping.view?v=1.16.1&c=tt&f=json'
check "memorylab root"     memorylab.analacres.ca:3261  /
check "memorylab /api/"    memorylab.analacres.ca:3261  /api/server/ping
check "filebank root"      filebank.analacres.ca:3261   /
check "filebank /status"   filebank.analacres.ca:3261   /status.php
check "filebank caldav"    filebank.analacres.ca:3261   /.well-known/caldav
check "old name 443"       nextcloud.termitetowers.ca:443 /
check "pics (unchanged)"   pics.justanotherhuman.ca:3261 / k
check "library. 443"       library.termitetowers.ca:443   /
check "music. 443"         music.termitetowers.ca:443     /

echo
c_info "public path — real DNS, then the router DNAT 443 -> monolith 3261"
printf '  %-42s %-6s %s\n' 'ENDPOINT' 'CODE' 'REDIRECT'
printf '  %-42s %-6s %s\n' '--------' '----' '--------'

check_public() {
    # Deliberately no --resolve: this exercises the real DNS answer and the
    # router rule, which is the path browsers and apps actually take.
    local label="$1" host="$2" out code redir
    out="$(curl -sS -o /dev/null --max-time 15 \
                -w '%{http_code} %{redirect_url}\n' \
                "https://$host/" 2>/dev/null)" || out='000 UNREACHABLE'
    code="${out%% *}"
    redir="${out#* }"
    [[ "$redir" == "$out" ]] && redir=''
    printf '  %-42s %-6s %s\n' "$label" "$code" "$redir"
}

check_public "wordbank.analacres.ca"  wordbank.analacres.ca
check_public "soundbank.analacres.ca" soundbank.analacres.ca
check_public "memorylab.analacres.ca" memorylab.analacres.ca
check_public "filebank.analacres.ca"  filebank.analacres.ca

echo
c_info "expected: roots 200 (soundbank 302 to /app/ is Navidrome itself, not a gate);"
c_info "          /api/ and /rest/ answer from the app, never a portal redirect;"
c_info "          pics and the two termitetowers hosts unchanged."
echo
fi
c_ok "done. Certificate renewal check:  sudo certbot renew --dry-run"
c_info "Public URLs carry no port: WAN 443 is DNATed to monolith 3261, so"
c_info "  https://wordbank.analacres.ca  https://soundbank.analacres.ca"
c_info "A 000 in the public table usually means the new A record has not"
c_info "propagated yet, not that the vhost is wrong."
c_info "Next: test the AudioBookshelf and Subsonic apps. The gate stays off until"
c_info "      Phase 2 — see wiki/runbook-authelia.md"
