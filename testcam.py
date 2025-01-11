import cv2
import subprocess
import mss
import numpy as np

def create_virtual_rtsp_stream():
    # Настройки для захвата экрана
    screen_width = 1920  # Ширина экрана
    screen_height = 1080  # Высота экрана

    # Настройки для передачи через FFmpeg
    rtsp_url = "rtsp://127.0.0.1:8554/test"
    ffmpeg_command = [
        'ffmpeg',
        '-re',  # Снимать с реальной частотой кадров
        '-f', 'rawvideo',
        '-vcodec', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-s', f'{screen_width}x{screen_height}',  # Разрешение экрана
        '-r', '25',  # Частота кадров
        '-i', '-',  # Входной поток через stdin
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-f', 'rtsp',
        rtsp_url
    ]

    # Запускаем FFmpeg
    process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE)

    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Выбираем первый монитор (основной экран)

        while True:
            # Захват экрана
            screenshot = sct.grab(monitor)
            frame = np.array(screenshot)

            # Преобразование цвета (с RGB на BGR)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            # Отправляем кадр в FFmpeg через stdin
            process.stdin.write(frame.tobytes())

    process.stdin.close()
    process.wait()

create_virtual_rtsp_stream()
