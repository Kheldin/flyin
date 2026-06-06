from parsing.errors import ParsingError


def parse_brackets(brackets: list[str], line_nb: int) -> dict[str, str]:
    if not brackets:
        raise ParsingError(line_nb, "Empty metadata brackets")

    joined = " ".join(brackets).strip()
    if not joined.startswith("[") or not joined.endswith("]"):
        raise ParsingError(line_nb, "Metadata should be between brackets []")

    inner = joined[1:-1].strip()
    if not inner:
        return {}

    res: dict[str, str] = {}
    tokens = inner.split()
    for token in tokens:
        if "=" not in token:
            raise ParsingError(line_nb, f"Invalid metadata token '{token}'")
        key, val = token.split("=", 1)
        key = key.strip()
        val = val.strip()
        if not key or not val:
            raise ParsingError(line_nb, f"Invalid metadata token '{token}'")
        res[key] = val

    return res
