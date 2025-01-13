import asyncio
import aiohttp
import cv2
from typing import Dict

from app.config import Config

camera_streams: Dict[int, Dict[str, bytes]] = {}


async def send_frame(frame_bytes: bytes) -> bytes:
    """Отправляет кадр на эндпоинт validate и возвращает полученное изображение."""
    headers = {'Content-Type': 'application/octet-stream'}
    async with aiohttp.ClientSession() as session:
        async with session.post('http://127.0.0.1:1111/validate', data=frame_bytes, headers=headers) as response:
            if response.status == 200:
                return await response.read()  # Получаем изображение из ответа
            else:
                print(f"Ошибка при отправке кадра: {response.status}")
                return frame_bytes  # Возвращаем оригинальный кадр в случае ошибки

async def video_capture(camera_id: int, camera_url: str, face_recognition: bool = True):
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

        if face_recognition:
            frame_bytes = await send_frame(frame_bytes)  # Отправляем кадр и получаем ответ

        camera_streams[camera_id] = {"frame": frame_bytes}  # Обновляем camera_streams

        await asyncio.sleep(0.001)

    cap.release()