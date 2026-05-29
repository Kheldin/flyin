from __future__ import annotations
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from models.map import Map, Hub, ZoneType


class Simulator:
    def __init__(self, map_data: Map):
        self.map = map_data
        self.total = self.map.nb_drones
        self.delivered = 0
        self.turn = 0
        # in_transit entries: dicts with keys: drone, from, to, conn (tuple), remaining (int)
        self.in_transit: List[Dict[str, Any]] = []
        self.in_transit_ids: set[int] = set()

        # Build adjacency by hub name
        self.adj: Dict[str, List[str]] = {}
        for hub in self.map.hubs:
            self.adj[hub.name] = []
        # connections map for capacities
        self.conn_caps: Dict[Tuple[str, str], int] = {}
        def _name(obj: Any) -> str:
            return obj.name if isinstance(obj, Hub) else str(obj)

        for conn in self.map.connections:
            h1 = _name(conn.hub_1)
            h2 = _name(conn.hub_2)
            self.adj.setdefault(h1, []).append(h2)
            self.adj.setdefault(h2, []).append(h1)
            # ensure a stable 2-tuple key
            key: Tuple[str, str] = (h1, h2) if h1 <= h2 else (h2, h1)
            self.conn_caps[key] = int(conn.max_link_capacity)

        self.start: Hub | None = next((h for h in self.map.hubs if h.start_hub), None)
        self.end: Hub | None = next((h for h in self.map.hubs if h.end_hub), None)

        # Per-drone path cache: drone_id -> list of hub names (inclusive)
        self.paths: Dict[int, List[str]] = {}

        # Initialize delivered count
        for d in self.map.drones:
            if self.end is not None and d.position.name == self.end.name:
                self.delivered += 1

    def _bfs_shortest_path(self, src: str, dst: str) -> Optional[List[str]]:
        # Use Dijkstra-like search where edge weight is cost of entering the neighbor hub
        if src == dst:
            return [src]
        import heapq

        def hub_cost(name: str) -> int:
            hub = next((h for h in self.map.hubs if h.name == name), None)
            if hub is None:
                return 9999
            if hub.zone == ZoneType.BLOCKED:
                return 9999
            if hub.zone == ZoneType.RESTRICTED:
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
            drone = it["drone"]
            dest_name = it["to"]
            frm = it["from"]
            conn_label = f"{frm}-{dest_name}"
            if it["remaining"] <= 0:
                # arrival
                dest_hub = next((h for h in self.map.hubs if h.name == dest_name), None)
                if dest_hub:
                    # Place drone
                    drone.position = dest_hub
                    if dest_hub.drones is None:
                        dest_hub.drones = []
                    if all(d.id != drone.id for d in dest_hub.drones):
                        dest_hub.drones.append(drone)
                    if dest_hub.end_hub:
                        self.delivered += 1
                    turn_moves.append(f"D{drone.id}-{dest_name}")
                self.in_transit_ids.discard(drone.id)
            else:
                new_in_transit.append(it)
                turn_moves.append(f"D{drone.id}-{conn_label}")
        self.in_transit = new_in_transit

        # Current occupancy after arrivals
        occupancy: Dict[str, int] = {}
        for h in self.map.hubs:
            occupancy[h.name] = len(h.drones) if h.drones else 0

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

        for drone in self.map.drones:
            # skip delivered drones
            if drone.id in self.in_transit_ids:
                continue
            if drone.position.name == self.end.name:
                continue
            # skip drones already in transit (shouldn't appear in map.drones list as moved)
            # compute path
            path = self._bfs_shortest_path(drone.position.name, self.end.name)
            if not path or len(path) < 2:
                continue
            next_hub_name = path[1]
            next_hub = next((h for h in self.map.hubs if h.name == next_hub_name), None)
            if not next_hub:
                continue

            # determine movement cost based on destination zone
            if next_hub.zone == ZoneType.BLOCKED:
                continue
            cost = 2 if next_hub.zone == ZoneType.RESTRICTED else 1

            intents.append({
                "drone": drone,
                "from": drone.position.name,
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
            if hub.start_hub or hub.end_hub:
                return 10**9
            return int(hub.max_drones)

        # pre-calc occupancy after considering leaves
        # we'll iterate intents in id order for determinism
        intents.sort(key=lambda x: x["drone"].id)
        planned_arrivals: Dict[str, int] = defaultdict(int)
        planned_conn_current: Dict[Tuple[str, str], int] = defaultdict(int)
        planned_conn_next: Dict[Tuple[str, str], int] = defaultdict(int)

        for it in intents:
            drone = it["drone"]
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
            drone = it["drone"]
            frm = it["from"]
            to = it["to"]
            cost = it["cost"]
            key = tuple(sorted((frm, to)))
            # Remove drone from from-hub list
            from_hub = next((h for h in self.map.hubs if h.name == frm), None)
            to_hub = next((h for h in self.map.hubs if h.name == to), None)
            if from_hub and from_hub.drones:
                from_hub.drones = [d for d in from_hub.drones if d.id != drone.id]

            if cost == 1:
                # immediate arrival
                if to_hub is not None:
                    if to_hub.drones is None:
                        to_hub.drones = []
                    to_hub.drones.append(drone)
                    drone.position = to_hub
                    if to_hub.end_hub:
                        self.delivered += 1
            else:
                # start transit, remaining=2 turns until arrival
                self.in_transit_ids.add(drone.id)
                self.in_transit.append({
                    "drone": drone,
                    "from": frm,
                    "to": to,
                    "conn": key,
                    "remaining": 2,
                })

            if cost == 1:
                moves.append(f"D{drone.id}-{to}")
            else:
                moves.append(f"D{drone.id}-{frm}-{to}")

        moves = turn_moves + moves

        is_finished = self.delivered >= self.total
        return is_finished, moves
