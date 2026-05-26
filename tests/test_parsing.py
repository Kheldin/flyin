import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from models.map import Color
from parsing.errors import ConnectionParsingError
from parsing.parse_hub import parse_hub
from parsing.parsing import parse_file


class ParsingTests(unittest.TestCase):
    def test_parse_hub_defaults_invalid_color_to_red(self) -> None:
        hub = parse_hub(
            "hub: alpha 1 2 [color=not_a_real_color]", 1, False, False
        )

        self.assertEqual(hub.color, Color.RED)

    def test_parse_file_rejects_connection_to_hub_defined_later(self) -> None:
        map_text = textwrap.dedent(
            """\
            nb_drones: 1
            start_hub: start 0 0 [color=green]
            connection: start-goal
            end_hub: goal 1 0 [color=red]
            """
        )

        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False
        ) as handle:
            handle.write(map_text)
            map_path = handle.name

        self.addCleanup(Path(map_path).unlink, missing_ok=True)

        with patch.object(sys, "argv", ["main.py", map_path]):
            with self.assertRaises(ConnectionParsingError) as exc:
                parse_file()

        self.assertEqual(str(exc.exception), "Line 3: Unknown hub: 'goal'")


if __name__ == "__main__":
    unittest.main()
