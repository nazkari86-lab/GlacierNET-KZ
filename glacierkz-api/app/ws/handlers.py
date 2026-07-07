"""WebSocket route handlers — connection lifecycle, room management."""

from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws.manager import get_ws_manager

ws_router = APIRouter(tags=["websocket"])


@ws_router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    manager = get_ws_manager()
    user_id = websocket.query_params.get("user_id")
    await manager.connect(websocket, client_id, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
                continue

            msg_type = message.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "timestamp": message.get("timestamp")})

            elif msg_type == "join_room":
                room = message.get("room", "")
                if room:
                    await manager.join_room(client_id, room)

            elif msg_type == "leave_room":
                room = message.get("room", "")
                if room:
                    await manager.leave_room(client_id, room)

            elif msg_type == "broadcast":
                await manager.broadcast(message.get("payload", {}), room=message.get("room"))

            elif msg_type == "stats":
                stats = manager.get_stats()
                await websocket.send_json({"type": "stats", "data": stats})

            else:
                await websocket.send_json({"type": "error", "detail": f"Unknown type: {msg_type}"})

    except WebSocketDisconnect:
        await manager.disconnect(client_id)
