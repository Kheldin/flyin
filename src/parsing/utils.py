from src.parsing.errors import ParsingError


def parse_brackets(brackets: list[str], line_nb: int) -> dict[str, str | int]:
    if not brackets[0].startswith("[") or not brackets[-1].endswith("]"):
        raise ParsingError(line_nb, "Metadata should be between brackets []")
    brackets[0] = brackets[0].replace("[", "")
    brackets[-1] = brackets[-1].replace("]", "")
    res: dict[str, str | int] = {}
    for data in brackets:
        splited_data: list[str] = data.split("=") 
        res.update({splited_data[0]: splited_data[1]})
    return res