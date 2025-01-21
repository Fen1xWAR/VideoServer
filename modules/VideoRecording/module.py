import base64
import cv2
import os
from datetime import datetime
import numpy as np
from modules.Module import Module
import time
from app.logger import LoggerSingleton  # Импортируем логгер

logger = LoggerSingleton.get_logger()  # Получаем логгер


class VideoRecording(Module):
    recorders = {}  # Словарь для хранения записей по камерам
    output_dir = "videos"
    logs = []  # Список логов

    def __init__(self, name, module_type, address, enabled, output_dir="videos"):
        super().__init__(name, module_type, address, enabled)
        VideoRecording.output_dir = output_dir
        os.makedirs(VideoRecording.output_dir, exist_ok=True)

    def add_log(self, log_message):
        """Метод для добавления логов в систему."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {log_message}"
        VideoRecording.logs.append(log_entry)
        logger.info(log_entry)  # Логирование добавленных сообщений

    @staticmethod
    def _initialize_writer(camera_id, frame):
        """Инициализация нового файла для записи для указанной камеры."""
        now = datetime.now()
        camera_dir = os.path.join(VideoRecording.output_dir, str(camera_id))
        os.makedirs(camera_dir, exist_ok=True)

        filename = f"{camera_id}_{now.strftime('%Y%m%d_%H%M%S')}.avi"
        video_path = os.path.join(camera_dir, filename)

        height, width, _ = frame.shape
        frame_size = (width, height)

        writer = cv2.VideoWriter(
            video_path,
            cv2.VideoWriter_fourcc(*"XVID"),
            30,  # Установленная частота кадров
            frame_size,
        )
        VideoRecording.recorders[camera_id] = {
            "writer": writer,
            "video_path": video_path,
            "last_frame_time": None,
        }

        # Логирование
        VideoRecording.add_log(f"Запись для камеры {camera_id} начата, сохраняется в {video_path}")

    @staticmethod
    def _finalize_writer(camera_id):
        """Завершение записи для указанной камеры."""
        if camera_id in VideoRecording.recorders:
            recorder = VideoRecording.recorders[camera_id]
            if recorder["writer"]:
                recorder["writer"].release()
            del VideoRecording.recorders[camera_id]

            # Логирование
            VideoRecording.add_log(f"Запись для камеры {camera_id} завершена, файл сохранен по пути {recorder['video_path']}")

    def proceed(self, data: base64):
        """Обрабатывает кадры для указанной камеры и сохраняет их в соответствующий видеофайл."""
        frame64_bytes = data.get("frame_bytes")
        frame_bytes = base64.b64decode(frame64_bytes)
        camera_id = data.get("camera_name")

        try:
            frame = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
            if frame is None:
                VideoRecording.add_log(f"[{camera_id}] Неверные данные кадра, пропуск...")  # Логирование ошибки
                return

            if camera_id not in VideoRecording.recorders:
                VideoRecording._initialize_writer(camera_id, frame)

            recorder = VideoRecording.recorders[camera_id]
            current_time = time.time()

            if recorder["last_frame_time"] is None:
                recorder["last_frame_time"] = current_time
            else:
                elapsed_time = current_time - recorder["last_frame_time"]
                recorder["last_frame_time"] = current_time
                num_repeats = max(1, int(30 * elapsed_time))  # 30 FPS
                for _ in range(num_repeats):
                    recorder["writer"].write(frame)
        except Exception as e:
            VideoRecording.add_log(f"[{camera_id}] Ошибка при записи видео: {e}")  # Логирование ошибки

    def finalize(self):
        """Завершает запись для всех камер."""
        for camera_id in list(VideoRecording.recorders.keys()):
            VideoRecording._finalize_writer(camera_id)

    def get_detailed_info(self):
        """Переопределение для предоставления детализированной информации о модуле записи видео."""
        files = []
        for camera_id, recorder in VideoRecording.recorders.items():
            files.append(recorder["video_path"])

        return {
            "recorded_files": files,
            "logs": VideoRecording.logs
        }

    def get_info(self):
        """Метод для получения информации о модуле."""
        info = {"basic": super().get_info(), "detailed": self.get_detailed_info()}
        logger.info(f"Информация о модуле: {info}")  # Логирование информации о модуле
        return self.generate_html_report(info)

    def generate_html_report(self, info):
        """Метод для создания HTML-отчета с данными из метода get_info"""
        # Получаем путь к директории, где находится текущий скрипт
        script_dir = os.path.dirname(os.path.abspath(__file__))  # Абсолютный путь к текущей директории
        template_path = os.path.join(script_dir, "template.html")  # Полный путь к файлу шаблона

        # Загружаем файл
        try:
            with open(template_path, "r", encoding="utf-8-sig") as file:
                template = file.read()
        except Exception as e:
            logger.error(f"Ошибка при чтении шаблона: {e}")
            return ""

        # Заполняем шаблон данными
        template = template.replace("{{module_name}}", info['basic']["name"])
        template = template.replace("{{module_type}}", info['basic']["module_type"])
        template = template.replace("{{address}}", info['basic']["address"])
        template = template.replace("{{enabled}}", str(info['basic']["enabled"]))

        # Заполняем списки файлов и логов
        recorded_files = "<li>" + "</li><li>".join(info["detailed"]["recorded_files"]) + "</li>"
        logs = "<li>" + "</li><li>".join(info["detailed"]["logs"]) + "</li>"

        template = template.replace("{{recorded_files}}", recorded_files)
        template = template.replace("{{logs}}", logs)

        logger.info(f"Сгенерирован HTML отчет для модуля {info['basic']['name']}")
        return template
