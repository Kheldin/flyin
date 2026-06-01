from __future__ import annotations
from collections import defaultdict
import heapq
import itertools
from typing import Any, Dict, List, Optional, Tuple, TypeAlias

from models.map import Connection, Map, Node, Zone


PathStep: TypeAlias = tuple[Node | Connection, int]
Path: TypeAlias = list[PathStep]


class PathError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


def _hub_name(node: Node | str) -> str:
    return node.name if isinstance(node, Node) else str(node)


def _connection_key(connection: Connection) -> tuple[str, str]:
    hub_1 = _hub_name(connection.node1)
    hub_2 = _hub_name(connection.node2)
    return (hub_1, hub_2) if hub_1 <= hub_2 else (hub_2, hub_1)


class SimulationState:
    def __init__(self, start_hub: Node, end_hub: Node, nb_drones: int) -> None:
        self.start_hub = start_hub
        self.end_hub = end_hub
        self.nb_drones = nb_drones

        self.node_reservations: dict[int, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
        self.conn_reservations: dict[int, dict[tuple[str, str], list[int]]] = defaultdict(lambda: defaultdict(list))

        self.node_reservations[0][_hub_name(self.start_hub)] = list(range(1, nb_drones + 1))

    def can_enter_node(self, node: Node, time: int) -> bool:
        if node == self.end_hub or node == self.start_hub:
            return True

        capacity: int = node.metadata.max_drones if node.metadata.max_drones else 1
        nb_drones_in: int = len(self.node_reservations.get(time, {}).get(_hub_name(node), []))
        return nb_drones_in < capacity

    def can_use_connection(self, connection: Connection, time: int) -> bool:
        capacity: int = connection.metadata.max_link_capacity if connection.metadata.max_link_capacity else 1
        nb_drones_on: int = len(self.conn_reservations.get(time, {}).get(_connection_key(connection), []))
        return nb_drones_on < capacity

    def reserve_node(self, node: Node, time: int, drone_id: int) -> None:
        self.node_reservations[time][_hub_name(node)].append(drone_id)

    def reserve_connection(self, connection: Connection, time: int, drone_id: int) -> None:
        self.conn_reservations[time][_connection_key(connection)].append(drone_id)


class PathFinder:
    def __init__(self, map_data: Map) -> None:
        self.map = map_data
        self.start_hub = self.map.start_hub
        self.end_hub = self.map.end_hub

        self._hub_by_name: dict[str, Node] = {hub.name: hub for hub in self.map.hubs}
        self._connections_by_key: dict[tuple[str, str], Connection] = {
            _connection_key(connection): connection for connection in self.map.connections
        }
        self._adjacency: dict[str, list[str]] = defaultdict(list)
        for connection in self.map.connections:
            hub_1 = _hub_name(connection.node1)
            hub_2 = _hub_name(connection.node2)
            self._adjacency[hub_1].append(hub_2)
            self._adjacency[hub_2].append(hub_1)

        self.state = SimulationState(self.start_hub, self.end_hub, self.map.nb_drones)
        self.drones_paths: dict[int, Path] = {}
        assert self.start_hub is not None
        assert self.end_hub is not None
        self.true_dist = self._compute_true_distances()

        if self.true_dist.get(self.start_hub.name, -1) == -1:
            raise PathError("map is not solvable")

    def route_all_drones(self) -> None:
        for drone_id in range(1, self.map.nb_drones + 1):
            path = self.find_path()
            if path:
                self._reserve_path(drone_id, path)
                self.drones_paths[drone_id] = path
            else:
                print("no path for ", drone_id)

    def _compute_true_distances(self) -> dict[str, int]:
        assert self.end_hub is not None
        distances: dict[str, int] = {hub.name: -1 for hub in self.map.hubs}
        distances[self.end_hub.name] = 0

        counter = itertools.count()
        queue: list[tuple[int, int, Node]] = [(0, next(counter), self.end_hub)]

        while queue:
            dist, _, current = heapq.heappop(queue)

            if distances[current.name] != -1 and dist > distances[current.name]:
                continue

            for neighbor_name in self._adjacency.get(current.name, []):
                neighbor = self._hub_by_name.get(neighbor_name)
                if neighbor is None:
                    continue

                if neighbor.metadata.zone == Zone.BLOCKED:
                    continue

                step_cost = 2 if neighbor.metadata.zone == Zone.RESTRICTED else 1
                new_dist = dist + step_cost
                if distances[neighbor.name] == -1 or new_dist < distances[neighbor.name]:
                    distances[neighbor.name] = new_dist
                    heapq.heappush(queue, (new_dist, next(counter), neighbor))

        return distances

    def _reserve_path(self, drone_id: int, path: Path) -> None:
        for location, time in path:
            if isinstance(location, Node):
                self.state.reserve_node(location, time, drone_id)
            else:
                self.state.reserve_connection(location, time, drone_id)

    def _heuristic(self, node: Node) -> int:
        return self.true_dist.get(node.name, -1)

    def find_path(self) -> Path:
        counter: itertools.count[int] = itertools.count()

        assert self.start_hub is not None
        assert self.end_hub is not None
        start_g = 0.0
        start_h = self._heuristic(self.start_hub)
        open_set: list[tuple[float, int, float, int, Node, Path]] = [
            (start_g + start_h, next(counter), start_g, -1, self.start_hub, [])
        ]
        visited: set[tuple[str, int]] = set()

        while open_set:
            _, _, g_score, current_time, current_node, path = heapq.heappop(open_set)

            if current_node == self.end_hub:
                return path

            state_key = (current_node.name, current_time)
            if state_key in visited:
                continue
            visited.add(state_key)

            next_time = current_time + 1
            if self.state.can_enter_node(current_node, next_time):
                new_path = path + [(current_node, next_time)]
                new_g = g_score + 1.0
                new_f = new_g + self._heuristic(current_node)
                heapq.heappush(open_set, (new_f, next(counter), new_g, next_time, current_node, new_path))

            for dest_name in self._adjacency.get(current_node.name, []):
                dest_node = self._hub_by_name.get(dest_name)
                if dest_node is None:
                    continue
                if dest_node.metadata.zone == Zone.BLOCKED:
                    continue

                connection = self._connections_by_key.get((current_node.name, dest_node.name))
                if connection is None:
                    connection = self._connections_by_key.get((dest_node.name, current_node.name))
                if connection is None:
                    continue

                cost: float = 1.0
                restricted_delay: int = 0
                priority_bonus: float = 0.0

                if dest_node.metadata.zone == Zone.RESTRICTED:
                    cost = 2.0
                    restricted_delay = 1
                elif dest_node.metadata.zone == Zone.PRIORITY:
                    priority_bonus = 0.5

                arrival_time = next_time + restricted_delay
                if self.state.can_use_connection(connection, next_time) and self.state.can_enter_node(dest_node, arrival_time):
                    new_path = path + [(connection, next_time)] + [(dest_node, arrival_time)]
                    new_g = g_score + cost
                    new_f = new_g + self._heuristic(dest_node) - priority_bonus
                    heapq.heappush(open_set, (new_f, next(counter), new_g, arrival_time, dest_node, new_path))

        return []


class Simulator:
    def __init__(self, map_data: Map):
        self.map = map_data
        self.total = self.map.nb_drones
        self.delivered = 0
        self.turn = 0
        # in_transit entries: dicts with keys: drone_id, from, to, conn (tuple), remaining (int)
        self.in_transit: List[Dict[str, Any]] = []
        self.in_transit_ids: set[int] = set()

        # Build adjacency by hub name
        self.adj: Dict[str, List[str]] = {}
        for hub in self.map.hubs:
            self.adj[hub.name] = []
        # connections map for capacities
        self.conn_caps: Dict[Tuple[str, str], int] = {}

        for conn in self.map.connections:
            h1 = conn.node1.name
            h2 = conn.node2.name
            self.adj.setdefault(h1, []).append(h2)
            self.adj.setdefault(h2, []).append(h1)
            # ensure a stable 2-tuple key
            key: Tuple[str, str] = (h1, h2) if h1 <= h2 else (h2, h1)
            capacity = conn.metadata.max_link_capacity if conn.metadata.max_link_capacity else 1
            self.conn_caps[key] = int(capacity)

        self.start: Node | None = self.map.start_hub
        self.end: Node | None = self.map.end_hub

        # Track drone positions: drone_id -> Node
        self.drone_positions: Dict[int, Node] = {}
        for i in range(1, self.map.nb_drones + 1):
            self.drone_positions[i] = self.start

    def _bfs_shortest_path(self, src: str, dst: str) -> Optional[List[str]]:
        # Use Dijkstra-like search where edge weight is cost of entering the neighbor hub
        if src == dst:
            return [src]
        import heapq

        def hub_cost(name: str) -> int:
            hub = next((h for h in self.map.hubs if h.name == name), None)
            if hub is None:
                return 9999
            if hub.metadata.zone == Zone.BLOCKED:
                return 9999
            if hub.metadata.zone == Zone.RESTRICTED:
                return 2
            return 1

        heap = [(0, [src])]
        seen_costs = {src: 0}
        while heap:
            cost, path = heapq.heappop(heap)
            node = path[-1]
            if node == dst:
                return path
            for neigh in self.adj.get(node, []):
                step_cost = hub_cost(neigh)
                if step_cost > 9000:
                    continue
                new_cost = cost + step_cost
                if neigh not in seen_costs or new_cost < seen_costs[neigh]:
                    seen_costs[neigh] = new_cost
                    heapq.heappush(heap, (new_cost, path + [neigh]))
        return None

    def step(self) -> Tuple[bool, List[str]]:
        """Perform one simulation turn.

        Returns (is_finished, moves) where moves is a list of strings describing each drone's move.
        Format: "<drone_id>-<hub_name>"
        """
        if self.delivered >= self.total:
            return True, []

        # Start of turn: process in-transit arrivals (decrement remaining and arrive if 0)
        self.turn += 1
        moves: List[str] = []

        # If there's no end hub defined, nothing to do
        if self.end is None:
            return True, []
        new_in_transit: List[Dict[str, Any]] = []
        turn_moves: List[str] = []
        for it in self.in_transit:
            it["remaining"] -= 1
            drone_id = it["drone_id"]
            dest_name = it["to"]
            frm = it["from"]
            conn_label = f"{frm}-{dest_name}"
            if it["remaining"] <= 0:
                # arrival
                dest_hub = next((h for h in self.map.hubs if h.name == dest_name), None)
                if dest_hub:
                    # Place drone
                    self.drone_positions[drone_id] = dest_hub
                    if dest_hub.name == self.end.name:
                        self.delivered += 1
                    turn_moves.append(f"D{drone_id}-{dest_name}")
                self.in_transit_ids.discard(drone_id)
            else:
                new_in_transit.append(it)
                turn_moves.append(f"D{drone_id}-{conn_label}")
        self.in_transit = new_in_transit

        # Current occupancy after arrivals
        occupancy: Dict[str, int] = {}
        for h in self.map.hubs:
            count = sum(1 for drone_id, pos in self.drone_positions.items() 
                       if pos.name == h.name and drone_id not in self.in_transit_ids)
            occupancy[h.name] = count

        # Build current connection usage (this turn)
        conn_usage_current: Dict[Tuple[str, str], int] = defaultdict(int)
        conn_usage_next: Dict[Tuple[str, str], int] = defaultdict(int)
        for it in self.in_transit:
            key = tuple(sorted((it["from"], it["to"])))
            if it["remaining"] >= 1:
                conn_usage_current[key] += 1
            if it["remaining"] >= 2:
                conn_usage_next[key] += 1

        # Prepare intents
        intents: List[Dict[str, Any]] = []
        # We'll also count planned leaves to free capacity during this turn
        planned_leaves: Dict[str, int] = defaultdict(int)

        for drone_id in range(1, self.map.nb_drones + 1):
            # skip delivered drones
            if drone_id in self.in_transit_ids:
                continue
            pos = self.drone_positions[drone_id]
            if pos.name == self.end.name:
                continue
            # compute path
            path = self._bfs_shortest_path(pos.name, self.end.name)
            if not path or len(path) < 2:
                continue
            next_hub_name = path[1]
            next_hub = next((h for h in self.map.hubs if h.name == next_hub_name), None)
            if not next_hub:
                continue

            # determine movement cost based on destination zone
            if next_hub.metadata.zone == Zone.BLOCKED:
                continue
            cost = 2 if next_hub.metadata.zone == Zone.RESTRICTED else 1

            intents.append({
                "drone_id": drone_id,
                "from": pos.name,
                "to": next_hub_name,
                "cost": cost,
            })

        # Greedy scheduling: try to accept intents while respecting hub capacities and connection caps
        accepted: List[Dict[str, Any]] = []
        # helper to get hub capacity (start/end are exceptions)
        def hub_capacity(hub_name: str) -> int:
            hub = next((h for h in self.map.hubs if h.name == hub_name), None)
            if hub is None:
                return 0
            if hub == self.start or hub == self.end:
                return 10**9
            capacity = hub.metadata.max_drones if hub.metadata.max_drones else 1
            return int(capacity)

        # pre-calc occupancy after considering leaves
        # we'll iterate intents in id order for determinism
        intents.sort(key=lambda x: x["drone_id"])
        planned_arrivals: Dict[str, int] = defaultdict(int)
        planned_conn_current: Dict[Tuple[str, str], int] = defaultdict(int)
        planned_conn_next: Dict[Tuple[str, str], int] = defaultdict(int)

        for it in intents:
            drone_id = it["drone_id"]
            frm = it["from"]
            to = it["to"]
            cost = it["cost"]
            # compute free slots at destination after accounting for planned leaves from that hub
            free_now = hub_capacity(to) - (occupancy.get(to, 0) - planned_leaves.get(to, 0) + planned_arrivals.get(to, 0))
            # connection key and caps
            key = tuple(sorted((frm, to)))
            cap = self.conn_caps.get(key, 1)
            # current and next usage including planned
            cur_usage = conn_usage_current.get(key, 0) + planned_conn_current.get(key, 0)
            next_usage = conn_usage_next.get(key, 0) + planned_conn_next.get(key, 0)

            # For cost==1 (normal/priority): needs free_now > 0 and cur_usage < cap
            if cost == 1:
                if free_now > 0 and cur_usage < cap:
                    accepted.append(it)
                    planned_arrivals[to] += 1
                    planned_leaves[frm] += 1
                    planned_conn_current[key] += 1
                else:
                    # can't move, will stay
                    continue
            else:
                # cost==2 restricted: need connection cap both current and next, and destination slot now (conservative)
                if free_now > 0 and cur_usage < cap and (next_usage + 1) <= cap:
                    accepted.append(it)
                    planned_arrivals[to] += 1
                    planned_leaves[frm] += 1
                    planned_conn_current[key] += 1
                    planned_conn_next[key] += 1
                else:
                    continue

        # Apply accepted moves
        for it in accepted:
            drone_id = it["drone_id"]
            frm = it["from"]
            to = it["to"]
            cost = it["cost"]
            key = tuple(sorted((frm, to)))
            to_hub = next((h for h in self.map.hubs if h.name == to), None)

            if cost == 1:
                # immediate arrival
                if to_hub is not None:
                    self.drone_positions[drone_id] = to_hub
                    if to_hub.name == self.end.name:
                        self.delivered += 1
            else:
                # start transit, remaining=2 turns until arrival
                self.in_transit_ids.add(drone_id)
                self.in_transit.append({
                    "drone_id": drone_id,
                    "from": frm,
                    "to": to,
                    "conn": key,
                    "remaining": 2,
                })

            if cost == 1:
                moves.append(f"D{drone_id}-{to}")
            else:
                moves.append(f"D{drone_id}-{frm}-{to}")

        moves = turn_moves + moves

        is_finished = self.delivered >= self.total
        return is_finished, moves
