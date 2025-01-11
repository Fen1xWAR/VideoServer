from sqlalchemy.orm import Session

from app.db_models import get_db, Camera


def get_camera_list(db: Session):
    db = get_db()
    return db.query(Camera).all()