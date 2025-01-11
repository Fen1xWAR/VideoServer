import asyncio
from typing import Dict

import cv2

from app.config import Config

camera_streams: Dict[int, Dict[str, bytes]] = {}

async def video_capture(camera_id: int, camera_url: str):
    if isinstance(camera_url, str):
        camera_url = int(camera_url)
    cap = cv2.VideoCapture(camera_url)
    if not cap.isOpened():
        print(f"Не удалось открыть камеру {camera_id}: {camera_url}")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"Ошибка чтения кадра с камеры {camera_id}")
            break

        frame = cv2.resize(frame, Config.settings().CAMERA_RESOLUTION)
        _, encoded_frame = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), Config.settings().JPEG_QUALITY])
        frame_bytes = encoded_frame.tobytes()

        camera_streams[camera_id] = {"frame": frame_bytes}

        await asyncio.sleep(0.001)

    cap.release()