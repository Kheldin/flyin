from pydantic import BaseModel, Field
from enum import Enum


class Color(str, Enum):
    BLUE = "blue"
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    ORANGE = "orange"


class ZoneType(str, Enum):
    NORMAL = "normal"
    RESTRICTED = "restricted"
    BLOCKED = "blocked"
    PRIORITY = "priority"


class Zone(BaseModel):
    type: ZoneType = Field(default=ZoneType.NORMAL)


class Hub(BaseModel):
    name: str
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    color: Color = Field(default=Color.BLUE)
    zone: Zone = Field(default=Zone(type=ZoneType.NORMAL))
    max_drones: int = Field(ge=0)
    start_hub: bool = Field(default=False)
    end_hub: bool = Field(default=False)
