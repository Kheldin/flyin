import sys
from models.map import Map, Connection, Node, Metadata
from parsing.errors import ParsingError, ArgumentError, ConnectionParsingError
from parsing.parse_hub import parse_hub, ensure_no_duplicate_hub
from parsing.parse_connection import parse_connection, check_connections_hubs, ensure_no_duplicate_connection

def parse_nb_drones(line: str, line_nb: int) -> int:
    line = line.replace(" ", "")
    nb_drones = int(line.split(":")[1])
    if not nb_drones > 0:
        raise ParsingError(line_nb, "nb_drones must be greater than 0")
    return int(line.split(":")[1])

def parse_file() -> Map:
    """Parse the map files"""
    if len(sys.argv) != 2:
        raise ArgumentError("Only one arg required: Path of the map")

    with open(sys.argv[1]) as f:
        file_content = f.read().splitlines()

    hubs: list[Node] = []
    connections: list[tuple[str, str, int]] = []
    first_kw = 1
    nb_drones = 0
    start_hub: Node | None = None
    end_hub: Node | None = None
    
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
                hub1_name, hub2_name, _ = connection
                if hub1_name not in current_hub_names or hub2_name not in current_hub_names:
                    missing = hub1_name if hub1_name not in current_hub_names else hub2_name
                    raise ConnectionParsingError(line_nb, f"Unknown hub: '{missing}'")
                ensure_no_duplicate_connection(connections, connection, line_nb)
                connections.append(connection)
            case "start_hub":
                hub = parse_hub(line, line_nb, True, False)
                ensure_no_duplicate_hub(hubs, hub, line_nb)
                if start_hub is not None:
                    raise ParsingError(line_nb, "You must provide only one start")
                start_hub = hub
                hubs.append(hub)
            case "end_hub":
                hub = parse_hub(line, line_nb, False, True)
                ensure_no_duplicate_hub(hubs, hub, line_nb)
                if end_hub is not None:
                    raise ParsingError(line_nb, "You must provide only one end")
                end_hub = hub
                hubs.append(hub)
            case _:
                raise ParsingError(line_nb, f"unknown keyword '{keyword}'")
    
    if start_hub is None or end_hub is None:
        raise ParsingError(0, "Start or end hub missing.")
    
    check_connections_hubs(connections, hubs)
    
    # Create Connection objects from parsed data
    hub_map = {hub.name: hub for hub in hubs}
    connection_objects: set[Connection] = set()
    for (hub1_name, hub2_name, max_capacity) in connections:
        node1 = hub_map[hub1_name]
        node2 = hub_map[hub2_name]
        metadata = Metadata(zone=None, color=None, max_link_capacity=max_capacity, max_drones=None)
        connection_obj = Connection(node1=node1, node2=node2, metadata=metadata)
        connection_objects.add(connection_obj)

    map = Map(
        nb_drones=nb_drones,
        start_hub=start_hub,
        end_hub=end_hub,
        hubs=hubs,
        connections=connection_objects
    )
    return map
