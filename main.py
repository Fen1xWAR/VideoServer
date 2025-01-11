# === main.py ===
# Основной файл для запуска приложения
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import Config
from app.routers import video, metrics, auth, cameras, face_recognition
from app.db_models import Base, engine, get_db
from app.routers.cameras import get_camera_list
from app.services.video_service import video_capture, camera_streams
import asyncio

app = FastAPI()

# Настройка CORS (разрешённые источники для запросов)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создание таблиц в базе данных
Base.metadata.create_all(bind=engine)

# Подключение маршрутов
app.include_router(video.router)
app.include_router(metrics.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(cameras.router, prefix="/cameras", tags=["cameras"])
app.include_router(face_recognition.router, prefix="/face-recognition", tags=["face-recognition"])


# Инициализация видеопотоков для камер
async def initialize_video_streams():
    # Получаем список камер из базы данных (с помощью get_camera_list)
    db = next(get_db())  # Получаем подключение к базе данных
    cameras = get_camera_list(db)  # Получаем список камер


    # Инициализируем видеопотоки для каждой камеры
    for camera in cameras:
        camera_streams[camera.id] = {"url": camera.url, "frame": None}
        # Создаем асинхронную задачу для захвата видеопотока
        asyncio.create_task(video_capture(camera.id, camera.url))

@app.on_event("startup")
async def on_startup():
    # Инициализация видеопотоков при старте приложения
    await initialize_video_streams()
# # # Инициализация видеопотоков для камер
# for camera in Config.CAMERA_CONFIG:
#     camera_streams[camera["id"]] = {"url": camera["url"], "frame": None}
#     asyncio.create_task(video_capture(camera["id"], camera["url"]))