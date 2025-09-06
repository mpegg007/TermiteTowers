#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: git-automation/get_language_mode_and_comments.sh:0 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 818b10f80f16e03e7862112837844d98e3d5cff1 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: 0 %
#  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2025-09-06 12:02:06 %
#  %ccm_git_file_last_modified: 2025-09-06 11:52:11 %
#  %ccm_git_file_name: get_language_mode_and_comments.sh %
#  %ccm_git_path: git-automation/get_language_mode_and_comments.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 10950 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  

file="$1"
ext="${file##*.}"
mode="" block_start="" block_end="" line_comment=""
if [ -n "$VSCODE_LANGUAGE_MODE" ]; then
    mode="$VSCODE_LANGUAGE_MODE"
else
    case "$ext" in
        sh|bash) mode="shellscript"; line_comment="#" ;;
        py) mode="python"; line_comment="#" ;;
        js|ts|jsx|tsx) mode="javascript"; line_comment="//" ;;
        bat|cmd) mode="bat"; line_comment="REM" ;;
        ps1|psm1|psd1) mode="powershell"; line_comment="#" ;;
        yaml|yml) mode="yaml"; line_comment="#" ;;
        sql) mode="sql"; line_comment="--" ;;
        html|xml|md) mode="html"; block_start="<!--"; block_end="-->"; line_comment="" ;;
        css|scss|less) mode="css"; block_start="/*"; block_end="*/"; line_comment="" ;;
        *) mode="$ext"; line_comment="#" ;;
    esac
fi
# Default block comments for some types
if [ -z "$block_start" ] && [ "$mode" = "python" ]; then block_start=""; block_end=""; fi
echo "$mode|$block_start|$block_end|$line_comment"
