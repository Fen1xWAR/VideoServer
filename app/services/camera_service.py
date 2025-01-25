import uuid

from sqlalchemy import delete

from app.models.camera import CameraModel
from app.models.table_models import Camera
from app.services.database_service import get_db
from app.services.video_service import start_camera, stop_camera


def get_camera_list():
    db = get_db()
    return db.query(Camera).all()


async def get_camera_by_id(camera_id):
    db = get_db()
    return db.query(Camera).filter(Camera.id == camera_id).first()


async def add_camera_internal(cameraModel: CameraModel):
    db = get_db()
    camera = Camera(name=cameraModel.name, url=cameraModel.url, active=cameraModel.active)
    db.add(camera)
    db.commit()
    db.refresh(camera)
    await start_camera(camera)
    return camera


async def remove_camera_internal(id: uuid.UUID):
    db = get_db()
    query = delete(Camera).where(Camera.id == id)
    db.execute(query)
    db.commit()


async def deactivate_camera_internal(camera : Camera):
    db = get_db()
    # Остановка потока камеры

    await stop_camera(camera)  # Остановка камеры

    # Обновление статуса камеры на неактивный
    db.query(Camera).filter(Camera.id == camera.id).update({"active": False})
    db.commit()
