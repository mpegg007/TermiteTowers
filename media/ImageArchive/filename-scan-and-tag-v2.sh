#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: media/ImageArchive/filename-scan-and-tag-v2.sh:149 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 71e83179816f9694bc79b04457308fa8d939f427 %
#  %ccm_git_commit_id: 610f7bb5f6f696dda924182dcec0efee3f85c625 %
#  %ccm_git_commit_count: 149 %
#  %ccm_git_commit_date: 2026-06-19 14:48:59 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: ita-v1 %
#  %ccm_git_modify_date: 2026-06-19 14:49:00 %
#  %ccm_git_file_last_modified: 2026-06-15 18:40:53 %
#  %ccm_git_file_name: filename-scan-and-tag-v2.sh %
#  %ccm_git_path: media/ImageArchive/filename-scan-and-tag-v2.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 1508 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
set -euo pipefail

FILE="$1"
FILENAME=$(basename "$FILE")

ORIG_DATE="$(exiftool -s -s -s -exif:DateTimeOriginal "$FILE")"
ORIG_SUBJECT="$(exiftool -s -s -s -XMP-dc:Subject "$FILE")"
if [[ -n "$ORIG_DATE" ]]; then
    echo "SKIP: $FILE OriginalDate[$ORIG_DATE] OrigSubject[$ORIG_SUBJECT] found"
    exit 1
fi

# 1. Extract date using regex
# Matches 6 or 8 digits at the start of the filename
if [[ "$FILENAME" =~ ^([0-9]{6,8})[,_\ ] ]]; then
    RAW_DATE="${BASH_REMATCH[1]}"
else
    echo "Error: No valid date found in filename: $FILENAME"
    exit 1
fi

# 2. Normalize date to YYYY:MM:DD
# If 6 digits, add 1900s or 2000s; if 8, use as is.
if [[ ${#RAW_DATE} -eq 6 ]]; then
    YY=${RAW_DATE:0:2}
    MM=${RAW_DATE:2:2}
    DD=${RAW_DATE:4:2}
    # Simple century heuristic: 25 or higher = 1900s
    YEAR=$(( YY > 25 ? 1900 + YY : 2000 + YY ))
    FORMATTED_DATE="${YEAR}:${MM}:${DD}"
else
    # Assumes 8-digit format is YYYYMMDD
    FORMATTED_DATE="${RAW_DATE:0:4}:${RAW_DATE:4:2}:${RAW_DATE:6:2}"
fi

# 3. Extract Keywords
# Remove date and leading underscore, then replace underscores/hyphens with spaces
KEYWORDS=$(echo "$FILENAME" \
    | sed -E "s/^[0-9]{6,8}[^0-9]//" \
    | sed 's/\.[^.]*$//' \
    | tr '_-' ' ')

# 5. Write metadata
exiftool -overwrite_original "${FILE}" \
  -exif:DateTimeOriginal="$FORMATTED_DATE 00:00:00" \
  -XMP-dc:Subject="Archive, File, OCP, $KEYWORDS" 

echo "INFO: Updated metadata for: $FILE  with Date: $FORMATTED_DATE and Keywords: $KEYWORDS"