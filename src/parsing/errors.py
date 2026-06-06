"""Custom exception modules tracking structural application errors.

Provides dedicated exception subclasses to intercept configuration syntax
anomalies, tokenization line mismatches, and CLI input argument violations.
"""


class ParsingError(Exception):
    """Raise when the map configuration file contains a semantic mismatch."""

    def __init__(self, line_no: int, reason: str) -> None:
        """Initialize the parsing exception context with location properties.

        Args:
            line_no: The absolute line number sequence index inside the file.
            reason: Text detail identifying the core validation failure.
        """
        super().__init__(f"Line {line_no}: {reason}")
        self.line_no = line_no
        self.reason = reason


class HubParsingError(ParsingError):
    """Raise when structural hub records fail layout schema rules."""

    def __init__(self, line_no: int, reason: str) -> None:
        """Initialize the hub exception utilizing
        the parsing baseline attributes.

        Args:
            line_no: The absolute line number sequence index inside the file.
            reason: Text detail identifying the node validation failure.
        """
        super().__init__(line_no, reason)


class ConnectionParsingError(ParsingError):
    """Raise when link or path structural bounds carry invalid tokens."""

    def __init__(self, line_no: int, reason: str) -> None:
        """Initialize connection exception utilizing parsing baseline values.

        Args:
            line_no: The absolute line number sequence index inside the file.
            reason: Text detail identifying the path validation failure.
        """
        super().__init__(line_no, reason)


class ArgumentError(Exception):
    """Raise when command-line parameters mismatch required input schemas."""

    def __init__(self, reason: str) -> None:
        """Initialize the argument exception enclosing the core violation tag.

        Args:
            reason:
                String message tracing missing flags or bad parameter options.
        """
        super().__init__(reason)
        self.reason = reason
