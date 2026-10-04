# Water Meter

Computer-vision pipeline + web viewer for reading a household water meter from
camera photos. Relocated from `AnalAcres/scripts/water_meter` into TermiteTowers
as a self-contained project.

## What's here

```
water-meter/
├── src/water_meter/
│   ├── core/          # pipeline modules (db, common, decode_meter, decode_odo, …)
│   └── webapp/        # FastAPI app (main + routers + static SPA)
├── tests/             # pytest smoke tests
├── systemd/           # systemd unit for the webapp
├── docs/              # pipeline logic documentation
├── run.sh             # venv + uvicorn launcher (port 3414)
└── pyproject.toml     # installable package (src layout)
```

## Webapp

FastAPI + a single self-contained SPA (`src/water_meter/webapp/static/index.html`).

- **URL:** http://localhost:3414
- **Launch:** `./run.sh [port] [host]` (default `localhost:3414`)
- **Port registry:** `wiki/ports.md` (Media range)

Endpoints are split into routers under `src/water_meter/webapp/routers/`:
`images`, `readings`, `usage`, `templates`, `debug`, `admin`.

## Pipeline

The pipeline (ingest → decode → anchor review → keepers/archive → extract CSV)
is orchestrated by `python -m water_meter.core.pipeline`. See
[`docs/water-meter-pipeline-logic.md`](docs/water-meter-pipeline-logic.md) for
the full flow.

## Setup

```bash
cd water-meter
python3 -m venv .venv
.venv/bin/pip install -e .            # installs water_meter + deps
.venv/bin/pip install -e '.[dev]'     # optional: pytest for tests
./run.sh                              # start webapp on :3414
```

## Configuration

External state is env-var driven and **not** stored in this repo:

| Env var | Default | Purpose |
|---|---|---|
| `WATER_METER_DB_DSN` | `postgresql:///ttdb_dev1` | PostgreSQL DSN (schema `water_meter`) |
| `WATER_METER_ROOT` | `~/pictures/water_meter/` | Image tree: `pending/`, `scanned/`, `proc/`, `debug/`, `templates/`, `keepers/` |

## Tests

```bash
.venv/bin/pytest
```

DB-dependent tests are skipped automatically when `ttdb_dev1` is unreachable.
