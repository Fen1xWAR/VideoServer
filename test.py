import asyncio
from app.services.video_service import send_frame

async def test_send_frame():
    """Тестирует функцию send_frame с примером изображения."""
    # Загрузка тестового изображения
    try:
        with open("images-3.jpeg", "rb") as f:
            frame_bytes = f.read()
    except FileNotFoundError:
        print("Файл images-3.jpeg не найден. Убедитесь, что он находится в том же каталоге, что и этот скрипт.")
        return

    # Отправка кадра на сервер
    response_bytes = await send_frame(frame_bytes)

    # Проверка: получен ли корректный ответ
    if response_bytes == frame_bytes:
        print("Ошибка: сервер вернул оригинальный кадр вместо обработанного изображения.")
    else:
        print("Успех: сервер вернул обработанное изображение.")

        # Сохранение результата для проверки
        with open("processed_image.jpeg", "wb") as output_file:
            output_file.write(response_bytes)
        print("Обработанное изображение сохранено как processed_image.jpeg")

# Запуск теста
if __name__ == "__main__":
    asyncio.run(test_send_frame())
