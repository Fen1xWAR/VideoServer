# === app/controllers/cameras.py ===
# Маршруты для управления камерами
import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db_models import Camera, get_db
from app.services.camera_service import get_camera_list
from app.services.security import get_current_user
from app.services.video_service import init_camera_capture, camera_streams, video_capture

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
        init_camera_capture(camera)
        return camera
    else:
        raise HTTPException(status_code=403, detail="Access denied: Admin role required")
@router.delete("/remove_camera/{id}")
def remove_camera(id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if user['role'] != "admin":
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only")

    query = delete(Camera).where(Camera.id == id)
    result = db.execute(query)
    db.commit()  #

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Camera not found")

    return {"detail": "Camera removed successfully"}

@router.post("/activate_camera")
def activate_camera(id: str, user : dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if user['role'] != "admin":
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only")
    camera =  db.query(Camera).filter(Camera.id == UUID(id))
    camera.update({"active": True})
    db.commit()
    camera_streams[str(id)]['running'] = True
    if not asyncio.iscoroutinefunction(video_capture):
        asyncio.create_task(video_capture(camera.id, camera.url))
    return {"detail": "Camera activated successfully"}

@router.post("/deactivate_camera")
def deactivate_camera(id: str, user : dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if user['role'] != "admin":
        raise HTTPException(status_code=403, detail="Access forbidden: Admins only")
    db.query(Camera).filter(Camera.id == UUID(id)).update({"active": False})
    db.commit()
    camera_streams[str(id)]['running'] = False
    return {"detail": "Camera deactivated successfully"}