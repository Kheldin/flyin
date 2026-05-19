from parsing.utils import parse_brackets
from parsing.errors import ConnectionParsingError
from models.map import Connection, Hub

def parse_connection(line: str, line_nb: int) -> Connection:
    info = line.split(":")[1].strip().split(" ")
    if len(info) < 1:
        raise ConnectionParsingError(line_nb, "Connections must follow this model: zone1-zone2 OptionnalMetaData['max_link_capacity']")
    if not '-' in info[0] or info[0].count("-") != 1:
        raise ConnectionParsingError(line_nb, "Provide only 2 zones separated by '-'")
    max_link_capacity = 1
    if len(info) > 1:
        meta_data = parse_brackets(info[1::], line_nb)
        if len(meta_data) != 1:
            raise ConnectionParsingError(line_nb, "Connections must follow this model: zone1-zone2 OptionnalMetaData['max_link_capacity']")
        if not "max_link_capacity" in  meta_data.keys():
            raise ConnectionParsingError(line_nb, "Only 'max_link_capacity' is allowed.")
        try:
            max_link_capacity = int(meta_data["max_link_capacity"])
            if max_link_capacity < 1:
                raise ConnectionParsingError(line_nb, "max_link_capacity must be greater than 0.")
        except ValueError:
            raise ConnectionParsingError(line_nb, "'max_link_capacity' should be a positive integer.")
    hub1 = info[0].split("-")[0]
    hub2 = info[0].split("-")[1]
    return Connection(hub_1=hub1, hub_2=hub2, max_link_capacity=max_link_capacity, line=line_nb)


def ensure_no_duplicate_connection(
    connections: list[Connection], connection: Connection, line_nb: int
) -> None:
    def endpoint_name(endpoint: Hub | str) -> str:
        return endpoint.name if isinstance(endpoint, Hub) else endpoint

    new_pair = tuple(
        sorted((endpoint_name(connection.hub_1),
                endpoint_name(connection.hub_2)))
    )
    for existing_con in connections:
        existing_pair = tuple(
            sorted(
                (endpoint_name(existing_con.hub_1),
                 endpoint_name(existing_con.hub_2))
            )
        )
        if existing_pair == new_pair:
            raise ConnectionParsingError(
                line_nb,
                f"Duplicate connection between '{connection.hub_1}' and '{connection.hub_2}'",
            )


def check_connections_hubs(connections: list[Connection], hubs: list[Hub]) -> None:
    """After parsing the whole file. We check if all connections hubs are known"""
    unique_hubs: set[str] = set()
    hub_to_line: dict[str, int] = {}
    for con in connections:
        hub1_name = con.hub_1.name if isinstance(con.hub_1, Hub) else con.hub_1
        hub2_name = con.hub_2.name if isinstance(con.hub_2, Hub) else con.hub_2
        unique_hubs.add(hub1_name)
        unique_hubs.add(hub2_name)
        hub_to_line[hub1_name] = con.line
        hub_to_line[hub2_name] = con.line
    hub_names = {hub.name for hub in hubs}
    for hub_con in unique_hubs:
        if hub_con not in hub_names:
            raise ConnectionParsingError(hub_to_line[hub_con], f"Unknown hub: '{hub_con}'")