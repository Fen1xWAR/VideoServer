from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.table_models import Base
from app.config import Config
from app.logger import LoggerSingleton

# Получаем логгер
logger = LoggerSingleton.get_logger()

# Глобальная сессия базы данных
global_db_session = None

def init_db():
    """Инициализация базы данных и создание всех таблиц"""
    global global_db_session
    if global_db_session is None:
        try:
            engine = create_engine(Config.settings().DATABASE_URL)
            session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            global_db_session = session_local()

            # Создаём таблицы, если их нет
            Base.metadata.create_all(bind=engine)
            logger.info("База данных успешно инициализирована и таблицы созданы.")
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}")
            raise RuntimeError("Не удалось инициализировать базу данных") from e
    else:
        logger.info("База данных уже инициализирована.")

def close_db():
    """Закрытие сессии базы данных"""
    global global_db_session
    if global_db_session:
        try:
            global_db_session.close()
            logger.info("Сессия базы данных успешно закрыта.")
        except Exception as e:
            logger.error(f"Ошибка при закрытии сессии базы данных: {e}")
        global_db_session = None
    else:
        logger.warning("Попытка закрыть неинициализированную сессию базы данных.")

def get_db():
    """Получение текущей сессии базы данных"""
    if global_db_session is None:
        logger.error("База данных не инициализирована.")
        raise RuntimeError("База данных не инициализирована")
    logger.info("Получена текущая сессия базы данных.")
    return global_db_session
