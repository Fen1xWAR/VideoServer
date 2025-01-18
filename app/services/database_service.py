import uuid
from sqlalchemy import create_engine, Column, String, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID  # Импортируем UUID для PostgreSQL

from app.services.config import Config

# Определение базового класса для моделей
Base = declarative_base()

# Модель пользователя
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True)  # Уникальное имя пользователя
    role = Column(String, index=True)  # Роль пользователя (например, 'admin', 'user')
    hashed_password = Column(String)  # Хэшированный пароль пользователя

# Модель камеры
class Camera(Base):
    __tablename__ = "cameras"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, index=True)  # Название камеры
    url = Column(String, unique=True, index=True)  # Уникальный URL камеры
    active = Column(Boolean, default=True)  # Статус активности камеры

# Модель модуля
class Module(Base):
    __tablename__ = 'modules'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)  # Название модуля
    module_type = Column(String(50), nullable=False)  # Тип модуля (например, 'video', 'audio', 'image', 'face_recognition')
    enabled = Column(Boolean, default=False)  # Включен ли модуль
    address = Column(String(255), nullable=True)  # Локальный путь или URL эндпоинта для модуля
    description = Column(Text, nullable=True)  # Описание модуля

# Глобальная сессия базы данных
global_db_session = None

def init_db():
    """Инициализация базы данных и создание всех таблиц"""
    global global_db_session
    if global_db_session is None:
        # Создаем соединение с базой данных
        engine = create_engine(Config.settings().DATABASE_URL)
        # Настройка сессии
        session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        global_db_session = session_local()
        # Создаем все таблицы, если они не существуют
        Base.metadata.create_all(bind=engine)

def close_db():
    """Закрытие сессии базы данных"""
    global global_db_session
    if global_db_session:
        global_db_session.close()
        global_db_session = None

def get_db():
    """Получение текущей сессии базы данных"""
    if global_db_session is None:
        raise RuntimeError("Database session is not initialized. Make sure to call init_db() during application startup.")
    return global_db_session
