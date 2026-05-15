from models.map import Hub
from parsing.errors import ParsingError
from parsing.utils import parse_brackets


def parse_hubs(line: str, line_nb: int) -> None:
    info = line.split(":")[1].strip().split(" ")
    name = info[0]
    pos_x = info[1]
    pos_y = info[2]
    if len(info) >= 4:
        meta_data = parse_brackets(info[3::], line_nb)
        valid_meta_keys = ["zone", "color", "max_drones"]
        for key in meta_data.keys():
            if not key in valid_meta_keys:
                raise ParsingError(
                    line_nb, f"Metadata '{key}' is invalid. "
                             f"Valid metadate: '{valid_meta_keys}'")