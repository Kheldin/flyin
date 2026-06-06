"""Connection string parser and graph validation mechanics module.

Provides procedural text-parsing algorithms and network integrity verification
rules to identify invalid nodes, track configurations, and drop duplicates.
"""

from models.map import Node
from parsing.errors import ConnectionParsingError
from parsing.parse_brackets import parse_brackets


def parse_connection(line: str, line_nb: int) -> tuple[str, str, int]:
    """Parse a single text connection record into a validated attribute tuple.

    Decodes linkage representations such as 'hubA-hubB [max_link_capacity=4]'
    to build layout tuples tracking structural routes.

    Args:
        line: The raw unparsed text record line coming from the map file.
        line_nb: The tracking context line number sequence index for errors.

    Returns:
        A tuple formatting layout values as (hub1_name, hub2_name, capacity).

    Raises:
        ConnectionParsingError: If formatting syntax, node delimiter count,
            key labels, or capacity data types violate structural rules.
    """
    info = line.split(":")[1].strip().split(" ")
    if len(info) < 1:
        raise ConnectionParsingError(
            line_nb,
            "Connections must follow this model: "
            "zone1-zone2 OptionnalMetaData['max_link_capacity']",
        )
    if "-" not in info[0] or info[0].count("-") != 1:
        raise ConnectionParsingError(
            line_nb, "Provide only 2 zones separated by '-'"
        )

    max_link_capacity = 1
    if len(info) > 1:
        meta_data = parse_brackets(info[1:], line_nb)
        if len(meta_data) != 1:
            raise ConnectionParsingError(
                line_nb,
                "Connections must follow this model: "
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
    return hub1, hub2, max_link_capacity


def ensure_no_duplicate_connection(
    connections: list[tuple[str, str, int]],
    connection: tuple[str, str, int],
    line_nb: int,
) -> None:
    """Detect and block symmetric duplicate paths in non-directional graphs.

    Normalizes endpoints alphabetically to
    identify whether 'A-B' matches 'B-A'.

    Args:
        connections: Global list logging active validated connection tuples.
        connection: Targeted connection candidate currently evaluated.
        line_nb: The tracking context line number sequence index for errors.

    Raises:
        ConnectionParsingError: If identical bidirectional paths are recorded.
    """
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
    """Validate graph referential integrity across all connection points.

    Iterates through accumulated link targets to catch and flag any routes
    referencing nodes missing from the global hub register.

    Args:
        connections: List containing all parsed route configuration triplets.
        hubs: Instantiated Node instances tracking registered stations.

    Raises:
        ConnectionParsingError: If a connection binds to an unregistered hub.
    """
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
