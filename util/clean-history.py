#!/usr/bin/env python3
# TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: util/clean-history.py:160 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 7936dbb07755f7994e2945e963aff0f01ae1ab34 %
#  %ccm_git_commit_id: 3a0dc6d000abbf72c8996a230bc72454f05c9f1b %
#  %ccm_git_commit_count: 160 %
#  %ccm_git_commit_date: 2026-09-25 21:30:36 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: cleanup %
#  %ccm_git_modify_date: 2026-09-25 21:30:37 %
#  %ccm_git_file_last_modified: 2026-07-18 11:10:08 %
#  %ccm_git_file_name: clean-history.py %
#  %ccm_git_path: util/clean-history.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 7427 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
"""
clean-history.py — Remove inline SQL DDL/DML entries from bash history.

Parses a bash history file with timestamped entries (delimited by #<epoch> lines).
Identifies entries containing SQL data-definition/modification commands inside
heredocs or inline, and removes the entire entry (command + timestamp).

Safe: writes to a new file; never modifies the original in-place.

Usage:
  python3 util/clean-history.py ~/.bash_history ~/.bash_history.clean
"""

import re
import sys
from pathlib import Path

# Patterns that mark an entry as "SQL DDL/DML" and warrant removal.
# These look at the entire multi-line entry body (command text), not individual lines.
SQL_DDL_PATTERNS = [
    # DDL — schema changes
    re.compile(r"\bCREATE\s+(TABLE|ROLE|DATABASE|SCHEMA|INDEX|USER|GROUP|TABLESPACE)\b", re.IGNORECASE),
    re.compile(r"\bALTER\s+(TABLE|ROLE|DATABASE|SCHEMA|INDEX|DEFAULT PRIVILEGES|SEQUENCE)\b", re.IGNORECASE),
    re.compile(r"\bDROP\s+(TABLE|ROLE|DATABASE|SCHEMA|INDEX|VIEW|FUNCTION|TRIGGER|SEQUENCE|OWNED)\b", re.IGNORECASE),
    re.compile(r"\bGRANT\s+(ALL|SELECT|INSERT|UPDATE|DELETE|USAGE|CONNECT|CREATE|TEMPORARY|EXECUTE)\b", re.IGNORECASE),
    re.compile(r"\bREVOKE\s+", re.IGNORECASE),
    re.compile(r"\bTRUNCATE\s+(TABLE\s+)?", re.IGNORECASE),
    # DML — data modification
    re.compile(r"\bINSERT\s+INTO\s+", re.IGNORECASE),
    re.compile(r"\bUPDATE\s+\w+\.?\w*\s+SET\s+", re.IGNORECASE),
    re.compile(r"\bDELETE\s+FROM\s+", re.IGNORECASE),
    # Password changes (inline SQL or heredoc containing \password)
    re.compile(r"\\password\s+", re.IGNORECASE),
    # PRAGMA writes (sqlite)
    re.compile(r"\bPRAGMA\s+(?!integrity_check|table_info|user_version|schema_version)\w+\s*=", re.IGNORECASE),
    # BEGIN / COMMIT / ROLLBACK as standalone DML wrappers
    re.compile(r"^\s*(BEGIN|COMMIT|ROLLBACK)\b", re.IGNORECASE | re.MULTILINE),
]

# Whitelist patterns — entries matching these are KEPT even if they also match DDL patterns.
# (e.g., "SELECT * FROM" is read-only; systemctl grep for mysql is benign)
SQL_KEEP_PATTERNS = [
    # Pure SELECT queries (read-only — keep these)
    re.compile(r"\bSELECT\s+(?!pg_reload_conf)\S", re.IGNORECASE),
    # psql meta-commands are fine: \dt, \l, \d, \du, \dn, \df, \dv, \ds
    re.compile(r"psql\s+.*\\[dltnufvs]\w*\b"),
    # sqlite3 . commands
    re.compile(r"sqlite3\s+.*\.\w+"),
    # grep / systemctl looking for mysql/postgres/database — not SQL
    re.compile(r"\b(grep|systemctl)\s+.*\b(mysql|mariadb|postgres|database)"),
    # pg_lsclusters, pg_isready, etc — admin, not DDL
    re.compile(r"\bpg_\w+"),
]

# Commands that are themselves just an SQL wrapper — if they contain DDL, flag them
SQL_WRAPPER_PREFIXES = [
    r"psql\s+",
    r"sudo\s+.*\bpsql\s+",
    r"sqlite3\s+",
    r"mysql\s+",
    r'docker\s+exec\s+.*\bsqlite3\s+',
]


def entry_contains_ddl(entry_body: str) -> bool:
    """Return True if the entry body contains SQL DDL/DML that should be removed."""

    # If the entire body is a SELECT-only query via psql wrapper, keep it
    if re.search(r"\bSELECT\s+", entry_body, re.IGNORECASE):
        # Check if there's ALSO DDL in it (unlikely, but be safe)
        has_ddl = any(p.search(entry_body) for p in SQL_DDL_PATTERNS)
        if not has_ddl:
            return False
        # If it has both SELECT and DDL, still remove it (e.g., SELECT + GRANT)
        # Fall through to removal

    # Check if entry uses a SQL wrapper with DDL
    uses_sql_wrapper = any(re.search(prefix, entry_body, re.IGNORECASE) for prefix in SQL_WRAPPER_PREFIXES)

    if uses_sql_wrapper:
        # Does it contain DDL?
        if any(p.search(entry_body) for p in SQL_DDL_PATTERNS):
            return True  # Remove: SQL wrapper + DDL

        # If it's a psql command without DDL (SELECT, meta-commands), keep it
        return False

    # Check if entry contains a heredoc that includes SQL DDL
    # Heredoc patterns: <<EOF ... EOF, <<SQL ... SQL, <<'SQL' ... SQL, etc.
    if re.search(r"<<['\"]?\w*['\"]?", entry_body):
        if any(p.search(entry_body) for p in SQL_DDL_PATTERNS):
            return True  # Remove: heredoc with DDL
        # If it's a heredoc with only SELECT, keep it
        return False

    # Entry doesn't use SQL wrappers or heredocs — check for raw DDL patterns
    # (unlikely in bash history, but be safe)
    if any(p.search(entry_body) for p in SQL_DDL_PATTERNS):
        return True

    return False


def parse_history_entries(path: Path) -> list[tuple[str, str]]:
    """
    Parse a bash history file into entries.
    Each entry is (timestamp_line, command_lines) where timestamp_line is the #<epoch> line
    and command_lines is the command text that follows (until the next timestamp or EOF).
    Returns list of (timestamp, body) tuples.
    """
    entries: list[tuple[str, str]] = []
    current_timestamp: str | None = None
    current_body_lines: list[str] = []

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            # A bash history timestamp line is # followed by digits only
            stripped = line.rstrip("\n")
            if re.match(r"^#\d{9,}$", stripped):
                # Save previous entry if any (skip very first timestamp-only)
                if current_timestamp is not None and current_body_lines:
                    body = "".join(current_body_lines).rstrip()
                    if body.strip():
                        entries.append((current_timestamp, body))
                current_timestamp = stripped
                current_body_lines = []
            elif current_timestamp is not None:
                current_body_lines.append(line)
            else:
                # Lines before any timestamp — include as body-less entry or skip
                pass

        # Handle last entry
        if current_timestamp is not None and current_body_lines:
            body = "".join(current_body_lines).rstrip()
            if body.strip():
                entries.append((current_timestamp, body))

    return entries


def main():
    if len(sys.argv) < 2:
        print("Usage: clean-history.py <input_history_file> [output_file]", file=sys.stderr)
        print("  If output_file is omitted, writes to stdout.", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1]).expanduser().resolve()
    if not input_path.is_file():
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    output_path = Path(sys.argv[2]).expanduser().resolve() if len(sys.argv) >= 3 else None

    entries = parse_history_entries(input_path)
    print(f"Total entries parsed: {len(entries)}", file=sys.stderr)

    removed_count = 0
    kept_count = 0

    out_lines: list[str] = []

    for timestamp, body in entries:
        if entry_contains_ddl(body):
            removed_count += 1
            continue
        kept_count += 1
        out_lines.append(timestamp + "\n")
        out_lines.append(body + "\n")

    print(f"Entries kept:     {kept_count}", file=sys.stderr)
    print(f"Entries removed:  {removed_count}", file=sys.stderr)

    output_content = "".join(out_lines)

    if output_path:
        output_path.write_text(output_content, encoding="utf-8")
        print(f"Wrote cleaned history to: {output_path}", file=sys.stderr)
    else:
        sys.stdout.write(output_content)


if __name__ == "__main__":
    main()