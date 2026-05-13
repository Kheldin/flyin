import sys
from models.map import Map, Drone, Connection, Hub
from parsing.errors import ParsingError


def parse_file() -> None:
    if (len(sys.argv) != 2):
        raise ParsingError("Only one arg required: Path of the map")
 
    with open(sys.argv[1]) as f:
        file_content = f.read()
    
    drones: list[Drone]
    hubs: list[Hub]
    connections: list[Connection]

    for line_nb, raw in enumerate(file_content.split('\n'), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        keyword = line.split(':')[0].strip()
        match keyword:
            case "nb_drones":
                pass
            case "hub":
                pass
            case "connection":
                pass
            case "start_hub":
                pass
            case "end_hub":
                pass
            case _:
                raise ParsingError(line_nb, f"unknown keyword '{keyword}'")
    return 