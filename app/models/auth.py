from pydantic import BaseModel


class Auth(BaseModel):
    username: str
    password: str


# Модели запросов
class RegisterRequest(BaseModel):
    username: str  # Имя пользователя
    password: str  # Пароль пользователя
    role: str  # Роль пользователя


class LoginRequest(BaseModel):
    username: str  # Имя пользователя
    password: str  # Пароль пользователя

