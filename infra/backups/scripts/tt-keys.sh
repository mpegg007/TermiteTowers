#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/backups/scripts/tt-keys.sh@188 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 6d70024c57678b2d4c519774f1e33c99dcd729a9 %
#  %ccm_git_commit_id: 311e8d32faa5df27eca3c67f5837a007bc611e6f %
#  %ccm_git_commit_count: 188 %
#  %ccm_git_commit_date: 2026-10-28 11:38:38 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: fix(backups): unlock used an undefined jq variable, and polluted stdout %
#  %ccm_git_modify_date: 2026-10-28 11:38:39 %
#  %ccm_git_file_last_modified: 2026-10-28 11:38:28 %
#  %ccm_git_file_name: tt-keys.sh %
#  %ccm_git_path: infra/backups/scripts/tt-keys.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 26723 %
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
#
# NOT YET (phase 5): rotate, rewrap, audit, prune, restore wiring. Phases 2-3
# wire the tiers into backup-tthealth.sh / backup-mail.py.
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

parse_init_opts() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --tiers)              OPT_TIERS="${2:?--tiers needs a value}"; shift 2 ;;
            --tiers=*)            OPT_TIERS="${1#*=}"; shift ;;
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
        import-legacy) require_tools; cmd_import_legacy "${1:-}" ;;
        ""|-h|--help|help) usage; exit 0 ;;
        *)             usage >&2; die "unknown command: $cmd" 3 ;;
    esac
}

main "$@"


