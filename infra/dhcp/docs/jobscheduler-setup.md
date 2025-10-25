<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: infra/dhcp/docs/jobscheduler-setup.md:110 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 4a170e09c4adedb08b5ab6bf01ba741e72330f11 %
  %ccm_git_commit_id: f58291ad575edfb9a551f895005def9b9f831304 %
  %ccm_git_commit_count: 110 %
  %ccm_git_commit_date: 2025-10-25 14:11:42 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: dhcp logging %
  %ccm_git_modify_date: 2025-10-25 14:11:42 %
  %ccm_git_file_last_modified: 2025-10-15 07:41:00 %
  %ccm_git_file_name: jobscheduler-setup.md %
  %ccm_git_path: infra/dhcp/docs/jobscheduler-setup.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 15514 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# JobScheduler (JS7) Setup Guide with PostgreSQL

## Overview

JobScheduler (now JS7) is an enterprise-grade open-source job scheduler for automating workflows, batch jobs, and scheduled tasks. This guide covers setting it up with PostgreSQL as the backend database for managing DHCP log parsing jobs.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    JS7 Architecture                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐         ┌─────────────────┐          │
│  │  JOC Cockpit │◄────────┤   PostgreSQL    │          │
│  │  (Web GUI)   │         │   (Job Config   │          │
│  └──────┬───────┘         │    & History)   │          │
│         │                 └─────────────────┘          │
│         │                                               │
│         ▼                                               │
│  ┌──────────────┐                                      │
│  │  Controller  │                                      │
│  │  (Scheduler) │                                      │
│  └──────┬───────┘                                      │
│         │                                               │
│         ▼                                               │
│  ┌──────────────┐                                      │
│  │   Agents     │  ◄──── Execute Jobs                 │
│  │  (Workers)   │                                      │
│  └──────────────┘                                      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Components

1. **JOC Cockpit** - Web-based GUI for job management and monitoring
2. **Controller** - Central scheduling engine (formerly JobScheduler Master)
3. **Agents** - Execute jobs on local or remote systems
4. **PostgreSQL** - Stores job configurations, schedules, and execution history

## Installation Steps

### 1. Prerequisites

```bash
# System requirements
# - Ubuntu 24.04 LTS (or compatible Linux)
# - Java JRE 11 or higher
# - PostgreSQL 12+ (already installed)
# - 2GB+ RAM
# - 2GB+ disk space

# Install Java if not present
sudo apt update
sudo apt install -y openjdk-11-jre-headless

# Verify Java installation
java -version
```

### 2. Create PostgreSQL Database for JS7

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE js7_joc;
CREATE USER js7_user WITH PASSWORD 'js7-secure-password-here';
GRANT ALL PRIVILEGES ON DATABASE js7_joc TO js7_user;

# Grant schema privileges
\c js7_joc
GRANT ALL ON SCHEMA public TO js7_user;
ALTER DATABASE js7_joc OWNER TO js7_user;

\q
```

### 3. Download JS7 Components

```bash
# Create installation directory
sudo mkdir -p /opt/js7
cd /opt/js7

# Download JS7 components (replace with current version)
# Visit: https://kb.sos-berlin.com/display/JS7/Download

# As of 2025, typical downloads:
# - js7_controller_linux.2.x.x.tar.gz
# - js7_agent_linux.2.x.x.tar.gz
# - js7_joc_linux.2.x.x.tar.gz

# Example download (adjust version):
JS7_VERSION="2.7.1"
wget https://download.sos-berlin.com/JobScheduler.2.0/js7_controller_linux.${JS7_VERSION}.tar.gz
wget https://download.sos-berlin.com/JobScheduler.2.0/js7_agent_linux.${JS7_VERSION}.tar.gz
wget https://download.sos-berlin.com/JobScheduler.2.0/js7_joc_linux.${JS7_VERSION}.tar.gz
```

### 4. Install JOC Cockpit (Web Interface)

```bash
# Extract JOC Cockpit
cd /opt/js7
tar -xzf js7_joc_linux.${JS7_VERSION}.tar.gz
cd joc

# Configure database connection
cat > resources/joc/hibernate.cfg.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE hibernate-configuration PUBLIC
    "-//Hibernate/Hibernate Configuration DTD 3.0//EN"
    "http://www.hibernate.org/dtd/hibernate-configuration-3.0.dtd">
<hibernate-configuration>
    <session-factory>
        <!-- PostgreSQL Database Connection -->
        <property name="hibernate.connection.driver_class">org.postgresql.Driver</property>
        <property name="hibernate.connection.url">jdbc:postgresql://localhost:5432/js7_joc</property>
        <property name="hibernate.connection.username">js7_user</property>
        <property name="hibernate.connection.password">js7-secure-password-here</property>
        <property name="hibernate.dialect">org.hibernate.dialect.PostgreSQLDialect</property>
        
        <!-- Connection Pool Settings -->
        <property name="hibernate.c3p0.min_size">5</property>
        <property name="hibernate.c3p0.max_size">20</property>
        <property name="hibernate.c3p0.timeout">300</property>
        <property name="hibernate.c3p0.max_statements">50</property>
        <property name="hibernate.c3p0.idle_test_period">3000</property>
        
        <!-- Schema Management -->
        <property name="hibernate.hbm2ddl.auto">update</property>
        <property name="hibernate.show_sql">false</property>
    </session-factory>
</hibernate-configuration>
EOF

# Install systemd service
sudo cat > /etc/systemd/system/js7-joc.service << 'EOF'
[Unit]
Description=JS7 JOC Cockpit
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=forking
User=js7
Group=js7
WorkingDirectory=/opt/js7/joc
ExecStart=/opt/js7/joc/bin/joc.sh start
ExecStop=/opt/js7/joc/bin/joc.sh stop
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

# Create JS7 user
sudo useradd -r -s /bin/bash -d /opt/js7 js7
sudo chown -R js7:js7 /opt/js7
```

### 5. Install Controller (Scheduler Engine)

```bash
# Extract Controller
cd /opt/js7
tar -xzf js7_controller_linux.${JS7_VERSION}.tar.gz
cd controller

# Basic configuration
cat > config/controller.conf << 'EOF'
js7 {
  web {
    # HTTPS configuration
    https {
      enabled = yes
      port = 4443
    }
  }
  
  configuration {
    # Working directory
    directory = "/opt/js7/controller/var"
  }
  
  journal {
    # PostgreSQL connection for journal
    # (alternatively can use file-based)
    type = "PostgreSQL"
    postgres {
      host = "localhost"
      port = 5432
      database = "js7_joc"
      user = "js7_user"
      password = "js7-secure-password-here"
    }
  }
}
EOF

# Install systemd service
sudo cat > /etc/systemd/system/js7-controller.service << 'EOF'
[Unit]
Description=JS7 Controller
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=js7
Group=js7
WorkingDirectory=/opt/js7/controller
ExecStart=/opt/js7/controller/bin/controller.sh start-fg
ExecStop=/opt/js7/controller/bin/controller.sh stop
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF
```

### 6. Install Agent (Job Executor)

```bash
# Extract Agent
cd /opt/js7
tar -xzf js7_agent_linux.${JS7_VERSION}.tar.gz
cd agent

# Basic configuration
cat > config/agent.conf << 'EOF'
js7 {
  web {
    # HTTPS configuration
    https {
      enabled = yes
      port = 4445
    }
  }
  
  configuration {
    directory = "/opt/js7/agent/var"
  }
  
  job {
    # Maximum concurrent jobs
    executions = 10
  }
}
EOF

# Install systemd service
sudo cat > /etc/systemd/system/js7-agent.service << 'EOF'
[Unit]
Description=JS7 Agent
After=network.target

[Service]
Type=simple
User=js7
Group=js7
WorkingDirectory=/opt/js7/agent
ExecStart=/opt/js7/agent/bin/agent.sh start-fg
ExecStop=/opt/js7/agent/bin/agent.sh stop
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF
```

### 7. Set Permissions and Enable Services

```bash
# Set ownership
sudo chown -R js7:js7 /opt/js7

# Reload systemd
sudo systemctl daemon-reload

# Enable and start services
sudo systemctl enable js7-joc js7-controller js7-agent
sudo systemctl start js7-controller
sleep 10
sudo systemctl start js7-agent
sleep 10
sudo systemctl start js7-joc

# Check status
sudo systemctl status js7-controller
sudo systemctl status js7-agent
sudo systemctl status js7-joc
```

### 8. Access JOC Cockpit

```bash
# Default URL (adjust if configured differently):
# http://localhost:4446/joc

# Default credentials (change immediately):
# Username: root
# Password: root
```

## Configuring DHCP Log Parser Job

### Job Configuration (XML format)

Create job definition in JOC Cockpit or as XML file:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<job name="dhcp-log-parser" title="Parse DHCP Logs to PostgreSQL">
    <script language="shell">
        <![CDATA[
#!/bin/bash
set -e

# Run DHCP log parser with sudo (for Kea logs)
sudo /usr/bin/python3 /home/mpegg-adm/source/TermiteTowers/infra/dhcp/scripts/monitoring/parse-kea-logs.py \
    --log-files /var/log/kea/kea-dhcp4.log \
    --log-type kea

# Exit with status
exit $?
        ]]>
    </script>
    
    <run_time>
        <!-- Run every 10 minutes -->
        <period single_start="00:00" repeat="00:10"/>
    </run_time>
    
    <monitor name="email_on_error">
        <script language="javascript">
            <![CDATA[
function spooler_task_after() {
    if (spooler_task.exit_code != 0) {
        spooler_log.mail().to("admin@example.com")
            .subject("DHCP Log Parser Failed")
            .body("Exit code: " + spooler_task.exit_code)
            .send();
    }
    return true;
}
            ]]>
        </script>
    </monitor>
</job>
```

### Alternative: Job Chain for Complex Workflow

```xml
<?xml version="1.0" encoding="UTF-8"?>
<job_chain name="dhcp-monitoring-workflow" title="DHCP Monitoring Workflow">
    <job_chain_node state="parse-logs" job="dhcp-log-parser"/>
    <job_chain_node state="check-anomalies" job="dhcp-anomaly-detector"/>
    <job_chain_node state="send-report" job="dhcp-daily-report"/>
    <job_chain_node state="success"/>
    <job_chain_node state="error"/>
</job_chain>
```

### Schedule Configuration

```xml
<?xml version="1.0" encoding="UTF-8"?>
<schedule name="every-10-minutes">
    <period repeat="00:10:00"/>
</schedule>
```

## Alternative: Simpler Systemd Timer Approach

If JobScheduler seems too heavyweight, here's a simple systemd timer alternative:

### Create Service File

```bash
sudo tee /etc/systemd/system/dhcp-log-parser.service << 'EOF'
[Unit]
Description=Parse DHCP logs to PostgreSQL
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=oneshot
User=root
WorkingDirectory=/home/mpegg-adm/source/TermiteTowers/infra/dhcp/scripts/monitoring
ExecStart=/usr/bin/python3 parse-kea-logs.py --log-files /var/log/kea/kea-dhcp4.log --log-type kea
StandardOutput=journal
StandardError=journal
SyslogIdentifier=dhcp-parser

[Install]
WantedBy=multi-user.target
EOF
```

### Create Timer File

```bash
sudo tee /etc/systemd/system/dhcp-log-parser.timer << 'EOF'
[Unit]
Description=Run DHCP log parser every 10 minutes
Requires=dhcp-log-parser.service

[Timer]
OnBootSec=2min
OnUnitActiveSec=10min
AccuracySec=1min

[Install]
WantedBy=timers.target
EOF
```

### Enable and Start Timer

```bash
sudo systemctl daemon-reload
sudo systemctl enable dhcp-log-parser.timer
sudo systemctl start dhcp-log-parser.timer

# Check timer status
sudo systemctl list-timers --all | grep dhcp
systemctl status dhcp-log-parser.timer

# View logs
journalctl -u dhcp-log-parser.service -f
```

## Comparison: JobScheduler vs Systemd Timer

| Feature | JobScheduler | Systemd Timer |
|---------|-------------|---------------|
| **Complexity** | High - Full enterprise scheduler | Low - Simple timer |
| **Setup Time** | 2-4 hours | 10 minutes |
| **GUI** | Yes (JOC Cockpit) | No |
| **Dependencies** | PostgreSQL, Java, Multiple components | None |
| **Job Chains** | Yes - Complex workflows | Limited |
| **Monitoring** | Built-in dashboard | journalctl |
| **Error Handling** | Advanced (retry, notifications, etc.) | Basic |
| **Resource Usage** | ~500MB RAM | ~1MB RAM |
| **Ideal For** | 50+ scheduled jobs, complex workflows | Simple periodic tasks |
| **Cost** | Free (Open Source) | Free (Built-in) |

## Recommendation

### Use JobScheduler If:
- You plan to schedule 20+ different jobs
- Need complex job dependencies and workflows
- Want centralized job monitoring dashboard
- Need advanced error handling and retry logic
- Have compliance/audit requirements
- Managing jobs across multiple servers

### Use Systemd Timer If:
- You have 1-10 simple scheduled tasks
- Jobs are independent (no complex dependencies)
- Prefer lightweight, built-in solutions
- Want quick setup and minimal maintenance
- System-level scheduling is sufficient

## For DHCP Log Parser Specifically

**Recommendation: Start with Systemd Timer**

Reasons:
1. Single, simple periodic task
2. No complex dependencies
3. Built-in, no additional software
4. Minimal resource overhead
5. Easy to debug with journalctl
6. Can migrate to JobScheduler later if needs grow

## Monitoring and Maintenance

### Systemd Timer Monitoring

```bash
# Check if timer is active
systemctl is-active dhcp-log-parser.timer

# View next scheduled run
systemctl status dhcp-log-parser.timer

# View execution history
journalctl -u dhcp-log-parser.service --since "1 day ago"

# Test manual execution
sudo systemctl start dhcp-log-parser.service
```

### Check Database Growth

```sql
-- Monitor table size
SELECT 
    pg_size_pretty(pg_total_relation_size('dhcp_history.lease_events')) as total_size,
    count(*) as event_count
FROM dhcp_history.lease_events;

-- Events per day
SELECT 
    date(timestamp) as event_date,
    count(*) as events,
    count(DISTINCT mac_address) as unique_devices
FROM dhcp_history.lease_events
WHERE timestamp > now() - interval '7 days'
GROUP BY date(timestamp)
ORDER BY event_date DESC;
```

## Future Enhancements

1. **Alerting**: Add email/Slack notifications for anomalies
2. **Dashboard**: Create Grafana dashboard for DHCP metrics
3. **Cleanup**: Add job to archive old events (>90 days)
4. **Multiple Sources**: Parse logs from additional DHCP servers
5. **API**: Expose DHCP history via REST API

## Resources

- [JS7 Documentation](https://kb.sos-berlin.com/display/JS7)
- [JS7 Downloads](https://kb.sos-berlin.com/display/JS7/Download)
- [PostgreSQL Integration](https://kb.sos-berlin.com/display/JS7/Database)
- [Systemd Timers](https://www.freedesktop.org/software/systemd/man/systemd.timer.html)

## Quick Start Command Reference

```bash
# Systemd Timer Quick Setup
cd /home/mpegg-adm/source/TermiteTowers/infra/systemd
sudo cp dhcp-log-parser.service /etc/systemd/system/
sudo cp dhcp-log-parser.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dhcp-log-parser.timer

# View status
systemctl status dhcp-log-parser.timer
journalctl -u dhcp-log-parser.service -f
```

---

**Created**: October 14, 2025  
**Author**: AI Assistant  
**Purpose**: DHCP Log Parser Automation Setup Guide
