"""
client.py — AnatoliaX gRPC Client
Portu otomatik olarak dosyadan okur. Localhost-only.

Kullanim:
    from anatoliax_grpc.client import AnatoliaXGrpcClient
    client = AnatoliaXGrpcClient()
    signal = client.get_signal("THYAO")
    risk = client.check_risk()
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
from typing import Optional

import grpc

from anatoliax_grpc import anatoliax_pb2
from anatoliax_grpc import anatoliax_pb2_grpc


PORT_FILE = Path(__file__).resolve().parents[2] / "data" / ".grpc_port"
DEFAULT_TIMEOUT_SEC = 5


class AnatoliaXGrpcClient:
    """
    AnatoliaX gRPC Client.
    - Portu dosyadan okur (service discovery)
    - Token/IP gerektirmez (localhost loopback)
    - Timeout ile guvenli fallback
    """

    def __init__(self, port_file: Path = PORT_FILE, timeout_sec: int = DEFAULT_TIMEOUT_SEC):
        self.port_file = port_file
        self.timeout_sec = timeout_sec
        self._channel: Optional[grpc.Channel] = None
        self._stub_signal: Optional[anatoliax_pb2_grpc.SignalServiceStub] = None
        self._stub_risk: Optional[anatoliax_pb2_grpc.RiskServiceStub] = None
        self._stub_report: Optional[anatoliax_pb2_grpc.ReportServiceStub] = None

    def _discover(self) -> tuple[str, int] | None:
        """Port dosyasindan host/port oku."""
        if not self.port_file.exists():
            return None
        try:
            data = json.loads(self.port_file.read_text(encoding="utf-8"))
            return data.get("host", "127.0.0.1"), int(data.get("port", 0))
        except Exception:
            return None

    def _connect(self) -> bool:
        """Server'a baglan. TLS aktifse secure channel kullanir."""
        if self._channel is not None:
            return True
        discovered = self._discover()
        if discovered is None:
            return False
        host, port = discovered
        target = f"{host}:{port}"
        use_tls = os.getenv("GRPC_TLS_CERT", "").strip() != ""
        if use_tls:
            creds = grpc.ssl_channel_credentials()
            self._channel = grpc.secure_channel(target, creds)
        else:
            self._channel = grpc.insecure_channel(target)
        self._stub_signal = anatoliax_pb2_grpc.SignalServiceStub(self._channel)
        self._stub_risk = anatoliax_pb2_grpc.RiskServiceStub(self._channel)
        self._stub_report = anatoliax_pb2_grpc.ReportServiceStub(self._channel)
        return True

    def get_signal(self, symbol: str) -> dict:
        """
        Sinyal iste.
        Returns: {"symbol": str, "valid": bool, ...} veya {"error": str}
        """
        if not self._connect():
            return {"error": "gRPC server bulunamadi (port dosyasi yok)"}
        try:
            req = anatoliax_pb2.SignalRequest(symbol=symbol)
            resp = self._stub_signal.GetSignal(req, timeout=self.timeout_sec)
            return {
                "symbol": resp.symbol,
                "valid": resp.valid,
                "score": resp.score,
                "entry": resp.entry,
                "sl": resp.sl,
                "tp1": resp.tp1,
                "tp2": resp.tp2,
                "r_r": resp.r_r,
                "kelly": resp.kelly,
                "regime": resp.regime,
                "reason": resp.reason,
            }
        except grpc.RpcError as e:
            return {"error": f"gRPC hatasi: {e.code()} - {e.details()}"}
        except Exception as e:
            return {"error": f"Baglanti hatasi: {e}"}

    def check_risk(self, daily_pnl: float = 0.0) -> dict:
        """
        Risk kontrolu iste.
        Returns: {"allowed": bool, "reason": str, ...} veya {"error": str}
        """
        if not self._connect():
            return {"error": "gRPC server bulunamadi (port dosyasi yok)"}
        try:
            req = anatoliax_pb2.RiskRequest(daily_pnl=daily_pnl)
            resp = self._stub_risk.CheckRisk(req, timeout=self.timeout_sec)
            return {
                "allowed": resp.allowed,
                "reason": resp.reason,
                "max_drawdown_pct": resp.max_drawdown_pct,
                "daily_pnl": resp.daily_pnl,
                "regime": resp.regime,
            }
        except grpc.RpcError as e:
            return {"error": f"gRPC hatasi: {e.code()} - {e.details()}"}
        except Exception as e:
            return {"error": f"Baglanti hatasi: {e}"}

    def generate_report(self, report_type: str) -> dict:
        """
        Rapor iste.
        Returns: {"success": bool, "content": str, ...} veya {"error": str}
        """
        if not self._connect():
            return {"error": "gRPC server bulunamadi (port dosyasi yok)"}
        try:
            req = anatoliax_pb2.ReportRequest(report_type=report_type)
            resp = self._stub_report.GenerateReport(req, timeout=self.timeout_sec)
            return {
                "success": resp.success,
                "content": resp.content,
                "timestamp": resp.timestamp,
                "error": resp.error,
            }
        except grpc.RpcError as e:
            return {"error": f"gRPC hatasi: {e.code()} - {e.details()}"}
        except Exception as e:
            return {"error": f"Baglanti hatasi: {e}"}

    def close(self):
        """Baglantiyi kapat."""
        if self._channel:
            self._channel.close()
            self._channel = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


if __name__ == "__main__":
    client = AnatoliaXGrpcClient()
    print("Sinyal THYAO:", client.get_signal("THYAO"))
    print("Risk kontrolu:", client.check_risk())
    client.close()
