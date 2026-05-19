from models.map import Hub, Color, ZoneType
from parsing.errors import ParsingError, HubParsingError
from parsing.utils import parse_brackets

def parse_hub(line: str, line_nb: int, start: bool, end: bool) -> Hub:
    valid_color = [c.value for c in Color]
    valid_meta_keys = ["zone", "max_drones", "color"]
    info = line.split(":")[1].strip().split(" ")
    if len(info) < 3:
        raise HubParsingError(line_nb, f"Hubs must follow this model: name x y OptionnalMetaData{valid_meta_keys}\n"
                           f"Available color: {valid_color}")
    name = info[0]
    if "-" in name:
        raise HubParsingError(line_nb, f"Hub name '{name}' is invalid. Names must not contain spaces or '-'.")
    try:
        pos_x = int(info[1])
        pos_y = int(info[2])
    except Exception as e:
        raise ParsingError(line_nb, f"{e.__repr__()}\n"
                           f"Hubs must follow this model: name x y OptionnalMetaData{valid_meta_keys}\n"
                           f"Available color: {valid_color}")
    zone: ZoneType = ZoneType.NORMAL
    color: Color = Color.RED
    max_drones: int = 1
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
                    zone = ZoneType(meta_data["zone"])
                except ValueError:
                    valid = [z.value for z in ZoneType]
                    raise ParsingError(line_nb, f"Zone '{meta_data['zone']}' is invalid. Valid zones: {valid}")
            elif key == "color":
                try:
                    color = Color(meta_data["color"])
                except ValueError:
                    raise ParsingError(line_nb, f"Color '{meta_data['color']}' is invalid. Valid colors: {valid_color}")
            else:
                try:
                    max_drones = int(meta_data["max_drones"])
                except Exception as e:
                    raise ParsingError(line_nb, e.__repr__())

    return Hub(name=name, x=pos_x, y=pos_y,
               zone=zone, max_drones=int(max_drones), color=color,
               start_hub=start, end_hub=end)


def ensure_no_duplicate_hub(hubs: list[Hub], hub: Hub, line_nb: int) -> None:
    for existing_hub in hubs:
        if existing_hub.name == hub.name:
            raise ParsingError(line_nb, f"Duplicate hub name: '{hub.name}'")
        if existing_hub.x == hub.x and existing_hub.y == hub.y:
            raise ParsingError(line_nb, f"Duplicate hub position: ({hub.x}, {hub.y})")
