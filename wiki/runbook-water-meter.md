<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2026-08-07 %
% ccm_author: mpegg %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: wiki/runbook-water-meter.md %
tt-ccm.header.end
-->

# Runbook: Water Meter Viewer (dev1)

Computer-vision pipeline + FastAPI web viewer that reads the household water
meter from camera photos. Relocated from `AnalAcres/scripts/water_meter`.

- Source: `water-meter/` (top-level folder in this repo)
- Pipeline docs: `water-meter/docs/water-meter-pipeline-logic.md`
- Port: `3414` (Media range, see `ports.md`)

## Install
- `python3 -m venv water-meter/.venv && water-meter/.venv/bin/pip install -e .`

## Start/Stop (webapp)
- Start (foreground): `water-meter/run.sh` (or `./run.sh 3414 localhost`)
- Start (systemd): `sudo systemctl start water-meter`
- Stop: `sudo systemctl stop water-meter`
- Enable on boot: `sudo systemctl enable water-meter`
- Status/logs: `sudo systemctl status water-meter -l` and `journalctl -u water-meter -f`

### Install the systemd unit
```bash
sudo ln -s /home/mpegg-adm/source/TermiteTowers/water-meter/systemd/water-meter.service /etc/systemd/system/water-meter.service
sudo systemctl daemon-reload && sudo systemctl enable --now water-meter
```

## URL
- Local: http://localhost:3414
- Optional remote: nginx site `infra/nginx/sites-available/water-meter.conf` (not enabled by default)

## Paths
- Program: /home/mpegg-adm/source/TermiteTowers/water-meter
- Data (external, not in repo): `~/pictures/water_meter/` (pending/scanned/proc/debug/templates/keepers)
- DB (external): PostgreSQL `ttdb_dev1`, schema `water_meter`, table `meter_readings`

## Config
- `WATER_METER_DB_DSN` (default `postgresql:///ttdb_dev1`) — see `water-meter/src/water_meter/core/db.py`
- `WATER_METER_ROOT` (default `~/pictures/water_meter/`) — see `water-meter/src/water_meter/core/common.py`

## Pipeline (cron-friendly)
- `water-meter/.venv/bin/python -m water_meter.core.pipeline --auto`
- Individual stages: `python -m water_meter.core.<stage>` (e.g. `decode_meter`, `decode_odo`, `calc_needle_readings`)

## Tests
- `water-meter/.venv/bin/python -m pytest water-meter/tests`

## Troubleshooting
- Webapp won't start: ensure venv exists (`pip install -e .`) and PostgreSQL is up.
- Missing images/crops: check `WATER_METER_ROOT` points at the real image tree.
- Debug endpoints shell out to `decode_meter` via the app venv — check `journalctl -u water-meter` for subprocess errors.
