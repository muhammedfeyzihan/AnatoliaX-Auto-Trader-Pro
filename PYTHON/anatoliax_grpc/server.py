"""
server.py — AnatoliaX gRPC Server
Local-only, token/IP gerektirmez. Otomatik port seçimi.

Kullanim:
    from anatoliax_grpc.server import AnatoliaXGrpcServer
    server = AnatoliaXGrpcServer()
    port = server.start()
    # ...
    server.stop()
"""
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

import json
import os
import time
import threading
from concurrent import futures
from datetime import datetime

import grpc

from anatoliax_grpc import anatoliax_pb2
from anatoliax_grpc import anatoliax_pb2_grpc


# Otomatik port kayit dosyasi (git ignore edilebilir)
PORT_FILE = Path(__file__).resolve().parents[2] / "data" / ".grpc_port"


class SignalServiceServicer(anatoliax_pb2_grpc.SignalServiceServicer):
    """Sinyal servisi: Teknik analiz sinyalleri sunar."""

    def GetSignal(self, request, context):
        symbol = request.symbol
        try:
            from paper_trading.signal_engine import SignalEngine
            engine = SignalEngine(paper_trading=False)
            signal = engine.analyze_symbol(symbol)
            if signal is None:
                return anatoliax_pb2.SignalResponse(
                    symbol=symbol, valid=False, reason="Sinyal yok"
                )
            return anatoliax_pb2.SignalResponse(
                symbol=symbol,
                score=signal.get("score", 0.0),
                entry=signal.get("entry", 0.0),
                sl=signal.get("sl", 0.0),
                tp1=signal.get("tp1", 0.0),
                tp2=signal.get("tp2", 0.0),
                r_r=signal.get("r_r", 0.0),
                kelly=signal.get("kelly", 0.0),
                regime=signal.get("regime", "UNKNOWN"),
                valid=True,
                reason="OK",
            )
        except Exception as e:
            return anatoliax_pb2.SignalResponse(
                symbol=symbol, valid=False, reason=str(e)
            )


class RiskServiceServicer(anatoliax_pb2_grpc.RiskServiceServicer):
    """Risk servisi: Portfoy risk kontrolu."""

    def CheckRisk(self, request, context):
        try:
            from risk.kill_switch import KillSwitch
            ks = KillSwitch(max_drawdown=20.0, daily_loss_limit=3.0)
            allowed = ks.is_trading_allowed()
            return anatoliax_pb2.RiskResponse(
                allowed=allowed,
                reason="KillSwitch OK" if allowed else "KillSwitch RED",
                max_drawdown_pct=20.0,
                daily_pnl=request.daily_pnl,
                regime="NEUTRAL",
            )
        except Exception as e:
            return anatoliax_pb2.RiskResponse(
                allowed=False, reason=str(e), max_drawdown_pct=0.0, daily_pnl=0.0
            )


class ReportServiceServicer(anatoliax_pb2_grpc.ReportServiceServicer):
    """Rapor servisi: Gunluk rapor uretimi."""

    def GenerateReport(self, request, context):
        report_type = request.report_type
        try:
            from telegram.reporter import send_report
            send_report(report_type=report_type)
            return anatoliax_pb2.ReportResponse(
                report_type=report_type,
                content=f"Rapor gonderildi: {report_type}",
                timestamp=datetime.now().isoformat(),
                success=True,
            )
        except Exception as e:
            return anatoliax_pb2.ReportResponse(
                report_type=report_type,
                content="",
                timestamp=datetime.now().isoformat(),
                success=False,
                error=str(e),
            )


class AnatoliaXGrpcServer:
    """
    AnatoliaX gRPC Server.
    - Localhost (127.0.0.1) bind
    - Otomatik port seçimi (port 0)
    - Port bilgisi dosyaya yazilir
    - Varsayilan: insecure (localhost-only gelistirme)
    - TLS: GRPC_TLS_CERT ve GRPC_TLS_KEY env var'lari ile aktif edilebilir
    """

    def __init__(self, max_workers: int = 10, use_tls: bool = False):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
        anatoliax_pb2_grpc.add_SignalServiceServicer_to_server(SignalServiceServicer(), self.server)
        anatoliax_pb2_grpc.add_RiskServiceServicer_to_server(RiskServiceServicer(), self.server)
        anatoliax_pb2_grpc.add_ReportServiceServicer_to_server(ReportServiceServicer(), self.server)
        self._port: int = 0
        self._thread: threading.Thread | None = None
        self._use_tls = use_tls or os.getenv("GRPC_TLS_CERT", "").strip() != ""

    def start(self) -> int:
        """
        Server'i baslat ve portu dondur.
        Returns: dinlenen port numarasi
        """
        if self._use_tls:
            cert_path = os.getenv("GRPC_TLS_CERT")
            key_path = os.getenv("GRPC_TLS_KEY")
            with open(cert_path, "rb") as f:
                cert = f.read()
            with open(key_path, "rb") as f:
                key = f.read()
            creds = grpc.ssl_server_credentials(((key, cert),))
            self._port = self.server.add_secure_port("127.0.0.1:0", creds)
        else:
            # Otomatik port secimi (port 0 = OS atar)
            self._port = self.server.add_insecure_port("127.0.0.1:0")
        self.server.start()
        self._save_port(self._port)
        return self._port

    def start_in_thread(self) -> int:
        """Arka planda baslat (test/daemon icin)."""
        port = self.start()
        self._thread = threading.Thread(target=self.server.wait_for_termination, daemon=True)
        self._thread.start()
        return port

    def stop(self, grace_period_sec: float = 5.0):
        """Server'i durdur."""
        self.server.stop(grace_period_sec)
        self._clear_port()

    @staticmethod
    def _save_port(port: int):
        PORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        PORT_FILE.write_text(json.dumps({"port": port, "host": "127.0.0.1", "timestamp": datetime.now().isoformat()}), encoding="utf-8")

    @staticmethod
    def _clear_port():
        if PORT_FILE.exists():
            PORT_FILE.unlink()


if __name__ == "__main__":
    s = AnatoliaXGrpcServer()
    port = s.start()
    print(f"gRPC server 127.0.0.1:{port} adresinde calisiyor...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Durduruluyor...")
        s.stop()
