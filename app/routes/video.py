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
                # logger.debug(f"{video_frame.width} * {video_frame.height}")
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


@router.websocket("/ws/video/{camera_id}")
async def websocket_video_stream(websocket: WebSocket, camera_id: str):
    await websocket.accept()
    pc = None
    db_session = None

    try:
        # Аутентификация
        data = await websocket.receive_text()
        message = json.loads(data)
        token = message.get("token")

        if not token:
            raise ValueError("Authentication token missing")

        # Валидация токена
        try:
            payload = jwt.decode(
                token,
                Config.settings().SECRET_KEY,
                algorithms=[Config.settings().ALGORITHM]
            )
            user = {"username": payload["sub"], "role": payload["role"]}
            logger.info(f"User {user['username']} connected")
        except Exception as e:
            raise ValueError(f"Invalid token: {str(e)}")

        # Проверка камеры
        db_session = get_db()
        camera_uuid = UUID(camera_id)
        camera = db_session.query(Camera).filter(Camera.id == camera_uuid).first()



        # WebRTC Configuration
        pc = RTCPeerConnection()

        # Добавляем видеотрек
        video_track = CameraVideoTrack(camera_uuid,camera.name)
        pc.addTrack(video_track)

        # SDP Negotiation
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        # Модифицируем SDP для sendonly режима
        modified_sdp = pc.localDescription.sdp.replace(
            "a=sendrecv",
            "a=sendonly"
        )

        await websocket.send_text(json.dumps({
            "sdp": modified_sdp,
            "type": "offer"
        }))

        # Измененный обработчик ICE-кандидатов
        @pc.on("icecandidate")
        async def on_ice_candidate(candidate):
            try:
                if candidate and candidate.candidate:
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
                logger.error(f"ICE candidate error: {str(e)}")

        # Обработка ответа от клиента
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("sdp"):
                answer = RTCSessionDescription(
                    sdp=message["sdp"],
                    type="answer"
                )
                await pc.setRemoteDescription(answer)
                logger.info("SDP answer received and processed")

            elif message.get("candidate"):
                candidate = message["candidate"]
                await pc.addIceCandidate(
                    RTCIceCandidate(
                        candidate=candidate["candidate"],
                        sdpMid=candidate["sdpMid"],
                        sdpMLineIndex=candidate["sdpMLineIndex"]
                    )
                )
                logger.info("ICE candidate added")

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from camera {camera_id}")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await websocket.send_text(json.dumps({"error": str(e)}))
    finally:
        try:
            if pc:
                await pc.close()
            if db_session:
                db_session.close()
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
        logger.info(f"WebSocket closed for camera {camera_id}")