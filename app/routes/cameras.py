import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.camera import CameraModel
from app.models.table_models import Camera
from app.services.camera_service import get_camera_list, add_camera_internal, remove_camera_internal, get_camera_by_id, \
    deactivate_camera_internal
from app.services.database_service import get_db
from app.services.security_service import get_current_user
from app.services.video_service import start_camera, camera_tasks

router = APIRouter()


# Получение списка камер
@router.get("/get_cameras")
def get_cameras(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получение списка камер для администратора"""
    if user['role'] == "admin":
        cameras = get_camera_list()  # Получаем список камер из сервиса
        return cameras
    else:
        raise HTTPException(status_code=403, detail="Access denied: Admin role required")


# Добавление новой камеры
@router.post("/add_camera")
async def add_camera(cameraModel: CameraModel, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Добавление камеры в систему"""
    if user['role'] == "admin":
        camera = await add_camera_internal(cameraModel)
        return camera
    else:
        raise HTTPException(status_code=403, detail="Access denied: Admin role required")


# Удаление камеры
@router.delete("/remove_camera/{id}")
async def remove_camera(id: uuid.UUID, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Удаление камеры по ID"""
    if user['role'] != "admin":
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only")
    await remove_camera_internal(id)
    return {"detail": "Camera removed successfully"}


# Активация камеры
@router.post("/activate_camera")
async def activate_camera(id: uuid.UUID, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Активация камеры"""
    if user['role'] != "admin":
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only")

    camera = await get_camera_by_id(id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    db.query(Camera).filter(Camera.id == id).update({"active": True})
    db.commit()

    if camera.id in camera_tasks:
        raise HTTPException(status_code=400, detail="Camera is already active")
    await start_camera(camera)

    return {"detail": "Camera activated successfully"}


# Деактивация камеры
@router.post("/deactivate_camera")
async def deactivate_camera(id: uuid.UUID, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Деактивация камеры"""
    if user['role'] != "admin":
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only")

    # Проверка существования камеры в базе данных
    camera = await get_camera_by_id(id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    if camera.id not in camera_tasks:
        raise HTTPException(status_code=400, detail="Camera is not active")
    await deactivate_camera_internal(camera)

    return {"detail": "Camera deactivated successfully"}
