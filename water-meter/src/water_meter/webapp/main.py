"""Water meter web application — FastAPI app assembly.

Single-page app served from static/index.html + JSON API endpoints.
Routers live in ``water_meter.webapp.routers``.

Usage:
    ./run.sh
    # or:
    uvicorn water_meter.webapp.main:app --host localhost --port 3414
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from water_meter.core.db import init_db

from .routers import admin, debug, images, readings, templates, usage

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="Water Meter Viewer", version="2.0.0", docs_url=None, redoc_url=None)
    init_db()

    if (STATIC_DIR / "index.html").exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # ── SPA entry ───────────────────────────────────────────────
    @app.get("/", response_class=HTMLResponse)
    def serve_spa() -> str:
        html_path = STATIC_DIR / "index.html"
        if html_path.exists():
            return html_path.read_text()
        return "<h1>Water Meter Viewer</h1><p>Frontend not found.</p>"

    app.include_router(images.router)
    app.include_router(readings.router)
    app.include_router(usage.router)
    app.include_router(templates.router)
    app.include_router(debug.router)
    app.include_router(admin.router)

    return app


app = create_app()
