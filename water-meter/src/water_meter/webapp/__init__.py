"""Water meter web viewer and template manager.

FastAPI web application, served on port 3414.
"""

from .main import create_app, app

__all__ = ["create_app", "app"]
