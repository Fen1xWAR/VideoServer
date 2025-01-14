# === app/services/security.py ===
import jwt
from fastapi import Depends, HTTPException
from datetime import datetime, timedelta
from typing import Union

from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from app.config import Config

# Утилиты для обеспечения безопасности
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")  # Указывает URL для получения токена

# Проверка пароля
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)

# Хэширование пароля
def get_password_hash(password: str) -> str:
    return password_context.hash(password)

# Создание токена доступа
def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, Config.settings().SECRET_KEY, algorithm=Config.settings().ALGORITHM)
    return token

# Получение текущего пользователя из токена
def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, Config.settings().SECRET_KEY, algorithms=[Config.settings().ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        if username is None or role is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"username": username, "role": role}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
