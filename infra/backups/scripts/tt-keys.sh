#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/backups/scripts/tt-keys.sh@189 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 63848ef3cc3c4db19de8fdb6b47cf4bf10a86d5f %
#  %ccm_git_commit_id: e4f75cef3cd2cd1877f825652b221973b909b6a1 %
#  %ccm_git_commit_count: 189 %
#  %ccm_git_commit_date: 2026-10-28 12:07:18 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: feat(backups): phase 5 - rotate, rewrap, audit, prune, restore wrapper %
#  %ccm_git_modify_date: 2026-10-28 12:07:19 %
#  %ccm_git_file_last_modified: 2026-10-28 12:06:28 %
#  %ccm_git_file_name: tt-keys.sh %
#  %ccm_git_path: infra/backups/scripts/tt-keys.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 42592 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# --- usage:begin
# tt-keys :: per-tier age DEKs, wrapped by a master identity kept OFF this host.
#
#   layer 1   master identity     age1...      escrowed offsite (1Password)
#   layer 2   keyring.tar.age     ciphertext   /mnt/ai_storage/backups/tt-keys
#   layer 3   per-tier DEKs       health | mail | general, every generation kept
#   layer 4   backup artifacts                 encrypted to a PUBLIC recipient
#
# The daily jobs never need the master: they read a public recipient file. The
# master is required only to unwrap a DEK, i.e. to verify, rotate or restore.
# Losing the host therefore loses ciphertext and a locked keyring, nothing else.
#
# USAGE
#   tt-keys.sh init [--tiers health,mail,general] [--gen 2026Q4]
#                   [--import-legacy PATH] [--master-recipient age1...]
#   tt-keys.sh list                        # tiers + every generation (no secret)
#   tt-keys.sh status                      # keyring + drift checks (no secret)
#   tt-keys.sh verify [tier...]            # master -> DEK -> ciphertext round-trip
#   tt-keys.sh unlock <tier>[:<gen>] [--out PATH]
#   tt-keys.sh import-legacy <path>        # add health/legacy after init
#   tt-keys.sh audit                       # generations vs artifacts on disk (no secret)
#   tt-keys.sh rotate <tier> [--gen L] [--yes]      # new generation, same tier
#   tt-keys.sh rewrap --new-recipient age1... [--yes]   # new MASTER, same DEKs
#   tt-keys.sh prune [--retire <tier>:<gen> --yes]  # report, or drop one dead DEK
#
# init/rotate/rewrap/prune modify key state and therefore refuse to run outside a
# git checkout (a deploy target like /srv/prd/tt is rsynced with --delete, which
# would silently revert the registry). --allow-non-git overrides for rehearsals.
#
# ENVIRONMENT
#   TT_MASTER_FILE        master identity file (default: interactive paste)
#   TT_AGE_DIR            default <repo>/infra/backups/age
#   TT_KEYRING_DIR        default /mnt/ai_storage/backups/tt-keys
#   TT_RETIRE_GRACE_DAYS  default 120 (90-day rotation + 30-day grace)
#
# The master identity is read into a 0700 tmpfs directory and shredded on exit.
# It is never written to the repo, the keyring directory or any backup path.
#
# EXIT CODES
#   0 ok | 2 missing tool | 3 bad arguments or configuration | 4 keyring or
#   crypto failure | 5 verification failure | 6 refused (unsafe state)
# --- usage:end
set -Eeuo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
AGE_DIR="${TT_AGE_DIR:-$REPO_DIR/infra/backups/age}"
REGISTRY="$AGE_DIR/registry.json"
MASTER_RECIPIENT_FILE="$AGE_DIR/master-recipient.txt"

KEYRING_DIR="${TT_KEYRING_DIR:-/mnt/ai_storage/backups/tt-keys}"
KEYRING="$KEYRING_DIR/keyring.tar.age"

DEFAULT_TIERS="health,mail,general"
RETIRE_GRACE_DAYS="${TT_RETIRE_GRACE_DAYS:-120}"
MASTER_FILE="${TT_MASTER_FILE:-}"

OPT_TIERS="$DEFAULT_TIERS"
OPT_GEN=""
OPT_IMPORT_LEGACY=""
OPT_MASTER_RECIPIENT=""
OPT_SPEC=""
OPT_OUT=""
OPT_NEW_RECIPIENT=""
OPT_RETIRE=""
OPT_YES=0
OPT_ALLOW_NON_GIT=0
BACKUP_ROOT="${TT_BACKUP_ROOT:-/mnt/ai_storage/backups}"

if [ -d /dev/shm ] && [ -w /dev/shm ]; then
    TMPBASE=/dev/shm
else
    TMPBASE="${TMPDIR:-/tmp}"
fi

log() { printf '[%s] [%-5s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" "${*:2}"; }
die() { printf '[%s] [ERROR] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" >&2; exit "${2:-3}"; }
step() { printf '\n== %s\n' "$*"; }

# Header-block markers rather than line numbers: the pre-commit hook prepends a
# CCM header above the shebang, so "NR >= 3" would print the wrong block.
usage() {
    sed -n '/^# --- usage:begin$/,/^# --- usage:end$/p' "${BASH_SOURCE[0]}" \
        | sed '1d;$d' \
        | sed 's/^# \{0,1\}//'
}

cleanup() {
    if [ -n "${WORK:-}" ] && [ -d "$WORK" ]; then
        find "$WORK" -type f -exec shred -u {} + 2>/dev/null || true
        rm -rf "$WORK"
    fi
}
trap cleanup EXIT

WORK="$(mktemp -d "$TMPBASE/tt-keys.XXXXXX")"
chmod 700 "$WORK"

require_tools() {
    local t
    for t in age age-keygen tar jq flock; do
        command -v "$t" >/dev/null 2>&1 || die "required tool not found: $t" 2
    done
}

default_gen() { printf '%sQ%s\n' "$(date +%Y)" "$(( ($(date +%-m) - 1) / 3 + 1 ))"; }

# The master PUBLIC recipient: an argument, then the committed file, else fail.
resolve_master_recipient() {
    local r=""
    if [ -n "$OPT_MASTER_RECIPIENT" ]; then
        r="$OPT_MASTER_RECIPIENT"
    elif [ -r "$MASTER_RECIPIENT_FILE" ]; then
        r="$(grep -Ev '^[[:space:]]*(#|$)' "$MASTER_RECIPIENT_FILE" | head -1)"
    fi
    [ -n "$r" ] || die "no master recipient: create $MASTER_RECIPIENT_FILE or pass --master-recipient" 3
    [[ "$r" =~ ^age1[0-9a-z]{50,}$ ]] || die "not a valid age recipient: $r" 3
    printf '%s\n' "$r"
}

# A path age can read the master identity from. TT_MASTER_FILE may also point
# at a passphrase-wrapped file - age prompts for the passphrase itself.
master_identity() {
    if [ -n "$MASTER_FILE" ]; then
        [ -r "$MASTER_FILE" ] || die "TT_MASTER_FILE is not readable: $MASTER_FILE" 3
        printf '%s\n' "$MASTER_FILE"
        return 0
    fi
    local dir="$WORK/master" line=""
    mkdir -p "$dir"; chmod 700 "$dir"
    printf 'master identity (paste the AGE-SECRET-KEY line, input is not echoed): ' >&2
    IFS= read -rs line || true
    printf '\n' >&2
    line="${line//$'\r'/}"
    case "$line" in
        AGE-SECRET-KEY-1*) : ;;
        *) die "that does not look like an age secret key" 3 ;;
    esac
    umask 077
    printf '%s\n' "$line" > "$dir/master.txt"
    chmod 600 "$dir/master.txt"
    printf '%s\n' "$dir/master.txt"
}

unwrap_keyring() {  # $1 = destination directory
    local dest="$1" ident
    mkdir -p "$dest"; chmod 700 "$dest"
    [ -r "$KEYRING" ] || die "keyring not found: $KEYRING" 4
    ident="$(master_identity)"
    if ! age -d -i "$ident" "$KEYRING" 2>"$WORK/age.err" | tar -xf - -C "$dest"; then
        # Distinguish "wrong key" from "corrupt keyring": derive the recipient of
        # the supplied identity (public data) and compare with the intended one.
        local got expected
        got="$(age-keygen -y "$ident" 2>/dev/null || true)"
        expected="$(jq -r '.master.recipient // empty' "$REGISTRY" 2>/dev/null || true)"
        if [ -n "$got" ] && [ -n "$expected" ] && [ "$got" != "$expected" ]; then
            log ERROR "the identity you supplied belongs to ${got}"
            log ERROR "the keyring is wrapped to            ${expected}"
            die "wrong master identity - the keyring was not touched" 4
        fi
        sed 's/^/    /' "$WORK/age.err" >&2 || true
        die "cannot open $KEYRING - wrong master identity?" 4
    fi
    [ -f "$dest/registry.json" ] || die "keyring has no registry.json - not a tt-keys keyring" 4
}

wrap_keyring() {  # $1 = source directory (must contain registry.json + keys/)
    local src="$1" recip tmp
    recip="$(resolve_master_recipient)"
    tmp="$KEYRING.tmp.$$"
    if ! ( cd "$src" && tar -cf - . ) | age -e -r "$recip" -o "$tmp"; then
        rm -f "$tmp"
        die "failed to wrap the keyring for recipient $recip" 4
    fi
    if [ "$(head -c 21 "$tmp" 2>/dev/null || true)" != "age-encryption.org/v1" ]; then
        rm -f "$tmp"
        die "wrapped keyring is not an age file" 4
    fi
    mv -f "$tmp" "$KEYRING"
    chmod 600 "$KEYRING"
    sync -f "$KEYRING" 2>/dev/null || true
    log INFO "keyring wrapped: $KEYRING ($(du -h "$KEYRING" | cut -f1), master $(printf '%s' "$recip" | cut -c1-16)...)"
}

write_recipient_file() {  # path tier gen pub created note
    local path="$1" t="$2" g="$3" pub="$4" cd="$5" note="$6"
    {
        printf '# tt-backup :: age recipient for the %s tier (generation %s)\n' "$t" "$g"
        printf '#\n'
        printf '# PUBLIC KEY ONLY - safe to commit. The private half lives in the wrapped\n'
        printf '# keyring (%s), which needs the master identity to open.\n' "$KEYRING"
        printf '# Never put a private key, the keyring or the master identity in this repo.\n'
        printf '#\n'
        printf '# tier: %s | generation: %s | created: %s' "$t" "$g" "$cd"
        if [ -n "$note" ] && [ "$note" != "generated" ]; then
            printf ' | note: %s' "$note"
        fi
        printf '\n'
        printf '%s\n' "$pub"
    } > "$path"
    chmod 0644 "$path"
}

# Write <tier>.recipient (current) plus history/<tier>-<gen>.recipient (all).
# The first row seen for a tier is that tier's current generation.
write_recipients() {  # $1 = tsv of tier/gen/pub/created/note
    local tsv="$1" t g pub cd note
    local -A seen=()
    mkdir -p "$AGE_DIR/history"
    while IFS=$'\t' read -r t g pub cd note; do
        [ -n "${t:-}" ] || continue
        write_recipient_file "$AGE_DIR/history/$t-$g.recipient" "$t" "$g" "$pub" "$cd" "$note"
        if [ -z "${seen[$t]:-}" ]; then
            seen[$t]=1
            write_recipient_file "$AGE_DIR/$t.recipient" "$t" "$g" "$pub" "$cd" "$note"
        fi
    done < "$tsv"
}

# Build the public registry.json from the TSV (tier, gen, pub, created, note).
build_registry() {  # $1 tsv  $2 out.json  $3 created-iso  $4 master-recipient
    python3 - "$1" "$2" "$3" "$4" "$RETIRE_GRACE_DAYS" <<'PY'
import json
import sys
from datetime import date, timedelta

tsv, out, created, master, grace = sys.argv[1:6]
grace = int(grace)
tiers = {}
with open(tsv, encoding="utf-8") as fh:
    for raw in fh:
        raw = raw.rstrip("\n")
        if not raw.strip():
            continue
        tier, gen, pub, cdate, note = (raw.split("\t") + ["", "", "", "", ""])[:5]
        slot = tiers.setdefault(tier, {"current": None, "generations": {}})
        if slot["current"] is None:
            slot["current"] = gen
        entry = {
            "created": cdate,
            "public": pub,
            "retire_after": "hold" if gen == "legacy"
            else (date.fromisoformat(cdate) + timedelta(days=grace)).isoformat(),
        }
        if note and note != "generated":
            entry["note"] = note
        slot["generations"][gen] = entry

registry = {
    "version": 1,
    "created": created,
    "master": {"recipient": master, "escrow": "1password-plain"},
    "retire_grace_days": grace,
    "tiers": tiers,
}
with open(out, "w", encoding="utf-8") as fh:
    json.dump(registry, fh, indent=2, sort_keys=True)
    fh.write("\n")
PY
}

# The pre-commit hook injects a JSON-safe CCM header under the key
# "%ccm_git_header_start"; drop it so two registries compare on content alone.
registry_semantic() {  # $1 = registry path
    jq -S 'del(.["%ccm_git_header_start"])' "$1"
}

# Copy a legacy age identity's secret line into the staging tree.
# Prints "<created>\t<public>" on success.
stage_legacy_key() {  # $1 = identity path  $2 = destination .key
    local path="$1" dest="$2" line created pub
    [ -r "$path" ] || die "legacy identity not readable: $path" 3
    line="$(grep -E '^AGE-SECRET-KEY-1' "$path" | head -1 || true)"
    [ -n "$line" ] || die "no AGE-SECRET-KEY line in $path" 3
    created="$(sed -n 's/^# created: \([0-9-]\{10\}\).*/\1/p' "$path" | head -1)"
    [ -n "$created" ] || created="$(date +%F)"
    mkdir -p "$(dirname "$dest")"; chmod 700 "$(dirname "$dest")"
    ( umask 077; printf '%s\n' "$line" > "$dest" )
    chmod 600 "$dest"
    pub="$(age-keygen -y "$dest" 2>/dev/null)" || die "cannot derive a public key from $path" 3
    printf '%s\t%s\n' "$created" "$pub"
}

add_legacy_row() {  # $1 identity path, $2 staging dir, $3 tsv
    local path="$1" st="$2" tsv="$3" fields created pub
    fields="$(stage_legacy_key "$path" "$st/keys/health/legacy.key")"
    created="${fields%%$'\t'*}"
    pub="${fields#*$'\t'}"
    printf 'health\tlegacy\t%s\t%s\timported from %s\n' \
        "$pub" "$created" "$(basename "$path")" >> "$tsv"
    printf '   %-9s %-8s %s (from %s)\n' health legacy "$pub" "$(basename "$path")"
    log INFO "imported legacy identity as health/legacy"
}

cmd_init() {
    local tiers="$OPT_TIERS" gen="$OPT_GEN" legacy="$OPT_IMPORT_LEGACY"
    [ -n "$gen" ] || gen="$(default_gen)"
    if ! [[ "$gen" =~ ^[0-9]{4}Q[1-4]$ ]] && ! [[ "$gen" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        die "bad generation label: '$gen' (want 2026Q4 or 2026-10-28)" 3
    fi
    require_git_checkout
    if [ -e "$KEYRING" ]; then
        die "keyring already exists: $KEYRING - refusing to re-init (see 'list' / 'status')" 6
    fi

    local master
    master="$(resolve_master_recipient)"

    step "layout"
    printf '   master     %s\n' "$master"
    printf '   keyring    %s\n' "$KEYRING"
    printf '   registry   %s\n' "$REGISTRY"
    printf '   generation %s\n' "$gen"

    mkdir -p "$KEYRING_DIR"; chmod 700 "$KEYRING_DIR"
    if [ ! -e "$KEYRING_DIR/.tt-keys.lock" ]; then
        ( umask 077; : > "$KEYRING_DIR/.tt-keys.lock" )
    fi
    chmod 600 "$KEYRING_DIR/.tt-keys.lock" 2>/dev/null || true
    exec 9>"$KEYRING_DIR/.tt-keys.lock"
    flock -n 9 || die "another tt-keys run holds $KEYRING_DIR/.tt-keys.lock" 6

    local st="$WORK/keyring"
    mkdir -p "$st/keys"; chmod 700 "$st"
    local tsv="$WORK/tiers.tsv"; : > "$tsv"

    step "tiers"
    local t kf pub
    local -a wanted=()
    IFS=',' read -r -a wanted <<< "$tiers"
    [ "${#wanted[@]}" -gt 0 ] || die "no tiers requested" 3
    for t in "${wanted[@]}"; do
        [[ "$t" =~ ^[a-z][a-z0-9_-]*$ ]] || die "bad tier name: '$t'" 3
        mkdir -p "$st/keys/$t"; chmod 700 "$st/keys/$t"
        kf="$st/keys/$t/$gen.key"
        age-keygen -o "$kf" 2>/dev/null || die "age-keygen failed for tier $t" 4
        chmod 600 "$kf"
        pub="$(age-keygen -y "$kf" 2>/dev/null)" || die "cannot derive public key for tier $t" 4
        printf 'probe' | age -r "$pub" -o "$WORK/probe.age" \
            || die "recipient for tier $t is unusable" 5
        rm -f "$WORK/probe.age"
        printf '%s\t%s\t%s\t%s\tgenerated\n' "$t" "$gen" "$pub" "$(date +%F)" >> "$tsv"
        printf '   %-9s %-8s %s\n' "$t" "$gen" "$pub"
    done

    if [ -n "$legacy" ]; then
        step "legacy identity"
        add_legacy_row "$legacy" "$st" "$tsv"
    fi

    step "registry"
    build_registry "$tsv" "$st/registry.json" "$(date --iso-8601=seconds)" "$master" \
        || die "cannot build registry.json" 4
    jq -e . "$st/registry.json" >/dev/null || die "registry.json is not valid JSON" 4
    install -m 0644 "$st/registry.json" "$REGISTRY"
    log INFO "published $REGISTRY (public: tier names, generation labels, public keys)"

    step "recipients"
    write_recipients "$tsv"
    log INFO "wrote $AGE_DIR/<tier>.recipient and $AGE_DIR/history/*.recipient"

    step "keyring"
    wrap_keyring "$st"

    cat <<NEXT

-----------------------------------------------------------------------------
PHASE 1 COMPLETE. Next, in this order:

  1. PROVE IT (needs the master identity - it prompts, nothing is persisted):
       $0 verify

  2. Review what will be committed. It must be public material only:
       git -C $REPO_DIR status --short infra/backups/age .gitignore
       git -C $REPO_DIR diff -- infra/backups/age

  3. Phase 2 (deploy hardening + 'jotta-cli add $KEYRING_DIR'), then
     Phase 3 (wire the tiers into backup-tthealth.sh / backup-mail.py).

Not implemented yet: rotate / rewrap / audit / prune (phase 5). Until then,
generation ${gen} is current and health/legacy covers every existing backup.
-----------------------------------------------------------------------------
NEXT
}

cmd_list() {
    [ -r "$REGISTRY" ] || die "no registry: $REGISTRY (run 'init' first)" 3
    jq -e . "$REGISTRY" >/dev/null 2>&1 || die "registry is not valid JSON: $REGISTRY" 4
    printf '%-9s %-11s %-12s %-13s %s\n' TIER GENERATION CREATED RETIRE_AFTER PUBLIC
    local t g cur
    for t in $(jq -r '.tiers | keys[]' "$REGISTRY"); do
        cur="$(jq -r --arg t "$t" '.tiers[$t].current' "$REGISTRY")"
        for g in $(jq -r --arg t "$t" '.tiers[$t].generations | keys[]' "$REGISTRY"); do
            printf '%-9s %-11s %-12s %-13s %s%s\n' \
                "$t" "$g" \
                "$(jq -r --arg t "$t" --arg g "$g" '.tiers[$t].generations[$g].created' "$REGISTRY")" \
                "$(jq -r --arg t "$t" --arg g "$g" '.tiers[$t].generations[$g].retire_after' "$REGISTRY")" \
                "$(jq -r --arg t "$t" --arg g "$g" '.tiers[$t].generations[$g].public' "$REGISTRY")" \
                "$([ "$g" = "$cur" ] && printf ' <- current')"
        done
    done
}

cmd_status() {
    local rc=0
    [ -r "$REGISTRY" ] || die "no registry: $REGISTRY" 3
    jq -e . "$REGISTRY" >/dev/null 2>&1 || die "registry is not valid JSON: $REGISTRY" 4

    local master
    master="$(jq -r '.master.recipient' "$REGISTRY")"

    step "master"
    printf '   escrow     %s\n' "$(jq -r '.master.escrow' "$REGISTRY")"
    printf '   recipient  %s\n' "$master"
    if [ -r "$MASTER_RECIPIENT_FILE" ]; then
        local filepub
        filepub="$(grep -Ev '^[[:space:]]*(#|$)' "$MASTER_RECIPIENT_FILE" | head -1)"
        printf '   source     %s\n' "$MASTER_RECIPIENT_FILE"
        if [ "$filepub" != "$master" ]; then
            printf '   state      DRIFT (file says %s)\n' "$filepub"
            rc=1
        fi
    else
        printf '   source     MISSING: %s\n' "$MASTER_RECIPIENT_FILE"
        rc=1
    fi

    step "keyring"
    printf '   path       %s\n' "$KEYRING"
    if [ -r "$KEYRING" ]; then
        printf '   size       %s\n' "$(du -h "$KEYRING" | cut -f1)"
        printf '   modified   %s\n' "$(stat -c '%y' "$KEYRING" | cut -d. -f1)"
        printf '   owner      %s\n' "$(stat -c '%A %U:%G' "$KEYRING")"
        if [ "$(head -c 21 "$KEYRING" 2>/dev/null || true)" = "age-encryption.org/v1" ]; then
            printf '   format     age (ciphertext)\n'
        else
            printf '   format     NOT an age file\n'
            rc=1
        fi
    else
        printf '   state      MISSING\n'
        rc=1
    fi

    step "tiers"
    printf '   %-9s %-9s %-13s %-17s %s\n' TIER CURRENT RETIRE_AFTER RECIPIENT_16 STATE
    local t cur ret state short today
    today="$(date +%F)"
    for t in $(jq -r '.tiers | keys[]' "$REGISTRY"); do
        cur="$(jq -r --arg t "$t" '.tiers[$t].current' "$REGISTRY")"
        ret="$(jq -r --arg t "$t" --arg g "$cur" '.tiers[$t].generations[$g].retire_after' "$REGISTRY")"
        if [ -r "$AGE_DIR/$t.recipient" ]; then
            if [ "$(grep -Ev '^[[:space:]]*(#|$)' "$AGE_DIR/$t.recipient" | head -1)" \
                 = "$(jq -r --arg t "$t" --arg g "$cur" '.tiers[$t].generations[$g].public' "$REGISTRY")" ]; then
                short="$(grep -Ev '^[[:space:]]*(#|$)' "$AGE_DIR/$t.recipient" | head -1 | cut -c1-16)"
                state=ok
            else
                short="$(grep -Ev '^[[:space:]]*(#|$)' "$AGE_DIR/$t.recipient" | head -1 | cut -c1-16)"
                state="DRIFT vs registry"
                rc=1
            fi
        else
            short="-"
            state="MISSING $t.recipient"
            rc=1
        fi
        if [ "$ret" != "hold" ] && [[ "$ret" < "$today" ]]; then
            state="$state, rotation overdue"
            rc=1
        fi
        printf '   %-9s %-9s %-13s %-17s %s\n' "$t" "$cur" "$ret" "$short" "$state"
    done

    printf '\n'
    if [ "$rc" -eq 0 ]; then
        log INFO "status: OK (keyring, recipients and registry agree)"
    else
        log WARNING "status: issues found - see STATE above"
    fi
    exit "$rc"
}

cmd_verify() {
    local -a want=("$@")
    local d="$WORK/unwrapped"
    unwrap_keyring "$d"

    if ! diff <(registry_semantic "$d/registry.json") <(registry_semantic "$REGISTRY") \
         >/dev/null 2>&1; then
        log WARNING "repo registry.json differs from the keyring copy - run 'status'"
    fi

    local master_reg master_file
    master_reg="$(jq -r '.master.recipient' "$d/registry.json")"
    master_file="$(resolve_master_recipient)"
    if [ "$master_reg" != "$master_file" ]; then
        die "master recipient mismatch: keyring says $master_reg, $MASTER_RECIPIENT_FILE says $master_file" 5
    fi
    log INFO "master recipient matches the keyring: $(printf '%s' "$master_reg" | cut -c1-16)..."

    local tiers t gen key pub reg probe out rc=0
    local -a list=()
    if [ "${#want[@]}" -gt 0 ]; then
        tiers="$(IFS=,; printf '%s' "${want[*]}")"
    else
        tiers="$(jq -r '.tiers | keys | join(",")' "$d/registry.json")"
    fi
    IFS=',' read -r -a list <<< "$tiers"

    step "round-trip"
    for t in "${list[@]}"; do
        gen="$(jq -r --arg t "$t" '.tiers[$t].current // empty' "$d/registry.json")"
        if [ -z "$gen" ]; then
            log ERROR "$t: not in the keyring registry"
            rc=5
            continue
        fi
        key="$d/keys/$t/$gen.key"
        if [ ! -f "$key" ]; then
            log ERROR "$t/$gen: key material missing from the keyring"
            rc=5
            continue
        fi
        pub="$(age-keygen -y "$key" 2>/dev/null || true)"
        reg="$(jq -r --arg t "$t" --arg g "$gen" '.tiers[$t].generations[$g].public' "$d/registry.json")"
        if [ "$pub" != "$reg" ]; then
            log ERROR "$t/$gen: keyring public key ($pub) != registry ($reg)"
            rc=5
            continue
        fi
        probe="tt-keys probe $(date --iso-8601=seconds)"
        if ! printf '%s' "$probe" | age -r "$pub" -o "$WORK/probe.age"; then
            log ERROR "$t/$gen: cannot encrypt to $pub"
            rc=5
            continue
        fi
        if ! out="$(age -d -i "$key" "$WORK/probe.age" 2>/dev/null)"; then
            log ERROR "$t/$gen: cannot decrypt with the unwrapped DEK"
            rc=5
            continue
        fi
        rm -f "$WORK/probe.age"
        if [ "$out" != "$probe" ]; then
            log ERROR "$t/$gen: round-trip plaintext mismatch"
            rc=5
            continue
        fi
        log INFO "$t/$gen: OK (master -> DEK -> ciphertext -> plaintext)"
    done
    [ "$rc" -eq 0 ] || die "verification failed" 5
    log INFO "verify: every requested tier round-trips"
}

cmd_unlock() {
    local spec="$OPT_SPEC" tier gen
    [ -n "$spec" ] || die "unlock needs <tier>[:<generation>]" 3
    tier="${spec%%:*}"
    gen="${spec#*:}"
    [ "$gen" = "$spec" ] && gen=""

    local d="$WORK/unwrapped"
    unwrap_keyring "$d"

    if [ -z "$gen" ]; then
        gen="$(jq -r --arg t "$tier" '.tiers[$t].current // empty' "$d/registry.json")"
        [ -n "$gen" ] || die "tier '$tier' is not in the keyring registry" 3
    fi
    local src="$d/keys/$tier/$gen.key"
    [ -f "$src" ] || die "no key material for $tier/$gen in the keyring" 3

    local out="$OPT_OUT"
    if [ -z "$out" ]; then
        local keep
        keep="$(mktemp -d "$TMPBASE/tt-unlock.XXXXXX")"
        chmod 700 "$keep"
        out="$keep/$tier-$gen.key"
    fi
    install -m 0600 "$src" "$out"
    # stdout must be EXACTLY the path, so callers can do KEY=$(tt-keys.sh unlock ...)
    log INFO "unwrapped $tier/$gen ($(age-keygen -y "$out" | cut -c1-16)...)" >&2
    printf '%s\n' "$out"
    log WARNING "plaintext DEK at $out - run 'shred -u $out' when you are done" >&2
}

cmd_import_legacy() {
    local path="${1:-}"
    [ -n "$path" ] || die "import-legacy needs the identity file path" 3
    require_git_checkout

    local d="$WORK/unwrapped"
    unwrap_keyring "$d"
    if [ -f "$d/keys/health/legacy.key" ]; then
        die "health/legacy is already in the keyring - nothing to do" 6
    fi

    local fields created pub
    fields="$(stage_legacy_key "$path" "$d/keys/health/legacy.key")"
    created="${fields%%$'\t'*}"
    pub="${fields#*$'\t'}"

    jq --arg t health --arg g legacy --arg pub "$pub" --arg cd "$created" \
       --arg note "imported from $(basename "$path")" \
       '.tiers[$t].generations[$g] = {created:$cd, public:$pub, retire_after:"hold", note:$note}' \
       "$d/registry.json" > "$d/registry.json.new"
    mv -f "$d/registry.json.new" "$d/registry.json"
    install -m 0644 "$d/registry.json" "$REGISTRY"

    mkdir -p "$AGE_DIR/history"
    write_recipient_file "$AGE_DIR/history/health-legacy.recipient" \
        health legacy "$pub" "$created" "imported from $(basename "$path")"

    wrap_keyring "$d"
    log INFO "health/legacy added (public $(printf '%s' "$pub" | cut -c1-16)...)"
}

# --- phase 5: safety rails and inventory -------------------------------------
# Key state (registry + recipients) must live in a checkout: a deploy target is
# rsynced with --delete and would silently revert it, leaving the keyring ahead
# of the registry that is supposed to describe it.
require_git_checkout() {
    if [ "$OPT_ALLOW_NON_GIT" -eq 1 ]; then
        log WARNING "--allow-non-git: writing key state outside a git checkout (rehearsal only)"
        return 0
    fi
    local top
    top="$(git -C "$AGE_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
    if [ -z "$top" ]; then
        die "refusing to modify key state outside a git checkout: $AGE_DIR
       A deploy target (e.g. /srv/prd/tt) is rsynced with --delete, which would
       silently revert the registry and leave the keyring ahead of it.
       Rotate in the checkout, commit, deploy, then re-run the installer.
       (--allow-non-git overrides this for sandboxes and rehearsals.)" 6
    fi
    log INFO "git checkout: $top"
}

require_yes() {  # $1 = what is about to happen
    if [ "$OPT_YES" -ne 1 ]; then
        die "$1 is irreversible - re-run with --yes if you mean it" 6
    fi
}

# Inventory of artifacts on disk: "<tier>\t<gen>\t<count>\t<newest-date>".
# Two sources, because the two jobs record the generation differently:
#   * filenames  ...__<tier>-<gen>.dump.age   (pg dumps; unsuffixed = pre-cutover)
#   * thunderbird/state.json entries          (mail chunks; tier/generation keys)
scan_artifacts() {
    python3 - "$@" <<'PY'
import json
import os
import re
import sys
from datetime import datetime

dirs = sys.argv[1:]
refs = {}
name_re = re.compile(r"__(?P<tier>[a-z][a-z0-9_-]*)-(?P<gen>[0-9A-Za-z._-]+)\.dump\.age$")


def bump(tier, gen, mtime):
    slot = refs.setdefault((tier, gen), [0, 0.0])
    slot[0] += 1
    slot[1] = max(slot[1], mtime)


for d in dirs:
    if not os.path.isdir(d):
        continue
    for fn in os.listdir(d):
        path = os.path.join(d, fn)
        if fn.endswith(".dump.age"):
            m = name_re.search(fn)
            if m:
                bump(m.group("tier"), m.group("gen"), os.path.getmtime(path))
            else:
                # Every pre-cutover dump was encrypted to the legacy identity.
                bump("health", "legacy", os.path.getmtime(path))
    state = os.path.join(d, "state.json")
    if os.path.isfile(state):
        try:
            with open(state, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        for entry in (data.get("periods") or {}).values():
            # Pre-cutover chunks carry no tier: they were all sealed with the one
            # legacy keypair, which the registry records once (health/legacy).
            # Inventing a "mail/legacy" generation would report an orphan key
            # that never existed.
            bump(entry.get("tier") or "health",
                 entry.get("generation") or "legacy", 0.0)

for (tier, gen), (count, newest) in sorted(refs.items()):
    when = datetime.fromtimestamp(newest).strftime("%Y-%m-%d") if newest else "-"
    print(f"{tier}\t{gen}\t{count}\t{when}")
PY
}

# Join the inventory against the registry. Exit 1 when something needs a human.
audit_report() {  # $1 = registry, $2 = scan.tsv
    python3 - "$1" "$2" <<'PY'
import json
import sys
from datetime import date

with open(sys.argv[1], encoding="utf-8") as fh:
    registry = json.load(fh)
rows = {}
with open(sys.argv[2], encoding="utf-8") as fh:
    for line in fh:
        tier, gen, count, newest = line.rstrip("\n").split("\t")
        rows[(tier, gen)] = (int(count), newest)

today = date.today().isoformat()
bad = 0
print(f"  {'TIER':<8} {'GENERATION':<11} {'FILES':>5}  {'NEWEST':<12} "
      f"{'RETIRE_AFTER':<13} VERDICT")
for tier, tdata in sorted(registry.get("tiers", {}).items()):
    current = tdata.get("current")
    for gen, meta in sorted(tdata.get("generations", {}).items()):
        count, newest = rows.pop((tier, gen), (0, "-"))
        retire = meta.get("retire_after", "?")
        retired = meta.get("retired")
        if retired:
            verdict = f"retired {retired}"
            if count:
                verdict += " BUT STILL REFERENCED"
                bad = 1
        elif gen == current:
            verdict = "current"
        elif count and gen == "legacy":
            verdict = f"pre-cutover key, referenced by {count}"
        elif count:
            verdict = f"referenced by {count} artifact(s)"
        elif retire == "hold":
            verdict = "hold - never auto-retire"
        else:
            verdict = "unreferenced"
            if retire != "?" and retire < today:
                verdict += " (retire_after passed)"
        print(f"  {tier:<8} {gen:<11} {count:>5}  {newest:<12} {retire:<13} {verdict}")
for (tier, gen), (count, newest) in sorted(rows.items()):
    print(f"  {tier:<8} {gen:<11} {count:>5}  {newest:<12} {'-':<13} "
          f"ORPHAN: {count} artifact(s) with no such generation in the registry")
    bad = 1
sys.exit(bad)
PY
}

# Directories scanned by audit/prune. TT_AUDIT_DIRS (colon-separated) overrides,
# which is also how the rehearsals keep themselves hermetic.
AUDIT_DIRS=()
audit_dir_list() {
    AUDIT_DIRS=()
    if [ -n "${TT_AUDIT_DIRS:-}" ]; then
        IFS=':' read -r -a AUDIT_DIRS <<< "$TT_AUDIT_DIRS"
    else
        AUDIT_DIRS=("$BACKUP_ROOT/tthealth" "$HOME/backups/tthealth" "$BACKUP_ROOT/thunderbird")
    fi
    printf '%s\n' "${AUDIT_DIRS[@]}"
}

cmd_audit() {
    [ -r "$REGISTRY" ] || die "no registry: $REGISTRY" 3
    jq -e . "$REGISTRY" >/dev/null 2>&1 || die "registry is not valid JSON: $REGISTRY" 4

    local scan="$WORK/inventory.tsv"
    step "inventory"
    # Not a pipeline: a pipeline would run audit_dir_list in a subshell and throw
    # away the AUDIT_DIRS it populates.
    audit_dir_list >/dev/null
    printf '   %s\n' "${AUDIT_DIRS[@]}"
    scan_artifacts "${AUDIT_DIRS[@]}" > "$scan"

    step "generations"
    local rc=0
    audit_report "$REGISTRY" "$scan" || rc=$?

    printf '\n'
    if [ "$rc" -eq 0 ]; then
        log INFO "audit: every generation is accounted for"
    else
        log WARNING "audit: something above needs a human (orphan artifact, or a retired key still in use)"
    fi
    exit "$rc"
}

cmd_rotate() {
    local tier="${1:-}" gen="$OPT_GEN"
    [ -n "$tier" ] || die "rotate needs a tier (health|mail|general)" 3
    [ -n "$gen" ] || gen="$(default_gen)"
    [[ "$gen" =~ ^[0-9]{4}Q[1-4]$ ]] || die "bad generation label: '$gen' (want 2027Q1)" 3
    require_git_checkout
    [ -r "$REGISTRY" ] || die "no registry: $REGISTRY" 3

    jq -er --arg t "$tier" '.tiers[$t].current' "$REGISTRY" >/dev/null 2>&1 \
        || die "tier '$tier' is not in the registry" 3
    if jq -e --arg t "$tier" --arg g "$gen" '.tiers[$t].generations[$g]' "$REGISTRY" >/dev/null 2>&1; then
        die "generation $tier/$gen already exists - pick another label" 6
    fi

    local d="$WORK/rotate"
    unwrap_keyring "$d"

    step "new generation"
    mkdir -p "$d/keys/$tier"; chmod 700 "$d/keys/$tier"
    local key="$d/keys/$tier/$gen.key" pub created probe out
    age-keygen -o "$key" 2>/dev/null || die "age-keygen failed" 4
    chmod 600 "$key"
    pub="$(age-keygen -y "$key")" || die "cannot derive the new public key" 4
    printf '   %-8s %-9s %s\n' "$tier" "$gen" "$pub"

    # Prove the pair works BEFORE anything live changes.
    probe="rotate probe $(date --iso-8601=seconds)"
    printf '%s' "$probe" | age -r "$pub" -o "$WORK/p.age" || die "new recipient cannot encrypt" 5
    out="$(age -d -i "$key" "$WORK/p.age")" || die "new key cannot decrypt" 5
    [ "$out" = "$probe" ] || die "round-trip mismatch for the new key" 5
    rm -f "$WORK/p.age"
    log INFO "new DEK round-trips"

    created="$(date +%F)"
    jq --arg t "$tier" --arg g "$gen" --arg pub "$pub" --arg cd "$created" \
       --arg ra "$(date -d "+${RETIRE_GRACE_DAYS} days" +%F)" \
       '.tiers[$t].generations[$g] = {created: $cd, public: $pub, retire_after: $ra}
        | .tiers[$t].current = $g | .rotated = $cd' \
       "$d/registry.json" > "$d/registry.json.new"
    mv -f "$d/registry.json.new" "$d/registry.json"

    step "keyring"
    # Keyring first: an extra DEK in it is harmless, a published generation whose
    # DEK is missing is not.
    wrap_keyring "$d"

    step "published files"
    install -m 0644 "$d/registry.json" "$REGISTRY"
    mkdir -p "$AGE_DIR/history"
    write_recipient_file "$AGE_DIR/$tier.recipient" "$tier" "$gen" "$pub" "$created" "rotated"
    write_recipient_file "$AGE_DIR/history/$tier-$gen.recipient" "$tier" "$gen" "$pub" "$created" "rotated"
    log INFO "registry and recipients now point at $tier/$gen"

    cat <<NEXT

-----------------------------------------------------------------------------
ROTATED ${tier} -> ${gen}. New artifacts are named *__${tier}-${gen}.* and are
the only ones using the new DEK; everything older keeps its own generation.

Still to do, in order:
  1. review and commit the key-state change - it is the audit trail:
       git -C $(git -C "$AGE_DIR" rev-parse --show-toplevel 2>/dev/null || echo "$AGE_DIR") status --short infra/backups/age
  2. if the service job reads /etc/tt-backup/age, re-run its installer so the
     deployed recipient matches:  sudo infra/backups/scripts/install-tt-backup-tthealth.sh
  3. prove the new key end to end:  $0 verify ${tier}
  4. see what is still encrypted under the previous generation:  $0 audit
  5. the MASTER is unchanged, so nothing needs re-escrowing today.
-----------------------------------------------------------------------------
NEXT
}


cmd_rewrap() {
    require_git_checkout
    require_yes "rewrapping the keyring under a new master"

    [ -r "$REGISTRY" ] || die "no registry: $REGISTRY" 3
    local old new
    old="$(jq -r '.master.recipient // empty' "$REGISTRY")"
    new="$OPT_NEW_RECIPIENT"
    if [ -z "$new" ] && [ -r "$MASTER_RECIPIENT_FILE" ]; then
        new="$(grep -Ev '^[[:space:]]*(#|$)' "$MASTER_RECIPIENT_FILE" | head -1)"
    fi
    [ -n "$new" ] || die "no new recipient: pass --new-recipient age1... or edit $MASTER_RECIPIENT_FILE" 3
    [[ "$new" =~ ^age1[0-9a-z]{50,}$ ]] || die "not a valid age recipient: $new" 3
    [ "$new" != "$old" ] || die "new recipient equals the current master ($old) - nothing to do" 6

    step "rewrap"
    printf '   from %s\n   to   %s\n' "$old" "$new"
    local d="$WORK/rewrap"
    unwrap_keyring "$d"          # with the OLD master
    jq --arg r "$new" --arg cd "$(date +%F)" \
       '.master.recipient = $r | .master.rewrapped = $cd' \
       "$d/registry.json" > "$d/registry.json.new"
    mv -f "$d/registry.json.new" "$d/registry.json"

    # The arg wins over the file inside resolve_master_recipient, so this wrap
    # targets the NEW recipient even before the file is rewritten.
    OPT_MASTER_RECIPIENT="$new"
    wrap_keyring "$d"
    install -m 0644 "$d/registry.json" "$REGISTRY"
    printf '%s\n' "$new" > "$MASTER_RECIPIENT_FILE"
    chmod 0644 "$MASTER_RECIPIENT_FILE"
    log INFO "master recipient repointed; registry and $MASTER_RECIPIENT_FILE updated"

    cat <<NEXT

-----------------------------------------------------------------------------
!! VERIFY BEFORE YOU WALK AWAY - the keyring is now wrapped to a key that this
   host cannot test on its own:

     TT_MASTER_FILE=<the NEW master identity> $0 verify

   Do not delete, rotate or overwrite the OLD master until that passes. If it
   fails, the keyring is wrapped to a key you cannot use and the DEKs are lost.
-----------------------------------------------------------------------------
NEXT
}

cmd_prune() {
    [ -r "$REGISTRY" ] || die "no registry: $REGISTRY" 3
    local scan="$WORK/inventory.tsv"
    audit_dir_list >/dev/null
    scan_artifacts "${AUDIT_DIRS[@]}" > "$scan"

    if [ -z "$OPT_RETIRE" ]; then
        step "generations"
        local rc=0
        audit_report "$REGISTRY" "$scan" || rc=$?
        printf '\n'
        log INFO "advisory only - nothing was changed. A generation may be retired when it is"
        log INFO "not current, not 'hold', and referenced by no artifact. To destroy one:"
        printf '     %s prune --retire <tier>:<generation> --yes\n' "$0"
        exit "$rc"
    fi

    local tier="${OPT_RETIRE%%:*}" gen="${OPT_RETIRE#*:}"
    if [ "$gen" = "$OPT_RETIRE" ] || [ -z "$tier" ] || [ -z "$gen" ]; then
        die "--retire wants <tier>:<generation>, e.g. health:2026Q4" 3
    fi
    require_git_checkout
    require_yes "destroying the private half of $tier/$gen"

    [ "$(jq -r --arg t "$tier" '.tiers[$t].current // empty' "$REGISTRY")" != "$gen" ] \
        || die "$tier/$gen is the CURRENT generation - rotate first" 6
    [ "$(jq -r --arg t "$tier" --arg g "$gen" '.tiers[$t].generations[$g].retire_after // empty' "$REGISTRY")" != "hold" ] \
        || die "$tier/$gen is 'hold': pre-cutover backups depend on it, never retire it" 6
    if awk -F'\t' -v t="$tier" -v g="$gen" '$1 == t && $2 == g && $3 > 0 { found = 1 } END { exit !found }' "$scan"; then
        die "$tier/$gen is still referenced by artifacts on disk - see '$0 audit'" 6
    fi

    local d="$WORK/prune"
    unwrap_keyring "$d"
    local key="$d/keys/$tier/$gen.key"
    [ -f "$key" ] || die "no key material for $tier/$gen in the keyring" 4
    shred -u "$key"
    jq --arg t "$tier" --arg g "$gen" --arg cd "$(date +%F)" \
       '.tiers[$t].generations[$g].retired = $cd' "$d/registry.json" > "$d/registry.json.new"
    mv -f "$d/registry.json.new" "$d/registry.json"

    wrap_keyring "$d"
    install -m 0644 "$d/registry.json" "$REGISTRY"
    log INFO "retired $tier/$gen: key material destroyed, registry entry kept for provenance"
    log WARNING "any copy of an artifact still in Jotta or on a rotation disk for this generation is now unreadable"
}


parse_init_opts() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --tiers)              OPT_TIERS="${2:?--tiers needs a value}"; shift 2 ;;
            --tiers=*)            OPT_TIERS="${1#*=}"; shift ;;
            --allow-non-git)      OPT_ALLOW_NON_GIT=1; shift ;;
            --gen)                OPT_GEN="${2:?--gen needs a value}"; shift 2 ;;
            --gen=*)              OPT_GEN="${1#*=}"; shift ;;
            --import-legacy)      OPT_IMPORT_LEGACY="${2:?--import-legacy needs a path}"; shift 2 ;;
            --import-legacy=*)    OPT_IMPORT_LEGACY="${1#*=}"; shift ;;
            --master-recipient)   OPT_MASTER_RECIPIENT="${2:?--master-recipient needs a value}"; shift 2 ;;
            --master-recipient=*) OPT_MASTER_RECIPIENT="${1#*=}"; shift ;;
            -h|--help)            usage; exit 0 ;;
            *)                    usage >&2; die "unknown option: $1" 3 ;;
        esac
    done
}

parse_unlock_opts() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --out)     OPT_OUT="${2:?--out needs a path}"; shift 2 ;;
            --out=*)   OPT_OUT="${1#*=}"; shift ;;
            -h|--help) usage; exit 0 ;;
            -*)        usage >&2; die "unknown option: $1" 3 ;;
            *)
                [ -z "$OPT_SPEC" ] || die "unlock takes exactly one <tier>[:<generation>]" 3
                OPT_SPEC="$1"
                shift
                ;;
        esac
    done
}

# Shared flags for audit / rotate / rewrap / prune.
parse_verb_opts() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --yes)             OPT_YES=1; shift ;;
            --allow-non-git)   OPT_ALLOW_NON_GIT=1; shift ;;
            --gen)             OPT_GEN="${2:?--gen needs a value}"; shift 2 ;;
            --gen=*)           OPT_GEN="${1#*=}"; shift ;;
            --new-recipient)   OPT_NEW_RECIPIENT="${2:?--new-recipient needs a value}"; shift 2 ;;
            --new-recipient=*) OPT_NEW_RECIPIENT="${1#*=}"; shift ;;
            --retire)          OPT_RETIRE="${2:?--retire needs <tier>:<gen>}"; shift 2 ;;
            --retire=*)        OPT_RETIRE="${1#*=}"; shift ;;
            -h|--help)         usage; exit 0 ;;
            -*)                usage >&2; die "unknown option: $1" 3 ;;
            *)
                [ -z "$OPT_SPEC" ] || die "unexpected extra argument: $1" 3
                OPT_SPEC="$1"
                shift
                ;;
        esac
    done
}

main() {
    local cmd="${1:-}"
    if [ $# -gt 0 ]; then
        shift
    fi
    case "$cmd" in
        init)          parse_init_opts "$@"; require_tools; cmd_init ;;
        list)          require_tools; cmd_list ;;
        status)        require_tools; cmd_status ;;
        verify)        require_tools; cmd_verify "$@" ;;
        unlock)        parse_unlock_opts "$@"; require_tools; cmd_unlock ;;
        import-legacy) parse_verb_opts "$@"; require_tools; cmd_import_legacy "$OPT_SPEC" ;;
        audit)         require_tools; cmd_audit ;;
        rotate)        parse_verb_opts "$@"; require_tools; cmd_rotate "$OPT_SPEC" ;;
        rewrap)        parse_verb_opts "$@"; require_tools; cmd_rewrap ;;
        prune)         parse_verb_opts "$@"; require_tools; cmd_prune ;;
        ""|-h|--help|help) usage; exit 0 ;;
        *)             usage >&2; die "unknown command: $cmd" 3 ;;
    esac
}

main "$@"


