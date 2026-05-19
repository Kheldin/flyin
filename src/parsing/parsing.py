import sys
from models.map import Map, Drone, Connection, Hub
from parsing.errors import ParsingError, ArgumentError
from parsing.parse_hub import parse_hub, ensure_no_duplicate_hub
from parsing.parse_connection import parse_connection, check_connections_hubs, ensure_no_duplicate_connection

def parse_nb_drones(line: str, line_nb: int) -> int:
    line = line.replace(" ", "")
    nb_drones = int(line.split(":")[1])
    if not nb_drones > 0:
        raise ParsingError(line_nb, "nb_drones must be greater than 0")
    return int(line.split(":")[1])

def start_end_present(hubs: list[Hub]) -> int:
    met_start = 0
    met_end = 0
    for hub in hubs:
        if hub.start_hub == 1:
            met_start = 1;
        if hub.end_hub == 1:
            met_end = 1
    return met_start and met_end

def parse_file() -> Map:
    """Parse the map files"""
    if len(sys.argv) != 2:
        raise ArgumentError("Only one arg required: Path of the map")

    with open(sys.argv[1]) as f:
        file_content = f.read().splitlines()

    drones: list[Drone] = []
    hubs: list[Hub] = []
    connections: list[Connection] = []
    first_kw = 1
    nb_drones = 0
    for line_nb, raw in enumerate(file_content, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        keyword = line.split(":")[0].strip()
        if first_kw == 1:
            if keyword != "nb_drones":
                raise ParsingError(
                    line_nb, "First line must define number of drones using 'nb_drones'"
                )
        first_kw = 0
        match keyword:
            case "nb_drones":
                nb_drones = parse_nb_drones(line, line_nb)
            case "hub":
                hub = parse_hub(line, line_nb, False, False)
                ensure_no_duplicate_hub(hubs, hub, line_nb)
                hubs.append(hub)
            case "connection":
                connection = parse_connection(line, line_nb)
                ensure_no_duplicate_connection(connections, connection, line_nb)
                connections.append(connection)
            case "start_hub":
                hub = parse_hub(line, line_nb, True, False)
                ensure_no_duplicate_hub(hubs, hub, line_nb)
                hubs.append(hub)
            case "end_hub":
                hub = parse_hub(line, line_nb, False, True)
                ensure_no_duplicate_hub(hubs, hub, line_nb)
                hubs.append(hub)
            case _:
                raise ParsingError(line_nb, f"unknown keyword '{keyword}'")
    check_connections_hubs(connections, hubs)
    # Replace hub string references with actual Hub objects in connections
    hub_map = {hub.name: hub for hub in hubs}
    for connection in connections:
        if isinstance(connection.hub_1, str):
            connection.hub_1 = hub_map[connection.hub_1]
        if isinstance(connection.hub_2, str):
            connection.hub_2 = hub_map[connection.hub_2]

    map = Map(
        nb_drones=nb_drones,
        drones=drones,
        connections=connections,
        hubs=hubs
    )
    if not start_end_present(hubs):
        raise ParsingError(0, "Start or end hub missing.")
    return map
