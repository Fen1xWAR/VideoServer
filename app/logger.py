import logging
import os
from datetime import datetime
import sys


class LoggerSingleton:
    _logger = None

    @classmethod
    def get_logger(cls):
        """Получение экземпляра логгера с использованием паттерна Singleton."""
        if cls._logger is None:
            cls._logger = cls._setup_logger()
        return cls._logger

    @staticmethod
    def _setup_logger():
        """Настройка логгера."""
        # Создаём папку logs, если она не существует
        if not os.path.exists('logs'):
            os.makedirs('logs')

        # Получаем текущую дату для имени файла
        log_file = os.path.join('logs', datetime.now().strftime('%Y-%m-%d') + '_app.log')

        # Настройка логгера
        logger = logging.getLogger('app_logger')
        logger.setLevel(logging.DEBUG)

        # Формат логирования
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Обработчик для записи логов в файл (с кодировкой UTF-8)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)

        # Обработчик для вывода логов в консоль (с кодировкой UTF-8)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        # Если на Windows, можем использовать sys.stdout для установки правильной кодировки

        if sys.stdout.encoding != 'UTF-8':
            console_handler.setStream(sys.stdout)

        # Добавляем обработчики в логгер
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger
