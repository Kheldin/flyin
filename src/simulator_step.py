from __future__ import annotations
from collections import defaultdict
import heapq
import itertools
from typing import Dict, List, Tuple, TypeAlias, Set

# Adjust import based on your project structure (fly_in.map_types vs models.map)
from models.map import Node, Connection, Zone, Map

PathStep: TypeAlias = tuple[Node | Connection, int]
Path: TypeAlias = list[PathStep]


class PathError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class SimulationState:
    def __init__(self, start_hub: Node, end_hub: Node, nb_drones: int) -> None:
        self.start_hub = start_hub
        self.end_hub = end_hub
        self.nb_drones = nb_drones

        self.node_reservations: dict[int, dict[Node, list[int]]] = \
            defaultdict(lambda: defaultdict(list))
        self.conn_reservations: dict[int, dict[Connection, list[int]]] = \
            defaultdict(lambda: defaultdict(list))

        self.node_reservations[0][self.start_hub] = list(
            range(1, nb_drones + 1))

    def can_enter_node(self, node: Node, time: int) -> bool:
        if node == self.end_hub or node == self.start_hub:
            return True
        capacity: int = node.metadata.max_drones if node.metadata.max_drones else 1

        nb_drones_in: int = len(self.node_reservations.get(time, {}).get(node, []))
        return nb_drones_in < capacity

    def can_use_connection(self, connection: Connection, time: int) -> bool:
        capacity: int = connection.metadata.max_link_capacity if connection.metadata.max_link_capacity else 1
        nb_drones_on: int = len(self.conn_reservations.get(time, {}).get(connection, []))
        return nb_drones_on < capacity

    def reserve_node(self, node: Node, time: int, drone_id: int) -> None:
        self.node_reservations[time][node].append(drone_id)

    def reserve_connection(self, connection: Connection, time: int, drone_id: int) -> None:
        self.conn_reservations[time][connection].append(drone_id)


class PathFinder:
    def __init__(self, map_data: Map) -> None:
        self.map = map_data
        self.state = SimulationState(map_data.start_hub, map_data.end_hub, map_data.nb_drones)
        self.drones_paths: dict[int, Path] = {}
        self.true_dist = self._compute_true_distances()
        if self.true_dist[self.map.start_hub] == -1:
            raise PathError("map is not solvable")

    def route_all_drones(self) -> None:
        for drone_id in range(1, self.map.nb_drones + 1):
            path = self.find_path()
            if path:
                self._reserve_path(drone_id, path)
                self.drones_paths[drone_id] = path
            else:
                print("no path for ", drone_id)

    def _compute_true_distances(self) -> dict[Node, int]:
        distances: dict[Node, int] = {node: -1 for node in self.map.hubs}
        distances[self.map.end_hub] = 0

        counter = itertools.count()
        queue: list[tuple[int, int, Node]] = [(0, next(counter), self.map.end_hub)]

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
                    if distances[neighbor] == -1 or new_dist < distances[neighbor]:
                        distances[neighbor] = new_dist
                        heapq.heappush(queue, (new_dist, next(counter), neighbor))
        return distances

    def _reserve_path(self, drone_id: int, path: Path) -> None:
        for location, time in path:
            if isinstance(location, Node):
                self.state.reserve_node(location, time, drone_id)
            elif isinstance(location, Connection): # type: ignore
                self.state.reserve_connection(location, time, drone_id)

    def _heuristic(self, node: Node) -> int:
        return self.true_dist[node]

    def find_path(self) -> Path:
        counter: itertools.count[int] = itertools.count()

        start_g = 0.0
        start_h = self._heuristic(self.map.start_hub)
        
        # FIX 1 : On commence explicitement au temps 0 (Tour 0 initial)
        open_set: list[tuple[float, int, float, int, Node, Path]] = [
            (start_g + start_h, next(counter), start_g, 0, self.map.start_hub, [])
        ]
        visited: set[tuple[Node, int]] = set()

        while open_set:
            _, _, g_score, current_time, current_node, path = heapq.heappop(open_set)

            if current_node == self.map.end_hub:
                return path

            state_key = (current_node, current_time)
            if state_key in visited:
                continue
            visited.add(state_key)

            next_time = current_time + 1
            if self.state.can_enter_node(current_node, next_time):
                new_path = path + [(current_node, next_time)]
                new_g = g_score + 1.0
                new_f = new_g + self._heuristic(current_node)
                heapq.heappush(open_set, (new_f, next(counter), new_g, next_time, current_node, new_path))

            for conn in self.map.connections:
                dest_node = None
                if conn.node1 == current_node:
                    dest_node = conn.node2
                elif conn.node2 == current_node:
                    dest_node = conn.node1

                if dest_node is None:
                    continue
                if dest_node.metadata.zone:
                    if dest_node.metadata.zone == Zone.BLOCKED:
                        continue

                cost: float = 1.0
                restricted: int = 0
                priority_bonus: float = 0.0
                
                if dest_node.metadata.zone:
                    if dest_node.metadata.zone == Zone.RESTRICTED:
                        cost = 2.0
                        restricted = 1
                    elif dest_node.metadata.zone == Zone.PRIORITY:
                        priority_bonus = 0.5

                # FIX 2 : Le trajet prend 1 tour de base sur la connexion + les restrictions éventuelles
                arrival_time = next_time + 1 + restricted

                # On vérifie que la connexion est libre sur l'ensemble de la traversée
                can_use_link = True
                for t in range(next_time, arrival_time):
                    if not self.state.can_use_connection(conn, t):
                        can_use_link = False
                        break

                if can_use_link and self.state.can_enter_node(dest_node, arrival_time):
                    # On génère un état pour chaque tour passé sur la connexion (évite d'écraser les clés)
                    connection_steps = [(conn, t) for t in range(next_time, arrival_time)]
                    new_path = path + connection_steps + [(dest_node, arrival_time)]
                    
                    new_g = g_score + cost
                    new_f = new_g + self._heuristic(dest_node) - priority_bonus
                    heapq.heappush(open_set, (new_f, next(counter), new_g, arrival_time, dest_node, new_path))

        return []

class Simulator:
    def __init__(self, map_data: Map) -> None:
        self.map = map_data
        self.total = self.map.nb_drones
        self.delivered = 0
        self.failed = 0
        self.turn = 0

        # Delegate pathfinding and reservation logic to the new object-based PathFinder
        self.path_finder = PathFinder(self.map)
        self.path_finder.route_all_drones()
        
        # O(1) lookup dictionary: schedule[drone_id][time] = location
        self.drone_schedules: Dict[int, Dict[int, Node | Connection]] = {}
        for drone_id, path in self.path_finder.drones_paths.items():
            self.drone_schedules[drone_id] = {time: loc for loc, time in path}

        # Drones with no path are marked as failed so simulation can terminate cleanly.
        self.failed_drones: Set[int] = {
            drone_id
            for drone_id in range(1, self.total + 1)
            if drone_id not in self.drone_schedules
        }
        self.failed = len(self.failed_drones)

        # Track state metrics
        self.current_locations: Dict[int, Node | Connection] = {
            i: self.map.start_hub for i in range(1, self.total + 1)
        }
        self.is_delivered: Set[int] = set()

        # Public runtime view expected by the UI
        self.drone_positions: Dict[int, Node | Connection] = dict(self.current_locations)
        self.in_transit: List[Dict[str, object]] = []

        # Initialize runtime state for turn 0
        self.update_runtime_state()

    def step(self) -> Tuple[bool, List[str]]:
        """Perform one simulation turn by reading the pre-calculated paths.
        
        Returns (is_finished, moves) where moves is a list of strings describing each drone's move.
        Format: "<drone_id>-<hub_name>" or "<drone_id>-<from>-<to>"
        """
        if self.delivered + self.failed >= self.total:
            return True, []

        moves: List[str] = []

        for drone_id in range(1, self.total + 1):
            if drone_id in self.is_delivered or drone_id in self.failed_drones:
                continue

            schedule = self.drone_schedules.get(drone_id, {})
            current_step_loc = schedule.get(self.turn)

            # If there is no action this turn, the drone has either finished or is waiting.
            if current_step_loc is None:
                continue

            # Only log an output string if the drone changes state/location
            if current_step_loc != self.current_locations[drone_id]:
                
                # Handling Node Arrivals
                if isinstance(current_step_loc, Node):
                    moves.append(f"D{drone_id}-{current_step_loc.name}")
                    
                    if current_step_loc == self.map.end_hub:
                        self.delivered += 1
                        self.is_delivered.add(drone_id)

                # Handling Connection Transit Start
                elif isinstance(current_step_loc, Connection): # type: ignore
                    prev_loc = self.current_locations[drone_id]
                    if isinstance(prev_loc, Node):
                        frm = prev_loc.name
                        to = current_step_loc.node2.name if current_step_loc.node1 == prev_loc else current_step_loc.node1.name
                        moves.append(f"D{drone_id}-{frm}-{to}")

                self.current_locations[drone_id] = current_step_loc

        self.turn += 1
        # Update public runtime views after the turn advances
        self.update_runtime_state()
        is_finished = (self.delivered + self.failed) >= self.total

        return is_finished, moves

    def update_runtime_state(self) -> None:
        """Update `drone_positions` and `in_transit` based on the current `turn`.

        - `drone_positions[drone_id]` is the location (Node or Connection) at `self.turn` if
          scheduled, otherwise the last known `current_locations`.
        - `in_transit` is a list of dicts: {'drone_id': int, 'conn': (hub1_name, hub2_name)}
          for drones whose scheduled location at `self.turn` is a `Connection`.
        """
        self.drone_positions = {}
        self.in_transit = []

        for drone_id in range(1, self.total + 1):
            schedule = self.drone_schedules.get(drone_id, {})
            loc = schedule.get(self.turn)
            if loc is None:
                loc = self.current_locations.get(drone_id, self.map.start_hub)

            self.drone_positions[drone_id] = loc

            if isinstance(loc, Connection):
                conn_tuple = (loc.node1.name, loc.node2.name)
                self.in_transit.append({
                    'drone_id': drone_id,
                    'conn': conn_tuple,
                })