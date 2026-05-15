from models.map import Hub
from parsing.errors import ParsingError


def parse_hub_brackets(brackets: list[str], line_nb: int) -> dict[str, str | int]:
    if not brackets[0].startswith("[") or not brackets[-1].endswith("]"):
        raise ParsingError(line_nb, "Metadata should be between brackets []")

def parse_hubs(line: str, line_nb: int) -> None:
    info = line.split(":")[1].strip().split(" ")
    name = info[0]
    pos_x = info[1]
    pos_y = info[2]
    if len(info) >= 4:
        parse_hub_brackets(info[3::], line_nb)
        