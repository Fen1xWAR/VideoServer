# === app/routers/cameras.py ===
# Маршруты для управления камерами
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db_models import Camera, get_db
from app.utils.security import get_current_user

router = APIRouter()


# Получение списка камер
@router.get("/cameras")
def get_cameras(user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    cameras = get_camera_list(db)
    return cameras

def get_camera_list(db: Session):
    return db.query(Camera).all()

# Добавление новой камеры
@router.post("/cameras")
def add_camera(name: str, url: str, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    camera = Camera(name=name, url=url)
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera