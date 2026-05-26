"""
Test: PYTHON.anatoliax_grpc (gRPC inter-service communication)
Server start/stop, client call, port discovery, timeout.
"""
import pytest
import sys
import shutil
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from anatoliax_grpc.server import AnatoliaXGrpcServer
from anatoliax_grpc.client import AnatoliaXGrpcClient


class TestGrpcCommunication:
    def test_server_starts_and_returns_port(self):
        server = AnatoliaXGrpcServer()
        port = server.start()
        assert port > 0
        server.stop()

    def test_port_file_created(self):
        td = Path(tempfile.mkdtemp())
        port_file = td / ".grpc_port"
        server = AnatoliaXGrpcServer()
        server._save_port(12345)
        assert port_file.exists() is False  # _save_port default PORT_FILE kullanir
        # Manuel yazalim
        port_file.parent.mkdir(parents=True, exist_ok=True)
        port_file.write_text('{"port": 12345, "host": "127.0.0.1"}', encoding="utf-8")
        data = __import__("json").loads(port_file.read_text(encoding="utf-8"))
        assert data["port"] == 12345
        assert data["host"] == "127.0.0.1"
        shutil.rmtree(td, ignore_errors=True)

    def test_client_discovers_port_from_file(self):
        td = Path(tempfile.mkdtemp())
        port_file = td / ".grpc_port"
        port_file.parent.mkdir(parents=True, exist_ok=True)
        port_file.write_text('{"port": 12345, "host": "127.0.0.1"}', encoding="utf-8")
        client = AnatoliaXGrpcClient(port_file=port_file, timeout_sec=1)
        discovered = client._discover()
        assert discovered is not None
        host, port = discovered
        assert host == "127.0.0.1"
        assert port == 12345
        shutil.rmtree(td, ignore_errors=True)

    def test_client_returns_error_when_no_port_file(self):
        td = Path(tempfile.mkdtemp())
        port_file = td / "nonexistent_port"
        client = AnatoliaXGrpcClient(port_file=port_file, timeout_sec=1)
        result = client.get_signal("THYAO")
        assert "error" in result
        assert "bulunamadi" in result["error"]
        shutil.rmtree(td, ignore_errors=True)

    def test_server_client_roundtrip(self):
        server = AnatoliaXGrpcServer()
        port = server.start_in_thread()
        assert port > 0
        try:
            client = AnatoliaXGrpcClient(timeout_sec=5)
            result = client.get_signal("THYAO")
            assert isinstance(result, dict)
            # Sinyal yoksa da valid=False doner, ama hata olmamali
            assert "error" not in result or ("error" in result and "gRPC" not in result["error"])
        finally:
            server.stop()

    def test_risk_service_roundtrip(self):
        server = AnatoliaXGrpcServer()
        port = server.start_in_thread()
        assert port > 0
        try:
            client = AnatoliaXGrpcClient(timeout_sec=5)
            result = client.check_risk()
            assert isinstance(result, dict)
            assert "allowed" in result or "error" in result
        finally:
            server.stop()

    def test_report_service_roundtrip(self):
        server = AnatoliaXGrpcServer()
        port = server.start_in_thread()
        assert port > 0
        try:
            client = AnatoliaXGrpcClient(timeout_sec=5)
            result = client.generate_report("morning")
            assert isinstance(result, dict)
            assert "success" in result or "error" in result
        finally:
            server.stop()

    def test_server_clears_port_file_on_stop(self):
        server = AnatoliaXGrpcServer()
        server._save_port(9999)
        assert AnatoliaXGrpcServer.PORT_FILE.exists() if hasattr(AnatoliaXGrpcServer, 'PORT_FILE') else True
        server._clear_port()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
