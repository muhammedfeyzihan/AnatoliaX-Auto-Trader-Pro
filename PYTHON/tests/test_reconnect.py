"""
Test: PYTHON.execution.reconnect
WebSocketReconnectHandler + FailoverManager.
"""
import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from execution.reconnect import WebSocketReconnectHandler, FailoverManager


class TestWebSocketReconnectHandler:
    def test_init(self):
        handler = WebSocketReconnectHandler(
            connect_fn=AsyncMock(),
            on_message=lambda msg: None,
        )
        assert handler.is_connected() is False
        assert handler._reconnect_attempts == 0

    def test_get_endpoint_single(self):
        handler = WebSocketReconnectHandler(
            connect_fn=AsyncMock(),
            on_message=lambda msg: None,
            endpoints=["ws://a"],
        )
        assert handler._get_endpoint() == "ws://a"

    def test_get_endpoint_rotation(self):
        handler = WebSocketReconnectHandler(
            connect_fn=AsyncMock(),
            on_message=lambda msg: None,
            endpoints=["ws://a", "ws://b"],
        )
        assert handler._get_endpoint() == "ws://a"
        assert handler._get_endpoint() == "ws://b"
        assert handler._get_endpoint() == "ws://a"

    def test_get_endpoint_empty(self):
        handler = WebSocketReconnectHandler(
            connect_fn=AsyncMock(),
            on_message=lambda msg: None,
        )
        assert handler._get_endpoint() == ""

    @pytest.mark.asyncio
    async def test_backoff_reconnect(self):
        handler = WebSocketReconnectHandler(
            connect_fn=AsyncMock(),
            on_message=lambda msg: None,
            max_reconnect_delay=5.0,
        )
        assert handler._reconnect_attempts == 0
        await handler._backoff_reconnect()
        assert handler._reconnect_attempts == 1

    @pytest.mark.asyncio
    async def test_send_not_connected(self):
        handler = WebSocketReconnectHandler(
            connect_fn=AsyncMock(),
            on_message=lambda msg: None,
        )
        # Bagli degilse hata vermemeli
        await handler.send({"test": 1})


class TestFailoverManager:
    @pytest.mark.asyncio
    async def test_execute_primary_success(self):
        primary = AsyncMock(return_value={"status": "ok"})
        fm = FailoverManager(adapters={"matriks": primary}, primary="matriks")
        result = await fm.execute({"cmd": "test"})
        assert result["status"] == "ok"
        primary.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_failover(self):
        primary = AsyncMock(side_effect=Exception("fail"))
        backup = AsyncMock(return_value={"status": "backup"})
        fm = FailoverManager(adapters={"matriks": primary, "ideal": backup}, primary="matriks")
        result = await fm.execute({"cmd": "test"})
        assert result["status"] == "backup"

    @pytest.mark.asyncio
    async def test_execute_all_fail(self):
        a = AsyncMock(side_effect=Exception("fail"))
        b = AsyncMock(side_effect=Exception("fail"))
        fm = FailoverManager(adapters={"a": a, "b": b}, primary="a")
        with pytest.raises(RuntimeError):
            await fm.execute({"cmd": "test"})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
