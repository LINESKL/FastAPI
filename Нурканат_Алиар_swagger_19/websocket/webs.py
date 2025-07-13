from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from typing import List
from datetime import datetime
import json
from jose import JWTError, jwt
from metadata import SECRET_KEY, ALGORITHM
import urllib.parse
import logging

router = APIRouter(
    prefix="/ws",
    tags=["websocket"]
)

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

async def get_websocket_token(websocket: WebSocket):
    query_string = websocket.scope.get("query_string", b"").decode()
    query_params = urllib.parse.parse_qs(query_string)
    return query_params.get("token", [None])[0]

@router.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    token = await get_websocket_token(websocket)
    
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise JWTError("Invalid token: no username")
            
        await manager.connect(websocket)
        await manager.send_personal_message({
            "type": "system",
            "message": f"Welcome, {username}!"
        }, websocket)
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await manager.broadcast({
                "type": "message",
                "username": username,
                "message": message.get("content"),
                "timestamp": datetime.now().isoformat()
            })
            
    except JWTError as e:
        logger.error(f"JWT error: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"User {username} disconnected")
    except json.JSONDecodeError:
        await websocket.send_json({
            "type": "error",
            "message": "Invalid JSON format"
        })
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await websocket.close()