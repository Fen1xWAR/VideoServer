import cv2
import base64
import psutil
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

camera_streams: Dict[int, Dict[str, bytes]] = {}
clients: Dict[int, List[WebSocket]] = {}

async def video_capture(camera_id: int, camera_url: str):
    cap = cv2.VideoCapture(camera_url)
    if not cap.isOpened():
        print(f"Не удалось открыть камеру {camera_id}: {camera_url}")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"Ошибка чтения кадра с камеры {camera_id}")
            break

        frame = cv2.resize(frame, (1920, 1080))

        _, encoded_frame = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        frame_bytes = encoded_frame.tobytes()

        camera_streams[camera_id] = {"frame": frame_bytes}

        await asyncio.sleep(0.001)

    cap.release()

@app.websocket("/ws/video/{camera_id}")
async def websocket_video_stream(websocket: WebSocket, camera_id: int):
    if camera_id not in camera_streams:
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
        clients[camera_id ].remove(websocket)
        if not clients[camera_id]:
            del clients[camera_id]
        print(f"Клиент отключился от камеры {camera_id}")

@app.get("/metrics")
def get_metrics():
    process = psutil.Process()
    memory_info = process.memory_info()
    return {
        "memory_usage_mb": memory_info.rss / 1024 / 1024,
        "num_clients": sum(len(client_list) for client_list in clients.values()),
        "num_cameras": len(camera_streams),
    }

camera_config = [
    0, # Локальная USB-камера
    1, # Локальные камера 2
]

# Запуск инициализации камер
for camera_id, camera_url in enumerate(camera_config):
    camera_streams[camera_id] = {"url": camera_url, "frame": None}
    asyncio.create_task(video_capture(camera_id, camera_url))