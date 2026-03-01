<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/systemd-naming-standard.md:121 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 807005174b06b13c0284aa3703ec796a24973141 %
  %ccm_git_commit_id: 4a1cbe1072eb42723822f202e3fcd45247e1aa03 %
  %ccm_git_commit_count: 121 %
  %ccm_git_commit_date: 2025-11-30 12:26:01 -0500 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: cleanup %
  %ccm_git_modify_date: 2025-11-30 12:28:04 %
  %ccm_git_file_last_modified: 2025-11-30 12:28:04 %
  %ccm_git_file_name: systemd-naming-standard.md %
  %ccm_git_path: wiki/systemd-naming-standard.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 17206 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!-- %git_commit_history: november changes % -->
# Systemd Service and Script Naming Standards

This document defines the naming conventions for systemd services, monitoring scripts, and watchdog services in the TermiteTowers infrastructure.

## Core Principles

### TermiteTowers `tt` Prefix Convention

The `tt` prefix identifies TermiteTowers-created resources from third-party/system resources:

**USE `tt-` prefix for**:
- Custom monitoring/watchdog services you create
- Custom deployment scripts and tools
- Log files from your monitoring scripts
- Databases (e.g., `ttdb-dev1`, `ttdb-prd1`)

**DO NOT use `tt-` prefix for**:
- Third-party packaged services (e.g., `kea-dhcp4`, `postgresql`)
- Services installed via apt/dnf/package manager
- Upstream project systemd units

**Rationale**: Quickly identify your infrastructure code vs system/third-party tools. `ls /var/log/tt-*` shows only YOUR monitoring logs.

## Environment Suffix Convention

All services use environment suffixes to indicate deployment stage:

- `-dev1` - Development/primary instance (monolith)
- `-dev2` - Secondary development instance
- `-prd1` - Production instance
- `-prd2` - Production failover instance

**Rationale**: Allows multiple instances of the same service to coexist, supports testing before production deployment, and clearly identifies environment in logs and process listings.

## Systemd Service Naming

### Third-Party/Packaged Services

**Format**: `<application>-<env>.service`

**Examples**:
- `kea-dhcp4-dev1.service` (Kea DHCP from apt package)
- `postgresql.service` (system PostgreSQL)
- `ollama-dev1.service` (third-party Ollama)
- `wyoming-piper-dev1.service` (third-party Wyoming)

**Rules**:
- NO `tt-` prefix for packaged/third-party services
- Use lowercase with hyphens
- Application name first, environment suffix last
- Multi-word applications use hyphens

### Custom TermiteTowers Services

**Format**: `tt-<service>-<function>-<env>.service`

**Examples**:
- `tt-kea-watchdog-dev1.service` (your auto-recovery for Kea)
- `tt-postgres-monitor-dev1.service` (your health monitoring)
- `tt-havoc-bridge-dev1.service` (your custom bridge service)
- `tt-backup-validator-dev1.service` (your backup checker)

**Rules**:
- Always use `tt-` prefix for services YOU created
- Format: `tt-<what>-<function>-<env>`
- Makes your services instantly identifiable

**Special Case - Environment-Agnostic Handlers**:
For OnFailure handlers that work across all environments:

- `tt-kea-watchdog.service` (no env suffix, handles all Kea instances)
- `tt-db-recovery.service` (handles all database failures)

**When to include env suffix**:
- Service has environment-specific configuration
- Different recovery procedures per environment  
- Multiple environments run simultaneously on same host

### Timer Units

**Format**: `<service>-<env>.timer`

**Examples**:
- `external-backup-dev1.timer`
- `log-rotation-dev1.timer`
- `cert-renewal-dev1.timer`

**Note**: Timer requires matching `.service` file with same base name

## Script Naming Standards

### Configuration File Naming

**Format**: `tt-<service>-<component>-<env>.conf`

**Source Location**: `infra/<service>/configs/<service>/`
**Deployed Location**: `/etc/<service>/` or `/srv/<env>/<service>/configs/`

**Examples**:
```
infra/dhcp/configs/kea/
├── tt-kea-dhcp4-dev1.conf           # Your dev1 DHCPv4 config
├── tt-kea-dhcp-ddns-dev1.conf       # Your dev1 DDNS config
├── tt-kea-dhcp4-dev1-nodb.conf      # Variant config (no database)
├── tt-kea-dhcp4-prd1.conf           # Production config (future)
└── kea-dhcp4.conf.install           # Package default (reference)
```

**Deployed**:
```
/etc/kea/
├── tt-kea-dhcp4-dev1.conf           # Active config
├── tt-kea-dhcp-ddns-dev1.conf
└── kea-*.conf.install               # Package defaults (keep as reference)
```

**Rules**:
- Always use `tt-` prefix for YOUR custom configs
- Include environment suffix (`-dev1`, `-prd1`)
- NO `tt-` prefix for package-installed default configs (those are `.install` files)
- Source filename MUST match deployed filename
- Variants use additional suffix: `-nodb`, `-minimal`, `-test`
- Systemd services reference these configs:
  ```ini
  ExecStart=/usr/sbin/kea-dhcp4 -c /etc/kea/tt-kea-dhcp4-dev1.conf
  ```

**Benefits**:
- Config names clearly identify as yours vs package defaults
- Environment obvious from filename
- Can deploy multiple environment configs side-by-side
- Source and deployed names match (no confusion)

### Monitoring Scripts

**Format**: `tt-<service>-<function>-<env>.sh`

**Source Location**: `infra/<service>/scripts/monitoring/`
**Deployed Location**: `/srv/<env>/<service>/scripts/monitoring/`

**Examples**:
```
infra/dhcp/scripts/monitoring/
├── tt-kea-health-check-dev1.sh       # Comprehensive health check
├── tt-kea-postgres-check-dev1.sh     # Database-specific check
├── tt-kea-ddns-check-dev1.sh         # DDNS-specific check
└── tt-kea-leases-check-dev1.sh       # Lease allocation check
```

**Rules**:
- Always use `tt-` prefix (these are YOUR scripts)
- Include environment suffix (`-dev1`, `-prd1`)
- Verb-noun format: `<what>-<action>-<env>`
- Return exit code 0 for success, non-zero for failure
- Include `#!/usr/bin/env bash` shebang
- Follow script-standards.md for logging

### Watchdog/Recovery Scripts

**Format**: `tt-<service>-watchdog-<env>.sh` or `tt-<service>-recovery-<env>.sh`

**Source Location**: `infra/<service>/scripts/monitoring/`
**Deployed Location**: `/srv/<env>/<service>/scripts/monitoring/`

**Examples**:
```
infra/dhcp/scripts/monitoring/
├── tt-kea-watchdog-dev1.sh           # Auto-restart on failure
├── tt-kea-recovery-dev1.sh           # Manual recovery procedure
└── tt-kea-failover-dev1.sh           # Switch to backup instance
```

**Rules**:
- Always use `tt-` prefix (these are YOUR scripts)
- Include environment suffix
- Use `-watchdog` for automatic recovery scripts
- Use `-recovery` for manual/complex recovery procedures
- Use `-failover` for high-availability switching
- Must be idempotent (safe to run multiple times)
- Log all actions to `/var/log/tt-<service>-watchdog-<env>.log`

### Deployment Scripts

**Format**: `deploy-<component>-<action>.sh`

**Location**: `infra/<service>/scripts/deploy/`

**Examples**:
```
infra/dhcp/scripts/deploy/
├── deploy-kea-config.sh         # Deploy configuration files
├── deploy-kea-ddns.sh           # Deploy DDNS-specific config
└── deploy-dhcp-config.sh        # Deploy ISC DHCP config
```

**Rules**:
- Use `deploy-` prefix
- Component before action
- Should be idempotent
- Include validation/dry-run mode

### Utility Scripts

**Format**: `<action>-<object>.sh`

**Location**: `infra/<service>/scripts/utils/` or `scripts/`

**Examples**:
```
scripts/
├── backup-to-external.sh
├── convert-dhcp-reservations.sh
├── generate-config.sh
└── setup-dhcp-history-db.sh
```

**Rules**:
- Verb-noun format
- Descriptive but concise
- Group related utilities in subdirectories

## File System Layout

### Source Repository Structure

```
infra/<service>/
├── configs/
│   ├── systemd/                      # Systemd unit files
│   │   ├── <service>-<env>.service       # Third-party service (no tt-)
│   │   ├── tt-<service>-watchdog-<env>.service  # YOUR service (tt- prefix)
│   │   └── <service>-<env>.timer
│   ├── <service>/                    # Service-specific configs
│   │   ├── <service>.conf
│   │   └── <service>-<variant>.conf
│   └── nginx/                        # Nginx configs (if applicable)
├── scripts/
│   ├── deploy/                       # Deployment scripts
│   │   └── deploy-<service>-<component>.sh
│   ├── monitoring/                   # Health checks and watchdogs
│   │   ├── tt-<service>-health-check-<env>.sh
│   │   └── tt-<service>-watchdog-<env>.sh
│   └── utils/                        # Utility scripts
└── docs/
    ├── README.md
    └── runbook-<service>.md
```

### Deployed System Structure

```
/srv/<env>/<service>/
├── scripts/                          # Symlink to source
│   └── monitoring/
│       ├── tt-<service>-health-check-<env>.sh
│       └── tt-<service>-watchdog-<env>.sh
├── configs/                          # Optional: symlink or copy
└── data/                             # Service runtime data

# Symlink pattern (like Docker compose files):
/srv/dev1/kea/scripts -> /home/mpegg-adm/source/TermiteTowers/infra/dhcp/scripts
```

### Deployment Convention

**Systemd Units**:
```bash
# Copy to system location
sudo cp infra/<service>/configs/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tt-<service>-watchdog-dev1.service
sudo systemctl start <service>-dev1.service
```

**Scripts via Symlink** (preferred - keeps source in git):
```bash
# Create /srv structure
sudo mkdir -p /srv/dev1/<service>

# Symlink scripts from source to deployment location
sudo ln -s /home/mpegg-adm/source/TermiteTowers/infra/<service>/scripts \
           /srv/dev1/<service>/scripts
```

**Important**: Systemd ExecStart should reference `/srv/<env>/` NOT `/home/` paths

## Logging Standards for Monitoring Scripts

### Log File Naming

**Format**: `/var/log/tt-<service>-<function>-<env>.log`

**Examples**:
- `/var/log/tt-kea-health-check-dev1.log`
- `/var/log/tt-kea-watchdog-dev1.log`
- `/var/log/tt-postgres-monitor-dev1.log`

**Third-Party Service Logs** (no tt- prefix):
- `/var/log/kea/kea-dhcp4.log` (from Kea itself)
- `/var/log/postgresql/postgresql-16-main.log` (from PostgreSQL)

**Rules**:
- YOUR monitoring logs MUST have `tt-` prefix
- Include environment suffix (`-dev1`, `-prd1`)
- All monitoring logs go to `/var/log/`
- Use hyphen-separated lowercase
- Rotate logs with logrotate
- **Benefit**: `ls /var/log/tt-*` shows only YOUR monitoring logs

### Log Format

All monitoring scripts MUST use this format:

```bash
LOG_FILE="/var/log/tt-<service>-<function>-<env>.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}
```

**Example**:
```bash
LOG_FILE="/var/log/tt-kea-health-check-dev1.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}
```

**Required log entries**:
```bash
log "=== Starting <Service> Health Check ==="
log "OK: <check description>"
log "ERROR: <failure description>"
log "WARNING: <warning description>"
log "=== Health Check Complete: X errors, Y warnings ==="
```

## Integration with Uptime Kuma

### Monitor Naming in Uptime Kuma

**Format**: `<Service> <Function> [<env>]`

**Examples**:
- `Kea DHCP Health [dev1]`
- `PostgreSQL Connection [dev1]`
- `Kea DHCP Port 67 [dev1]`
- `PowerDNS DNS Updates [dev1]`

**Rules**:
- Title case for service names
- Environment in brackets at end
- Descriptive function in middle
- Group by service using Uptime Kuma tags

### Script Monitor Configuration

```yaml
Monitor Type: Script
Command: /home/mpegg-adm/source/TermiteTowers/infra/<service>/scripts/monitoring/check-<service>-health.sh
Interval: 5 minutes
Expected Exit Code: 0
```

### Complete Example: Kea DHCP Infrastructure

**Source Repository**:
```
infra/dhcp/
├── configs/
│   ├── systemd/
│   │   ├── kea-dhcp4-dev1.service           # Third-party service (no tt-)
│   │   ├── kea-dhcp-ddns.service            # Third-party service
│   │   └── tt-kea-watchdog-dev1.service     # YOUR watchdog (tt- prefix)
│   ├── kea/
│   │   ├── tt-kea-dhcp4-dev1.conf           # YOUR config (tt- prefix)
│   │   ├── tt-kea-dhcp-ddns-dev1.conf       # YOUR config
│   │   ├── tt-kea-dhcp4-dev1-nodb.conf      # Variant config
│   │   └── kea-dhcp4.conf.install           # Package default (reference)
│   └── nginx/
│       └── kea-status-endpoint.conf
├── scripts/
│   ├── deploy/
│   │   ├── deploy-kea-config.sh
│   │   ├── deploy-kea-ddns.sh
│   │   └── migrate-to-tt-naming.sh
│   ├── monitoring/
│   │   ├── tt-kea-health-check-dev1.sh      # YOUR script (tt- prefix)
│   │   ├── tt-kea-watchdog-dev1.sh          # YOUR script
│   │   └── parse-kea-logs.py
│   └── utils/
└── docs/
    ├── README.md
    └── uptime-kuma-setup.md
```

**Deployed System**:
```
/srv/dev1/kea/
├── scripts/  → symlink to source repo
└── configs/  → symlink to source repo (optional)

/etc/kea/
├── tt-kea-dhcp4-dev1.conf                   # YOUR config (active)
├── tt-kea-dhcp-ddns-dev1.conf
└── kea-dhcp4.conf.install                   # Package default

/etc/systemd/system/
├── kea-dhcp4-dev1.service                   # Runs /etc/kea/tt-kea-dhcp4-dev1.conf
├── kea-dhcp-ddns.service
└── tt-kea-watchdog-dev1.service             # YOUR watchdog

/var/log/
├── tt-kea-health-check-dev1.log             # YOUR logs (tt- prefix)
├── tt-kea-watchdog-dev1.log
└── kea/
    ├── kea-dhcp4.log                        # Kea's own logs
    └── kea-ddns.log
```

## Examples

### Complete Service Setup: Kea DHCP (Following tt- Standard)

**Source Repository**:
```
infra/dhcp/
├── configs/
│   ├── systemd/
│   │   ├── kea-dhcp4-dev1.service       # Main service
│   │   ├── kea-dhcp-ddns-dev1.service   # DDNS companion
│   │   └── tt-kea-watchdog-dev1.service # Failure handler (tt- prefix)
│   └── kea/
│       ├── tt-kea-dhcp4-dev1.conf       # YOUR config (tt- prefix)
│       └── tt-kea-dhcp-ddns-dev1.conf
├── scripts/
│   ├── deploy/
│   │   ├── deploy-kea-config.sh
│   │   └── deploy-kea-ddns.sh
│   ├── monitoring/
│   │   ├── tt-kea-health-check-dev1.sh  # Comprehensive check (tt- prefix)
│   │   ├── tt-kea-postgres-check-dev1.sh # DB connectivity
│   │   ├── tt-kea-watchdog-dev1.sh      # Auto-recovery (tt- prefix)
│   │   └── tt-kea-recovery-dev1.sh      # Manual recovery
│   └── utils/
│       └── parse-kea-logs.py
└── docs/
    ├── README.md
    └── uptime-kuma-setup.md
```

### Systemd Service with Watchdog

`/etc/systemd/system/kea-dhcp4-dev1.service`:
```ini
[Unit]
Description=Kea DHCPv4 Server (dev1)
After=network.target postgresql.service
Requires=postgresql.service
OnFailure=tt-kea-watchdog-dev1.service

[Service]
ExecStart=/usr/sbin/kea-dhcp4 -c /etc/kea/tt-kea-dhcp4-dev1.conf
Restart=on-failure
RestartSec=10
User=root
Group=root

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/tt-kea-watchdog-dev1.service`:
```ini
[Unit]
Description=Kea DHCP Watchdog - Auto Recovery (dev1)
After=network.target

[Service]
Type=oneshot
ExecStart=/srv/dev1/kea/scripts/monitoring/tt-kea-watchdog-dev1.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Quick Reference

| Type | Naming Pattern | Example |
|------|----------------|---------|
| **Third-Party Service** | `<app>-<env>.service` | `kea-dhcp4-dev1.service` |
| **Custom Service** | `tt-<service>-<function>-<env>.service` | `tt-kea-watchdog-dev1.service` |
| **Timer Unit** | `<service>-<env>.timer` | `backup-dev1.timer` |
| **Config File** | `tt-<service>-<component>-<env>.conf` | `tt-kea-dhcp4-dev1.conf` |
| **Health Check Script** | `tt-<service>-<function>-<env>.sh` | `tt-kea-health-check-dev1.sh` |
| **Watchdog Script** | `tt-<service>-watchdog-<env>.sh` | `tt-kea-watchdog-dev1.sh` |
| **Deployment Script** | `deploy-<component>-<action>.sh` | `deploy-kea-config.sh` |
| **Log File** | `/var/log/tt-<service>-<function>-<env>.log` | `/var/log/tt-kea-watchdog-dev1.log` |

## Migration Checklist

When creating new monitoring infrastructure:

- [ ] Follow environment suffix convention (`-dev1`, `-dev2`, etc.)
- [ ] Use `tt-` prefix for YOUR services, scripts, configs, and logs
- [ ] NO `tt-` prefix for third-party/packaged services
- [ ] Use hyphenated lowercase for all file names
- [ ] Place systemd units in `infra/<service>/configs/systemd/`
- [ ] Place configs in `infra/<service>/configs/<service>/` with `tt-` prefix
- [ ] Place monitoring scripts in `infra/<service>/scripts/monitoring/` with `tt-` prefix
- [ ] Use standard log format with timestamps
- [ ] Deploy scripts to `/srv/<env>/<service>/` via symlinks
- [ ] Systemd ExecStart uses `/srv/<env>/` paths NOT `/home/` paths
- [ ] Make scripts executable: `chmod +x *.sh`
- [ ] Follow `script-standards.md` for bash best practices
- [ ] Add monitors to Uptime Kuma with consistent naming
- [ ] Document in service README and runbook
- [ ] Test failure scenarios and watchdog recovery
- [ ] Verify logs appear with `ls /var/log/tt-*`

## Related Documents

- `script-standards.md` - Bash script coding standards
- `compose-conventions.md` - Docker compose naming conventions
- `Device-Naming-Standard.md` - Network device naming
- Individual runbooks in `wiki/runbook-*.md`
