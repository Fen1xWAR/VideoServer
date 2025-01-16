import asyncio
import aiohttp
import cv2
import hashlib
from typing import Dict, Any
from app.config import Config
from app.db_models import Camera

semaphore = asyncio.Semaphore(20)  # Ограничение на количество запросов

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# Пример структуры для управления потоками камер
camera_tasks: Dict[int, asyncio.Task] = {}
camera_streams: Dict[int, Dict[str, Any]] = {}


async def video_capture(camera: Camera):
    """ Метод запускает захват кадров с камеры """
    print(f"Запуск захвата камеры {camera.name}")
    if isinstance(camera.url, str):
        try:
            camera_url = int(camera.url)
        except ValueError:
            pass

    cap = cv2.VideoCapture(camera_url)
    if not cap.isOpened():
        print(f"Не удалось открыть камеру {camera.name}: {camera_url}")
        return

    previous_frame_hash = None

    while camera_streams[camera.id]["running"]:
        ret, frame = cap.read()
        if not ret:
            print(f"Ошибка чтения кадра с камеры {camera.name}")
            break

        frame = cv2.resize(frame, Config.settings().CAMERA_RESOLUTION)
        _, encoded_frame = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), Config.settings().JPEG_QUALITY])
        frame_bytes = encoded_frame.tobytes()

        frame_hash = hash_frame(frame_bytes)
        if previous_frame_hash == frame_hash:
            await asyncio.sleep(0.001)
            continue

        previous_frame_hash = frame_hash

        if Config.settings().FACE_RECOGNITION and detect_face(frame):
            frame_bytes = await send_frame(frame_bytes)

        camera_streams[camera.id]["frame"] = frame_bytes
        await asyncio.sleep(0.001)

    cap.release()
    print(f"Захват камеры {camera.name} завершён.")


async def start_camera(camera: Camera):
    """ Метод запускает захват камеры"""
    if camera.id in camera_tasks:
        print(f"Камера {camera.name} уже запущена.")
        return
    if camera.active:

        camera_streams[camera.id] = {"url": camera.url, "frame": None, "running": True}
    else:
        camera_streams[camera.id] = {"url": camera.url, "frame": None, "running": False}
    # camera_streams[camera.id] = {"running": True, "frame": None}
    task = asyncio.create_task(video_capture(camera))
    camera_tasks[camera.id] = task


async def stop_camera(camera: Camera):
    """ Метод останавливает захват камеры"""
    if camera.id not in camera_tasks:
        print(f"Камера {camera.name} не запущена.")
        return

    camera_streams[camera.id]["running"] = False
    await camera_tasks[camera.id]
    del camera_tasks[camera.id]
    del camera_streams[camera.id]
    print(f"Камера {camera.name} остановлена.")


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
            try:

                async with session.post('http://127.0.0.1:1111/validate', data=frame_bytes,
                                        headers=headers) as response:
                    if response.status == 200:
                        return await response.read()  # Получаем обработанное изображение
                    else:
                        print(f"Ошибка при отправке кадра: {response.status}")
                        return frame_bytes  # Возвращаем оригинальный кадр в случае ошибки
            except Exception as e:
                print(e)
                return frame_bytes

# async def video_capture(camera_id: int, camera_url: str):
#     print('capture')
#     if isinstance(camera_url, str):
#         camera_url = int(camera_url)
#     cap = cv2.VideoCapture(camera_url)
#     if not cap.isOpened():
#         print(f"Не удалось открыть камеру {camera_id}: {camera_url}")
#         return
#
#     previous_frame_hash = None
#
#     while camera_streams[str(camera_id)]["running"]:  # Проверяем флаг running
#         ret, frame = cap.read()
#         if not ret:
#             print(f"Ошибка чтения кадра с камеры {camera_id}")
#             break
#
#         # Изменение размера кадра и сжатие
#         frame = cv2.resize(frame, Config.settings().CAMERA_RESOLUTION)
#         _, encoded_frame = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), Config.settings().JPEG_QUALITY])
#         frame_bytes = encoded_frame.tobytes()
#
#         # Проверка на изменения кадра
#         frame_hash = hash_frame(frame_bytes)
#         if previous_frame_hash == frame_hash:
#             await asyncio.sleep(0.001)  # Если кадр не изменился, пропускаем обработку
#             continue
#
#         previous_frame_hash = frame_hash
#
#         # Локальная проверка на наличие лица (если включено)
#         if Config.settings().FACE_RECOGNITION and detect_face(frame):
#             frame_bytes = await send_frame(frame_bytes)  # Отправляем кадр на сервер
#
#         camera_streams[str(camera_id)]["frame"] = frame_bytes  # Обновляем camera_streams
#
#         await asyncio.sleep(0.001)  # Исключаем 100% загрузку процессора
#
#     cap.release()
#     print('capture over')
