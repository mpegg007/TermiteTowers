# Git Hook Safety Guide

## ⚠️ CRITICAL: Why Hook Files Are Dangerous to Process

### The Problem
Git hooks that modify themselves create a **self-modifying code** scenario with catastrophic risks:

1. **Infinite Recursion** - Hook triggers itself → modifies itself → triggers again → infinite loop
2. **Corruption** - One bad `sed` pattern breaks your entire git workflow
3. **Hard Recovery** - Broken hooks prevent commits, making it hard to fix the problem
4. **Silent Failures** - Hooks fail silently or with cryptic errors

### Real-World Example
```bash
# Hook runs and processes itself
sed -i 's/pattern/replacement/' enhanced-pre-commit.sh
# Oops! That sed command had a typo and broke the shebang
# Now ALL commits fail and you can't commit a fix!
```

## ✅ Safety Measures Implemented

### 1. Triple-Layer Protection

**Layer 1: Hard Exclusion (First Check - NEVER bypass)**
```bash
case "$FILE" in
  git-automation/*.sh|.git/hooks/*)
    echo "[INFO] SAFETY: Skipping (hook/automation script - never process)"
    continue
    ;;
esac
```
- Runs FIRST in the loop
- No conditions, no overrides
- Protects ALL `.sh` files in `git-automation/`
- Protects ALL git hooks in `.git/hooks/`

**Layer 2: Skip Marker**
```bash
# tt-hooks.skip-post-commit
```
Add this comment to any file to exclude it from processing.

**Layer 3: Try Mode Override (Testing Only)**
```bash
./enhanced-pre-commit.sh somefile.sh --try
```
- Only bypasses the secondary specific file check
- Does NOT bypass Layer 1 hard exclusion
- Used for testing changes without git operations

### 2. Protected Files List

**Always Excluded (Layer 1 - No Exceptions):**
- `git-automation/*.sh` - All shell scripts in automation folder
- `.git/hooks/*` - All git hooks
- Any file matching the wildcard patterns above

**Examples of Protected Files:**
- ✅ `git-automation/enhanced-pre-commit.sh`
- ✅ `git-automation/enhanced-post-commit.sh`
- ✅ `git-automation/enhanced-secrets-pattern-scanner.sh`
- ✅ `git-automation/get_language_mode_and_comments.sh`
- ✅ `.git/hooks/pre-commit`
- ✅ `.git/hooks/post-commit`

### 3. Additional Safety Features

**Lock Files** (post-commit only)
```bash
LOCK_FILE=$(git rev-parse --git-path ccm-post-commit.lock)
if [ -f "$LOCK_FILE" ]; then
  echo "Lock present, skipping to avoid recursion"
  exit 0
fi
```

**Hook Bypass for Amend**
```bash
git -c core.hooksPath=/dev/null commit --amend --no-edit
```
- Prevents hooks from running during the amend
- Breaks potential infinite loops

**Parameter Safety**
```bash
# Use ${2-} instead of $2 to handle missing arguments
if [ "${2-}" == "--try" ]; then
```

## 🔧 How to Safely Modify Hook Files

### Option 1: Manual Edit (Recommended)
1. Edit the file directly in your editor
2. Test with `--try` mode:
   ```bash
   ./enhanced-pre-commit.sh testfile.txt --try
   ```
3. Review the log:
   ```bash
   tail -f git-automation/enhanced-hooks.log
   ```
4. Commit manually when satisfied

### Option 2: Temporary Disable Hooks
```bash
# Disable hooks
git config core.hooksPath /dev/null

# Make your changes
vim git-automation/enhanced-pre-commit.sh

# Test the modified hook
./git-automation/enhanced-pre-commit.sh somefile.txt

# Re-enable hooks
git config --unset core.hooksPath

# Commit
git add git-automation/enhanced-pre-commit.sh
git commit -m "Updated pre-commit hook"
```

### Option 3: Use Skip Marker
Add to the hook file itself:
```bash
#!/usr/bin/env bash
# tt-hooks.skip-post-commit
```

## 📋 Testing Checklist

Before modifying hooks, test:

- [ ] Run with `--try` mode on a test file
- [ ] Check `enhanced-hooks.log` for errors
- [ ] Verify exclusion patterns work:
  ```bash
  ./enhanced-pre-commit.sh git-automation/enhanced-pre-commit.sh
  # Should see: "SAFETY: Skipping (hook/automation script)"
  ```
- [ ] Test on a non-critical file first
- [ ] Verify lock file is created/removed (post-commit)
- [ ] Test with missing arguments (should not crash)

## 🚨 Recovery Procedures

### If a Hook Breaks

**Quick Disable:**
```bash
git config core.hooksPath /dev/null
```

**Fix the hook:**
```bash
# Edit the broken hook
vim git-automation/enhanced-pre-commit.sh

# Or restore from git history
git checkout HEAD~1 -- git-automation/enhanced-pre-commit.sh
```

**Re-enable:**
```bash
git config --unset core.hooksPath
```

### If Stuck in a Loop

1. Check for lock file:
   ```bash
   ls -la .git/ccm-post-commit.lock
   rm .git/ccm-post-commit.lock  # If exists
   ```

2. Check for infinite recursion in log:
   ```bash
   tail -100 git-automation/enhanced-hooks.log
   ```

3. Kill the process:
   ```bash
   ps aux | grep enhanced-
   kill -9 <PID>
   ```

## 📝 Best Practices

1. **Never remove the hard exclusion check** (Layer 1)
2. **Always test with `--try` mode** before committing hook changes
3. **Keep backups** of working hooks
4. **Use descriptive commit messages** when changing hooks
5. **Review logs** after hook modifications
6. **Add skip markers** to files that should never be processed
7. **Document any changes** to hook logic in this file

## 🔍 Verification Commands

**Check what files will be processed:**
```bash
git diff --cached --name-only | while read f; do
  case "$f" in
    git-automation/*.sh|.git/hooks/*) echo "SKIP: $f" ;;
    *) echo "PROCESS: $f" ;;
  esac
done
```

**Verify hook protection:**
```bash
# Should show SAFETY skip message
./git-automation/enhanced-pre-commit.sh git-automation/enhanced-pre-commit.sh
grep "SAFETY" git-automation/enhanced-hooks.log | tail -5
```

**Check for patterns that might be dangerous:**
```bash
# Search for sed commands that might process hooks
grep -n "sed.*-i.*\$FILE" git-automation/enhanced-*.sh
# All should be AFTER the safety checks
```

## 📚 Related Documentation

- [SECRET-SCANNING-README.md](./SECRET-SCANNING-README.md) - Secret scanning configuration
- [CCM_HEADER_TEMPLATE.txt](./CCM_HEADER_TEMPLATE.txt) - Header template format
- [enhanced-hooks.log](./enhanced-hooks.log) - Runtime log for debugging

---

**Last Updated:** October 12, 2025  
**Maintainer:** mpegg  
**Critical Level:** ⚠️⚠️⚠️ HIGH - Changes to hooks can break git workflow
