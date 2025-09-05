#!/usr/bin/env bash

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
