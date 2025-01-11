# === app/controllers/auth.py ===
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import timedelta

from app.db_models import User, get_db
from app.services.security import verify_password, get_password_hash, create_access_token

router = APIRouter()


# Модели запросов
class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str


class LoginRequest(BaseModel):
    username: str
    password: str


# Регистрация нового пользователя
@router.post("/register")
def register_user(request: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = get_password_hash(request.password)
    user = User(username=request.username, hashed_password=hashed_password, role=request.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "User registered successfully"}


# Логин (вход) пользователя
@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, expires_delta=timedelta(minutes=30)
    )
    return {"access_token": access_token, "token_type": "bearer"}
