"""Local control-plane API + static frontend (operator UI).

Start via ``python scripts/run_agent.py --ui``. Binds localhost by default.
"""

from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.config.settings import Settings
from src.orchestration.session import AgentSession

_FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


class KillSwitchBody(BaseModel):
    enabled: bool = Field(..., description="True to disarm (block new runs).")


def create_app(session: AgentSession) -> FastAPI:
    """Build a FastAPI app bound to an in-memory ``AgentSession``."""
    app = FastAPI(
        title="Trading Agent",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
    )
    app.state.session = session

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/state")
    def get_state(request: Request) -> dict[str, Any]:
        return _session(request).snapshot()

    @app.post("/api/run")
    def run_once(request: Request) -> dict[str, Any]:
        sess = _session(request)
        if sess.settings.kill_switch:
            return {
                "ok": False,
                "blocked": True,
                "reason": "kill_switch",
                "added": 0,
                "state": sess.snapshot(),
            }
        records = sess.run_once()
        return {
            "ok": True,
            "blocked": False,
            "reason": None,
            "added": len(records),
            "state": sess.snapshot(),
        }

    @app.post("/api/kill-switch")
    def set_kill_switch(body: KillSwitchBody, request: Request) -> dict[str, Any]:
        sess = _session(request)
        sess.set_kill_switch(body.enabled)
        return {"ok": True, "kill_switch": sess.settings.kill_switch, "state": sess.snapshot()}

    if _FRONTEND_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
    else:

        @app.get("/")
        def missing_frontend() -> JSONResponse:
            return JSONResponse(
                status_code=500,
                content={"detail": "frontend/ directory is missing"},
            )

    return app


def _session(request: Request) -> AgentSession:
    sess = getattr(request.app.state, "session", None)
    if sess is None:
        raise HTTPException(status_code=500, detail="agent session not initialized")
    return sess


def serve_ui(
    settings: Settings,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    """Run one seeding iteration, then serve the UI until interrupted."""
    import uvicorn

    session = AgentSession(settings)
    session.run_once()
    app = create_app(session)
    url = f"http://{host}:{port}"
    print(f"Trading agent UI: {url}")
    print("Paper broker, stub quotes, no live APIs. Ctrl+C to stop.")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001 — opening a browser is best-effort
            pass
    uvicorn.run(app, host=host, port=port, log_level="info")
