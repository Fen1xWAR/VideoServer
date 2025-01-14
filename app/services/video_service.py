import asyncio
import aiohttp
import cv2
import hashlib
from typing import Dict
from app.config import Config

camera_streams: Dict[int, Dict[str, bytes]] = {}
semaphore = asyncio.Semaphore(20)  # Ограничение на количество запросов

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

def detect_face(frame) -> bool:
    """Локальная проверка на наличие лица."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    return len(faces) > 0

def hash_frame(frame_bytes: bytes) -> str:
    """Создание хэша для проверки изменений кадра."""
    return hashlib.md5(frame_bytes).hexdigest()

async def send_frame(frame_bytes: bytes) -> bytes:
    """Отправляет кадр на эндпоинт validate и возвращает полученное изображение."""
    headers = {'Content-Type': 'application/octet-stream'}
    async with semaphore:  # Контроль числа одновременных запросов
        async with aiohttp.ClientSession() as session:
            async with session.post('http://127.0.0.1:1111/validate', data=frame_bytes, headers=headers) as response:
                if response.status == 200:
                    return await response.read()  # Получаем обработанное изображение
                else:
                    print(f"Ошибка при отправке кадра: {response.status}")
                    return frame_bytes  # Возвращаем оригинальный кадр в случае ошибки

async def video_capture(camera_id: int, camera_url: str):
    if isinstance(camera_url, str):
        camera_url = int(camera_url)
    cap = cv2.VideoCapture(camera_url)
    if not cap.isOpened():
        print(f"Не удалось открыть камеру {camera_id}: {camera_url}")
        return

    previous_frame_hash = None

    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"Ошибка чтения кадра с камеры {camera_id}")
            break

        # Изменение размера кадра и сжатие
        frame = cv2.resize(frame, Config.settings().CAMERA_RESOLUTION)
        _, encoded_frame = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), Config.settings().JPEG_QUALITY])
        frame_bytes = encoded_frame.tobytes()

        # Проверка на изменения кадра
        frame_hash = hash_frame(frame_bytes)
        if previous_frame_hash == frame_hash:
            await asyncio.sleep(0.001)  # Если кадр не изменился, пропускаем обработку
            continue

        previous_frame_hash = frame_hash

        # Локальная проверка на наличие лица (если включено)
        if Config.settings().FACE_RECOGNITION and detect_face(frame):
            frame_bytes = await send_frame(frame_bytes)  # Отправляем кадр на сервер

        camera_streams[camera_id] = {"frame": frame_bytes}  # Обновляем camera_streams

        await asyncio.sleep(0.001)  # Исключаем 100% загрузку процессора

    cap.release()
