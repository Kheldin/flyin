class ParsingError(Exception):
    """Raised when the map file contains a syntax or semantic error."""

    def __init__(self, line_no: int, reason: str) -> None:
        super().__init__(f"Line {line_no}: {reason}")
        self.line_no = line_no
        self.reason  = reason


class ArgumentError(Exception):
    """Raised when with dont have the correct number of arg"""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason  = reason