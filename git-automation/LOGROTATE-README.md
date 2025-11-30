<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: git-automation/LOGROTATE-README.md:122 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 355abf2d821663b1195f26e3f7abcd9e0195157e %
  %ccm_git_commit_id: 911abf33d3a165541ef9f5e4f965e884eb2a438e %
  %ccm_git_commit_count: 122 %
  %ccm_git_commit_date: 2025-11-30 15:57:30 -0500 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: logging cleanup %
  %ccm_git_modify_date: 2025-11-30 15:57:31 %
  %ccm_git_file_last_modified: 2025-11-30 15:43:28 %
  %ccm_git_file_name: LOGROTATE-README.md %
  %ccm_git_path: git-automation/LOGROTATE-README.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 5924 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# Git Hooks Logrotate Integration

This directory contains logrotate configuration files that are **maintained in the repository** and used by the enhanced git hooks to manage log rotation.

## Architecture

The logrotate setup follows a hybrid approach that combines the best of both worlds:

✅ **Professional log management** - Uses system `logrotate` utility  
✅ **On-demand rotation** - Triggered by git commits (when logs actually grow)  
✅ **Repository-maintained configs** - All configuration lives in version control  
✅ **No cron needed** - Git hooks trigger logrotate checks automatically  

## Files

### `logrotate.conf`
Main logrotate configuration file. Defines global defaults and includes configs from `logrotate.d/`.

### `logrotate.d/git-hooks.conf`
Specific configuration for git hook logs. Defines:
- **Size trigger**: Rotate when log exceeds 10MB
- **Retention**: Keep last 5 rotated logs
- **Compression**: Gzip rotated logs with date-stamped filenames
- **Pattern**: Matches all `*-enhanced-hooks.log` files in `$HOME/log/`

### `setup-logrotate.sh`
One-time setup script that:
- Creates `$HOME/log/` directory
- Creates `$HOME/.logrotate.state` file
- Verifies repository configs exist

## Initial Setup

Run once after cloning the repository:

```bash
cd /home/mpegg-adm/source/TermiteTowers
./git-automation/setup-logrotate.sh
```

This sets up the necessary directories and state files.

## How It Works

### On Every Git Commit:

1. **Pre-commit hook** (`enhanced-pre-commit.sh`) runs first
2. Calls: `logrotate -s ~/.logrotate.state git-automation/logrotate.conf`
3. Logrotate checks state file and log size
4. **If rotation needed**: Archives current log, compresses it, creates new log
5. **If not needed**: Does nothing (fast, minimal overhead)
6. Writes to log: `$HOME/log/TermiteTowers-enhanced-hooks.log`
7. **Post-commit hook** (`enhanced-post-commit.sh`) does the same

### Rotation Behavior:

When `TermiteTowers-enhanced-hooks.log` exceeds 10MB:
```
TermiteTowers-enhanced-hooks.log                    # Current log
TermiteTowers-enhanced-hooks-20251130-154500.log.gz # 1st rotation
TermiteTowers-enhanced-hooks-20251129-093000.log.gz # 2nd rotation
TermiteTowers-enhanced-hooks-20251128-141200.log.gz # 3rd rotation
TermiteTowers-enhanced-hooks-20251127-102345.log.gz # 4th rotation
TermiteTowers-enhanced-hooks-20251126-165430.log.gz # 5th rotation (oldest kept)
```

Older rotations are automatically deleted to maintain only 5 archives.

## Log Locations

### Active Logs
All current logs are stored in:
```
$HOME/log/
├── TermiteTowers-enhanced-hooks.log
├── havoc-enhanced-hooks.log
└── home-assistant-config-enhanced-hooks.log
```

Each repository gets its own log file based on repository name.

### Rotated/Archived Logs
Compressed archives are stored in the same directory:
```
$HOME/log/
├── TermiteTowers-enhanced-hooks-20251130-154500.log.gz
├── TermiteTowers-enhanced-hooks-20251129-093000.log.gz
└── ...
```

## Testing

### Test logrotate manually (verbose mode):
```bash
logrotate -v -s ~/.logrotate.state /home/mpegg-adm/source/TermiteTowers/git-automation/logrotate.conf
```

### Force rotation (for testing):
```bash
logrotate -f -s ~/.logrotate.state /home/mpegg-adm/source/TermiteTowers/git-automation/logrotate.conf
```

### Check current log size:
```bash
ls -lh ~/log/*-enhanced-hooks.log
```

### View rotated logs:
```bash
ls -lht ~/log/*-enhanced-hooks-*.log.gz
```

### Read a compressed log:
```bash
zcat ~/log/TermiteTowers-enhanced-hooks-20251130-154500.log.gz | tail -n 50
```

## Configuration Changes

All logrotate configuration is maintained in this repository. To modify rotation behavior:

1. Edit `git-automation/logrotate.d/git-hooks.conf`
2. Adjust settings like:
   - `size 10M` → Change rotation size threshold
   - `rotate 5` → Change number of archives to keep
   - `compress` / `nocompress` → Toggle compression
   - `dateformat` → Customize archive timestamp format
3. Commit changes
4. Changes take effect on next git commit (hooks will use updated config)

## Why This Approach?

### vs. Custom Rotation Code in Script:
- ❌ Custom code: Duplicated logic, harder to maintain
- ✅ logrotate: Industry-standard, battle-tested, feature-rich

### vs. System Logrotate (`/etc/logrotate.d/`):
- ❌ System: Requires sudo, mixes user logs with system logs
- ✅ Repo-based: No sudo needed, configs in version control

### vs. Cron-based Logrotate:
- ❌ Cron: Polls every N minutes regardless of activity
- ✅ Hook-triggered: Only checks when commits happen (when logs grow)

## Troubleshooting

### Logs not rotating:
```bash
# Check if logrotate is installed
which logrotate

# Test rotation manually with verbose output
logrotate -v -s ~/.logrotate.state git-automation/logrotate.conf

# Check state file
cat ~/.logrotate.state
```

### Permissions issues:
```bash
# Ensure log directory is writable
ls -ld ~/log

# Ensure state file is writable
ls -l ~/.logrotate.state
```

### See what logrotate would do without rotating:
```bash
logrotate -d git-automation/logrotate.conf
```

## Benefits

✅ **Centralized config** - All repos can share logrotate.d/ configs  
✅ **Version controlled** - Configuration changes are tracked in git  
✅ **Portable** - Clone repo, run setup script, done  
✅ **Professional** - Uses industry-standard tools  
✅ **Efficient** - Only runs when needed (git commits)  
✅ **Low overhead** - logrotate is fast when no rotation needed  
✅ **Self-maintaining** - Automatic cleanup of old logs  

## Related Files

- `enhanced-pre-commit.sh` - Calls logrotate before processing files
- `enhanced-post-commit.sh` - Calls logrotate after commit finalization
- `CCM_HEADER_TEMPLATE.txt` - Template for CCM headers
- `get_language_mode_and_comments.sh` - Language detection helper
- `enhanced-secrets-pattern-scanner.sh` - Secret scanning integration
