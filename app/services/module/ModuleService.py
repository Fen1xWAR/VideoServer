import importlib
import os
import aiohttp

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
        print('process data')
        """Обработать данные всеми активными модулями (асинхронно)"""
        results = []
        for module in ModuleManager.modules.values():
            if module.enabled:
                if module.module_type == "network":
                    # Асинхронная обработка сетевых модулей
                    result = await ModuleManager._process_network(module, data)
                else:
                    # Синхронная обработка локальных модулей
                    result = ModuleManager._process_local(module, data)
                results.append(result)
        return results

    @staticmethod
    async def _process_network(module, data):
        """Обработка данных для сетевого модуля (асинхронно)"""
        try:
            async with aiohttp.ClientSession() as session:
                if isinstance(data, bytes):
                    # Отправка как бинарных данных (например, изображение)
                    async with session.post(module.address + "/proceed", data=data) as response:
                        return await ModuleManager._handle_response(response, module.name)
                else:
                    # Если это не бинарные данные, отправляем как JSON
                    async with session.post(module.address, json=data) as response:
                        return await ModuleManager._handle_response(response, module.name)
        except aiohttp.ClientError as e:
            return f"Error processing data for {module.name} at {module.address}: {e}"

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
            print(cls)
            if cls:
                # Создаём экземпляр класса и вызываем метод proceed
                instance = cls(name=module.name, module_type="local", address=module.address, enabled=module.enabled)
                result = instance.proceed(data)
                return result
            else:
                print( f"Local module {module.name} does not have a loaded class.")
        except Exception as e:
            print(e)
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
                loaded_class = cls
            )

        print("Модули инициализированы")
        print(ModuleManager.modules.values())

    @staticmethod
    def get_all_modules():
        """Получить все модули из базы данных"""
        db = get_db()
        return db.query(database_service.Module).all()  # Возвращаем все модули из базы данных
