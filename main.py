from contextlib import asynccontextmanager
from fastapi.openapi.utils import get_openapi
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app.controllers import video, metrics, auth, cameras, module
from app.services.database_service import *
from app.services.module.ModuleService import ModuleManager
from app.services.camera_service import get_camera_list
from app.services.video_service import start_camera


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
    Config.initialize()
    init_db()
    ModuleManager.initialize_modules()

    db = get_db()  # Получаем подключение к базе данных
    camera_list = get_camera_list()  # Получаем список камер
    # Инициализируем видеопотоки для каждой камеры
    for camera in camera_list:
        await  start_camera(camera)
    # Подключение маршрутов

    app.include_router(video.router)
    app.include_router(metrics.router)
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(cameras.router, prefix="/cameras", tags=["cameras"])

    app.include_router(module.router, prefix="/modules", tags=["modules"])

    app.mount("/", StaticFiles(directory="client", html=True), name="client")


async def close_app():
    close_db()


@asynccontextmanager
async def init(app: FastAPI):
    await init_app()
    print("starting app")
    yield
    await close_app()
    print("finished app")





app = FastAPI(lifespan=init)

app.openapi = custom_openapi
# Настройка CORS (разрешённые источники для запросов)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
