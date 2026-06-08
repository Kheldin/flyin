"""Pathfinding engines and simulation orchestration mechanics module.

Provides a space-time A* routing pipeline, multi-agent reservation logs,
and transactional loop advancement steps for autonomous vehicle networks.
"""

from __future__ import annotations

import heapq
import itertools
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from models.map import Connection, Map, Node, Zone

# Type aliases defining coordinates inside the space-time continuum matrix
PathStep = tuple[Node | Connection, int]
Path = list[PathStep]


class PathError(Exception):
    """Raise when graph constraints render route optimization impossible."""

    def __init__(self, *args: object) -> None:
        """Initialize the path exception wrapping base attributes.

        Args:
            *args: Arbitrary arguments forwarded to the exception base.
        """
        super().__init__(*args)


class SimulationState:
    """Manage space-time occupation logs across elements and turns."""

    def __init__(self, start_hub: Node, end_hub: Node, nb_drones: int) -> None:
        """Initialize reservation ledgers and seed starting distributions.

        Args:
            start_hub: Map origin target where actors prepare for launch.
            end_hub: Final destination terminal bounding traversal logic.
            nb_drones: Volume count specifying cumulative actors in scope.
        """
        self.start_hub = start_hub
        self.end_hub = end_hub
        self.nb_drones = nb_drones

        # Imbricated ledgers matching structure: ledger[turn][element] -> IDs
        self.node_reservations: dict[int, dict[Node, list[int]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self.conn_reservations: dict[
            int, dict[Connection, list[int]]
        ] = defaultdict(lambda: defaultdict(list))

        # Station all acting drone references inside the origin node at Turn 0
        self.node_reservations[0][self.start_hub] = list(
            range(1, nb_drones + 1)
        )

    def can_enter_node(self, node: Node, time: int) -> bool:
        """Evaluate clearance metrics of a targeted node at a specific turn.

        Args:
            node: Objective Node instance evaluated for clearance.
            time: Target discrete turn snapshot index.

        Returns:
            True if capacity thresholds accommodate another entry.
        """
        if node == self.end_hub or node == self.start_hub:
            return True
        capacity: int = (
            node.metadata.max_drones if node.metadata.max_drones else 1
        )

        nb_drones_in: int = len(
            self.node_reservations.get(time, {}).get(node, [])
        )
        return nb_drones_in < capacity

    def can_use_connection(self, connection: Connection, time: int) -> bool:
        """Evaluate operational overhead of a path route at a specific turn.

        Args:
            connection: Target directional Link model evaluated for clearance.
            time: Target discrete turn snapshot index.

        Returns:
            True if ongoing transits remain strictly beneath capacity caps.
        """
        capacity: int = (
            connection.metadata.max_link_capacity
            if connection.metadata.max_link_capacity
            else 1
        )
        nb_drones_on: int = len(
            self.conn_reservations.get(time, {}).get(connection, [])
        )
        return nb_drones_on < capacity

    def reserve_node(self, node: Node, time: int, drone_id: int) -> None:
        """Log an exclusive station reservation inside node matrices.

        Args:
            node: Target Node destination receiving the reservation.
            time: Target discrete turn execution index.
            drone_id: Numeric identity code of the reserving actor.
        """
        self.node_reservations[time][node].append(drone_id)

    def reserve_connection(
        self, connection: Connection, time: int, drone_id: int
    ) -> None:
        """Log an exclusive path reservation inside transit matrices.

        Args:
            connection: Target Connection link path tracking allocations.
            time: Target discrete turn execution index.
            drone_id: Numeric identity code of the reserving actor.
        """
        self.conn_reservations[time][connection].append(drone_id)


class PathFinder:
    """Compute optimal non-conflicting profiles across structured maps."""

    def __init__(self, map_data: Map) -> None:
        """Initialize routing structures and compile lookahead tables.

        Args:
            map_data: Complete environment layout data structure.

        Raises:
            PathError: If topological analysis exposes an unsolvable graph.
        """
        self.map = map_data
        self.state = SimulationState(
            map_data.start_hub, map_data.end_hub, map_data.nb_drones
        )
        self.drones_paths: dict[int, Path] = {}
        self.true_dist = self._compute_true_distances()
        if self.true_dist[self.map.start_hub] == -1:
            raise PathError("map is not solvable")

    def route_all_drones(self) -> None:
        """Loop through actor indexes to compile collision-free strategies."""
        for drone_id in range(1, self.map.nb_drones + 1):
            path = self.find_path()
            if path:
                self._reserve_path(drone_id, path)
                self.drones_paths[drone_id] = path
            else:
                print("no path for ", drone_id)

    def _compute_true_distances(self) -> dict[Node, int]:
        """Compute absolute static distance matrices via backward Dijkstra.

        Returns:
            A lookup table mapping Node instances to minimum step lengths.
        """
        distances: dict[Node, int] = {node: -1 for node in self.map.hubs}
        distances[self.map.end_hub] = 0

        counter = itertools.count()
        queue: list[tuple[int, int, Node]] = [
            (0, next(counter), self.map.end_hub)
        ]

        while queue:
            dist, _, current = heapq.heappop(queue)

            if dist > distances[current] or distances[current] == -1:
                continue

            for conn in self.map.connections:
                neighbor = None
                if conn.node1 == current:
                    neighbor = conn.node2
                elif conn.node2 == current:
                    neighbor = conn.node1

                if neighbor:
                    if neighbor.metadata.zone == Zone.BLOCKED:
                        continue

                    new_dist = dist + 1
                    if (
                        distances[neighbor] == -1
                        or new_dist < distances[neighbor]
                    ):
                        distances[neighbor] = new_dist
                        heapq.heappush(
                            queue, (new_dist, next(counter), neighbor)
                        )
        return distances

    def _reserve_path(self, drone_id: int, path: Path) -> None:
        """Commit an optimized trajectory into global state registers.

        Args:
            drone_id: Numeric identity code of the routing actor.
            path: Final sequence of time-stamped elements to lock down.
        """
        for location, time in path:
            if isinstance(location, Node):
                self.state.reserve_node(location, time, drone_id)
            elif isinstance(location, Connection):
                self.state.reserve_connection(location, time, drone_id)

    def _heuristic(self, node: Node) -> int:
        """Provide perfect lookahead estimates using backward distances.

        Args:
            node: Targeted station node evaluated for cost analysis.

        Returns:
            Minimum steps required to transition towards terminus anchor.
        """
        return self.true_dist[node]

    def find_path(self) -> Path:
        """Execute a Space-Time A* search to calculate non-conflicting paths.

        Returns:
            A calculated list of time-stamped spatial movements, or an empty
            list if all branches evaluate to blockages.
        """
        counter: itertools.count[int] = itertools.count()

        # Starting Cost
        start_g = 0.0
        # Estimated cost since the beginning
        start_h = self._heuristic(self.map.start_hub)

        # F Score, Counter value, G Score, Actual Time, Actual Node, Path
        open_set: list[tuple[float, int, float, int, Node, Path]] = [
            (
                start_g + start_h,
                next(counter),
                start_g,
                0,
                self.map.start_hub,
                [],
            )
        ]
        visited: set[tuple[Node, int]] = set()

        while open_set:
            _, _, g_score, current_time, current_node, path = heapq.heappop(
                open_set
            )

            if current_node == self.map.end_hub:
                return path

            state_key = (current_node, current_time)
            if state_key in visited:
                continue
            visited.add(state_key)

            # --- OPTION 1 : Wait in place ---
            next_time = current_time + 1
            if self.state.can_enter_node(current_node, next_time):
                new_path = path + [(current_node, next_time)]
                new_g = g_score + 1.0
                new_f = new_g + self._heuristic(current_node)
                heapq.heappush(
                    open_set,
                    (
                        new_f,
                        next(counter),
                        new_g,
                        next_time,
                        current_node,
                        new_path,
                    ),
                )

            # --- OPTION 2 : Transition towards a neighbor hub ---
            for conn in self.map.connections:
                dest_node = None
                if conn.node1 == current_node:
                    dest_node = conn.node2
                elif conn.node2 == current_node:
                    dest_node = conn.node1

                if dest_node is None:
                    continue
                if dest_node.metadata.zone == Zone.BLOCKED:
                    continue

                # Evaluate movement weight adjustments based on zone metadata
                cost: float = 1.0
                is_restricted = False
                priority_bonus: float = 0.0

                if dest_node.metadata.zone == Zone.RESTRICTED:
                    cost = 2.0
                    is_restricted = True
                elif dest_node.metadata.zone == Zone.PRIORITY:
                    priority_bonus = 0.5

                if is_restricted:
                    arrival_time = current_time + 2
                    can_use_link = self.state.can_use_connection(
                        conn, current_time + 1
                    ) and self.state.can_use_connection(conn, current_time + 2)
                    connection_steps = [
                        (conn, current_time + 1),
                        (conn, current_time + 2),
                    ]
                else:
                    arrival_time = current_time + 1
                    can_use_link = self.state.can_use_connection(
                        conn, current_time + 1
                    )
                    connection_steps = [(conn, current_time + 1)]

                # Enforce link and node constraints simultaneously
                if can_use_link and self.state.can_enter_node(
                    dest_node, arrival_time
                ):
                    new_path = (
                        path + connection_steps + [(dest_node, arrival_time)]
                    )
                    new_g = g_score + cost
                    new_f = new_g + self._heuristic(dest_node) - priority_bonus
                    heapq.heappush(
                        open_set,
                        (
                            new_f,
                            next(counter),
                            new_g,
                            arrival_time,
                            dest_node,
                            new_path,
                        ),
                    )

        return []


class Simulator:
    """Simulation orchestrator coordinating state advancements and logs."""

    def __init__(self, map_data: Map) -> None:
        """Initialize pipelines, generate schedules, and audit capabilities.

        Args:
            map_data: Main parsed model schema tracking map details.
        """
        self.map = map_data
        self.total = self.map.nb_drones
        self.delivered = 0
        self.failed = 0
        self.turn = 0

        self.path_finder = PathFinder(self.map)
        self.path_finder.route_all_drones()

        # Compile time-to-location mappings to achieve O(1) performance lookups
        self.drone_schedules: Dict[int, Dict[int, Node | Connection]] = {}
        for drone_id, path in self.path_finder.drones_paths.items():
            self.drone_schedules[drone_id] = {time: loc for loc, time in path}

        # Track unrouted items as immediate execution exceptions
        self.failed_drones: Set[int] = {
            drone_id
            for drone_id in range(1, self.total + 1)
            if drone_id not in self.drone_schedules
        }
        self.failed = len(self.failed_drones)

        self.current_locations: Dict[int, Node | Connection] = {
            i: self.map.start_hub for i in range(1, self.total + 1)
        }
        self.is_delivered: Set[int] = set()

        self.drone_positions: Dict[int, Node | Connection] = dict(
            self.current_locations
        )
        self.in_transit: List[Dict[str, object]] = []

        self.update_runtime_state()

    def step(self) -> Tuple[bool, List[str]]:
        """Advance the environment clock by one discrete turn slice.

        Returns:
            A tuple tracking completion flags and output move log string items.
        """
        if self.delivered + self.failed >= self.total:
            return True, []

        moves: List[str] = []

        for drone_id in range(1, self.total + 1):
            if (
                drone_id in self.is_delivered
                or drone_id in self.failed_drones
            ):
                continue

            schedule = self.drone_schedules.get(drone_id, {})
            current_step_loc = schedule.get(self.turn)

            if current_step_loc is None:
                continue

            if current_step_loc != self.current_locations[drone_id]:
                if isinstance(current_step_loc, Node):
                    moves.append(f"D{drone_id}-{current_step_loc.name}")

                    if current_step_loc == self.map.end_hub:
                        self.delivered += 1
                        self.is_delivered.add(drone_id)

                elif isinstance(current_step_loc, Connection):
                    prev_loc = self.current_locations[drone_id]
                    if isinstance(prev_loc, Node):
                        frm = prev_loc.name
                        to = (
                            current_step_loc.node2.name
                            if current_step_loc.node1 == prev_loc
                            else current_step_loc.node1.name
                        )
                        moves.append(f"D{drone_id}-{frm}-{to}")

                self.current_locations[drone_id] = current_step_loc

        self.turn += 1
        self.update_runtime_state()
        is_finished = (self.delivered + self.failed) >= self.total

        return is_finished, moves

    def update_runtime_state(self) -> None:
        """Synchronize runtime cache variables with the current time step."""
        self.drone_positions = {}
        self.in_transit = []

        for drone_id in range(1, self.total + 1):
            schedule = self.drone_schedules.get(drone_id, {})
            loc = schedule.get(self.turn)
            if loc is None:
                loc = self.current_locations.get(
                    drone_id, self.map.start_hub
                )

            self.drone_positions[drone_id] = loc

            if isinstance(loc, Connection):
                conn_tuple = (loc.node1.name, loc.node2.name)
                self.in_transit.append(
                    {
                        "drone_id": drone_id,
                        "conn": conn_tuple,
                    }
                )
