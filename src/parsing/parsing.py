import sys
from models.map import Map, Drone, Connection, Hub
from parsing.errors import ParsingError, ArgumentError
from parsing.parse_hub import parse_hub
from parsing.parse_connection import parse_connection


def parse_nb_drones(line: str, line_nb: int) -> int:
    line = line.replace(" ", "")
    nb_drones = int(line.split(":")[1])
    if not nb_drones > 0:
        raise ParsingError(line_nb, "nb_drones must be greater than 0")  
    return (int(line.split(":")[1]))

def parse_file() -> None:
    if (len(sys.argv) != 2):
        raise ArgumentError("Only one arg required: Path of the map")
 
    with open(sys.argv[1]) as f:
        file_content = f.read().splitlines()
    
    drones: list[Drone] = []
    hubs: list[Hub] = []
    connections: list[Connection] = []
    first_kw = 1;
    for line_nb, raw in enumerate(file_content, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        keyword = line.split(':')[0].strip()
        if first_kw == 1:
            if keyword != "nb_drones":
                raise ParsingError(line_nb, "First line must define number of drones using 'nb_drones'")
        first_kw = 0
        match keyword:
            case "nb_drones":
                nb_drones = parse_nb_drones(line, line_nb)
            case "hub":
                hub = parse_hub(line, line_nb)
                for existing_hub in hubs:
                    if existing_hub.name == hub.name:
                        raise ParsingError(line_nb, f"Duplicate hub name: '{hub.name}'")
                    if existing_hub.x == hub.x and existing_hub.y == hub.y:
                        raise ParsingError(line_nb, f"Duplicate hub position: ({hub.x}, {hub.y})")
                hubs.append(hub)
            case "connection":
                parse_connection(line, line_nb)
            case "start_hub":
                pass
            case "end_hub":
                pass
            case _:
                raise ParsingError(line_nb, f"unknown keyword '{keyword}'")
    return