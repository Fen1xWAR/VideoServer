import psutil
import time
from fastapi import APIRouter

from app.services.video_service import camera_streams

router = APIRouter()


@router.get("/metrics")
def get_metrics():
    process = psutil.Process()
    memory_info = process.memory_info()

    # Метрика процессора
    cpu_percent = process.cpu_percent()

    # Количество процессов
    num_threads = process.num_threads()

    # Время жизни
    uptime_seconds = time.time() - process.create_time()

    # Метрики IO
    try:
        io_counters = process.io_counters()
        io_read_mb = io_counters.read_bytes / (1024 ** 2)
        io_write_mb = io_counters.write_bytes / (1024 ** 2)
    except psutil.AccessDenied:
        io_read_mb = None
        io_write_mb = None

    try:
        num_fds = process.num_fds()
    except AttributeError:
        num_fds = None

    try:
        num_connections = len(process.connections())
    except psutil.AccessDenied:
        num_connections = None

    return {
        "memory_usage_mb": memory_info.rss / (1024 ** 2),
        "cpu_percent": cpu_percent,
        "num_threads": num_threads,
        "uptime_seconds": round(uptime_seconds, 2),
        "io_read_mb": round(io_read_mb, 2) if io_read_mb is not None else None,
        "io_write_mb": round(io_write_mb, 2) if io_write_mb is not None else None,
        "num_fds": num_fds,
        "num_connections": num_connections,
        "num_cameras": len(camera_streams),
        "system_cpu_usage": psutil.cpu_percent(),
        "system_memory_usage": psutil.virtual_memory().percent,

    }