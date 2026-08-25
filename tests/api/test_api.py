"""Tests for the local operator API and frontend."""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from src.api.main import create_app
from src.config.settings import Settings
from src.orchestration.session import AgentSession


def _client(symbols: list[str] | None = None) -> tuple[TestClient, AgentSession]:
    settings = Settings(
        llm_enabled=False,
        symbol_allowlist=symbols or ["AAPL"],
        live_trading_enabled=False,
        broker="paper",
    )
    session = AgentSession(settings, initial_capital=Decimal("100000"))
    return TestClient(create_app(session)), session


def test_health_ok():
    client, _ = _client()
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_frontend_index_served():
    client, _ = _client()
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Trading Agent" in res.text
    assert "/styles.css" in res.text
    assert "/app.js" in res.text


def test_frontend_assets_served():
    client, _ = _client()
    css = client.get("/styles.css")
    js = client.get("/app.js")
    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert "--bg:" in css.text
    assert js.status_code == 200
    assert "Run iteration" in js.text or "btn-run" in js.text


def test_state_before_and_after_run():
    client, _ = _client()
    before = client.get("/api/state").json()
    assert before["status"]["runs"] == 0
    assert before["status"]["broker"] == "paper"
    assert before["status"]["live_trading_enabled"] is False
    assert before["audit"] == []

    run = client.post("/api/run")
    assert run.status_code == 200
    body = run.json()
    assert body["ok"] is True
    assert body["added"] >= 1
    assert body["state"]["status"]["runs"] == 1
    assert len(body["state"]["audit"]) >= 1
    assert body["state"]["portfolio"]["positions"]


def test_kill_switch_blocks_run():
    client, _ = _client()
    armed = client.post("/api/kill-switch", json={"enabled": True})
    assert armed.status_code == 200
    assert armed.json()["kill_switch"] is True

    blocked = client.post("/api/run").json()
    assert blocked["ok"] is False
    assert blocked["blocked"] is True
    assert blocked["reason"] == "kill_switch"
    assert blocked["state"]["status"]["runs"] == 0

    client.post("/api/kill-switch", json={"enabled": False})
    resumed = client.post("/api/run").json()
    assert resumed["ok"] is True
    assert resumed["state"]["status"]["runs"] == 1
