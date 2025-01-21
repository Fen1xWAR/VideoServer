from app.models.table_models import Camera
from app.services.database_service import get_db


def get_camera_list():
    db = get_db()
    return db.query(Camera).all()