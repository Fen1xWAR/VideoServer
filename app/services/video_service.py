import asyncio
import cv2
import hashlib
from typing import Dict, Any

from app.services.module.ModuleService import ModuleManager
from app.services.config import Config
from app.services.database_service import Camera

# Лимит на количество одновременных задач
semaphore = asyncio.Semaphore(20)

# Загружаем каскад для детекции лиц
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# Структуры для управления потоками камер и их кадрами
camera_tasks: Dict[int, asyncio.Task] = {}
camera_streams: Dict[int, Dict[str, Any]] = {}

# Функция для захвата видео с камеры
import base64


async def video_capture(camera: Camera):
    """Метод запускает захват кадров с камеры"""
    print(f"Запуск захвата камеры {camera.name}")

    # Проверка URL камеры
    try:
        camera_url = int(camera.url)  # Преобразуем строку в число, если это возможно
    except ValueError:
        camera_url = camera.url  # Если строка не является числом, используем её как есть

    # Открываем видеопоток с камеры
    cap = cv2.VideoCapture(camera_url)
    if not cap.isOpened():
        print(f"Не удалось открыть камеру {camera.name}: {camera_url}")
        return

    previous_frame_hash = None
    frame_counter = 0  # Счётчик кадров

    try:
        while camera_streams[camera.id]["running"]:
            ret, frame = cap.read()  # Чтение кадра
            if not ret:
                print(f"Ошибка чтения кадра с камеры {camera.name}")
                break

            # Изменение разрешения кадра
            frame = cv2.resize(frame, Config.settings().CAMERA_RESOLUTION)
            _, encoded_frame = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), Config.settings().JPEG_QUALITY])
            frame_bytes = encoded_frame.tobytes()

            # Хэшируем кадр для проверки изменений
            frame_hash = hashlib.sha256(frame_bytes).hexdigest()
            if previous_frame_hash == frame_hash:
                await asyncio.sleep(0.001)  # Если кадр не изменился, пропускаем обработку
                continue

            previous_frame_hash = frame_hash

            frame_counter += 1  # Увеличиваем счётчик кадров
            camera_streams[camera.id]["frame"] = frame_bytes  # Сохраняем текущий кадр

            # Отправляем кадр в обработку каждые 10 кадров (или по какой-то другой логике)
            # if frame_counter % 10 == 0:
            frame_base64 = base64.b64encode(frame_bytes).decode('utf-8')

                # Создаем задачу для асинхронной обработки
            asyncio.create_task(ModuleManager.process_data({
                "frame_bytes": frame_base64,
                "camera_name": camera.name
            }))

            await asyncio.sleep(0.001)  # Пауза перед следующей итерацией

    finally:
        cap.release()  # Освобождаем ресурсы видеопотока
        print(f"Захват камеры {camera.name} завершён.")



# Функция для запуска камеры
async def start_camera(camera: Camera):
    """ Метод запускает захват камеры """
    if camera.id in camera_tasks:
        print(f"Камера {camera.name} уже запущена.")
        return
    if camera.active:
        camera_streams[camera.id] = {"url": camera.url, "frame": None, "running": True}
    else:
        camera_streams[camera.id] = {"url": camera.url, "frame": None, "running": False}

    task = asyncio.create_task(video_capture(camera))  # Создаём задачу для захвата видео
    camera_tasks[camera.id] = task


# Функция для остановки камеры
async def stop_camera(camera: Camera):
    """ Метод останавливает захват камеры """
    if camera.id not in camera_tasks:
        print(f"Камера {camera.name} не запущена.")
        return

    camera_streams[camera.id]["running"] = False  # Останавливаем захват
    await camera_tasks[camera.id]  # Ожидаем завершения задачи
    del camera_tasks[camera.id]  # Удаляем задачу
    del camera_streams[camera.id]  # Удаляем информацию о камере
    print(f"Камера {camera.name} остановлена.")


# Функция для локальной проверки наличия лиц на кадре
def detect_face(frame) -> bool:
    """ Локальная проверка на наличие лица """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # Переводим кадр в серый цвет
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))  # Поиск лиц
    return len(faces) > 0  # Возвращаем True, если лица найдены


# Функция для хэширования кадра
def hash_frame(frame_bytes: bytes) -> str:
    """ Создание хэша для проверки изменений кадра """
    return hashlib.md5(frame_bytes).hexdigest()  # Используем MD5 для хэширования кадра
