"""
PYTHON/dashboard/websocket_server.py — FastAPI + WebSocket Canlı Dashboard

Kullanim:
    uvicorn PYTHON.dashboard.websocket_server:app --host 0.0.0.0 --port 8081
    veya
    python PYTHON/dashboard/websocket_server.py

Endpointler:
    - GET  /          -> HTML dashboard
    - GET  /metrics   -> Prometheus metrikler (opsiyonel)
    - WS   /ws/dashboard -> Canli portfoy + sinyal akisi
"""
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

import asyncio
import json
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="AnatoliaX Dashboard", version="3.0")

# Static dosyalar (index.html)
static_path = Path(__file__).resolve().parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")


class ConnectionManager:
    """WebSocket baglanti yoneticisi."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        text = json.dumps(message, ensure_ascii=False, default=str)
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


def _get_portfolio_snapshot() -> dict:
    """SQLite'den canli portfoy ozeti cek."""
    try:
        from risk.database import get_session
        from paper_trading.models import PaperPortfolio, PaperSignal

        session = get_session()
        try:
            # Paper portfoy
            pf = session.query(PaperPortfolio).first()
            if pf:
                portfolio = {
                    "capital": float(pf.current_capital),
                    "pnl": float(pf.total_pnl),
                    "return_pct": float(pf.total_return_pct),
                }
            else:
                portfolio = {"capital": 0.0, "pnl": 0.0, "return_pct": 0.0}

            # Son 5 sinyal
            recent_signals = (
                session.query(PaperSignal)
                .order_by(PaperSignal.signal_time.desc())
                .limit(5)
                .all()
            )
            signals = []
            for s in recent_signals:
                signals.append({
                    "symbol": s.symbol,
                    "score": s.signal_score,
                    "regime": s.regime,
                    "outcome": s.outcome,
                    "time": s.signal_time.isoformat() if s.signal_time else None,
                })

            return {
                "type": "snapshot",
                "timestamp": datetime.now().isoformat(),
                "portfolio": portfolio,
                "signals": signals,
                "positions": portfolio.get("capital", 0),
            }
        finally:
            session.close()
    except Exception:
        # Hata durumunda bos snapshot
        return {
            "type": "snapshot",
            "timestamp": datetime.now().isoformat(),
            "portfolio": {"capital": 0.0, "pnl": 0.0, "return_pct": 0.0},
            "signals": [],
            "positions": 0,
        }


async def _broadcast_loop():
    """Her 5 saniyede tüm baglanti portfoy snapshot'i gonder."""
    while True:
        await asyncio.sleep(5)
        snapshot = _get_portfolio_snapshot()
        await manager.broadcast(snapshot)


@app.get("/", response_class=HTMLResponse)
async def index():
    """Dashboard ana sayfa."""
    index_file = static_path / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse(
        "<!DOCTYPE html>\n"
        '<html><head><title>AnatoliaX Dashboard</title></head>\n'
        "<body><h1>AnatoliaX Dashboard v3.0</h1>\n"
        '<p>Static/index.html bulunamadi. WebSocket: /ws/dashboard</p>\n'
        "</body></html>"
    )


@app.get("/health")
async def health():
    return {"status": "ok", "connections": len(manager.active_connections)}


@app.get("/metrics")
async def metrics():
    """Prometheus basic metrics."""
    lines = [
        f"# TYPE anatoliax_ws_connections gauge",
        f"anatoliax_ws_connections {len(manager.active_connections)}",
    ]
    return PlainTextResponse(content="\n".join(lines))


@app.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    await manager.connect(websocket)
    # Hemen ilk snapshot gonder
    await websocket.send_text(json.dumps(_get_portfolio_snapshot(), ensure_ascii=False, default=str))
    try:
        while True:
            # Istemciden gelen mesajlari al (ping/keep-alive)
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@app.on_event("startup")
async def on_startup():
    asyncio.create_task(_broadcast_loop())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "PYTHON.dashboard.websocket_server:app",
        host="0.0.0.0",
        port=8081,
        log_level="info",
    )
