import asyncio
import importlib
import os
import re

import aiohttp
from sqlalchemy.orm import Session

from app.services import database_service
from app.services.database_service import get_db
from modules.Module import Module


class ModuleManager:
    modules = {}  # Словарь всех модулей, ключ — имя модуля, значение — экземпляр модуля
    _instance = None  # Экземпляр Singleton

    def __new__(cls, *args, **kwargs):
        """Создаёт единственный экземпляр класса (Singleton)"""
        if cls._instance is None:
            cls._instance = super(ModuleManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    @staticmethod
    def add_module(name, module_type, loaded_class, address=None, enabled=False):
        """Добавление модуля в систему"""
        # Проверяем, существует ли уже экземпляр модуля с таким именем
        if name not in ModuleManager.modules:
            module = Module(name, module_type, address, enabled, loaded_class)
            ModuleManager.modules[name] = module

    @staticmethod
    def enable_module(module_name):
        """Включить модуль по имени"""
        return ModuleManager._toggle_module(module_name, enabled=True)

    @staticmethod
    def disable_module(module_name):
        """Выключить модуль по имени"""
        return ModuleManager._toggle_module(module_name, enabled=False)

    @staticmethod
    def _toggle_module(module_name, enabled):
        """Включение/выключение модуля"""
        if module_name in ModuleManager.modules:
            module = ModuleManager.modules[module_name]
            module.enabled = enabled
            return f"Module {module_name} {'enabled' if enabled else 'disabled'}."
        return f"Module {module_name} not found."

    @staticmethod
    def get_status(module_name):
        """Получить статус модуля по имени"""
        if module_name in ModuleManager.modules:
            module = ModuleManager.modules[module_name]
            return f"Module {module.name} is {'enabled' if module.enabled else 'disabled'}."
        return f"Module {module_name} not found."

    @staticmethod
    async def process_data(data):
        """Обработать данные всеми активными модулями (асинхронно)"""
        results = []
        for module in ModuleManager.modules.values():
            if module.enabled:
                try:
                    if module.module_type == "network":
                        # Асинхронная обработка сетевых модулей
                        result = await ModuleManager._process_network(module, data)
                    else:
                        # Синхронная обработка локальных модулей
                        result = ModuleManager._process_local(module, data)
                    results.append(result)
                except GeneratorExit:
                    # Игнорируем завершение сопрограммы
                    continue
                except Exception as e:
                    # Логируем или обрабатываем другие ошибки
                    print(f"Error processing module {module}: {e}")
        return results

    @staticmethod
    async def _process_network(module, data):
        """Обработка данных для сетевого модуля (асинхронно)"""
        try:
            async with aiohttp.ClientSession() as session:
                # Отправка данных как JSON
                async with session.post(module.address + "/proceed", json=data) as response:
                    # Проверка успешности ответа
                    response.raise_for_status()  # Поднимет исключение для кода ответа >= 400
                    return await ModuleManager._handle_response(response, module.name)

        except aiohttp.ClientError as e:
            # Общая ошибка при сетевых запросах
            return f"Network error processing data for {module.name} at {module.address}: {e}"
        except aiohttp.http_exceptions.HttpProcessingError as e:
            # Ошибка при обработке HTTP запроса (например, ошибки статуса)
            return f"HTTP error processing data for {module.name} at {module.address}: {e}"
        except asyncio.TimeoutError:
            # Обработка тайм-аутов
            return f"Timeout error processing data for {module.name} at {module.address}"
        except Exception as e:
            # Обработка других непредвиденных ошибок
            return f"Unexpected error processing data for {module.name} at {module.address}: {e}"

    @staticmethod
    async def _handle_response(response, module_name):
        """Обработка ответа от сервера"""
        if response.status == 200:
            return await response.json()  # Ответ от сервера
        return f"Error: Status code {response.status} received from {module_name}"

    @staticmethod
    def _process_local(module, data):
        """Обработка данных для локального модуля"""
        try:
            # Используем уже загруженный класс локального модуля
            cls = module.loaded_class
            if cls:
                # Создаём экземпляр класса и вызываем метод proceed
                instance = cls(name=module.name, module_type="local", address=module.address, enabled=module.enabled)
                result = instance.proceed(data)
                return result
            else:
                print(f"Local module {module.name} does not have a loaded class.")
        except Exception as e:
            return f"Error processing data for {module.name}: {e}"

    @staticmethod
    def initialize_modules():
        """Инициализация модулей из базы данных"""
        cls = None
        modules_from_db = ModuleManager.get_all_modules()  # Получаем все модули из БД
        for module in modules_from_db:
            # Если модуль локальный, загружаем его
            if module.module_type == "local":
                module_path = os.path.join("modules", module.address, "module.py")
                if os.path.exists(module_path):
                    module_name = f"modules.{module.name}.module"
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    loaded_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(loaded_module)

                    # Используем имя класса из базы данных
                    class_name = module.name  # Имя класса из базы данных
                    cls = getattr(loaded_module, class_name, None)
                    if cls is None:
                        raise AttributeError(f"Class {class_name} not found in {module_path}")
                    # Сохраняем класс в модуле для дальнейшего использования

            # Добавляем модуль в систему
            ModuleManager.add_module(
                name=module.name,
                module_type=module.module_type,
                address=module.address,
                enabled=module.enabled,
                loaded_class=cls
            )

        print("Модули инициализированы")
        print(ModuleManager.modules.values())

    @staticmethod
    def get_all_modules():
        """Получить все модули из базы данных"""
        db = get_db()
        return db.query(database_service.Module).all()  # Возвращаем все модули из базы данных

    @staticmethod
    async def get_module_info(module_name: str, db: Session = None):
        """Получить информацию о модуле (метод get_info)"""
        if module_name in ModuleManager.modules:
            module = ModuleManager.modules[module_name]
            if module.module_type == "local" and module.loaded_class:
                # Если это локальный модуль, вызовем метод get_info
                try:
                    instance = module.loaded_class(name=module.name, module_type="local", address=module.address,
                                                   enabled=module.enabled)
                    return instance.get_info()  # Предполагаем, что метод get_info() существует в классе
                except Exception as e:
                    return f"Error getting info for {module.name}: {e}"
            elif module.module_type == "network":
                try:
                    # Асинхронный запрос для получения контента с URL
                    async def fetch_module_content(url: str):
                        async with aiohttp.ClientSession() as session:
                            async with session.get(url) as response:
                                return await response.text()

                    # Если модуль сетевой, получаем URL для подключения
                    module_url = module.address
                    html_content = await fetch_module_content(f"{module_url}/getinfo")  # Теперь используем await

                    # Возвращаем HTML или JSON в зависимости от содержания
                    if is_html(html_content):
                        return html_content
                    else:
                        return {"content": html_content}
                except Exception as e:
                    return f"Error connecting to the network module: {str(e)}"
            else:
                return f"Module {module_name} is not a local or network module."
        return f"Module {module_name} not found."


# Функция для проверки, является ли контент HTML
def is_html(content: str) -> bool:
    """Проверка, является ли строка HTML-разметкой."""
    return bool(re.search(r'<html.*?>.*</html>', content, re.DOTALL))
