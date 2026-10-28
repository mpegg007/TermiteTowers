# CCM Git Hooks V2

## Architecture

```
v2/
├── ccm-lib.sh              Shared library: metadata capture, header formatting, field updates, permission preservation
├── ccm-apply.sh            Single-entry orchestrator: strips old header, formats new one, inserts, preserves permissions
├── detect-language.sh      Language mode detection: content heuristics → shebang → extension → fallback
├── pre-commit.sh           Thin pre-commit wrapper: loops staged files, applies CCM header, secret scans, git add
├── post-commit.sh          Thin post-commit wrapper: fills commit-bound fields, amends commit
├── secret-scanner.sh       Secret scanning: custom regex patterns + GitGuardian ggshield, stderr output
├── secrets-patterns.conf   Pattern definitions (data file, not bash code)
├── CCM_HEADER_TEMPLATE.txt        Default template (shellscript, python, yaml, etc.)
├── CCM_JSON_HEADER_TEMPLATE.txt   JSON template (ASIS mode, valid JSON structure)
├── CCM_MARKDOWN_HEADER_TEMPLATE.txt  Markdown template (ASIS mode, HTML comments)
└── README.md               This file
```

## Key Improvements Over V1

### 1. exec_flag Timing Bug Fixed
V1 captured `exec_flag` AFTER `remove_ccm_header()` had already stripped `+x` from the file. V2 captures file metadata BEFORE any modification and restores permissions at the end.

### 2. Modular Architecture
V1 had a 220-line inline function (`insert_ccm_header`) in `enhanced-pre-commit.sh`. V2 splits this into named functions in `ccm-lib.sh` with a clean orchestration script (`ccm-apply.sh`).

### 3. Secret Scanning UX
V1 suppressed all ggshield output to a log file. Users only saw "check the log". V2 prints secret details directly to stderr. Patterns are defined in a data file (`secrets-patterns.conf`) instead of a bash array.

### 4. Markdown Template
New `CCM_MARKDOWN_HEADER_TEMPLATE.txt` uses HTML comments, invisible in rendered markdown.

### 5. Template Isolation
V2 templates are in the v2 directory. Changing the v1 template does not affect v2 and vice versa.

## CCM Tags (All Preserved)

All 25 CCM tags from v1 are preserved:

| Tag | Description |
|-----|-------------|
| `%ccm_git_repo:` | Repository name |
| `%ccm_git_branch:` | Git branch |
| `%ccm_git_object_id:` | File path:revision |
| `%ccm_git_author:` | Git user.name |
| `%ccm_git_author_email:` | Git user.email |
| `%ccm_git_blob_sha:` | Git blob hash |
| `%ccm_git_commit_id:` | Commit SHA |
| `%ccm_git_commit_count:` | Total commit count |
| `%ccm_git_commit_date:` | Commit timestamp |
| `%ccm_git_commit_author:` | Commit author |
| `%ccm_git_commit_email:` | Commit author email |
| `%ccm_git_commit_message:` | Commit message |
| `%ccm_git_modify_date:` | Hook processing timestamp |
| `%ccm_git_file_last_modified:` | Filesystem mtime |
| `%ccm_git_file_name:` | Filename |
| `%ccm_git_path:` | Repo-relative path |
| `%ccm_git_language_mode:` | Detected language mode |
| `%ccm_git_file_type:` | MIME type |
| `%ccm_git_file_encoding:` | MIME encoding |
| `%ccm_git_file_eol:` | Line endings (CRLF/LF) |
| `%ccm_git_exec:` | Execute bit (yes/no) |
| `%ccm_git_size:` | File size in bytes |
| `%ccm_git_tag:` | Git tag (if any) |
| `%git_commit_history:` | Accumulated history trail |

## Template Directives

```
##TEMPLATE_ASIS         Insert template lines verbatim (no comment wrapping)
##HISTORY_ASIS           Insert history line verbatim (no comment wrapping)
##COMMIT_HISTORY: format  History line format with $DATE, $AUTHOR, $MESSAGE
```

## Commit History Trail

`%git_commit_history` rows are deduplicated and capped so the trail cannot
compound across runs:

- `extract_preserved_history` normalises (strips a trailing CR/whitespace) and
  de-duplicates collected rows, keeping at most `CCM_HISTORY_MAX` (default 50,
  override via the environment).
- `remove_ccm_header` strips every `%git_commit_history` row together with the
  header, so `format_ccm_header` is the single writer of the trail.
- `format_ccm_header` re-emits the deduplicated trail and skips the new entry
  when an identical one is already present.

## Compact Mode (`%ccm_compact`)

Volatile documents that are read for their content rather than their provenance
can opt out of the header machinery entirely. This is **self-declared** — there
is no config file and no path list. A file declares itself compact by carrying
the token on its **first line**:

```markdown
<!-- %ccm_compact: -->
# Active Context
...
```

Behaviour: `ccm-apply.sh` sees the token and exits 0 **without writing
anything**. The token *is* the header. No strip, no reformatting, no field
rewrite, no `%git_commit_history` trail.

| Aspect | Full header | Compact |
|---|---|---|
| Lines | 9 (markdown) / 24 (default) | 1 |
| History trail | grows to `CCM_HISTORY_MAX` (50) | none, ever |
| Rewritten by pre-commit | yes | no |
| Amended by post-commit | yes | no |
| Freshness source | `%ccm_git_commit_date` in the file | `git log -1 --format=%cI -- <path>` |

Design notes:

- **One choke point.** The guard is Step 0 of `ccm-apply.sh`, not of
  `pre-commit.sh`, so every caller (the hook today, a bulk reheader tool later)
  inherits it.
- **No change needed in `post-commit.sh`.** Its processing gate is
  `grep -qE '%ccm_git_.*: .* %'`; a compact file never matches, so it is
  skipped there automatically and no amend churn is produced.
- **Detection is first-line-only.** This README and `.clinerules/` both mention
  the token by name; a whole-file grep would silently opt *them* out of CCM. Do
  not weaken the `head -n 1` check.
- **No shebang support.** The token must be on line 1, so compact mode does not
  apply to scripts. That is deliberate — an escaping rule would complicate the
  one property that makes this mode safe.
- **Idempotent by construction.** The file is never written, so running the hook
  twice cannot accumulate anything.

Covered by `tests/git-automation/test_compact_header.sh`, which asserts
byte-identity, idempotency, absence of a history trail, the post-commit gate,
line-1-only detection, and that unmarked files still receive a full header.

Trade-off: a compact file carries no in-file provenance. Diff history and
`git log` are the only record. Use it for status documents that change often,
not for code.

## Usage

### Normal Operation
Git hooks run automatically on commit:
- `pre-commit`: CCM header applied + secret scan
- `post-commit`: Commit fields finalized + commit amended

### Manual Testing
```bash
# Apply CCM header to a single file (dry run)
./git-automation/v2/ccm-apply.sh path/to/file.sh path/to/file.sh

# Run pre-commit logic manually
./git-automation/v2/pre-commit.sh path/to/file.sh

# Run post-commit logic manually
./git-automation/v2/post-commit.sh path/to/file.sh

# Test secret scanner
./git-automation/v2/secret-scanner.sh path/to/file.sh
./git-automation/v2/secret-scanner.sh --list-patterns
./git-automation/v2/secret-scanner.sh --dry-run path/to/file.sh
```

## Rollback to V1

```bash
cd .git/hooks
rm pre-commit post-commit
mv pre-commit.v1 pre-commit
mv post-commit.v1 post-commit
```

## Secret Scanning

### Adding Patterns
Edit `secrets-patterns.conf`:
```
# Format: regex|severity|description
API_KEY\s*=\s*["'][^"']+["']|high|Hardcoded API key
```

### Bypass
Add a comment to the file:
- `# tt-secrets.skip` — bypass custom pattern scanning
- `# tt-ggshield.skip` — bypass GitGuardian
- `# tt-hooks.skip-post-commit` — bypass all hook processing