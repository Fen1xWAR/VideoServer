import jwt
from fastapi import Depends, HTTPException
from datetime import datetime, timedelta
from typing import Union

from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from app.config import Config
from app.logger import LoggerSingleton

# Получаем логгер
logger = LoggerSingleton.get_logger()

# Утилиты для обеспечения безопасности
password_context = CryptContext(schemes=["bcrypt"],
                                deprecated="auto")  # Контекст для хэширования паролей с использованием bcrypt
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")  # Указывает URL для получения токена


# Проверка пароля
def verify_password(plain_password: str, hashed_password: str) -> bool:

    result = password_context.verify(plain_password, hashed_password)
    if result:
        logger.info("Пароль совпал.")
    else:
        logger.warning("Пароль не совпал.")
    return result


# Хэширование пароля
def get_password_hash(password: str) -> str:

    hashed_password = password_context.hash(password)
    logger.info(f"Пароль хэширован: {hashed_password}")
    return hashed_password


# Создание токена доступа
def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:

    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, Config.settings().SECRET_KEY, algorithm=Config.settings().ALGORITHM)
    logger.info(f"Создан токен доступа для пользователя: {data['sub']} с временем жизни: {expire}")
    return token


# Получение текущего пользователя из токена
def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:

    try:
        # Декодируем токен и извлекаем информацию
        payload = jwt.decode(token, Config.settings().SECRET_KEY, algorithms=[Config.settings().ALGORITHM])
        username = payload.get("sub")  # Извлекаем имя пользователя
        role = payload.get("role")  # Извлекаем роль пользователя
        if username is None or role is None:
            logger.error(f"Неверный токен: {token}")
            raise HTTPException(status_code=401, detail="Неверный токен")  # Если данных нет, возвращаем ошибку
        logger.info(f"Пользователь {username} с ролью {role} успешно извлечён из токена.")
        return {"username": username, "role": role}
    except jwt.PyJWTError as e:
        logger.error(f"Ошибка декодирования токена: {e}")
        raise HTTPException(status_code=401, detail="Неверный токен")  # Ошибка декодирования токена
