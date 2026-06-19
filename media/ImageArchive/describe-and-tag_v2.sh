#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: media/ImageArchive/describe-and-tag_v2.sh:149 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 9b0b214b4c765e23d6bec9e2adc7bbc551b41eff %
#  %ccm_git_commit_id: 610f7bb5f6f696dda924182dcec0efee3f85c625 %
#  %ccm_git_commit_count: 149 %
#  %ccm_git_commit_date: 2026-06-19 14:48:59 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: ita-v1 %
#  %ccm_git_modify_date: 2026-06-19 14:49:00 %
#  %ccm_git_file_last_modified: 2026-06-18 20:24:17 %
#  %ccm_git_file_name: describe-and-tag_v2.sh %
#  %ccm_git_path: media/ImageArchive/describe-and-tag_v2.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 2382 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
set -euo pipefail

get_block() {
    local model="$1"
    awk -v RS='' -v model="$model" '
        $0 ~ ("model:" model) { print; exit }
    ' ~/source/TermiteTowers/media/ImageArchive/prompts.txt
}

get_prompt() {
    get_block "$1" | awk '
        /^prompt:/ {flag=1; next}
        /^tags:/ {flag=0}
        flag {print}
    '
}

get_tags() {
    get_block "$1" | awk '
        /^tags:/ {sub(/^tags:/,""); print; exit}
    '
}

FILE="$1"
##MODEL="LLaVA-Next-34B"
MODEL="${2:-moondream}"
PROMPT="Describe this image in detail."
PROMPT="$(get_prompt "$MODEL")"
TAGS="$(get_tags "$MODEL")"


# --- 1. Run Ollama and capture ONLY the model output text ---

ORIG_DESCRIPTION="$(exiftool -s -s -s -XMP:Description "$FILE")"
if [[ -n "$ORIG_DESCRIPTION" ]]; then
    echo "Original description: $ORIG_DESCRIPTION"
    echo "Original description found, skipping: $FILE"
##    exit 0
fi
ORIG_CREATOR_TOOL="$(exiftool -s -s -s -XMP:CreatorTool "$FILE")"
if [[ -n "$ORIG_CREATOR_TOOL" ]]; then
    echo "Original creator tool: $ORIG_CREATOR_TOOL"
    echo "Original creator tool found, skipping: $FILE"
##    exit 0
fi

# --- 1. Run Ollama via API for clean, non-streaming output ---

# Convert image to base64 as required by the API
IMAGE_B64=$(base64 -w 0 "$FILE")

RAW_OUTPUT=$(curl -s http://localhost:11434/api/generate -d @- <<EOF | jq -r '.response'
{
  "model": "$MODEL",
  "prompt": "$PROMPT",
  "images": ["$IMAGE_B64"],
  "stream": false
}
EOF
)
##RAW_OUTPUT="$(
##  ollama run "$MODEL" "$FILE" "$PROMPT"
##)"

echo "Raw output from Ollama:"
echo "$RAW_OUTPUT"

DESCRIPTION="$RAW_OUTPUT" 

echo "Cleaned description:"
echo "$DESCRIPTION"

# --- 2. Write metadata using ExifTool ---
exiftool -overwrite_original \
  -XMP-dc:Description="old" \
  -XMP-dc:Title="" \
  -XMP-dc:Subject="" \
  -XMP-xmp:CreatorTool="" \
  "$FILE"

# This creates a sidecar file instead of overwriting the original image
exiftool -o "${FILE}.xmp" \
  -XMP-dc:Description="$DESCRIPTION" \
  -XMP-dc:Title="Archive Entry: $(basename "$FILE")" \
  -XMP-dc:Subject="Archive, Scan, OCP" \
  -XMP-xmp:Label="$FILM_TYPE" \
  -XMP-iptcCore:IntellectualGenre="$PROCESSING_TYPE" \
  -XMP-xmp:UserComment="Roll: $FILM_ROLL | Lab: $LAB_NAME" \
  -XMP-xmp:CreatorTool="$MODEL" \
  "$FILE"


echo "Updated metadata for: $FILE"
echo "Model: $MODEL"
echo "Description length: ${#DESCRIPTION} chars"
