from fastapi import HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.services.database_service import get_db, Module
from app.services.module.ModuleService import ModuleManager, is_html
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


@router.get("/enable_module/{module_id}")
async def enable_module(module_id: str, db: Session = Depends(get_db)):
    module_id = UUID(module_id)
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    ModuleManager.enable_module(module.name)
    db.query(Module).filter(Module.id == module_id).update({"enabled": True})
    db.commit()


@router.get("/disable_module/{module_id}")
async def disable_module(module_id: str, db: Session = Depends(get_db)):
    module_id = UUID(module_id)
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    ModuleManager.disable_module(module.name)
    db.query(Module).filter(Module.id == module_id).update({"enabled": False})
    db.commit()


@router.get("/get_module/{module_id}", response_class=HTMLResponse)
async def serve_module_html(module_id: str, db: Session = Depends(get_db)):
    module_id = UUID(module_id)
    module = db.query(Module).filter(Module.id == module_id).first()

    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Получаем информацию о модуле через ModuleManager
    module_info = await ModuleManager.get_module_info(module.name, db)  # Теперь ожидаем результат асинхронно

    # Проверяем, является ли информация HTML
    if isinstance(module_info, str) and is_html(module_info):
        # Если информация является HTML, возвращаем её как HTML-страницу
        return HTMLResponse(content=module_info)
    elif isinstance(module_info, dict):
        # Если это JSON-ответ, возвращаем его как JSON
        return JSONResponse(content=module_info)
    else:
        # Если информация является строкой с ошибкой
        raise HTTPException(status_code=500, detail=module_info)