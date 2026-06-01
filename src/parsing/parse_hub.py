from models.map import Node, Metadata, Zone
from parsing.errors import ParsingError, HubParsingError
from parsing.utils import parse_brackets

def parse_hub(line: str, line_nb: int, start: bool, end: bool) -> Node:
    valid_meta_keys = ["zone", "max_drones", "color"]
    info = line.split(":")[1].strip().split(" ")
    if len(info) < 3:
        raise HubParsingError(line_nb, f"Hubs must follow this model: name x y OptionnalMetaData{valid_meta_keys}")
    name = info[0]
    if "-" in name:
        raise HubParsingError(line_nb, f"Hub name '{name}' is invalid. Names must not contain spaces or '-'.")
    try:
        pos_x = int(info[1])
        pos_y = int(info[2])
    except Exception as e:
        raise ParsingError(line_nb, f"{e.__repr__()}\n"
                           f"Hubs must follow this model: name x y OptionnalMetaData{valid_meta_keys}")
    zone: Zone | None = Zone.NORMAL
    color: str | None = "red"
    max_drones: int | None = 1
    if len(info) >= 4:
        meta_data = parse_brackets(info[3::], line_nb)
        for key in meta_data.keys():
            if key not in valid_meta_keys:
                raise ParsingError(
                    line_nb, f"Metadata '{key}' is invalid. "
                    f"Valid metadata: '{valid_meta_keys}'"
                )
            if key == "zone":
                try:
                    zone = Zone.get_zone(meta_data["zone"])
                except Exception:
                    valid = ["normal", "restricted", "priority", "blocked"]
                    raise ParsingError(line_nb, f"Zone '{meta_data['zone']}' is invalid. Valid zones: {valid}")
            elif key == "color":
                # Accept any string for color; it's stored as-is and defaults to 'red'
                color = meta_data["color"]
            else:
                try:
                    max_drones = int(meta_data["max_drones"])
                    if max_drones <= 0:
                        raise HubParsingError(line_nb, "max_drones should be greater than 0.")
                except Exception as e:
                    raise ParsingError(line_nb, e.__repr__())

    metadata = Metadata(zone=zone, color=color, max_link_capacity=None, max_drones=max_drones)
    return Node(name=name, x=pos_x, y=pos_y, metadata=metadata)


def ensure_no_duplicate_hub(hubs: list[Node], hub: Node, line_nb: int) -> None:
    for existing_hub in hubs:
        if existing_hub.name == hub.name:
            raise ParsingError(line_nb, f"Duplicate hub name: '{hub.name}'")
        if existing_hub.x == hub.x and existing_hub.y == hub.y:
            raise ParsingError(line_nb, f"Duplicate hub position: ({hub.x}, {hub.y})")
