import uuid

from sqlalchemy import Column, String, UUID, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
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
    module_type = Column(String(50), nullable=False)  # Тип модуля
    enabled = Column(Boolean, default=False)  # Включен ли модуль
    address = Column(String(255), nullable=True)  # Локальный путь или URL эндпоинта для модуля
    description = Column(Text, nullable=True)  # Описание модуля
