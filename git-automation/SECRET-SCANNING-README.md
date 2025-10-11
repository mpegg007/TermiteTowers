# Enhanced Secret Scanning

## Overview
The pre-commit hook uses `enhanced-secrets-pattern-scanner.sh` to scan for secrets before allowing commits.

## Architecture
- **Hook**: `enhanced-pre-commit.sh` (rarely needs modification)
- **Scanner**: `enhanced-secrets-pattern-scanner.sh` (easy to modify)

## Scanner Features
1. **Custom Regex Patterns** - Fast, local, version-controlled
2. **GitGuardian ggshield** - Comprehensive secret database

## Adding Custom Patterns

Edit: `git-automation/enhanced-secrets-pattern-scanner.sh`

Find the `PATTERNS` array (around line 40) and add new patterns:

```bash
declare -a PATTERNS=(
    # Kea DHCP database passwords
    '"password"\s*:\s*"[^"]+"'"|high|Hardcoded database password in Kea config"
    
    # Your new pattern
    'API_KEY\s*=\s*["\047][^"\047]+["\047]|high|Hardcoded API key'
)
```

**Format**: `'regex_pattern|severity|description'`
**Severity**: `low`, `medium`, `high`, `critical`

## Bypass Options

### Bypass Custom Patterns Only
Add comment to file: `# tt-secrets.skip` or `// tt-secrets.skip`

### Bypass GitGuardian Only  
Add comment to file: `# tt-ggshield.skip` or `// tt-ggshield.skip`

### Bypass Both
Add both markers to the file

## Testing

Create a test file with a secret:
```bash
echo '{"password": "test123"}' > test.json
git add test.json
# Should be blocked by scanner
```

## Configuration Files
- `.gitguardian.yml` - GitGuardian config (minimal, no custom patterns)
- `enhanced-secrets-pattern-scanner.sh` - All custom patterns go here

## Notes
- ggshield custom patterns via web dashboard are NOT recommended (manual process)
- Keep all custom patterns in the scanner script for easy version control
- The hook logs all scans to `git-automation/enhanced-hooks.log`
