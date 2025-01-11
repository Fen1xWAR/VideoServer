import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from app.config import Config

# === app/utils/security.py ===
# Утилиты для обеспечения безопасности и работы с токенами
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
# Проверка пароля
def verify_password(plain_password, hashed_password):
    return password_context.verify(plain_password, hashed_password)

# Хэширование пароля
def get_password_hash(password):
    return password_context.hash(password)

# Создание токена доступа
def create_access_token(data: dict):
    to_encode = data.copy()
    token = jwt.encode(to_encode, Config.SECRET_KEY, algorithm=Config.ALGORITHM)
    return token

# Получение текущего пользователя из токена
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
