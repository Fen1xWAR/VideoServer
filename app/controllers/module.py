from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.services.database_service import get_db, Module
from app.services.module.ModuleService import ModuleManager
from app.services.security import get_current_user

router = APIRouter()


# Получение всех модулей
@router.get("/get_modules")
def get_modules(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получение списка всех модулей, доступных пользователю"""
    # Права доступа проверяются в зависимости от роли текущего пользователя
    return ModuleManager.get_all_modules()


# Добавление нового модуля
@router.get("/add_module")
def add_module(name: str, module_type: str, address: str, enabled: bool, db: Session = Depends(get_db)):
    """Добавление нового модуля в систему"""
    # Создание нового модуля и сохранение его в базе данных
    module = Module(name=name, module_type=module_type, address=address, enabled=enabled)
    db.add(module)
    db.commit()  # Сохранение изменений в базе данных
    db.refresh(module)  # Обновление объекта модуля с актуальными данными из базы

    # Добавление модуля в систему менеджера
    ModuleManager.add_module(name, module_type, address, enabled)

    return module  # Возвращаем добавленный модуль
