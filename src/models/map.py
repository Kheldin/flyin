"""Data models representing structural components of the map network.

Provides data classes, immutable structures, and enumeration profiles tracking
individual node coordinates, links, restrictions, and core layouts.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional


class Zone(Enum):
    """Enumerate spatial operation profiles and navigation constraints."""

    NORMAL = auto()
    RESTRICTED = auto()
    PRIORITY = auto()
    BLOCKED = auto()

    @staticmethod
    def get_zone(zone_str: str) -> Optional["Zone"]:
        """Parse raw string keywords into structured Zone instances.

        Args:
            zone_str: Categorical context tag read from input files.

        Returns:
            The matched Zone identifier representation, or None if invalid.
        """
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
    """Encapsulate configuration parameters binding elements together.

    Attributes:
        zone: Dynamic traversal clearance restriction state classification.
        color: Optional styling hex or name parameter for rendering.
        max_link_capacity: Structural transit limits inside paths.
        max_drones: Maximum concurrent items allowed stationed on target.
    """

    zone: Optional[Zone]
    color: Optional[str]
    max_link_capacity: Optional[int]
    max_drones: Optional[int]


@dataclass(frozen=True)
class Node:
    """Represent an immutable geographic focal target node.

    Attributes:
        name: Unique string name assigned to identify this station.
        x: Absolute grid column location index coordinate.
        y: Absolute grid row location index coordinate.
        metadata: Associated capacity and zone restriction configurations.
    """

    name: str
    x: int
    y: int
    metadata: Metadata


@dataclass(frozen=True)
class Connection:
    """Represent a bidirectional linkage track between two target nodes.

    Attributes:
        node1: Primary endpoint boundary node anchorage.
        node2: Secondary endpoint boundary node anchorage.
        metadata: Traversal constraint profiling specifications.
    """

    node1: Node
    node2: Node
    metadata: Metadata

    def __eq__(self, other: Any) -> bool:
        """Evaluate equality symmetrically ignoring relative endpoint sorting.

        Args:
            other: Objective instance matching type criteria to compare.

        Returns:
            True if both collections manage identical node elements.
        """
        if not isinstance(other, Connection):
            return NotImplemented
        return frozenset([self.node1, self.node2]) == frozenset(
            [other.node1, other.node2]
        )

    def __hash__(self) -> int:
        """Compute an order-agnostic hash using structural references.

        Returns:
            An integer hash sequence derived from the underlying frozenset.
        """
        return hash(frozenset([self.node1, self.node2]))


@dataclass
class Map:
    """Container structure storing global map environment parameters.

    Attributes:
        nb_drones: Total baseline volume count of operating actors.
        start_hub: Origin hub reference where items launch.
        end_hub: Final destination target target node reference.
        hubs: Sequential lookup collection housing all global stations.
        connections: Deduplicated set tracking link entities.
    """

    nb_drones: int
    start_hub: Node
    end_hub: Node
    hubs: list[Node]
    connections: set[Connection]
