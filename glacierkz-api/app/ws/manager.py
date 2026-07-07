"""WebSocket connection manager — pub/sub, rooms, broadcasts."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from fastapi import WebSocket

logger = logging.getLogger("glacierkz.ws")


@dataclass
class WSClient:
    ws: WebSocket
    client_id: str
    user_id: Optional[str] = None
    rooms: set[str] = field(default_factory=set)
    connected_at: float = field(default_factory=time.time)
    last_ping: float = field(default_factory=time.time)


class ConnectionManager:
    """Manages WebSocket connections with rooms, pub/sub, and heartbeat."""

    def __init__(self):
        self._clients: dict[str, WSClient] = {}
        self._rooms: dict[str, set[str]] = defaultdict(set)
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._broadcast_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info("WebSocket manager started")

    async def stop(self) -> None:
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._broadcast_task:
            self._broadcast_task.cancel()
        for client in list(self._clients.values()):
            await client.ws.close()
        self._clients.clear()
        self._rooms.clear()
        logger.info("WebSocket manager stopped")

    async def connect(self, ws: WebSocket, client_id: str, user_id: str | None = None) -> WSClient:
        await ws.accept()
        client = WSClient(ws=ws, client_id=client_id, user_id=user_id)
        self._clients[client_id] = client
        await ws.send_json({"type": "connected", "client_id": client_id})
        logger.info(f"WS connected: {client_id}")
        return client

    async def disconnect(self, client_id: str) -> None:
        client = self._clients.pop(client_id, None)
        if client:
            for room in client.rooms:
                self._rooms[room].discard(client_id)
                if not self._rooms[room]:
                    del self._rooms[room]
            logger.info(f"WS disconnected: {client_id}")

    async def join_room(self, client_id: str, room: str) -> None:
        client = self._clients.get(client_id)
        if client:
            client.rooms.add(room)
            self._rooms[room].add(client_id)
            await self._send_to_client(client, {"type": "room_joined", "room": room})

    async def leave_room(self, client_id: str, room: str) -> None:
        client = self._clients.get(client_id)
        if client:
            client.rooms.discard(room)
            self._rooms[room].discard(client_id)
            if not self._rooms[room]:
                del self._rooms[room]

    async def send_to_client(self, client_id: str, message: dict) -> None:
        client = self._clients.get(client_id)
        if client:
            await self._send_to_client(client, message)

    async def broadcast(self, message: dict, room: str | None = None) -> None:
        if room:
            client_ids = self._rooms.get(room, set())
            targets = [self._clients[cid] for cid in client_ids if cid in self._clients]
        else:
            targets = list(self._clients.values())
        for client in targets:
            await self._send_to_client(client, message)

    async def send_progress(
        self,
        client_id: str,
        task_id: str,
        progress: float,
        message: str = "",
        stage: str = "",
    ) -> None:
        await self.send_to_client(
            client_id,
            {
                "type": "progress",
                "task_id": task_id,
                "progress": min(100.0, max(0.0, progress)),
                "message": message,
                "stage": stage,
                "timestamp": time.time(),
            },
        )

    async def send_result(self, client_id: str, task_id: str, result: dict) -> None:
        await self.send_to_client(
            client_id,
            {
                "type": "result",
                "task_id": task_id,
                "result": result,
                "timestamp": time.time(),
            },
        )

    async def send_error(self, client_id: str, task_id: str, error: str) -> None:
        await self.send_to_client(
            client_id,
            {
                "type": "error",
                "task_id": task_id,
                "error": error,
                "timestamp": time.time(),
            },
        )

    async def send_notification(self, client_id: str, title: str, body: str, level: str = "info") -> None:
        await self.send_to_client(
            client_id,
            {
                "type": "notification",
                "title": title,
                "body": body,
                "level": level,
                "timestamp": time.time(),
            },
        )

    async def _send_to_client(self, client: WSClient, message: dict) -> None:
        try:
            await client.ws.send_json(message)
            client.last_ping = time.time()
        except Exception:
            await self.disconnect(client.client_id)

    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(30)
            now = time.time()
            stale = [cid for cid, c in self._clients.items() if now - c.last_ping > 60]
            for cid in stale:
                await self.disconnect(cid)
                logger.info(f"Heartbeat timeout: {cid}")

    async def _broadcast_loop(self) -> None:
        while True:
            message = await self._message_queue.get()
            await self.broadcast(message)

    @property
    def active_connections(self) -> int:
        return len(self._clients)

    @property
    def active_rooms(self) -> list[str]:
        return list(self._rooms.keys())

    def get_client_info(self, client_id: str) -> dict | None:
        client = self._clients.get(client_id)
        if not client:
            return None
        return {
            "client_id": client.client_id,
            "user_id": client.user_id,
            "rooms": list(client.rooms),
            "connected_at": client.connected_at,
        }

    def get_stats(self) -> dict:
        return {
            "connections": self.active_connections,
            "rooms": len(self._rooms),
            "clients": [self.get_client_info(cid) for cid in list(self._clients.keys())[:10]],
        }


_manager: Optional[ConnectionManager] = None


def get_ws_manager() -> ConnectionManager:
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager
