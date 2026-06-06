"""Metadata bracket tokenizer and syntax parser module.

Provides specialized algorithms designed to extract, validate, and structure
key-value option attributes encapsulated inside bracket token segments.
"""

from parsing.errors import ParsingError


def parse_brackets(brackets: list[str], line_nb: int) -> dict[str, str]:
    """Parse inline metadata attribute structures enclosed in brackets.

    Converts raw bracket tokens formatted as [key1=val1 key2=val2] into
    a standard key-to-value string mapping collection.

    Args:
        brackets: Sequential list of string parts representing metadata bounds.
        line_nb: The tracking context line number sequence index for errors.

    Returns:
        A formatted collection tracking configured string parameter keys.

    Raises:
        ParsingError: If structural formats, boundaries, tags, or assignment
            operators contain empty profiles or syntax violations.
    """
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

        # Split at the first assignment token character to preserve data
        key, val = token.split("=", 1)
        key = key.strip()
        val = val.strip()

        if not key or not val:
            raise ParsingError(line_nb, f"Invalid metadata token '{token}'")

        res[key] = val

    return res
