from collections import defaultdict

from fastapi import WebSocket


class KitchenConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[int, list[WebSocket]] = defaultdict(list)

    async def connect(self, restaurant_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[restaurant_id].append(websocket)

    def disconnect(self, restaurant_id: int, websocket: WebSocket) -> None:
        if websocket in self.active_connections.get(restaurant_id, []):
            self.active_connections[restaurant_id].remove(websocket)

    async def broadcast(self, restaurant_id: int, message: dict) -> None:
        stale_connections = []
        for connection in self.active_connections.get(restaurant_id, []):
            try:
                await connection.send_json(message)
            except RuntimeError:
                stale_connections.append(connection)

        for connection in stale_connections:
            self.disconnect(restaurant_id, connection)


kitchen_ws_manager = KitchenConnectionManager()
