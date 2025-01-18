import asyncio
import base64
import json
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect, HTTPException, APIRouter
import jwt

from app.services.database_service import get_db, Camera
from app.services.security import Config
from app.services.video_service import camera_streams

router = APIRouter()


@router.websocket("/ws/video/{camera_id}")
async def websocket_video_stream(websocket: WebSocket, camera_id: str):
    """WebSocket для передачи видеопотока с камеры"""
    await websocket.accept()

    try:
        # Ожидание получения первого сообщения с токеном
        data = await websocket.receive_text()
        message = json.loads(data)
        token = message.get("token")

        if not token:
            print("JWT токен отсутствует в сообщении")
            await websocket.close(code=1008)
            return

        # Проверка JWT токена
        try:
            payload = jwt.decode(
                token, Config.settings().SECRET_KEY, algorithms=[Config.settings().ALGORITHM]
            )
            user = {"username": payload.get("sub"), "role": payload.get("role")}
            if not user["username"] or not user["role"]:
                raise HTTPException(status_code=401, detail="Invalid token")
        except jwt.PyJWTError:
            print("Invalid JWT token")
            await websocket.close(code=1008)
            return

        # Получаем информацию о камере из базы данных
        db = get_db()
        camera_id = UUID(camera_id)
        camera_obj = db.get(Camera, camera_id)
        print(f"Пользователь {user['username']} подключился к камере {camera_obj.name}")

        # Обработка видеопотока
        while True:
            frame = camera_streams.get(camera_id, {}).get("frame")

            if frame:
                # Кодируем видеокадр в base64 для передачи через WebSocket
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
