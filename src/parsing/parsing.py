import sys
from models.map import Map, Drone, Connection, Hub
from parsing.errors import ParsingError, ArgumentError, ConnectionParsingError
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
            if met_start == 1:
                raise ParsingError(hub.line, "You must provide only one start")
            met_start = 1
        if hub.end_hub == 1:
            if met_end == 1:
                raise ParsingError(hub.line, "You must provide only one end")
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
                current_hub_names = {hub.name for hub in hubs}
                hub1_name = connection.hub_1 if isinstance(connection.hub_1, str) else connection.hub_1.name
                hub2_name = connection.hub_2 if isinstance(connection.hub_2, str) else connection.hub_2.name
                if hub1_name not in current_hub_names or hub2_name not in current_hub_names:
                    missing = hub1_name if hub1_name not in current_hub_names else hub2_name
                    raise ConnectionParsingError(line_nb, f"Unknown hub: '{missing}'")
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

    start_hub = next((hub for hub in hubs if hub.start_hub), None)
    if start_hub is not None:
        drones = [Drone(id=index + 1, position=start_hub) for index in range(nb_drones)]
        for hub in hubs:
            hub.drones = []
        start_hub.drones = drones

    map = Map(
        nb_drones=nb_drones,
        drones=drones,
        connections=connections,
        hubs=hubs
    )
    if not start_end_present(hubs):
        raise ParsingError(0, "Start or end hub missing.")
    return map
