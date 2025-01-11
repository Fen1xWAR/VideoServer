# === app/services/video_service.py ===
import asyncio
from typing import Dict, List

import cv2
from fastapi import WebSocket

from app.config import Config

camera_streams: Dict[int, Dict[str, bytes]] = {}
clients: Dict[int, List[WebSocket]] = {}

async def video_capture(camera_id: int, camera_url: str):
    print(camera_streams)
    cap = cv2.VideoCapture(camera_url)
    if not cap.isOpened():
        print(f"Не удалось открыть камеру {camera_id}: {camera_url}")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"Ошибка чтения кадра с камеры {camera_id}")
            break

        frame = cv2.resize(frame, Config.CAMERA_RESOLUTION)
        _, encoded_frame = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), Config.JPEG_QUALITY])
        frame_bytes = encoded_frame.tobytes()

        camera_streams[camera_id] = {"frame": frame_bytes}

        await asyncio.sleep(0.001)

    cap.release()