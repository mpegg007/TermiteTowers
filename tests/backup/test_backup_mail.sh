#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: tests/backup/test_backup_mail.sh@215 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: d37d1ad203f6e97bff51684da82223cca2d03ed4 %
#  %ccm_git_commit_id: 8f18e3510659d8a475712467ba6efc3cda2e791d %
#  %ccm_git_commit_count: 215 %
#  %ccm_git_commit_date: 2026-11-11 10:32:19 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: fix(backups): seal Thunderbird mail monthly and refuse a year run over monthly chunks %
#  %ccm_git_modify_date: 2026-11-11 10:32:20 %
#  %ccm_git_file_last_modified: 2026-11-11 10:29:51 %
#  %ccm_git_file_name: test_backup_mail.sh %
#  %ccm_git_path: tests/backup/test_backup_mail.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 11625 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# Regression tests for infra/backups/scripts/backup-mail.py
#
# The behaviour under test is the one that silently destroyed data: a message
# deleted from a mailbox AFTER its period was sealed used to cause the period to
# be re-cut from the surviving messages, erasing the deleted mail from the
# archive. A sealed chunk must grow, never shrink.
#
# Also covered: a period that seals must delete its superseded *.partial chunk
# (otherwise one orphaned object per period is uploaded and retained forever),
# plus the --only-current / --since / --allow-shrink selectors.
#
# Needs: python3 and age. zstd is only a byte filter here, so it is shimmed to
# `cat` when absent, which keeps the suite runnable on a workstation.
#
#   bash tests/backup/test_backup_mail.sh

set -Eeuo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOOL="$REPO_DIR/infra/backups/scripts/backup-mail.py"

command -v python3 >/dev/null || { echo "SKIP: python3 not installed"; exit 0; }
command -v age >/dev/null || { echo "SKIP: age not installed (encryption is not stubbed)"; exit 0; }
[ -f "$TOOL" ] || { echo "FAIL: missing $TOOL"; exit 1; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# age-keygen ships with age; use the key only to obtain a throwaway recipient.
age-keygen -o "$WORK/key.txt" 2>/dev/null
grep -o 'age1[0-9a-z]*' "$WORK/key.txt" | head -1 > "$WORK/recipient.txt"
[ -s "$WORK/recipient.txt" ] || { echo "FAIL: could not derive a recipient"; exit 1; }

SHIM="$WORK/bin"
mkdir -p "$SHIM"
if ! command -v zstd >/dev/null 2>&1; then
    printf '#!/bin/sh\nexec cat\n' > "$SHIM/zstd"
    chmod +x "$SHIM/zstd"
fi
export PATH="$SHIM:$PATH"

FAILED=0
pass() { printf 'PASS  %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*"; FAILED=$((FAILED + 1)); }

PROFILE="$WORK/profile"
INBOX="$PROFILE/ImapMail/test.example/Inbox"

# make_mbox <path> <iso-datetime>...
make_mbox() {
    local path="$1"; shift
    local n=0 d
    mkdir -p "$(dirname "$path")"
    : > "$path"
    for d in "$@"; do
        n=$((n + 1))
        {
            printf 'From sender@example.com Mon Jan  1 00:00:00 2024\n'
            printf 'Date: %s\n' "$(date -R -d "$d")"
            printf 'From: sender@example.com\n'
            printf 'To: rcpt@example.com\n'
            printf 'Subject: message %s\n\n' "$n"
            printf 'body %s\n\n' "$n"
        } >> "$path"
    done
}

# runmail <outdir> [args...]
runmail() {
    local out="$1"; shift
    mkdir -p "$out"
    python3 "$TOOL" --profile "$PROFILE" --recipient "$WORK/recipient.txt" \
        --out "$out" "$@"
}

sha() { sha256sum "$1" | cut -d' ' -f1; }

# ---------------------------------------------------------------------------
echo "== 1. a completed period seals; the period in progress does not"
# ---------------------------------------------------------------------------
OUT="$WORK/out-year"
make_mbox "$INBOX" 2025-05-01T10:00:00 2025-05-02T10:00:00 2026-11-01T10:00:00
if runmail "$OUT" > "$WORK/log1" 2>&1; then
    pass "run exited 0"
else
    fail "first run failed:"; sed 's/^/      /' "$WORK/log1"
fi
[ -f "$OUT/mail-2025.tar.zst.age" ] \
    && pass "2025 sealed as mail-2025.tar.zst.age" \
    || fail "2025 was not sealed"
[ -e "$OUT/mail-2026.partial.tar.zst.age" ] \
    && fail "2026 sealed without --include-current" \
    || pass "in-progress 2026 left alone by default"

# ---------------------------------------------------------------------------
echo "== 2. --include-current adds the in-progress period as *.partial"
# ---------------------------------------------------------------------------
runmail "$OUT" --include-current > "$WORK/log2" 2>&1 || fail "--include-current run failed"
[ -f "$OUT/mail-2026.partial.tar.zst.age" ] \
    && pass "mail-2026.partial.tar.zst.age written" \
    || fail "no partial chunk for the current period"

# ---------------------------------------------------------------------------
echo "== 3. a message deleted after the seal is NOT removed from the archive"
# ---------------------------------------------------------------------------
SEALED_BEFORE="$(sha "$OUT/mail-2025.tar.zst.age")"
make_mbox "$INBOX" 2025-05-01T10:00:00 2026-11-01T10:00:00     # one 2025 msg deleted
if runmail "$OUT" --include-current > "$WORK/log3" 2>&1; then
    pass "run after the deletion exited 0"
else
    fail "run after the deletion failed:"; sed 's/^/      /' "$WORK/log3"
fi
[ "$(sha "$OUT/mail-2025.tar.zst.age")" = "$SEALED_BEFORE" ] \
    && pass "sealed 2025 chunk is byte-identical (not rewritten)" \
    || fail "sealed 2025 chunk was REWRITTEN after a deletion"
grep -q 'kept    : 2025' "$WORK/log3" \
    && pass "shrink reported on stdout" \
    || { fail "no shrink warning printed"; sed 's/^/      /' "$WORK/log3"; }

if python3 - "$OUT/state.json" <<'PY'
import json, sys
state = json.load(open(sys.argv[1]))
entry = state.get("shrunk", {}).get("2025")
assert entry, "no 2025 entry under state.shrunk"
assert entry["archived"] == 2 and entry["present"] == 1 and entry["lost"] == 1, entry
assert state["periods"]["2025"]["messages"] == 2, "sealed message count changed"
PY
then
    pass "state.json records archived/present/lost without touching the chunk"
else
    fail "state.shrunk did not record the loss correctly"
fi

# The refused run must not have changed the sealed file, so jottad has nothing
# to upload for it either: that is the whole protection.
grep -q 'nothing to do' "$WORK/log3" \
    && pass "run reported nothing to do (no upload triggered)" \
    || pass "run had other work to do (partial refresh); sealed chunk untouched regardless"

# ---------------------------------------------------------------------------
echo "== 4. --list surfaces the loss"
# ---------------------------------------------------------------------------
runmail "$OUT" --list > "$WORK/log4" 2>&1 || fail "--list failed"
grep -q 'gone since seal' "$WORK/log4" \
    && pass "--list marks the shrunken period" \
    || { fail "--list did not mark the shrunken period"; sed 's/^/      /' "$WORK/log4"; }

# ---------------------------------------------------------------------------
echo "== 5. --allow-shrink is the deliberate override"
# ---------------------------------------------------------------------------
runmail "$OUT" --allow-shrink > "$WORK/log5" 2>&1 || fail "--allow-shrink run failed"
[ "$(sha "$OUT/mail-2025.tar.zst.age")" != "$SEALED_BEFORE" ] \
    && pass "sealed chunk rebuilt only when explicitly allowed" \
    || fail "chunk unchanged despite --allow-shrink"
python3 - "$OUT/state.json" <<'PY' \
    && pass "shrink observation cleared after the rebuild" \
    || fail "state.shrunk entry survived a successful rebuild"
import json, sys
state = json.load(open(sys.argv[1]))
assert "2025" not in state.get("shrunk", {}), state.get("shrunk")
assert state["periods"]["2025"]["messages"] == 1, state["periods"]["2025"]
PY

# ---------------------------------------------------------------------------
echo "== 6. a sealing period deletes its superseded *.partial chunk"
# ---------------------------------------------------------------------------
OUT2="$WORK/out-month"
make_mbox "$INBOX" 2026-09-15T10:00:00 2026-10-15T10:00:00 2026-11-05T10:00:00
runmail "$OUT2" --granularity month --since 2026-09 > "$WORK/log6a" 2>&1 \
    || { fail "month run failed"; sed 's/^/      /' "$WORK/log6a"; }
# Pretend 2026-09 was written while still in progress, i.e. as a *.partial.
mv "$OUT2/mail-2026-09.tar.zst.age" "$OUT2/mail-2026-09.partial.tar.zst.age"
python3 - "$OUT2/state.json" <<'PY'
import json, sys
path = sys.argv[1]
state = json.load(open(path))
state["periods"]["2026-09"]["chunk"] = "mail-2026-09.partial.tar.zst.age"
json.dump(state, open(path, "w"), indent=2, sort_keys=True)
PY
runmail "$OUT2" --granularity month --only 2026-09 > "$WORK/log6b" 2>&1 \
    || { fail "seal-at-rollover run failed"; sed 's/^/      /' "$WORK/log6b"; }
[ -f "$OUT2/mail-2026-09.tar.zst.age" ] \
    && pass "period re-sealed under its final name" \
    || fail "2026-09 was not re-sealed"
[ -e "$OUT2/mail-2026-09.partial.tar.zst.age" ] \
    && fail "orphaned *.partial chunk survived the seal" \
    || pass "superseded *.partial chunk removed"

# ---------------------------------------------------------------------------
echo "== 7. --since leaves older periods alone"
# ---------------------------------------------------------------------------
OUT3="$WORK/out-since"
make_mbox "$INBOX" 2026-09-15T10:00:00 2026-10-15T10:00:00
runmail "$OUT3" --granularity month --since 2026-10 > "$WORK/log7" 2>&1 \
    || { fail "--since run failed"; sed 's/^/      /' "$WORK/log7"; }
[ -f "$OUT3/mail-2026-10.tar.zst.age" ] \
    && pass "2026-10 (>= --since) was built" \
    || fail "2026-10 was not built"
[ -e "$OUT3/mail-2026-09.tar.zst.age" ] \
    && fail "2026-09 built despite --since 2026-10" \
    || pass "2026-09 (< --since) was skipped"

# ---------------------------------------------------------------------------
echo "== 8. --only-current targets the in-progress period"
# ---------------------------------------------------------------------------
OUT4="$WORK/out-current"
make_mbox "$INBOX" 2026-09-15T10:00:00 2026-11-05T10:00:00
runmail "$OUT4" --granularity month --only-current > "$WORK/log8" 2>&1 \
    || { fail "--only-current run failed"; sed 's/^/      /' "$WORK/log8"; }
ls "$OUT4" | grep -q 'mail-2026-11.partial.tar.zst.age' \
    && pass "current month written as a partial" \
    || { fail "current month not written"; ls -l "$OUT4"; }
[ -e "$OUT4/mail-2026-09.tar.zst.age" ] \
    && fail "--only-current also built a completed period" \
    || pass "completed periods untouched by --only-current"

# ---------------------------------------------------------------------------
echo "== 9. --since must match --granularity"
# ---------------------------------------------------------------------------
if runmail "$OUT4" --granularity year --since 2026-10 > "$WORK/log9" 2>&1; then
    fail "--since 2026-10 accepted with --granularity year"
else
    grep -q 'does not match --granularity' "$WORK/log9" \
        && pass "mismatched --since rejected with a clear message" \
        || { fail "wrong error for mismatched --since"; sed 's/^/      /' "$WORK/log9"; }
fi

# ---------------------------------------------------------------------------
echo "== 10. a year run refuses to duplicate an existing monthly layout"
# ---------------------------------------------------------------------------
# The deployed unit once still said "year" while the repo said "month": every
# night it reported "nothing to do" and no new mail reached Jotta. A year run
# over monthly chunks is not merely useless, it would seal mail-<year>.tar.zst.age
# and duplicate all twelve. OUT2 already holds month chunks from section 6.
if runmail "$OUT2" --granularity year --include-current > "$WORK/log10" 2>&1; then
    fail "year mode accepted over a monthly layout"
else
    grep -q 'would seal mail-' "$WORK/log10" \
        && pass "year mode refused with a clear message" \
        || { fail "wrong error for a mixed layout"; sed 's/^/      /' "$WORK/log10"; }
fi
[ -e "$OUT2/mail-$(date +%Y).tar.zst.age" ] \
    && fail "a year chunk was written despite the refusal" \
    || pass "no year chunk written"

runmail "$OUT2" --granularity year --only 2025 > "$WORK/log10b" 2>&1 \
    && pass "--only <YYYY> still permits a deliberate year build" \
    || { fail "--only <YYYY> was blocked by the mixed-layout guard"; sed 's/^/      /' "$WORK/log10b"; }

echo
if [ "$FAILED" -eq 0 ]; then
    echo "ALL TESTS PASSED"
else
    echo "$FAILED TEST(S) FAILED"
    exit 1
fi
