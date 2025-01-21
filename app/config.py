import json
import os
from app.logger import LoggerSingleton  # Импортируем логгер

logger = LoggerSingleton.get_logger()  # Получаем логгер


class Config:
    _settings = None

    class Settings:
        def __init__(self, filepath: str):
            """Инициализация настроек с параметрами по умолчанию"""
            self.filepath = filepath
            self.CAMERA_RESOLUTION = (1920, 1080)  # Разрешение видеопотока
            self.JPEG_QUALITY = 50  # Качество сжатия JPEG
            self.DATABASE_URL = "sqlite:///./app.db"  # URL для подключения к базе данных SQLite
            self.SECRET_KEY = "your_secret_key"  # Секретный ключ для JWT
            self.ALGORITHM = "HS256"  # Алгоритм шифрования JWT
            self.ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Время жизни токена доступа
            self.FACE_RECOGNITION = False  # По умолчанию лицо не распознается
            self._load_settings()  # Попытка загрузить настройки из файла

        def _load_settings(self):
            """Загрузка настроек из файла"""
            try:
                if os.path.exists(self.filepath):
                    with open(self.filepath, "r") as file:
                        data = json.load(file)
                        self.CAMERA_RESOLUTION = tuple(data.get("CAMERA_RESOLUTION", self.CAMERA_RESOLUTION))
                        self.JPEG_QUALITY = data.get("JPEG_QUALITY", self.JPEG_QUALITY)
                        self.DATABASE_URL = data.get("DATABASE_URL", self.DATABASE_URL)
                        self.SECRET_KEY = data.get("SECRET_KEY", self.SECRET_KEY)
                        self.ALGORITHM = data.get("ALGORITHM", self.ALGORITHM)
                        self.ACCESS_TOKEN_EXPIRE_MINUTES = data.get("ACCESS_TOKEN_EXPIRE_MINUTES", self.ACCESS_TOKEN_EXPIRE_MINUTES)
                        self.FACE_RECOGNITION = data.get("FACE_RECOGNITION", self.FACE_RECOGNITION)
                    logger.info(f"Настройки загружены из файла {self.filepath}")
                else:
                    logger.warning(f"Файл настроек {self.filepath} не найден. Создаю настройки по умолчанию.")
                    self._save_settings()

            except Exception as e:
                logger.error(f"Ошибка при загрузке настроек из {self.filepath}: {e}")
                self._save_settings()  # Если ошибка при загрузке — сохраняем по умолчанию

        def _save_settings(self):
            """Сохранение настроек в файл"""
            try:
                with open(self.filepath, "w") as file:
                    json.dump(self.to_dict(), file, indent=4)
                logger.info(f"Настройки сохранены в файл {self.filepath}")
            except Exception as e:
                logger.error(f"Ошибка при сохранении настроек в файл {self.filepath}: {e}")

        def to_dict(self):
            """Преобразование настроек в словарь для сохранения в JSON"""
            return {
                "CAMERA_RESOLUTION": self.CAMERA_RESOLUTION,
                "JPEG_QUALITY": self.JPEG_QUALITY,
                "DATABASE_URL": self.DATABASE_URL,
                "SECRET_KEY": self.SECRET_KEY,
                "ALGORITHM": self.ALGORITHM,
                "ACCESS_TOKEN_EXPIRE_MINUTES": self.ACCESS_TOKEN_EXPIRE_MINUTES,
                "FACE_RECOGNITION": self.FACE_RECOGNITION
            }

        def update(self, **kwargs):
            """Обновление настроек"""
            try:
                for key, value in kwargs.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
                self._save_settings()
                logger.info(f"Настройки обновлены: {kwargs}")
            except Exception as e:
                logger.error(f"Ошибка при обновлении настроек: {e}")

    @classmethod
    def initialize(cls, filepath="settings.json"):
        """Инициализация глобальных настроек"""
        logger.info('Инициализация настроек')
        if cls._settings is None:
            cls._settings = cls.Settings(filepath)

    @classmethod
    def settings(cls):
        """Получение текущих настроек"""
        if cls._settings is None:
            Config.initialize()
        return cls._settings
