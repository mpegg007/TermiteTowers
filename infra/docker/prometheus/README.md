<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: infra/docker/prometheus/README.md % -->
<!-- %ccm_git_object_id: infra/docker/prometheus/README.md@218 % -->
<!-- %ccm_git_commit_date: 2026-11-13 14:50:44 -0500 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: changes 261113 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
# Prometheus config (dev1)

This directory is the **source of truth** for Prometheus configuration. It is
mounted read-only at `/etc/prometheus` by
[`../prometheus-dev1.yml`](../prometheus-dev1.yml).

```
prometheus/
  prometheus.yml     global settings, rule_files, scrape_configs
  rules/
    host.yml         disk capacity/trend, memory, load, systemd units
    containers.yml   restart loops, OOM kills, engine-metrics blindness
    backup.yml       backup staleness, emitter heartbeat, textfile errors
    scrape.yml       target down, rule evaluation lag, TSDB growth
```

Do not hand-edit `/mnt/ai_storage/prometheus/config`. It is no longer mounted.
The previous setup generated that file from a heredoc in
`scripts/deploy-prometheus-tensorflow.sh`, which is how a scrape target of
`localhost:9100` — inside the Prometheus container, therefore unreachable by
definition — stayed broken and unnoticed. That generator is now removed.

## Applying a change

```bash
# edit a file here, then:
scripts/deploy-prometheus.sh
```

That validates with `promtool` (in the pinned image, so the version matches the
server), POSTs `/-/reload`, and prints target health. Individual actions:

```bash
scripts/deploy-prometheus.sh validate
scripts/deploy-prometheus.sh reload
scripts/deploy-prometheus.sh verify
```

`verify` exits non-zero if any target is down. The listener is loopback-only, so
this runs on the host.

## Design decisions worth not undoing

**No `alerting:` block, no Alertmanager.** Prometheus cannot send mail; the gap
is a delivery agent, not a coordinator. [`scripts/tt-prometheus-alerts.sh`](../../../scripts/tt-prometheus-alerts.sh)
reads alert state and hands delivery to `ttmail`, which already has an
allow-list, rate caps and loop detection. One script instead of another daemon,
and rules stay where they belong.

**`node` scrapes `node-exporter:9100`, never `localhost`.** Container DNS on
`monitor-apps-net-dev1`. `localhost` inside the Prometheus container is
Prometheus itself.

**`docker` scrapes `172.17.0.1:9323`, not `host.docker.internal`.** The latter
resolves to the compose bridge gateway `10.10.64.1`, which does not reach a
listener bound to docker0. Enable the listener with
[`scripts/system/enable-docker-metrics.sh`](../../../scripts/system/enable-docker-metrics.sh).

**Retention is capped by both time and size** (30d, 5GB). Time-only retention on
a pool shared with the data being watched has no upper bound.

**Metrics are not backed up.** They are disposable. Losing the TSDB costs
history, not data.
