from dataclasses import dataclass
from typing import Optional, Any
from enum import Enum, auto


class Zone(Enum):
    NORMAL = auto()
    RESTRICTED = auto()
    PRIORITY = auto()
    BLOCKED = auto()

    @staticmethod
    def get_zone(zone_str: str) -> Optional["Zone"]:
        match zone_str:
            case "normal":
                return Zone.NORMAL
            case "restricted":
                return Zone.RESTRICTED
            case "priority":
                return Zone.PRIORITY
            case "blocked":
                return Zone.BLOCKED
            case _:
                return None


@dataclass(frozen=True)
class Metadata:
    zone: Optional[Zone]
    color: Optional[str]
    max_link_capacity: Optional[int]
    max_drones: Optional[int]


@dataclass(frozen=True)
class Node:
    name: str
    x: int
    y: int
    metadata: Metadata


@dataclass(frozen=True)
class Connection:
    node1: Node
    node2: Node
    metadata: Metadata

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Connection):
            return NotImplemented
        return frozenset([self.node1, self.node2]) == frozenset(
            [other.node1, other.node2]
        )

    def __hash__(self) -> int:
        return hash(frozenset([self.node1, self.node2]))


@dataclass
class Map:
    nb_drones: int
    start_hub: Node
    end_hub: Node
    hubs: list[Node]
    connections: set[Connection]
