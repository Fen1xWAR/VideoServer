import cv2
import threading
import base64
import psutil  # Для мониторинга системных ресурсов
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List
from fastapi.middleware.cors import CORSMiddleware

# Создание FastAPI приложения
app = FastAPI()

# Разрешённые домены
origins = [
    "http://localhost",  # Для локального хоста
    "http://127.0.0.1",  # Альтернативный локальный хост
    "http://localhost:5500",  # Если вы используете Live Server
    "http://your-frontend-domain.com",  # Укажите домен фронтенда
]

# Добавление миддлвари CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Хранилище потоков для камер
camera_streams = {}
clients = {}  # Активные клиенты WebSocket

lock = threading.Lock()

# Функция для захвата видео с камеры
def video_capture(camera_id: int, camera_url: str):
    cap = cv2.VideoCapture(camera_url)
    if not cap.isOpened():
        print(f"Не удалось открыть камеру {camera_id}: {camera_url}")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"Ошибка чтения кадра с камеры {camera_id}")
            break
        _, encoded_frame = cv2.imencode('.jpg', frame)
        with lock:
            camera_streams[camera_id]["frame"] = encoded_frame.tobytes()

    cap.release()

# Инициализация камер
def initialize_cameras(camera_config: List[Dict[str, str]]):
    for camera_id, camera_url in enumerate(camera_config):
        camera_streams[camera_id] = {"url": camera_url, "frame": None}
        thread = threading.Thread(target=video_capture, args=(camera_id, camera_url), daemon=True)
        thread.start()



@app.websocket("/ws/video/{camera_id}")
async def websocket_video_stream(websocket: WebSocket, camera_id: int):
    if camera_id not in camera_streams:
        await websocket.close(code=1003)  # Ошибка, если камеры нет
        return

    await websocket.accept()
    if camera_id not in clients:
        clients[camera_id] = []
    clients[camera_id].append(websocket)

    try:
        while True:
            with lock:
                frame = camera_streams[camera_id].get("frame")
            if frame is None:
                continue
            # Кодируем кадр в base64 для отправки
            encoded_frame = base64.b64encode(frame).decode("utf-8")
            await websocket.send_text(encoded_frame)
    except WebSocketDisconnect:
        clients[camera_id].remove(websocket)
        print(f"Клиент отключился от камеры {camera_id}")

# Эндпоинт для мониторинга системных ресурсов
@app.get("/metrics")
def get_metrics():
    # Использование оперативной памяти процессом
    process = psutil.Process()
    memory_info = process.memory_info()
    return {
        "memory_usage_mb": memory_info.rss / 1024 / 1024,  # RSS (Resident Set Size) в мегабайтах
        "num_clients": sum(len(client_list) for client_list in clients.values()),  # Количество подключённых клиентов
        "num_cameras": len(camera_streams),  # Количество камер
    }

# Пример конфигурации камер
camera_config = [
    0,                # Локальная USB-камера
    # "rtsp://...",       # Сетевая RTSP-камера
    # Добавьте URL других камер
]

# Запуск инициализации камер
initialize_cameras(camera_config)
