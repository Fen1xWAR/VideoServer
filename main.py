from contextlib import asynccontextmanager
from fastapi.openapi.utils import get_openapi
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from app.routes import video, metrics, auth, cameras, module
from app.services.database_service import *
from app.services.camera_service import get_camera_list
from app.services.module_service import ModuleManager
from app.services.video_service import start_camera
from app.logger import LoggerSingleton

# Получаем логгер
logger = LoggerSingleton.get_logger()


# Настройка OpenAPI-схемы для отображения Bearer-токена
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Secure API",
        version="1.0.0",
        description="Api for Video server",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


async def init_app():
    logger.info("Инициализация конфигурации...")
    Config.initialize()

    logger.info("Инициализация базы данных...")
    init_db()

    logger.info("Инициализация модулей...")
    ModuleManager.initialize_modules()

    logger.info("Получение списка камер...")
    camera_list = get_camera_list()

    logger.info(f"Запуск захвата видео для {len(camera_list)} камер...")
    for camera in camera_list:
        await start_camera(camera)

    # Подключение маршрутов
    logger.info("Подключение маршрутов...")
    app.include_router(video.router)
    app.include_router(metrics.router)
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(cameras.router, prefix="/cameras", tags=["cameras"])
    app.include_router(module.router, prefix="/modules", tags=["modules"])

    # Подключение статических файлов (клиент)
    logger.info("Монтирование клиентских статических файлов...")
    app.mount("/", StaticFiles(directory="client", html=True), name="client")


async def close_app():
    logger.info("Закрытие соединения с базой данных...")
    close_db()


@asynccontextmanager
async def init(app: FastAPI):
    logger.info("Запуск приложения...")
    await init_app()
    yield
    await close_app()
    logger.info("Завершение работы приложения...")


app = FastAPI(lifespan=init)

# Настройка кастомного OpenAPI
app.openapi = custom_openapi

# Настройка CORS (разрешённые источники для запросов)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
