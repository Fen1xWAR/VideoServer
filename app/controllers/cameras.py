from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete
from sqlalchemy.orm import Session
from app.services.database_service import Camera, get_db
from app.services.camera_service import get_camera_list
from app.services.security import get_current_user
from app.services.video_service import stop_camera, start_camera, camera_tasks

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
def add_camera(name: str, url: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Добавление камеры в систему"""
    if user['role'] == "admin":
        camera = Camera(name=name, url=url, active=False)  # Создание камеры
        db.add(camera)
        db.commit()  # Сохранение камеры в базе данных
        db.refresh(camera)
        start_camera(camera)  # Запуск камеры
        return camera
    else:
        raise HTTPException(status_code=403, detail="Access denied: Admin role required")


# Удаление камеры
@router.delete("/remove_camera/{id}")
def remove_camera(id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Удаление камеры по ID"""
    if user['role'] != "admin":
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only")

    query = delete(Camera).where(Camera.id == id)  # Удаляем камеру по ID
    result = db.execute(query)
    db.commit()

    if result.rowcount == 0:  # Если камера не найдена
        raise HTTPException(status_code=404, detail="Camera not found")

    return {"detail": "Camera removed successfully"}


# Активация камеры
@router.post("/activate_camera")
async def activate_camera(id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Активация камеры"""
    if user['role'] != "admin":
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only")

    # Проверка существования камеры в базе данных
    camera = db.query(Camera).filter(Camera.id == UUID(id)).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    # Обновление статуса камеры на активный
    db.query(Camera).filter(Camera.id == UUID(id)).update({"active": True})
    db.commit()

    if camera.id in camera_tasks:  # Проверка, активен ли поток камеры
        raise HTTPException(status_code=400, detail="Camera is already active")
    await start_camera(camera)  # Запуск камеры

    return {"detail": "Camera activated successfully"}


# Деактивация камеры
@router.post("/deactivate_camera")
async def deactivate_camera(id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Деактивация камеры"""
    if user['role'] != "admin":
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only")

    # Проверка существования камеры в базе данных
    camera = db.query(Camera).filter(Camera.id == UUID(id)).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    # Остановка потока камеры
    if camera.id not in camera_tasks:
        raise HTTPException(status_code=400, detail="Camera is not active")
    await stop_camera(camera)  # Остановка камеры

    # Обновление статуса камеры на неактивный
    db.query(Camera).filter(Camera.id == UUID(id)).update({"active": False})
    db.commit()

    return {"detail": "Camera deactivated successfully"}
