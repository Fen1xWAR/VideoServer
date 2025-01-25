import asyncio
import json
import time
from uuid import UUID
from datetime import datetime

import jwt

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCIceCandidate
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from av import VideoFrame
from app.config import Config
from app.logger import LoggerSingleton
from app.models.table_models import Camera
from app.services.database_service import get_db
from app.services.video_service import camera_streams

router = APIRouter()
logger = LoggerSingleton.get_logger()

class CameraVideoTrack(VideoStreamTrack):
    """Класс для передачи кадров через WebRTC с исправлениями"""

    def __init__(self, camera_id: UUID, camera_name: str):
        super().__init__()
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.last_frame_time = datetime.now()

    async def recv(self) -> VideoFrame:
        while True:
            try:
                # Получаем последний кадр из потока
                stream_data = camera_streams.get(self.camera_id)
                if not stream_data:
                    await asyncio.sleep(0.1)
                    continue

                frame = stream_data.get("frame")
                if frame is None:
                    await asyncio.sleep(0.05)
                    continue


                # Конвертация формата для WebRTC
                video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
                video_frame = video_frame.reformat(
                    format="yuv420p",
                    width=video_frame.width,
                    height=video_frame.height
                )
                video_frame.pts = int(time.monotonic() * 1000000)
                video_frame.time_base = "1/1000000"

                return video_frame

            except Exception as e:
                logger.error(f"Ошибка генерации кадра: {e}")
                await asyncio.sleep(0.1)


# WebSocket endpoint для видеопотока с конкретной камеры
@router.websocket("/ws/video/{camera_id}")
async def video_stream(websocket: WebSocket, camera_id: str):
    # Принимаем WebSocket соединение
    await websocket.accept()

    # Инициализация переменных для WebRTC соединения и БД сессии
    pc = None  # RTCPeerConnection объект
    db_session = None  # Сессия подключения к базе данных

    try:
        # Этап 1: Аутентификация пользователя
        # Получаем и парсим сообщение с токеном
        data = await websocket.receive_text()
        message = json.loads(data)
        token = message.get("token")

        if not token:
            raise ValueError("Отсуствует токен авторизации")

        # Валидируем JWT токен
        try:
            payload = jwt.decode(
                token,
                Config.settings().SECRET_KEY,
                algorithms=[Config.settings().ALGORITHM]
            )
            # Формируем объект пользователя из payload токена
            user = {"username": payload["sub"], "role": payload["role"]}
            logger.info(f"Пользователь {user['username']} подключился")
        except Exception as e:
            raise ValueError(f"Токен недействителен: {str(e)}")

        db_session = get_db()
        camera_uuid = UUID(camera_id)
        camera = db_session.query(Camera).filter(Camera.id == camera_uuid).first()

        # Этап 2: Настройка WebRTC соединения
        pc = RTCPeerConnection()  # Создаем новое WebRTC соединение

        # Создаем и добавляем видеотрек для указанной камеры
        video_track = CameraVideoTrack(camera_uuid, camera.name)
        pc.addTrack(video_track)  # Добавляем трек в соединение

        # Создаем SDP offer для инициализации соединения
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)  # Устанавливаем локальное описание

        # Модифицируем SDP для режима "только отправка" (sendonly)
        modified_sdp = pc.localDescription.sdp.replace(
            "a=sendrecv",  # Стандартный режим отправки/приема
            "a=sendonly"  # Меняем на режим только отправки
        )

        # Отправляем модифицированный offer клиенту
        await websocket.send_text(json.dumps({
            "sdp": modified_sdp,
            "type": "offer"
        }))

        # Этап 3: Обработка ICE-кандидатов
        # Коллбэк для обработки генерации ICE-кандидатов
        @pc.on("icecandidate")
        async def on_ice_candidate(candidate):
            try:
                if candidate and candidate.candidate:
                    # Формируем данные кандидата для отправки клиенту
                    ice_data = {
                        "candidate": candidate.candidate,
                        "sdpMid": candidate.sdpMid,
                        "sdpMLineIndex": candidate.sdpMLineIndex
                    }
                    await websocket.send_text(json.dumps({
                        "type": "candidate",
                        "data": ice_data
                    }))
            except Exception as e:
                logger.error(f"Ошибка ICE кандидатов: {str(e)}")

        # Этап 4: Обработка клиентских ответов
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Обработка SDP answer от клиента
            if message.get("sdp"):
                answer = RTCSessionDescription(
                    sdp=message["sdp"],
                    type="answer"
                )
                await pc.setRemoteDescription(answer)  # Устанавливаем удаленное описание
                logger.info("SDP ответ получен")

            # Обработка ICE кандидатов от клиента
            elif message.get("candidate"):
                candidate = message["candidate"]
                await pc.addIceCandidate(
                    RTCIceCandidate(
                        candidate=candidate["candidate"],
                        sdpMid=candidate["sdpMid"],
                        sdpMLineIndex=candidate["sdpMLineIndex"]
                    )
                )
                logger.info("ICE кандидат добавлен")

    # Обработка разрыва соединения
    except WebSocketDisconnect:
        logger.info(f"Пользователь {user['username']} отключился от камеры {camera_id}")

    # Обработка общих ошибок
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await websocket.send_text(json.dumps({"ошибка": str(e)}))

    # ФинализациЯ: очистка ресурсов
    finally:
        try:
            if pc:
                await pc.close()  # Закрываем WebRTC соединение
            if db_session:
                db_session.close()  # Закрываем сессию с БД
        except Exception as e:
            logger.error(f"Ошибка очистки: {str(e)}")

        logger.info(f"Вебсокет закрыт для камеры {camera_id}")