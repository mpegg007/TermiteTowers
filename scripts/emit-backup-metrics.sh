#!/usr/bin/env bash
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: scripts/emit-backup-metrics.sh@218 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: a6a0cc38762cb7a12e77b40252a30095b4dc7c81 %
#  %ccm_git_commit_id: 72c0eae6bb7ccad09a6031b8cf1fff35b571a7e4 %
#  %ccm_git_commit_count: 218 %
#  %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: changes 261113 %
#  %ccm_git_modify_date: 2026-11-13 14:50:47 %
#  %ccm_git_file_last_modified: 2026-11-13 14:49:39 %
#  %ccm_git_file_name: emit-backup-metrics.sh %
#  %ccm_git_path: scripts/emit-backup-metrics.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: LF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 5599 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# TermiteTowers — publish backup freshness as Prometheus textfile metrics.
#
# WHY MTIMES AND NOT EXIT CODES
#   A backup job reporting success proves the job ran, not that data landed. This
#   reads the newest file in each backup directory, so the metric reflects what
#   is actually on disk. A job that "succeeds" while writing nothing still reads
#   as stale, and a job that never ran cannot claim otherwise.
#
#   It is also deliberately read-only and unprivileged: it needs no database
#   access, no age key and no docker, just group read on the backup tree.
#
# CONSUMER
#   node-exporter's textfile collector reads $OUT_DIR and republishes these as
#   node_textfile_mtime_seconds plus the metrics below. Rules in
#   infra/docker/prometheus/rules/backup.yml evaluate them.
#
# METRICS
#   tt_backup_last_success_timestamp_seconds{job}  newest file mtime, unix seconds
#   tt_backup_file_count{job}                      files present in the directory
#   tt_backup_directory_present{job}               1 or 0
#   tt_backup_emit_timestamp_seconds               heartbeat of this emitter
#
# USAGE
#   scripts/emit-backup-metrics.sh
#   OUT_DIR=/tmp/t BACKUP_ROOT=/tmp/backups scripts/emit-backup-metrics.sh
#
# EXIT
#   0  published (absence of a directory is data, not an error)
#   2  cannot write to OUT_DIR

set -Eeuo pipefail

OUT_DIR="${OUT_DIR:-/mnt/ai_storage/prometheus/textfile}"
BACKUP_ROOT="${BACKUP_ROOT:-/mnt/ai_storage/backups}"
OUT_FILE="${OUT_DIR}/tt_backup.prom"

# job name -> directory under the backup root. Keep in step with the units in
# infra/systemd/ and infra/systemd/user/, and the directories documented in
# infra/backups/README.md.
#
# ttdb and ttphoto were added 2026-11-13: both databases had NO backup at all
# until then, so they had no series here either - which is why BackupStale could
# never have noticed them.
JOBS=(tthealth mealie thunderbird ttdb ttphoto)

log() { printf '%s\n' "$*" >&2; }

[ -d "$OUT_DIR" ] || { log "error: ${OUT_DIR} does not exist"; exit 2; }
[ -w "$OUT_DIR" ] || { log "error: ${OUT_DIR} is not writable by $(id -un)"; exit 2; }

# Write to a temp file in the SAME directory and rename, so node-exporter never
# reads a half-written file. A partially written .prom becomes a scrape error.
tmp="$(mktemp "${OUT_DIR}/.tt_backup.XXXXXX")"
trap 'rm -f "$tmp"' EXIT

{
    printf '# HELP tt_backup_last_success_timestamp_seconds Newest file mtime in the backup directory.\n'
    printf '# TYPE tt_backup_last_success_timestamp_seconds gauge\n'
    printf '# HELP tt_backup_file_count Files present in the backup directory.\n'
    printf '# TYPE tt_backup_file_count gauge\n'
    printf '# HELP tt_backup_directory_present Whether the backup directory exists.\n'
    printf '# TYPE tt_backup_directory_present gauge\n'
    printf '# HELP tt_backup_emit_timestamp_seconds When this emitter last ran.\n'
    printf '# TYPE tt_backup_emit_timestamp_seconds gauge\n'

    for job in "${JOBS[@]}"; do
        dir="${BACKUP_ROOT}/${job}"
        if [ -d "$dir" ]; then
            printf 'tt_backup_directory_present{job="%s"} 1\n' "$job"

            count="$(find "$dir" -maxdepth 1 -type f 2>/dev/null | wc -l)"
            printf 'tt_backup_file_count{job="%s"} %s\n' "$job" "$count"

            newest="$(find "$dir" -maxdepth 1 -type f -printf '%T@\n' 2>/dev/null \
                      | sort -n | tail -1 | cut -d. -f1)"
            # 0 when the directory is empty, NOT omitted. A series that exists
            # with value 0 makes BackupStale fire (time() - 0 is enormous), so an
            # emptied or never-written backup directory is loud. Omitting the
            # series would let it go silent, which is the failure mode this whole
            # metric exists to prevent.
            printf 'tt_backup_last_success_timestamp_seconds{job="%s"} %s\n' \
                "$job" "${newest:-0}"
            log "${job}: ${count:-0} file(s)"
        else
            # Reported as 0 rather than skipped: a vanished backup directory is
            # exactly the kind of silent failure this exists to catch.
            printf 'tt_backup_directory_present{job="%s"} 0\n' "$job"
            log "${job}: directory missing (${dir})"
        fi
    done

    printf 'tt_backup_emit_timestamp_seconds %s\n' "$(date +%s)"
} > "$tmp"

# 0644: node-exporter runs as root in its container, but keep it readable so a
# permission mismatch never needs a root shell to diagnose.
chmod 0644 "$tmp"
mv -f "$tmp" "$OUT_FILE"
trap - EXIT

log "published ${OUT_FILE}"
