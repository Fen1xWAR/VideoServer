from pydantic import BaseModel


class CameraModel(BaseModel):
    name: str
    url: str
    active: bool