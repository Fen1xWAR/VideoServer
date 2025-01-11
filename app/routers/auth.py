# === app/routers/auth.py ===
# Маршруты для авторизации и регистрации пользователей
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

import app.models.auth
from app.db_models import User, SessionLocal
from app.models.auth import Auth
from app.utils.security import verify_password, get_password_hash, create_access_token

router = APIRouter()

# Получение сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Регистрация нового пользователя
@router.post("/register")
def register_user(username: str, password: str, db: Session = Depends(get_db)):
    hashed_password = get_password_hash(password)
    user = User(username=username, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "User registered successfully"}

# Авторизация пользователя
@router.post("/login")
def login_user(login_data : Auth, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == login_data.username).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}
