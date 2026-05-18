from models.map import Color

class ParsingError(Exception):
    """Raised when the map file contains a syntax or semantic error."""

    def __init__(self, line_no: int, reason: str) -> None:
        super().__init__(f"Line {line_no}: {reason}")
        self.line_no = line_no
        self.reason  = reason


class HubParsingError(ParsingError):
    """Raised when hub sections are not well defined in map files"""
    valid_color = [c.value for c in Color]
    valid_meta_keys = ["zone", "max_drones", "color"]
    def __init__(self, line_no: int, reason: str) -> None:
        super().__init__(line_no, reason)
        # print(f"Valid MedataData: {self.valid_meta_keys}\nValid color: {self.valid_color}")


class ConnectionParsingError(ParsingError):
    """Raised when hub sections are not well defined in map files"""
    valid_color = [c.value for c in Color]
    valid_meta_keys = ["zone", "max_drones", "color"]
    def __init__(self, line_no: int, reason: str) -> None:
        super().__init__(line_no, reason)


class ArgumentError(Exception):
    """Raised when with dont have the correct number of args"""
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason  = reason