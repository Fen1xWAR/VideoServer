# === app/routers/video.py ===
import asyncio
import base64

from fastapi import APIRouter
from fastapi import WebSocket, WebSocketDisconnect

from app.services.video_service import camera_streams, clients

router = APIRouter()

@router.websocket("/ws/video/{camera_id}")
async def websocket_video_stream(websocket: WebSocket, camera_id: int):
    print(camera_id)
    print(camera_streams)
    if camera_id not in camera_streams:
        print(camera_streams)
        await websocket.close(code=1003)
        return

    await websocket.accept()
    if camera_id not in clients:
        clients[camera_id] = []
    clients[camera_id].append(websocket)

    try:
        while True:
            if camera_id in camera_streams:
                frame = camera_streams[camera_id].get("frame")
                if frame is not None:
                    encoded_frame = base64.b64encode(frame).decode("utf-8")
                    await websocket.send_text(encoded_frame)
            await asyncio.sleep(0.001)
    except WebSocketDisconnect:
        clients[camera_id].remove(websocket)
        if not clients[camera_id]:
            del clients[camera_id]
        print(f"Клиент отключился от камеры {camera_id}")
