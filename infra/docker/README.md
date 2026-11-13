<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: infra/docker/README.md % -->
<!-- %ccm_git_object_id: infra/docker/README.md@218 % -->
<!-- %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: changes 261113 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!--
-->

# docker (migrate to infra)

These compose files are candidates to move into `../infra/docker`.
For now, they remain here; tools and scripts should tolerate either path.

## Monitoring

| File | Role |
|---|---|
| `prometheus-dev1.yml` | TSDB, rule evaluation. Loopback-only listener; config mounted read-only from `prometheus/`. |
| `prometheus/` | **Source of truth** for Prometheus config and alert rules. Edit here, then run `scripts/deploy-prometheus.sh`. See [`prometheus/README.md`](prometheus/README.md). |
| `node-exporter-dev1.yml` | Host metrics: filesystem capacity, memory, systemd units. No published port. |
| `uptime-kuma-dev1.yml` | Availability probes and alerting. |

Runbook: [`wiki/runbook-prometheus.md`](../../wiki/runbook-prometheus.md).
Deploy: `scripts/deploy-prometheus.sh` (validate + reload + verify).
Docker engine metrics for container alerts:
`scripts/system/enable-docker-metrics.sh`.
