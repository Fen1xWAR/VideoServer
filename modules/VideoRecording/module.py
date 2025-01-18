import base64
import cv2
import os
from datetime import datetime
import numpy as np
from modules.Module import Module


class VideoRecording(Module):
    recorders = {}  # Словарь для хранения записей по камерам
    output_dir = "videos"
    fps = 30

    def __init__(self, name, module_type, address, enabled, output_dir="videos", fps=30):
        """
        Модуль записи видео с нескольких камер. Сохраняет видеофайлы в один файл на камеру.
        :param output_dir: Папка для сохранения видеофайлов
        :param fps: Частота кадров
        """
        super().__init__(name, module_type, address, enabled)
        VideoRecording.output_dir = output_dir
        VideoRecording.fps = fps
        os.makedirs(VideoRecording.output_dir, exist_ok=True)

    @staticmethod
    def _initialize_writer(camera_id, frame):
        """
        Инициализация нового файла для записи для указанной камеры.
        :param camera_id: Идентификатор камеры
        :param frame: Первый кадр (numpy array) для определения размера видео
        """
        now = datetime.now()
        current_date = now.date()
        camera_dir = os.path.join(VideoRecording.output_dir, str(camera_id))
        os.makedirs(camera_dir, exist_ok=True)

        filename = f"{camera_id}_{current_date}.avi"
        video_path = os.path.join(camera_dir, filename)

        height, width, _ = frame.shape
        frame_size = (width, height)

        writer = cv2.VideoWriter(
            video_path,
            cv2.VideoWriter_fourcc(*"XVID"),
            VideoRecording.fps,
            frame_size,
        )
        VideoRecording.recorders[camera_id] = {
            "writer": writer,
            "video_path": video_path,
        }

        print(f"[{camera_id}] Video file opened: {video_path}")

    @staticmethod
    def _finalize_writer(camera_id):
        """Завершение записи для указанной камеры."""
        if camera_id in VideoRecording.recorders:
            recorder = VideoRecording.recorders[camera_id]
            if recorder["writer"]:
                recorder["writer"].release()
                print(f"[{camera_id}] Video file saved: {recorder['video_path']}")
            del VideoRecording.recorders[camera_id]

    def proceed(self, data: base64):
        print("proceed")
        """
        Обрабатывает кадры для указанной камеры и сохраняет их в соответствующий видеофайл.
        """
        frame64_bytes = data.get("frame_bytes")
        frame_bytes = base64.b64decode(frame64_bytes)
        camera_id = data.get("camera_name")

        try:
            # Декодирование кадра из bytes в numpy array
            frame = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
            if frame is None:
                print(f"[{camera_id}] Invalid frame data, skipping...")
                return

            # Инициализация writer, если его еще нет
            if camera_id not in VideoRecording.recorders:
                VideoRecording._initialize_writer(camera_id, frame)

            # Запись кадра в текущий видеофайл
            writer = VideoRecording.recorders[camera_id]["writer"]
            writer.write(frame)
            print(f"[{camera_id}] Frame written")
        except Exception as e:
            print(f"[{camera_id}] Error in video recording: {e}")

    def finalize(self):
        """Завершает запись для всех камер."""
        for camera_id in list(VideoRecording.recorders.keys()):
            VideoRecording._finalize_writer(camera_id)