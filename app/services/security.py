﻿import jwt
from fastapi import Depends, HTTPException
from datetime import datetime, timedelta
from typing import Union

from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from app.services.config import Config

# Утилиты для обеспечения безопасности
password_context = CryptContext(schemes=["bcrypt"],
                                deprecated="auto")  # Контекст для хэширования паролей с использованием bcrypt
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")  # Указывает URL для получения токена


# Проверка пароля
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет, совпадает ли обычный пароль с хэшированным паролем.

    :param plain_password: Обычный пароль
    :param hashed_password: Хэшированный пароль
    :return: True, если пароли совпадают, иначе False
    """
    return password_context.verify(plain_password, hashed_password)


# Хэширование пароля
def get_password_hash(password: str) -> str:
    """
    Хэширует пароль с использованием bcrypt.

    :param password: Обычный пароль
    :return: Хэшированный пароль
    """
    return password_context.hash(password)


# Создание токена доступа
def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    """
    Создает токен доступа с заданными данными и временем жизни.

    :param data: Данные, которые будут закодированы в токене
    :param expires_delta: Время жизни токена (по умолчанию 30 минут)
    :return: JWT токен
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))  # Устанавливаем срок действия токена
    to_encode.update({"exp": expire})  # Добавляем информацию о времени истечения
    token = jwt.encode(to_encode, Config.settings().SECRET_KEY, algorithm=Config.settings().ALGORITHM)
    return token


# Получение текущего пользователя из токена
def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Извлекает текущего пользователя из JWT токена.

    :param token: JWT токен
    :return: Данные пользователя (username, role)
    :raises HTTPException: Если токен некорректен
    """
    try:
        # Декодируем токен и извлекаем информацию
        payload = jwt.decode(token, Config.settings().SECRET_KEY, algorithms=[Config.settings().ALGORITHM])
        username = payload.get("sub")  # Извлекаем имя пользователя
        role = payload.get("role")  # Извлекаем роль пользователя
        if username is None or role is None:
            raise HTTPException(status_code=401, detail="Invalid token")  # Если данных нет, возвращаем ошибку
        return {"username": username, "role": role}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")  # Ошибка декодирования токена
