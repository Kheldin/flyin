from models.map import Hub, Color, ZoneType
from parsing.errors import ParsingError
from parsing.utils import parse_brackets

def parse_hubs(line: str, line_nb: int) -> Hub:
    info = line.split(":")[1].strip().split(" ")
    name = info[0]
    try:
        pos_x = int(info[1])
        pos_y = int(info[2])
    except Exception as e:
        raise ParsingError(line_nb, e.__repr__())
    zone: ZoneType = ZoneType.NORMAL
    color: Color = Color.RED
    max_drones: int = 1

    if len(info) >= 4:
        meta_data = parse_brackets(info[3::], line_nb)
        valid_meta_keys = ["zone", "color", "max_drones"]
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
                    valid = [c.value for c in Color]
                    raise ParsingError(line_nb, f"Color '{meta_data['color']}' is invalid. Valid colors: {valid}")
            else:
                try:
                    max_drones = int(meta_data["max_drones"])
                except Exception as e:
                    raise ParsingError(line_nb, e.__repr__())

    return Hub(name=name, x=pos_x, y=pos_y,
               zone=zone, max_drones=int(max_drones), color=color,
               start_hub=False, end_hub=False)