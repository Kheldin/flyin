from parsing.utils import parse_brackets
from parsing.errors import ConnectionParsingError
from models.map import Connection

def parse_connection(line: str, line_nb: int) -> Connection:
    info = line.split(":")[1].strip().split(" ")
    if len(info) < 1:
        raise ConnectionParsingError(line_nb, "Connections must follow this model: zone1-zone2 OptionnalMetaData['max_link_capacity']")
    if not '-' in info[0]:
        raise ConnectionParsingError(line_nb, "Zones must be separated by '-'")
    max_link_capacity = 1
    if len(info) > 1:
        meta_data = parse_brackets(info[1::], line_nb)
        if len(meta_data) != 1:
            raise ConnectionParsingError(line_nb, "Connections must follow this model: zone1-zone2 OptionnalMetaData['max_link_capacity']")

    hub1 = info[0].split("-")[0]
    hub2 = info[0].split("-")[1]
    return Connection(hub_1=hub1, hub_2=hub2, max_link_capacity=max_link_capacity, line=line_nb)