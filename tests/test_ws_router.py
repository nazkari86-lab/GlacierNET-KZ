"""Tests for WebSocket ConnectionManager (app.ws.manager)."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "glacierkz-api"))

from app.ws.manager import ConnectionManager


@pytest.fixture
def manager():
    return ConnectionManager()


@pytest.fixture
def mock_ws():
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    ws.accept = AsyncMock()
    return ws


class TestConnectionManagerInit:
    def test_starts_empty(self, manager):
        assert manager.active_connections == 0


class TestConnectionManagerConnect:
    @pytest.mark.asyncio
    async def test_connect_increases_count(self, manager, mock_ws):
        await manager.connect(mock_ws, "client-1")
        assert manager.active_connections == 1

    @pytest.mark.asyncio
    async def test_connect_stores_client(self, manager, mock_ws):
        await manager.connect(mock_ws, "client-1")
        assert "client-1" in manager._clients

    @pytest.mark.asyncio
    async def test_multiple_connections(self, manager):
        for i in range(5):
            ws = AsyncMock()
            ws.send_json = AsyncMock()
            ws.accept = AsyncMock()
            await manager.connect(ws, f"client-{i}")
        assert manager.active_connections == 5


class TestConnectionManagerDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, manager, mock_ws):
        await manager.connect(mock_ws, "client-1")
        await manager.disconnect("client-1")
        assert manager.active_connections == 0

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent(self, manager):
        await manager.disconnect("missing-client")


class TestConnectionManagerRooms:
    @pytest.mark.asyncio
    async def test_join_room(self, manager, mock_ws):
        await manager.connect(mock_ws, "client-1")
        await manager.join_room("client-1", "updates")
        assert "updates" in manager._rooms
        assert "client-1" in manager._rooms["updates"]

    @pytest.mark.asyncio
    async def test_leave_room(self, manager, mock_ws):
        await manager.connect(mock_ws, "client-1")
        await manager.join_room("client-1", "updates")
        await manager.leave_room("client-1", "updates")
        assert "client-1" not in manager._rooms.get("updates", set())


class TestConnectionManagerBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_to_room(self, manager):
        ws1 = AsyncMock()
        ws1.send_json = AsyncMock()
        ws1.accept = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_json = AsyncMock()
        ws2.accept = AsyncMock()
        await manager.connect(ws1, "client-1")
        await manager.connect(ws2, "client-2")
        await manager.join_room("client-1", "updates")
        await manager.join_room("client-2", "updates")
        await manager.broadcast({"type": "test", "data": "hello"}, room="updates")
        assert ws1.send_json.call_count >= 2
        assert ws2.send_json.call_count >= 2

    @pytest.mark.asyncio
    async def test_broadcast_filters_by_room(self, manager):
        ws1 = AsyncMock()
        ws1.send_json = AsyncMock()
        ws1.accept = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_json = AsyncMock()
        ws2.accept = AsyncMock()
        await manager.connect(ws1, "client-1")
        await manager.connect(ws2, "client-2")
        await manager.join_room("client-1", "task-1")
        await manager.join_room("client-2", "task-2")
        ws1.send_json.reset_mock()
        ws2.send_json.reset_mock()
        await manager.broadcast({"type": "update"}, room="task-1")
        ws1.send_json.assert_called()
        ws2.send_json.assert_not_called()


class TestConnectionManagerSendToClient:
    @pytest.mark.asyncio
    async def test_send_to_client(self, manager, mock_ws):
        await manager.connect(mock_ws, "client-1")
        mock_ws.send_json.reset_mock()
        await manager.send_to_client("client-1", {"type": "ping"})
        mock_ws.send_json.assert_called_once_with({"type": "ping"})


class TestConnectionManagerStats:
    @pytest.mark.asyncio
    async def test_active_connections_reflects_disconnects(self, manager):
        ws1 = AsyncMock()
        ws1.send_json = AsyncMock()
        ws1.accept = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_json = AsyncMock()
        ws2.accept = AsyncMock()
        await manager.connect(ws1, "client-1")
        await manager.connect(ws2, "client-2")
        assert manager.active_connections == 2
        await manager.disconnect("client-1")
        assert manager.active_connections == 1
