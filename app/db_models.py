import uuid
from sqlalchemy import create_engine, Column, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID  # Импортируем UUID для PostgreSQL

from app.config import Config

# Определение моделей базы данных
Base = declarative_base()

# Модель камеры
class Camera(Base):
    __tablename__ = "cameras"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # Используем UUID
    name = Column(String, index=True)
    url = Column(String, unique=True, index=True)
    active = Column(Boolean, default=True)

# Модель пользователя
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # Используем UUID
    username = Column(String, unique=True, index=True)
    role = Column(String, index=True)
    hashed_password = Column(String)

global_db_session = None

def init_db():
    global global_db_session
    if global_db_session is None:
        engine = create_engine(Config.settings().DATABASE_URL)
        session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        global_db_session = session_local()
        Base.metadata.create_all(bind=engine)

def close_db():
    global global_db_session
    if global_db_session:
        global_db_session.close()
        global_db_session = None

def get_db():
    if global_db_session is None:
        raise RuntimeError("Database session is not initialized. Make sure to call init_db() during application startup.")
    return global_db_session