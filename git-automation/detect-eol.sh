#!/usr/bin/env bash
# detect-eol.sh: Classify a file's line endings.
#
# Usage: detect-eol.sh <file>
#
# Prints exactly one word on stdout:
#   LF      no CR bytes present           -> header lines need no extra terminator
#   CRLF    CR and LF both present        -> header lines need a trailing CR
#   CR      CR only, no LF (classic Mac)  -> header lines need a trailing CR
#   BINARY  file contains NUL bytes       -> never touch the line endings
#   EMPTY   missing, unreadable, or zero-length file
#
# Always exits 0 when the file is readable; the classification is the payload.
#
# This is the single source of truth for %ccm_git_file_eol and for the
# `line_end` field consumed by format_ccm_header. It replaces the previous
# `grep -q $'\r\n'` idiom, which was broken: bash splits $'\r\n' into a CR
# plus an empty alternative at the embedded newline, so the empty branch
# matched every line of every file and classified pure-LF files as CRLF.

set -euo pipefail

file="${1-}"

if [ -z "$file" ] || [ ! -f "$file" ] || [ ! -r "$file" ] || [ ! -s "$file" ]; then
    echo "EMPTY"
    exit 0
fi

# NUL bytes outrank every line-ending class. A file containing NUL is not a
# line-oriented text file, and byte-level rewriting corrupts it -- the UTF-16LE
# README.md that got an ASCII header spliced into it is the cautionary example.
# Check this first, before counting any CRs.
bytes_total=$(LC_ALL=C wc -c < "$file")
bytes_without_nul=$(LC_ALL=C tr -d '\000' < "$file" | LC_ALL=C wc -c)
if [ "$bytes_without_nul" -lt "$bytes_total" ]; then
    echo "BINARY"
    exit 0
fi

cr_count=$(LC_ALL=C tr -dc '\r' < "$file" | LC_ALL=C wc -c)
lf_count=$(LC_ALL=C tr -dc '\n' < "$file" | LC_ALL=C wc -c)

if [ "$cr_count" -eq 0 ]; then
    echo "LF"
elif [ "$lf_count" -eq 0 ]; then
    echo "CR"
else
    echo "CRLF"
fi
