import psutil
# === app/routers/metrics.py ===
from fastapi import APIRouter

from app.services.video_service import camera_streams, clients

router = APIRouter()

@router.get("/metrics")
def get_metrics():
    process = psutil.Process()
    memory_info = process.memory_info()
    return {
        "memory_usage_mb": memory_info.rss / 1024 / 1024,
        "num_clients": sum(len(client_list) for client_list in clients.values()),
        "num_cameras": len(camera_streams),
    }
