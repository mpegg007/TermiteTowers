<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: wiki/runbook-prometheus.md % -->
<!-- %ccm_git_object_id: wiki/runbook-prometheus.md@218 % -->
<!-- %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: changes 261113 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
# Runbook: Prometheus & node-exporter (dev1)

Answers questions Uptime Kuma cannot: *how fast is this filling, what keeps
restarting, and is the last backup actually on disk.* Uptime Kuma remains the
authority on "is it up right now".

## Components

| Piece | What it is | Where |
|---|---|---|
| `prometheus-dev1` | TSDB + rule evaluation | `127.0.0.1:3720` → container `9090` |
| `node-exporter-dev1` | Host metrics | `node-exporter:9100` on `monitor-apps-net-dev1`, no published port |
| `dockerd` metrics | Container metrics | `172.17.0.1:9323` (docker0 only, not LAN) |
| `tt-prometheus-alerts.timer` | Alert delivery via ttmail | every 5 min |
| `tt-prometheus-metrics.timer` | Backup freshness metrics | every 15 min |
| nginx vhost | Human access, authenticated | https://prometheus.termitetowers.ca |

Config is repo-managed: [`infra/docker/prometheus/`](../infra/docker/prometheus/README.md).

## Start / stop

```bash
docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/prometheus-dev1.yml up -d
docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/node-exporter-dev1.yml up -d
docker logs --tail 100 prometheus-dev1
docker logs --tail 100 node-exporter-dev1
```

## URL, and why it needs a password

Prometheus has **no authentication of its own**. Its API exposes scrape targets
(which is internal topology), the live config, and the full metric history, so
the vhost is behind `auth_basic`. The container also publishes on loopback only,
so the LAN cannot bypass nginx.

Create the password file once, from the per-tier secrets location — never commit
it:

```bash
# as root; htpasswd comes from apache2-utils
sudo htpasswd -c /etc/nginx/htpasswd-prometheus prometheus
sudo chown root:www-data /etc/nginx/htpasswd-prometheus
sudo chmod 0640 /etc/nginx/htpasswd-prometheus
sudo nginx -t && sudo systemctl reload nginx
```

The vhost is also **gate-ready**: `Location /` includes
`snippets/tt-gate.conf`, inert until Authelia lands (see
[`runbook-authelia.md`](runbook-authelia.md)). Because that gate does nothing
yet, `auth_basic` is the actual protection — do not remove it on the assumption
the gate is covering for it.

Verify from outside the LAN:

```bash
curl -sk -o /dev/null -w '%{http_code}\n' https://prometheus.termitetowers.ca/api/v1/targets
# 401 = correct. 200 = the vhost is open; fix before anything else.
curl -s http://127.0.0.1:3720/-/healthy     # should still work on the host
```

## Alert delivery

`tt-prometheus-alerts.timer` runs
[`scripts/tt-prometheus-alerts.sh`](../scripts/tt-prometheus-alerts.sh), which
reads firing alerts from the API and mails changes through `ttmail`. One mail on
fire, one on resolve, nothing while unchanged. Alertmanager is deliberately not
deployed.

Recipient config lives outside the repo:

```bash
sudo install -m 0640 -o root -g mpegg-adm /dev/null /etc/tt-secrets/dev1/env/prometheus-alerts.env
# contents:
#   ALERT_TO=you@example.com
#   # optional: TTMAIL_BIN=/path/to/ttmail
```

Test without sending anything:

```bash
scripts/tt-prometheus-alerts.sh --dry-run
```

Prove the whole path end to end, including delivery:

```bash
# 1. Add a rule that fires immediately, to infra/docker/prometheus/rules/tmp-test.yml:
#      groups:
#        - name: tmp-test
#          rules:
#            - alert: TTPipelineTest
#              expr: vector(1)
#              for: 0m
#              labels: {severity: warning}
#              annotations:
#                summary: "synthetic test alert"
#                description: "Delete tmp-test.yml"
# 2. scripts/deploy-prometheus.sh
# 3. sudo systemctl start tt-prometheus-alerts.service   # expect exactly one mail
# 4. sudo systemctl start tt-prometheus-alerts.service   # expect no second mail
# 5. rm rules/tmp-test.yml && scripts/deploy-prometheus.sh
# 6. sudo systemctl start tt-prometheus-alerts.service   # expect one resolved mail
```

If step 4 mails again, dedup state is not persisting: check
`/var/lib/tt-prometheus/alerts.state`.

## Backup freshness

[`scripts/emit-backup-metrics.sh`](../scripts/emit-backup-metrics.sh) reads the
newest file mtime in each backup directory and writes `tt_backup.prom` into
`/mnt/ai_storage/prometheus/textfile`, which node-exporter republishes. It
measures what is on disk, not what a job claimed.

```bash
sudo -u mpegg-adm scripts/emit-backup-metrics.sh
cat /mnt/ai_storage/prometheus/textfile/tt_backup.prom
```

Install the timers:

```bash
sudo install -m 0644 infra/systemd/tt-prometheus-alerts.{service,timer} /etc/systemd/system/
sudo install -m 0644 infra/systemd/tt-prometheus-metrics.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tt-prometheus-alerts.timer tt-prometheus-metrics.timer
systemctl list-timers 'tt-prometheus-*'
```

## Notifications at a glance

| Alert | Means | First check |
|---|---|---|
| `DiskFillingFast` | filesystem reaches zero within 4 days at current rate | what is growing: `du -xh --max-depth=1 /mnt/ai_storage` |
| `DiskLow` | under 15% free | as above, sooner |
| `InodeLow` | out of inodes, not bytes | `df -i` |
| `MemoryPressure` | under 10% available 15m | leaking container; check OOM alerts |
| `ContainerRestartingLoop` | >3 restarts in 1h | `docker logs --tail 100 <name>`, `docker inspect` exit code |
| `ContainerOOMKilled` | kernel killed a process for memory | raise limit deliberately or fix the leak |
| `SystemdUnitFailed` | a unit is failed | `systemctl status <unit>`; if tt-backup, backups are not running |
| `BackupStale` | no new backup file in 26h | `systemctl status tt-backup-<job>.timer` |
| `BackupMetricsMissing` | emitter gone; backup alerts are blind | `tt-prometheus-metrics.timer` |
| `TargetDown` | Prometheus cannot scrape | node down ⇒ all disk alerts blind |
| `ContainerDown` | engine metrics unreachable | `enable-docker-metrics.sh --check` |

## Troubleshooting

**Targets down.** `scripts/deploy-prometheus.sh verify` lists each job. `node`
down means node-exporter is not running or not on the network. `docker` down
means `metrics-addr` is absent from `/etc/docker/daemon.json`:

```bash
scripts/system/enable-docker-metrics.sh --check
```

**Mountpoint labels look wrong.** Confirm what node-exporter actually reports
before trusting a filesystem rule:

```bash
curl -s http://127.0.0.1:3720/api/v1/label/mountpoint/values
```

If paths appear as `/host/mnt/ai_storage`, the rootfs prefix is not being
stripped: rules in `rules/host.yml` match the unprefixed form.

**Alerts never mail.** In order: is the rule firing
(`/api/v1/alerts` through the vhost, or `curl 127.0.0.1:3720/api/v1/alerts`), is
the timer active, does `--dry-run` list it, does `ttmail` resolve (see
`TTMAIL_BIN`), and is `ALERT_TO` set in the EnvironmentFile.

**Reload returns 403.** `--web.enable-lifecycle` is missing from the compose
command.

**Config edit does nothing.** The container mounts the repo directory. Verify the
mount, not the host copy:

```bash
docker inspect prometheus-dev1 --format '{{range .Mounts}}{{.Source}} -> {{.Destination}} ({{.RW}}){{"\n"}}{{end}}'
```
