"""Hub string parser and node structural validation mechanics module.

Provides procedural text-parsing algorithms and network constraint rules
to validate node attributes, enforce coordinate formats
and prevent duplicates.
"""

from models.map import Metadata, Node, Zone
from parsing.errors import HubParsingError, ParsingError
from parsing.parse_brackets import parse_brackets


def parse_hub(line: str, line_nb: int, start: bool, end: bool) -> Node:
    """Parse a single text hub record into a validated structural Node model.

    Decodes node layout definitions like 'BaseA 100 250 [zone=priority]'
    and enforces baseline type rules and fallback values.

    Args:
        line: The raw unparsed text record line coming from the map file.
        line_nb: The tracking context line number sequence index for errors.
        start: Flag indicating if this hub is marked as the network origin.
        end: Flag indicating if this hub is marked as the final destination.

    Returns:
        An instantiated and fully validated Node object representation.

    Raises:
        HubParsingError: If schema lengths or attribute configurations are
            violated.
        ParsingError: If coordinate conversions fail or metadata keys and
            assignment sub-values are invalid.
    """
    valid_meta_keys = ["zone", "max_drones", "color"]
    info = line.split(":")[1].strip().split(" ")
    if len(info) < 3:
        raise HubParsingError(
            line_nb,
            "Hubs must follow this model: "
            f"name x y OptionnalMetaData{valid_meta_keys}",
        )

    name = info[0]
    if "-" in name:
        raise HubParsingError(
            line_nb,
            f"Hub name '{name}' is invalid. "
            "Names must not contain spaces or '-'.",
        )

    try:
        pos_x = int(info[1])
        pos_y = int(info[2])
    except Exception as e:
        raise ParsingError(
            line_nb,
            f"{e!r}\n"
            "Hubs must follow this model: "
            f"name x y OptionnalMetaData{valid_meta_keys}",
        )

    # Establish baseline runtime configurations before checking brackets
    zone: Zone | None = Zone.NORMAL
    color: str | None = "red"
    max_drones: int | None = 1

    if len(info) >= 4:
        meta_data = parse_brackets(info[3:], line_nb)
        for key in meta_data.keys():
            if key not in valid_meta_keys:
                raise ParsingError(
                    line_nb,
                    f"Metadata '{key}' is invalid. "
                    f"Valid metadata: '{valid_meta_keys}'",
                )

            if key == "zone":
                try:
                    zone = Zone.get_zone(meta_data["zone"])
                except Exception:
                    valid = ["normal", "restricted", "priority", "blocked"]
                    raise ParsingError(
                        line_nb,
                        f"Zone '{meta_data['zone']}' "
                        f"is invalid. Valid zones: {valid}",
                    )
            elif key == "color":
                color = meta_data["color"]
            else:
                try:
                    max_drones = int(meta_data["max_drones"])
                    if max_drones <= 0:
                        raise HubParsingError(
                            line_nb, "max_drones should be greater than 0."
                        )
                except Exception as e:
                    raise ParsingError(line_nb, repr(e))

    metadata = Metadata(
        zone=zone, color=color, max_link_capacity=None, max_drones=max_drones
    )
    return Node(name=name, x=pos_x, y=pos_y, metadata=metadata)


def ensure_no_duplicate_hub(hubs: list[Node], hub: Node, line_nb: int) -> None:
    """Enforce identifier and geometric uniqueness constraints across nodes.

    Prevents name collisions and protects against overlapping coordinate sets
    within the global layout registry.

    Args:
        hubs: Global list logging active validated Node configurations.
        hub: Targeted node candidate currently evaluated.
        line_nb: The tracking context line number sequence index for errors.

    Raises:
        ParsingError: If duplicate identifiers or overlapping grid positions
            are recorded.
    """
    for existing_hub in hubs:
        if existing_hub.name == hub.name:
            raise ParsingError(line_nb, f"Duplicate hub name: '{hub.name}'")
        if existing_hub.x == hub.x and existing_hub.y == hub.y:
            raise ParsingError(
                line_nb, f"Duplicate hub position: ({hub.x}, {hub.y})"
            )
