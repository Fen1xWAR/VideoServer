# === app/controllers/cameras.py ===
# Маршруты для управления камерами

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db_models import Camera, get_db
from app.services.camera_service import get_camera_list
from app.services.security import get_current_user

router = APIRouter()


# Получение списка камер
@router.get("/get_cameras")
def get_cameras(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if user['role'] == "admin":

        cameras = get_camera_list(db)
        return cameras
    else:
        raise HTTPException(status_code=403, detail="Access denied: Admin role required")

#Добавление камеры
@router.post("/add_camera")
def add_camera(name: str, url: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    # Проверка роли пользователя
    if user['role'] == "admin":
        camera = Camera(name=name, url=url, active=False)
        db.add(camera)
        db.commit()
        db.refresh(camera)
        return camera
    else:
        raise HTTPException(status_code=403, detail="Access denied: Admin role required")