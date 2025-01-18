from app.services.database_service import get_db, Camera


def get_camera_list():
    db = get_db()
    return db.query(Camera).all()