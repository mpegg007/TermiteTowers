#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/backups/scripts/install-tt-keys.sh@189 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: a674e1055af9f93437bc0cfe1c92439ad7a5cd40 %
#  %ccm_git_commit_id: e4f75cef3cd2cd1877f825652b221973b909b6a1 %
#  %ccm_git_commit_count: 189 %
#  %ccm_git_commit_date: 2026-10-28 12:07:18 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: feat(backups): phase 5 - rotate, rewrap, audit, prune, restore wrapper %
#  %ccm_git_modify_date: 2026-10-28 12:07:19 %
#  %ccm_git_file_last_modified: 2026-10-28 12:07:07 %
#  %ccm_git_file_name: install-tt-keys.sh %
#  %ccm_git_path: infra/backups/scripts/install-tt-keys.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 10438 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# --- usage:begin
# install-tt-keys :: deploy + verify the wrapped-DEK keyring (phase 2).
#
# RUN AS ROOT (repairs ownership/modes and reloads systemd):
#     sudo infra/backups/scripts/install-tt-keys.sh
#
# READ-ONLY AUDIT, no root needed - safe to run any time, also from cron:
#     infra/backups/scripts/install-tt-keys.sh --check
#
# What it does:
#   1. asserts the keyring exists and really is an age file
#   2. repairs /mnt/ai_storage/backups/tt-keys (0700, keyring 0600, owner)
#   3. asserts the tt-backup account CANNOT read or even traverse that dir
#      (DAC, plus InaccessiblePaths= in the unit)
#   4. re-links tt-backup-tthealth.service and runs systemctl daemon-reload
#   5. reports whether the keyring folder is in Jotta's backup set
#
# What it CANNOT do for you: add the folder to Jotta. jotta-cli runs with the
# login session of mpegg-adm, not root:
#     jotta-cli add /mnt/ai_storage/backups/tt-keys && jotta-cli scan
#
# The keyring is ciphertext, so replicating it offsite is safe and is the whole
# point: losing this one file loses the ability to rotate or restore any
# generation held inside it (existing data stays readable only while the
# wrapped DEKs survive).
#
# EXIT CODES
#   0 ok | 1 one or more checks failed | 2 missing tool | 3 bad configuration
#   4 could not repair a path
# --- usage:end
set -Eeuo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

AGE_DIR="${TT_AGE_DIR:-$REPO_DIR/infra/backups/age}"
REGISTRY="$AGE_DIR/registry.json"

KEYRING_DIR="${TT_KEYRING_DIR:-/mnt/ai_storage/backups/tt-keys}"
KEYRING="$KEYRING_DIR/keyring.tar.age"

OWNER="${TT_KEYRING_OWNER:-mpegg-adm}"
SERVICE_USER="tt-backup"
UNIT="tt-backup-tthealth.service"

MODE="repair"
OK=0
FAIL=0

log() { printf '[%s] [%-5s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" "${*:2}"; }
die() { printf '[%s] [ERROR] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" >&2; exit "${2:-3}"; }
step() { printf '\n== %s\n' "$*"; }
pass() { printf '   [ ok ] %s\n' "$*"; OK=$((OK + 1)); }
warn() { printf '   [warn] %s\n' "$*"; }
fail() { printf '   [FAIL] %s\n' "$*"; FAIL=$((FAIL + 1)); }

usage() {
    sed -n '/^# --- usage:begin$/,/^# --- usage:end$/p' "${BASH_SOURCE[0]}" \
        | sed '1d;$d' \
        | sed 's/^# \{0,1\}//'
}

as_user() {  # user cmd...
    local u="$1"; shift
    if command -v runuser >/dev/null 2>&1; then
        runuser -u "$u" -- "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo -n -u "$u" -- "$@"
    else
        return 127
    fi
}

require_tools() {
    local t
    for t in jq stat install systemctl; do
        command -v "$t" >/dev/null 2>&1 || die "required tool not found: $t" 2
    done
}

check_keyring() {
    step "keyring"
    if [ -r "$KEYRING" ]; then
        pass "readable: $KEYRING ($(du -h "$KEYRING" | cut -f1))"
    else
        fail "missing: $KEYRING (run 'scripts/tt-keys.sh init')"
        return 0
    fi
    if [ "$(head -c 21 "$KEYRING" 2>/dev/null || true)" = "age-encryption.org/v1" ]; then
        pass "age ciphertext header present"
    else
        fail "not an age file: $KEYRING"
    fi
    if [ -r "$REGISTRY" ] && jq -e . "$REGISTRY" >/dev/null 2>&1; then
        pass "registry parses: tiers=$(jq -r '.tiers | keys | join(",")' "$REGISTRY")"
    else
        fail "registry missing or not valid JSON: $REGISTRY"
    fi
}

check_perms() {
    step "permissions"
    if [ -d "$KEYRING_DIR" ]; then
        local dperm downer
        dperm="$(stat -c '%a' "$KEYRING_DIR")"
        downer="$(stat -c '%U' "$KEYRING_DIR")"
        if [ "$dperm" = "700" ] && [ "$downer" = "$OWNER" ]; then
            pass "dir is $dperm $downer"
        else
            fail "dir is $dperm $downer (want 700 $OWNER)"
        fi
    else
        fail "dir missing: $KEYRING_DIR"
    fi
    if [ -f "$KEYRING" ]; then
        local fperm fowner
        fperm="$(stat -c '%a' "$KEYRING")"
        fowner="$(stat -c '%U' "$KEYRING")"
        if [ "$fperm" = "600" ] && [ "$fowner" = "$OWNER" ]; then
            pass "keyring is $fperm $fowner"
        else
            fail "keyring is $fperm $fowner (want 600 $OWNER)"
        fi
    fi
}

check_isolation() {
    step "isolation from the backup account"
    if [ "$(id -u)" -ne 0 ]; then
        warn "not root: cannot switch to $SERVICE_USER, so the DAC test is skipped"
        return 0
    fi
    if ! id "$SERVICE_USER" >/dev/null 2>&1; then
        warn "service account $SERVICE_USER does not exist on this host"
        return 0
    fi
    if as_user "$SERVICE_USER" test -r "$KEYRING" 2>/dev/null; then
        fail "$SERVICE_USER CAN read $KEYRING"
    else
        pass "$SERVICE_USER cannot read the keyring (DAC)"
    fi
    if as_user "$SERVICE_USER" test -x "$KEYRING_DIR" 2>/dev/null; then
        fail "$SERVICE_USER CAN traverse $KEYRING_DIR"
    else
        pass "$SERVICE_USER cannot traverse the keyring dir"
    fi
}

check_unit() {
    step "systemd unit"
    if systemctl cat "$UNIT" >/dev/null 2>&1; then
        pass "$UNIT is known to systemd"
    else
        fail "$UNIT is not installed"
        return 0
    fi
    local ondisk loaded
    # The FILE having the setting and systemd having LOADED it are different
    # things: a stale daemon reports the old config until daemon-reload runs.
    ondisk="$(systemctl cat "$UNIT" 2>/dev/null | grep -F 'InaccessiblePaths=' | grep -F "$KEYRING_DIR" || true)"
    if [ -n "$ondisk" ]; then
        pass "unit file sets InaccessiblePaths=$KEYRING_DIR"
    else
        fail "unit file has no InaccessiblePaths for $KEYRING_DIR"
    fi
    loaded="$(systemctl show -p InaccessiblePaths --value "$UNIT" 2>/dev/null || true)"
    case "$loaded" in
        *"$KEYRING_DIR"*) pass "systemd has loaded the restriction" ;;
        *) fail "systemd has NOT loaded it: sudo systemctl daemon-reload" ;;
    esac
    local link="/etc/systemd/system/$UNIT"
    if [ -L "$link" ]; then
        pass "$link -> $(readlink "$link")"
    elif [ -f "$link" ]; then
        warn "$link is a real file, not the /srv/dev1 symlink (content can drift from the repo)"
    else
        fail "$link missing"
    fi
    if systemctl is-enabled --quiet tt-keys-audit.timer 2>/dev/null; then
        pass "tt-keys-audit.timer is enabled (weekly audit)"
    else
        warn "tt-keys-audit.timer is not enabled - the weekly audit will not run"
    fi
}

check_jotta() {
    step "offsite replication (Jotta)"
    if [ "$(id -u)" -eq 0 ]; then
        warn "root has no jotta-cli session; re-run --check as $OWNER to test this"
        return 0
    fi
    if ! command -v jotta-cli >/dev/null 2>&1; then
        warn "jotta-cli not in PATH"
        return 0
    fi
    if jotta-cli status 2>/dev/null | grep -qF "$KEYRING_DIR"; then
        pass "$KEYRING_DIR is in the Jotta backup set"
    else
        fail "$KEYRING_DIR is NOT backed up: jotta-cli add $KEYRING_DIR && jotta-cli scan"
    fi
}

repair() {
    step "repair"
    if [ "$(id -u)" -ne 0 ]; then
        die "read-only mode: run 'sudo $0' to repair, or '$0 --check' to audit" 3
    fi
    install -d -o "$OWNER" -g "$OWNER" -m 0700 "$KEYRING_DIR" \
        || die "cannot create $KEYRING_DIR" 4
    if [ -f "$KEYRING" ]; then
        chown "$OWNER:$OWNER" "$KEYRING" || die "chown failed on $KEYRING" 4
        chmod 0600 "$KEYRING" || die "chmod failed on $KEYRING" 4
    fi
    log INFO "owner/mode asserted on $KEYRING_DIR"

    local src
    local -a units=("$UNIT" "tt-keys-audit.service" "tt-keys-audit.timer")
    for u in "${units[@]}"; do
        src="/srv/dev1/systemd/$u"
        [ -f "$src" ] || src="$REPO_DIR/infra/systemd/$u"
        if [ -f "$src" ]; then
            ln -sfn "$src" "/etc/systemd/system/$u"
            log INFO "linked $u -> $src"
        else
            warn "unit file not found, skipped: $u"
        fi
    done
    systemctl daemon-reload
    systemctl enable --now tt-keys-audit.timer 2>/dev/null \
        && log INFO "tt-keys-audit.timer enabled (weekly, no secrets needed)" \
        || warn "could not enable tt-keys-audit.timer"

    if command -v systemd-analyze >/dev/null 2>&1; then
        if systemd-analyze verify "/etc/systemd/system/$UNIT" >/dev/null 2>&1; then
            log INFO "systemd-analyze verify: ok"
        else
            warn "systemd-analyze verify reported problems for $UNIT"
        fi
    fi
}

main() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --check)   MODE="check"; shift ;;
            --owner)   OWNER="${2:?--owner needs a value}"; shift 2 ;;
            --owner=*) OWNER="${1#*=}"; shift ;;
            -h|--help) usage; exit 0 ;;
            *)         usage >&2; die "unknown option: $1" 3 ;;
        esac
    done

    require_tools

    step "environment"
    printf '   keyring   %s\n' "$KEYRING"
    printf '   registry  %s\n' "$REGISTRY"
    printf '   owner     %s\n' "$OWNER"
    printf '   mode      %s\n' "$MODE"

    if [ "$MODE" = "repair" ]; then
        repair
    fi

    check_keyring
    check_perms
    check_isolation
    check_unit
    check_jotta

    printf '\n'
    if [ "$FAIL" -eq 0 ]; then
        log INFO "phase 2: $OK checks ok, 0 failed"
        exit 0
    fi
    log ERROR "phase 2: $OK checks ok, $FAIL FAILED"
    exit 1
}

main "$@"

