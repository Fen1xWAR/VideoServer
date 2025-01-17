import asyncio
import base64
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect, HTTPException, APIRouter
import json
import jwt

from app.db_models import get_db, Camera
from app.services.security import Config
from app.services.video_service import camera_streams

router = APIRouter()


@router.websocket("/ws/video/{camera_id}")
async def websocket_video_stream(websocket: WebSocket, camera_id: str):
    await websocket.accept()

    try:
        # Ожидаем первое сообщение с токеном
        data = await websocket.receive_text()
        message = json.loads(data)
        token = message.get("token")

        if not token:
            print("JWT токен отсутствует в сообщении")
            await websocket.close(code=1008)
            return

        # Проверяем токен
        try:
            payload = jwt.decode(
                token, Config.settings().SECRET_KEY, algorithms=[Config.settings().ALGORITHM]
            )
            user = {"username": payload.get("sub"), "role": payload.get("role")}
            if user["username"] is None or user["role"] is None:
                raise HTTPException(status_code=401, detail="Invalid token")
        except jwt.PyJWTError:
            print("Invalid JWT token")
            await websocket.close(code=1008)
            return

        db = get_db()
        camera_id = UUID(camera_id)
        camera_obj = db.get(Camera, camera_id)
        print(f"Пользователь {user['username']} подключился к камере {camera_obj.name}")

        # Обрабатываем поток данных
        while True:
            frame = camera_streams.get(camera_id, {}).get("frame")

            if frame is not None:
                encoded_frame = base64.b64encode(frame).decode("utf-8")
                await websocket.send_text(encoded_frame)
            await asyncio.sleep(0.01)

    except WebSocketDisconnect:
        print(f"Клиент отключился от камеры {camera_obj.name}")
    except json.JSONDecodeError:
        print("Невалидный формат сообщения от клиента")
        await websocket.close(code=1003)
    finally:
        print(f"WebSocket для камеры {camera_obj.name} закрыт")
