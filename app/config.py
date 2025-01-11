class Config:
    CAMERA_RESOLUTION = (1920, 1080)  # Разрешение видеопотока
    JPEG_QUALITY = 50  # Качество сжатия JPEG
    CAMERA_CONFIG = [
        {"id": 0, "url": 0, "name": "USB Camera"},  # Настройка первой камеры
        {"id": 1, "url": 1, "name": "Local Camera 2"},  # Настройка второй камеры
    ]
    DATABASE_URL = "sqlite:///./app.db"  # URL для подключения к базе данных SQLite
    SECRET_KEY = "your_secret_key"  # Секретный ключ для JWT
    ALGORITHM = "HS256"  # Алгоритм шифрования JWT
    ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Время жизни токена доступа