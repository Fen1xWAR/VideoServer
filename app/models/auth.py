from pydantic import BaseModel


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str


class LoginRequest(BaseModel):
    username: str
    password: str
