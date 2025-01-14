# === app/controllers/video.py ===
import asyncio
import base64
from uuid import UUID

from fastapi import APIRouter
from fastapi import WebSocket, WebSocketDisconnect

from app.services.video_service import camera_streams

router = APIRouter()

@router.websocket("/ws/video/{camera_id}")
async def websocket_video_stream(websocket: WebSocket, camera_id: str):
    camera_id = UUID(camera_id)
    if camera_id not in camera_streams:
        print("Camera ID not found")
        await websocket.close(code=1003)
        return

    await websocket.accept()
    try:
        while True:
            if camera_id in camera_streams:
                frame = camera_streams[camera_id].get("frame")
                if frame is not None:
                    encoded_frame = base64.b64encode(frame).decode("utf-8")
                    await websocket.send_text(encoded_frame)
            await asyncio.sleep(0.001)
    except WebSocketDisconnect:

        print(f"Клиент отключился от камеры {camera_id}")
