import asyncio
import importlib
import json
import os
import re
from contextlib import suppress
from typing import Dict, List, Optional

import aiohttp
from sqlalchemy.orm import Session

from app.models import table_models
from app.services.database_service import get_db
from modules.Module import Module
from app.logger import LoggerSingleton

logger = LoggerSingleton.get_logger()


class ModuleManager:
    _instance: Optional['ModuleManager'] = None
    modules: Dict[str, Module] = {}
    frame_counter: int = 0  # Счётчик кадров

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._initialized = True
            self.initialize_modules()

    @classmethod
    def add_module(
            cls,
            name: str,
            module_type: str,
            loaded_class: Optional[type] = None,
            address: Optional[str] = None,
            enabled: bool = False
    ) -> None:
        if name not in cls.modules:
            module = Module(
                name=name,
                module_type=module_type,
                address=address,
                enabled=enabled,
                loaded_class=loaded_class
            )
            cls.modules[name] = module
            logger.info(f"Module added: {name} ({module_type})")
        else:
            logger.warning(f"Module already exists: {name}")

    @classmethod
    def toggle_module(cls, module_name: str, enable: bool) -> str:
        if module_name not in cls.modules:
            logger.error(f"Module not found: {module_name}")
            return f"Module {module_name} not found"

        module = cls.modules[module_name]
        module.enabled = enable
        status = "enabled" if enable else "disabled"
        logger.info(f"Module {module_name} {status}")
        return f"Module {module_name} {status}"

    @classmethod
    def get_module_status(cls, module_name: str) -> str:
        module = cls.modules.get(module_name)
        if not module:
            logger.error(f"Module not found: {module_name}")
            return f"Module {module_name} not found"
        return f"Module {module_name} is {'enabled' if module.enabled else 'disabled'}"

    @classmethod
    async def process_data(cls, data: dict) -> List[dict]:
        results = []
        active_modules = [m for m in cls.modules.values() if m.enabled]

        if not active_modules:
            logger.warning("No active modules to process data")
            return []

        for module in active_modules:
            if module.module_type == "local":
                cls._process_local_module(module, data)
        cls.frame_counter += 1  # Увеличиваем счётчик кадров
        if cls.frame_counter % 10 == 0:  # Если это 10-й кадр
            try:
                async with asyncio.TaskGroup() as tg:
                    tasks = [tg.create_task(cls._process_single_module(module, data))
                             for module in active_modules if module.module_type == "network"]

                for task in tasks:
                    if not task.cancelled() and not isinstance(task.result(), Exception):
                        results.append(task.result())

            except ExceptionGroup as eg:
                for ex in eg.exceptions:
                    logger.error(f"Task group error: {ex}")
            except Exception as e:
                logger.error(f"Unexpected processing error: {e}")

        return results

    @classmethod
    async def _process_single_module(cls, module: Module, data: dict):
        with suppress(asyncio.CancelledError):
            try:
                if module.module_type == "network":
                    return await cls._process_network_request(module, data)
                return cls._process_local_module(module, data)
            except Exception as e:
                logger.error(f"Module {module.name} error: {e}")
                return e

    @classmethod
    async def _process_network_request(cls, module: Module, data: dict):
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                try:
                    async with session.post(
                            f"{module.address}/proceed",
                            json=data,
                            timeout=timeout
                    ) as response:
                        response.raise_for_status()
                        return await cls._handle_network_response(response, module.name)
                except asyncio.TimeoutError:
                    logger.warning(f"Таймаут в процессе ожидания ответа от  {module.name}")
                    return {"error": "Превышено время ожидание ответа"}
                except aiohttp.ClientError as e:
                    logger.error(f"Сетевая ошибка в  {module.name}: {e}")
                    return {"error": str(e)}
                except Exception as e:
                    logger.error(f"Неизвестная ошибка в {module.name}: {e}")
                    return {"error": f"Неизвестная ошибка в: {e}"}

        except asyncio.CancelledError:
            logger.warning(f"Запрос отклонен от : {module.name}")
            raise
        except Exception as e:
            logger.error(f"Неизвестная ошибка от {module.name}: {e}")
            return {"error": f"Неизвестная ошибка в процессе установления соединения: {e}"}

    @classmethod
    def _process_local_module(cls, module: Module, data: dict):
        if not module.loaded_class:
            logger.error(f"Класс не был загружен для модуля: {module.name}")
            return {"error": "Класс модуля не был загружен"}

        try:
            instance = module.loaded_class(
                name=module.name,
                module_type="local",
                address=module.address,
                enabled=module.enabled
            )
            result = instance.proceed(data)
            return result
        except Exception as e:
            logger.error(f"Ошибка локального модуля {module.name}: {e}")
            return {"error": str(e)}

    @classmethod
    def initialize_modules(cls):
        logger.info("Initializing modules from database")
        db_modules = cls.get_all_modules()

        for db_module in db_modules:
            loaded_class = None
            if db_module.module_type == "local":
                loaded_class = cls._load_local_module_class(db_module)

            cls.add_module(
                name=db_module.name,
                module_type=db_module.module_type,
                loaded_class=loaded_class,
                address=db_module.address,
                enabled=db_module.enabled
            )

        logger.info(f"Initialized modules: {len(cls.modules)}")

    @classmethod
    def get_all_modules(cls):
        db = get_db()
        try:
            return db.query(table_models.Module).all()
        except Exception as e:
            logger.error(f"Database error: {e}")
            return []
        finally:
            db.close()

    @classmethod
    def _load_local_module_class(cls, db_module) -> Optional[type]:
        module_path = os.path.join("modules", db_module.address, "module.py")
        if not os.path.exists(module_path):
            logger.error(f"Module file not found: {module_path}")
            return None

        try:
            module_name = f"modules.{db_module.name}.module"
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, db_module.name, None)
        except Exception as e:
            logger.error(f"Module load error {db_module.name}: {e}")
            return None

    @classmethod
    async def get_module_info(cls, module_name: str, db: Session = None) -> dict:
        module = cls.modules.get(module_name)
        if not module:
            return {"error": "Module not found"}

        try:
            async with asyncio.timeout(15):
                if module.module_type == "local":
                    return cls._get_local_module_info(module)
                return await cls._get_network_module_info(module)
        except TimeoutError:
            logger.error(f"Timeout getting info for {module_name}")
            return {"error": "Request timeout"}
        except Exception as e:
            logger.error(f"Info request error {module_name}: {e}")
            return {"error": str(e)}

    @classmethod
    def _get_local_module_info(cls, module: Module) -> dict:
        if not module.loaded_class:
            return {"error": "Module class not loaded"}

        try:
            instance = module.loaded_class(
                name=module.name,
                module_type="local",
                address=module.address,
                enabled=module.enabled
            )
            return instance.get_info()
        except Exception as e:
            return {"error": str(e)}

    @classmethod
    async def _get_network_module_info(cls, module: Module) -> dict:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{module.address}/getinfo") as response:
                    content = await response.text()
                    return {
                        "status": response.status,
                        "content": cls._parse_module_content(content)
                    }
        except aiohttp.ClientError as e:
            return {"error": str(e)}

    @classmethod
    def _parse_module_content(cls, content: str) -> dict:
        if re.search(r'<html.*?>.*</html>', content, re.DOTALL):
            return {"type": "html", "content": content[:500] + "..."}

        try:
            return {"type": "json", "content": json.loads(content)}
        except json.JSONDecodeError:
            return {"type": "text", "content": content[:500] + "..."}

    @classmethod
    async def _handle_network_response(cls, response, name):
        logger.debug(f"Network response {name}, {response}")


# Функция для проверки, является ли контент HTML
def is_html(content: str) -> bool:
    """Проверка, является ли строка HTML-разметкой."""
    return bool(re.search(r'<html.*?>.*</html>', content, re.DOTALL))
