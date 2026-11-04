import os
import sys
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

# Garante inclusão da raiz do projeto no sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from app.web.app import app

    @app.middleware("http")
    async def global_error_capture_middleware(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception:
            err = traceback.format_exc()
            return PlainTextResponse(f"Runtime Exception:\n\n{err}", status_code=200)

except Exception:
    startup_error = traceback.format_exc()
    app = FastAPI(title="Focus Publisher Diagnostic")

    @app.api_route("/{path_name:path}", methods=["GET", "POST", "HEAD", "OPTIONS"])
    async def catch_all(request: Request, path_name: str = ""):
        return PlainTextResponse(f"Startup Exception Traceback:\n\n{startup_error}", status_code=200)

__all__ = ["app"]
