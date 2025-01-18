import cv2
import base64
import os
import unittest
import time

from modules.VideoRecording.module import VideoRecording


class TestVideoRecording(unittest.TestCase):

    def setUp(self):
        # Перед каждым тестом создаём новый объект VideoRecording
        self.module = VideoRecording(
            name="test_module",
            module_type="test_type",
            address="test_address",
            enabled=True,
            output_dir="test_videos",
            fps=30,
        )
        # Удаляем папку, если она существует, чтобы тест всегда был чистым
        if os.path.exists("test_videos"):
            for root, dirs, files in os.walk("test_videos", topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))

    def test_video_recording(self):
        # Открываем камеру (по умолчанию будет использоваться первая камера)
        cap = cv2.VideoCapture(0)
        self.assertTrue(cap.isOpened(), "Не удалось открыть камеру")

        camera_id = "camera_1"
        frame_count = 0
        max_frames = 30 * 30  # 30 секунд по 30 кадров в секунду (900 кадров)

        start_time = time.time()

        # Захватываем кадры в течение 30 секунд
        while frame_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            # Преобразуем кадр в base64 для передачи в метод proceed
            _, frame_bytes = cv2.imencode(".jpg", frame)
            frame64_bytes = base64.b64encode(frame_bytes).decode("utf-8")

            # Отправляем кадр в обработку
            data = {"frame_bytes": frame64_bytes, "camera_name": camera_id}
            self.module.proceed(data)

            frame_count += 1

        # Закрываем камеру
        cap.release()

        # Проверяем, что видеофайл был создан
        video_dir = os.path.join("test_videos", camera_id)
        self.assertTrue(os.path.exists(video_dir), "Директория с видео не была создана")

        # Получаем список файлов в директории
        video_files = os.listdir(video_dir)
        self.assertGreater(len(video_files), 0, "Видео файлы не были созданы")

        # Ожидаем, что файл видео будет в формате .avi
        video_file = video_files[0]
        self.assertTrue(video_file.endswith(".avi"), f"Ожидался файл с расширением .avi, но получен {video_file}")

        # Завершаем запись
        self.module.finalize()

        # Проверяем, что файл был сохранен
        video_path = os.path.join(video_dir, video_file)
        self.assertTrue(os.path.exists(video_path), "Видео файл не был сохранен")

        # Проверяем продолжительность видео
        video_capture = cv2.VideoCapture(video_path)
        fps = video_capture.get(cv2.CAP_PROP_FPS)
        frame_count = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps
        self.assertAlmostEqual(duration, 30, delta=1, msg="Длительность видео не соответствует 30 секундами.")
    #
    # def tearDown(self):
    #     # Удаляем все файлы и папки, чтобы тесты не влияли друг на друга
    #     if os.path.exists("test_videos"):
    #         for root, dirs, files in os.walk("test_videos", topdown=False):
    #             for file in files:
    #                 os.remove(os.path.join(root, file))
    #             for dir in dirs:
    #                 os.rmdir(os.path.join(root, dir))


if __name__ == "__main__":
    unittest.main()
