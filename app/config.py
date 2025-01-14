# === app/settings.py ===
import json


class Config:
    _settings = None

    class Settings:
        def __init__(self, filepath: str):
            self.filepath = filepath
            self.CAMERA_RESOLUTION = (1920, 1080)  # Разрешение видеопотока
            self.JPEG_QUALITY = 50  # Качество сжатия JPEG
            self.DATABASE_URL = "sqlite:///./app.db"  # URL для подключения к базе данных SQLite
            self.SECRET_KEY = "your_secret_key"  # Секретный ключ для JWT
            self.ALGORITHM = "HS256"  # Алгоритм шифрования JWT
            self.ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Время жизни токена доступа
            self.FACE_RECOGNITION = False
            self._load_settings()

        def _load_settings(self):
            try:
                with open(self.filepath, "r") as file:
                    data = json.load(file)
                    self.CAMERA_RESOLUTION = tuple(data.get("CAMERA_RESOLUTION", self.CAMERA_RESOLUTION))
                    self.JPEG_QUALITY = data.get("JPEG_QUALITY", self.JPEG_QUALITY)
                    self.DATABASE_URL = data.get("DATABASE_URL", self.DATABASE_URL)
                    self.SECRET_KEY = data.get("SECRET_KEY", self.SECRET_KEY)
                    self.ALGORITHM = data.get("ALGORITHM", self.ALGORITHM)
                    self.ACCESS_TOKEN_EXPIRE_MINUTES = data.get("ACCESS_TOKEN_EXPIRE_MINUTES", self.ACCESS_TOKEN_EXPIRE_MINUTES)
                    self.FACE_RECOGNITION = data.get("FACE_RECOGNITION", self.FACE_RECOGNITION)
            except FileNotFoundError:
                self._save_settings()

        def _save_settings(self):
            with open(self.filepath, "w") as file:
                json.dump(self.to_dict(), file, indent=4)

        def to_dict(self):
            return {
                "CAMERA_RESOLUTION": self.CAMERA_RESOLUTION,
                "JPEG_QUALITY": self.JPEG_QUALITY,
                "DATABASE_URL": self.DATABASE_URL,
                "SECRET_KEY": self.SECRET_KEY,
                "ALGORITHM": self.ALGORITHM,
                "ACCESS_TOKEN_EXPIRE_MINUTES": self.ACCESS_TOKEN_EXPIRE_MINUTES,
                "FACE_RECOGNITION": self.FACE_RECOGNITION,
            }

        def update(self, **kwargs):
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            self._save_settings()

    @classmethod
    def initialize(cls, filepath="settings.json"):
        print('initializing settings')
        if cls._settings is None:
            cls._settings = cls.Settings(filepath)

    @classmethod
    def settings(cls):
        if cls._settings is None:
            raise RuntimeError("Config is not initialized. Call Config.initialize() first.")
        return cls._settings