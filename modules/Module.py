import base64


class Module:
    def __init__(self, name, module_type, address=None, enabled=False, loaded_class = None):
        """Модуль может быть сетевым или локальным"""
        self.name = name
        self.module_type = module_type  # "network" или "local"
        self.address = address  # URL для сетевых модулей или путь к файлу для локальных
        self.enabled = enabled
        self.loaded_class = loaded_class

    def proceed(self, data : base64):
        """Обработка данных"""
        raise NotImplementedError("Each module must implement the 'proceed' function.")