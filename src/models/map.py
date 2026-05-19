from __future__ import annotations
from pydantic import BaseModel, Field
from enum import Enum


class Color(str, Enum):
    BLUE    = "blue"
    RED     = "red"
    DARKRED = "darkred"
    YELLOW  = "yellow"
    GREEN   = "green"
    ORANGE  = "orange"
    PURPLE  = "purple"
    CYAN    = "cyan"
    LIME    = "lime"
    BROWN   = "brown"
    MAGENTA = "magenta"
    GOLD    = "gold"
    MAROON  = "maroon"
    CRIMSON = "crimson"
    VIOLET  = "violet"
    BLACK   = "black"
    RAINBOW = "rainbow"


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
    x: int
    y: int
    color: Color    = Field(default=Color.RED)
    zone: ZoneType  = Field(default=ZoneType.NORMAL)
    max_drones: int = Field(ge=1, default=1)
    start_hub: bool = Field(default=False)
    end_hub: bool   = Field(default=False)
    drones: list[Drone] | None = Field(default=None)
    line: int


class Connection(BaseModel):
    hub_1: Hub | str
    hub_2: Hub | str
    max_link_capacity: int = Field(ge=1, default=1)
    line: int


class Map(BaseModel):
    nb_drones: int
    drones: list[Drone]
    connections: list[Connection]
    hubs: list[Hub]


Drone.model_rebuild()
Hub.model_rebuild()