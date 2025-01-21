import asyncio
from datetime import datetime

import cv2
import hashlib
import base64
from typing import Dict, Any

from app import logger
from app.config import Config
from app.logger import LoggerSingleton
from app.models.table_models import Camera
from app.services.module_service import ModuleManager

logger = LoggerSingleton.get_logger()
# Лимит на количество одновременных задач
semaphore = asyncio.Semaphore(20)

# Структуры для управления потоками камер и их кадрами
camera_tasks: Dict[int, asyncio.Task] = {}
camera_streams: Dict[int, Dict[str, Any]] = {}


def validate_camera_url(camera_url: str) -> Any:
    """Проверяет URL камеры и преобразует строку в число, если это возможно."""
    try:
        return int(camera_url)
    except ValueError:
        return camera_url


def hash_frame(frame_bytes: bytes) -> str:
    """Создаёт хэш для проверки изменений кадра."""
    return hashlib.md5(frame_bytes).hexdigest()


async def process_frame(camera_id: int, frame_bytes: bytes, camera_name: str):
    """Обрабатывает кадр, отправляя его в асинхронный модуль."""
    frame_base64 = base64.b64encode(frame_bytes).decode('utf-8')
    await ModuleManager.process_data({
        "frame_bytes": frame_base64,
        "camera_name": camera_name
    })


# async def video_capture(camera: Camera):
#     """Метод запускает захват кадров с камеры."""
#     logger.info(f"Запуск захвата камеры {camera.name}")
#     camera_url = validate_camera_url(camera.url)
#     cap = cv2.VideoCapture(camera_url)
#
#     if not cap.isOpened():
#         logger.warning(f"Не удалось открыть камеру {camera.name}: {camera_url}")
#         return
#
#     if camera.id not in camera_streams:
#         camera_streams[camera.id] = {"running": True, "frame": None}
#
#     previous_frame_hash = None
#
#     try:
#         while camera_streams[camera.id]["running"]:
#             ret, frame = cap.read()
#             if not ret:
#                 logger.error(f"Ошибка чтения кадра с камеры {camera.name}")
#                 break
#
#             try:
#                 frame = cv2.resize(frame, Config.settings().CAMERA_RESOLUTION)
#                 _, encoded_frame = cv2.imencode(
#                     '.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), Config.settings().JPEG_QUALITY]
#                 )
#                 frame_bytes = encoded_frame.tobytes()
#
#                 frame_hash = hash_frame(frame_bytes)
#                 if previous_frame_hash == frame_hash:
#                     await asyncio.sleep(0.001)
#                     continue
#
#                 previous_frame_hash = frame_hash
#                 camera_streams[camera.id]["frame"] = frame_bytes
#
#                 asyncio.create_task(process_frame(camera.id, frame_bytes, camera.name))
#             except Exception as e:
#                 logger.error(f"Ошибка обработки кадра: {e}")
#
#             await asyncio.sleep(0.001)
#
#     finally:
#         cap.release()
#         logger.info(f"Захват камеры {camera.name} завершён.")

async def video_capture(camera: Camera):
    """Метод запускает захват кадров с камеры."""
    logger.info(f"Запуск захвата камеры {camera.name}")
    camera_url = validate_camera_url(camera.url)
    cap = cv2.VideoCapture(camera_url)

    if not cap.isOpened():
        logger.warning(f"Не удалось открыть камеру {camera.name}: {camera_url}")
        return

    # Сохраняем сырые кадры вместо JPEG
    camera_streams[camera.id] = {
        "running": True,
        "frame": None,  # Здесь будет numpy array
        "processed_frame": None  # Для JPEG, если нужно
    }

    previous_frame_hash = None

    try:
        while camera_streams[camera.id]["running"]:
            ret, frame = cap.read()
            if not ret:
                logger.error(f"Ошибка чтения кадра с камеры {camera.name}")
                break

            try:
                # Наложение текста на кадр
                current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                text = f"{current_time} | Cam: {camera.name}"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 1.0
                thickness = 2
                text_color = (255, 255, 255)  # Белый цвет текста
                bg_color = (0, 0, 0)  # Чёрный фон
                margin = 10

                # Вычисляем размеры текста
                frame_height, frame_width, _ = frame.shape
                (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)

                # Позиция текста: правый нижний угол
                x = frame_width - text_width - margin
                y = frame_height - margin

                # Рисуем фон под текстом
                cv2.rectangle(
                    frame,
                    (x - 5, y - text_height - 5),  # Верхний левый угол фона
                    (x + text_width + 5, y + baseline + 5),  # Нижний правый угол фона
                    bg_color,
                    thickness=cv2.FILLED  # Заливка
                )

                # Накладываем текст
                cv2.putText(
                    frame,
                    text,
                    (x, y),
                    font,
                    font_scale,
                    text_color,
                    thickness,
                    cv2.LINE_AA
                )

                # Сохраняем сырой кадр для WebRTC
                resized_frame = cv2.resize(frame, Config.settings().CAMERA_RESOLUTION)
                camera_streams[camera.id]["frame"] = resized_frame

                # Отдельно готовим JPEG для модулей
                _, encoded_frame = cv2.imencode(
                    '.jpg', resized_frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), Config.settings().JPEG_QUALITY]
                )
                frame_bytes = encoded_frame.tobytes()

                # Проверка изменений кадра
                frame_hash = hash_frame(frame_bytes)
                if previous_frame_hash == frame_hash:
                    await asyncio.sleep(0.001)
                    continue

                previous_frame_hash = frame_hash
                camera_streams[camera.id]["processed_frame"] = frame_bytes

                # Отправляем в модули
                asyncio.create_task(process_frame(camera.id, frame_bytes, camera.name))

            except Exception as e:
                logger.error(f"Ошибка обработки кадра: {e}")

            await asyncio.sleep(0.001)

    finally:
        cap.release()
        logger.info(f"Захват камеры {camera.name} завершён.")
        # Очищаем данные
        if camera.id in camera_streams:
            del camera_streams[camera.id]


async def start_camera(camera: Camera):
    """Метод запускает захват камеры."""
    if camera.id in camera_tasks:
        logger.info(f"Камера {camera.name} уже запущена.")
        return

    camera_streams[camera.id] = {
        "url": camera.url,
        "frame": None,
        "running": camera.active
    }

    if camera.active:
        task = asyncio.create_task(video_capture(camera))
        camera_tasks[camera.id] = task
        logger.info(f"Камера {camera.name} запущена.")


async def stop_camera(camera: Camera):
    """Метод останавливает захват камеры."""
    if camera.id not in camera_tasks:
        logger.info(f"Камера {camera.name} не запущена.")
        return

    camera_streams[camera.id]["running"] = False
    await camera_tasks[camera.id]

    del camera_tasks[camera.id]
    del camera_streams[camera.id]
    logger.info(f"Камера {camera.name} остановлена.")
