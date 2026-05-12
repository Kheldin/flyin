from pydantic import BaseModel
from models.hub import Hub

class Drone(BaseModel):
    id: int
    position: Hub