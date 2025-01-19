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

    def get_info(self):
        """
        Универсальный метод для получения информации о модуле.
        - info_type определяет, какую информацию запрашивать:
        - "basic" для базовой информации
        - "detailed" для детальной информации, специфичной для модуля.
        """
        info = {
            "name": self.name,
            "module_type": self.module_type,
            "address": self.address,
            "enabled": self.enabled
        }
        print(info)
        return info