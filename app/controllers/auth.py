from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import timedelta

from app.services.database_service import User, get_db
from app.models.auth import RegisterRequest, LoginRequest
from app.services.security import verify_password, get_password_hash, create_access_token, get_current_user

router = APIRouter()


# Регистрация нового пользователя
@router.post("/register")
def register_user(request: RegisterRequest, db: Session = Depends(get_db)):
    """Регистрация нового пользователя в системе"""
    # Проверка существующего пользователя с таким же именем
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Хеширование пароля и создание нового пользователя
    hashed_password = get_password_hash(request.password)
    user = User(username=request.username, hashed_password=hashed_password, role=request.role)
    db.add(user)
    db.commit()  # Сохранение пользователя в БД
    db.refresh(user)  # Обновление данных о пользователе
    return {"detail": "User registered successfully"}


# Логин (вход) пользователя
@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Аутентификация пользователя с получением токена доступа"""
    # Поиск пользователя в БД по имени
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # Генерация токена доступа
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, expires_delta=timedelta(minutes=30)
    )
    return {"access_token": access_token, "token_type": "bearer"}


# Получение данных о пользователе
@router.get("/user_data")
async def get_user_data(user_id: str, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """Получение данных о пользователе по ID"""
    user_data = db.query(User).filter(User.id == user_id).first()
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    return user_data
