from parsing.parse_brackets import parse_brackets
from parsing.errors import ConnectionParsingError
from models.map import Node


def parse_connection(line: str, line_nb: int) -> tuple[str, str, int]:
    """Parse a connection line and return tuple of
    (hub1_name, hub2_name, max_link_capacity)"""
    info = line.split(":")[1].strip().split(" ")
    if len(info) < 1:
        raise ConnectionParsingError(
            line_nb,
            "Connections must follow this model: " +
            "zone1-zone2 OptionnalMetaData['max_link_capacity']",
        )
    if "-" not in info[0] or info[0].count("-") != 1:
        raise ConnectionParsingError(line_nb,
                                     "Provide only 2 zones separated by '-'")
    max_link_capacity = 1
    if len(info) > 1:
        meta_data = parse_brackets(info[1::], line_nb)
        if len(meta_data) != 1:
            raise ConnectionParsingError(
                line_nb,
                "Connections must follow this model: " +
                "zone1-zone2 OptionnalMetaData['max_link_capacity']",
            )
        if "max_link_capacity" not in meta_data.keys():
            raise ConnectionParsingError(
                line_nb, "Only 'max_link_capacity' is allowed."
            )
        try:
            max_link_capacity = int(meta_data["max_link_capacity"])
            if max_link_capacity < 1:
                raise ConnectionParsingError(
                    line_nb, "max_link_capacity must be greater than 0."
                )
        except ValueError:
            raise ConnectionParsingError(
                line_nb, "'max_link_capacity' should be a positive integer."
            )
    hub1 = info[0].split("-")[0]
    hub2 = info[0].split("-")[1]
    return (hub1, hub2, max_link_capacity)


def ensure_no_duplicate_connection(
    connections: list[tuple[str, str, int]],
    connection: tuple[str, str, int],
    line_nb: int,
) -> None:
    hub1_name, hub2_name, _ = connection
    new_pair = tuple(sorted((hub1_name, hub2_name)))

    for existing_hub1, existing_hub2, _ in connections:
        existing_pair = tuple(sorted((existing_hub1, existing_hub2)))
        if existing_pair == new_pair:
            raise ConnectionParsingError(
                line_nb,
                f"Duplicate conn between '{hub1_name}' and '{hub2_name}'",
            )


def check_connections_hubs(
    connections: list[tuple[str, str, int]], hubs: list[Node]
) -> None:
    """After parsing the whole file.
    We check if all connections hubs are known"""
    unique_hubs: set[str] = set()
    hub_to_line: dict[str, int] = {}
    for idx, (hub1_name, hub2_name, _) in enumerate(connections):
        unique_hubs.add(hub1_name)
        unique_hubs.add(hub2_name)
        hub_to_line[hub1_name] = idx
        hub_to_line[hub2_name] = idx
    hub_names = {hub.name for hub in hubs}
    for hub_con in unique_hubs:
        if hub_con not in hub_names:
            raise ConnectionParsingError(
                hub_to_line[hub_con], f"Unknown hub: '{hub_con}'"
            )
