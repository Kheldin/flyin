from __future__ import annotations
from pydantic import BaseModel, Field
from enum import Enum


class Color(str, Enum):
    BLUE    = "blue"
    RED     = "red"
    YELLOW  = "yellow"
    GREEN   = "green"
    ORANGE  = "orange"
    PURPLE  = "purple"
    CYAN    = "cyan"
    LIME    = "lime"
    BROWN   = "brown"
    MAGENTA = "magenta"
    GOLD    = "gold"


class ZoneType(str, Enum):
    NORMAL     = "normal"
    RESTRICTED = "restricted"
    BLOCKED    = "blocked"
    PRIORITY   = "priority"


class Drone(BaseModel):
    id: int
    position: Hub


class Hub(BaseModel):
    name: str
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    color: Color           = Field(default=Color.BLUE)
    zone_type: ZoneType    = Field(default=ZoneType.NORMAL)
    max_drones: int        = Field(ge=1, default=1)
    start_hub: bool        = Field(default=False)
    end_hub: bool          = Field(default=False)
    drones: list[Drone] | None = Field(default=None)


class Connection(BaseModel):
    hub_1: Hub
    hub_2: Hub
    max_link_capacity: int = Field(ge=1, default=1)


class Map(BaseModel):
    nb_drones: int
    drones: list[Drone]
    connections: list[Connection]
    hubs: list[Hub]


Drone.model_rebuild()
Hub.model_rebuild()