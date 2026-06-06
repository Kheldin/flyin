"""Main entry point script responsible for initializing the application.

Configures environment properties, compiles layout maps from terminal
arguments, provisions multimedia subsystems, and triggers the active core game
loop framework inside execution blocks.
"""

import os

# Suppress the default Pygame community greeting prompt in standard outputs
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import pygame as pg  # noqa: E402

from game.game_loop import game_loop  # noqa: E402
from parsing.parsing import parse_file  # noqa: E402


def main() -> None:
    """Orchestrate compilation and subsystem allocations sequentially.

    Parses target asset definitions, signals driver starts, and passes control
    mechanics to background viewport pipelines inside isolated boundaries.
    """
    try:
        map_ = parse_file()
        pg.init()
        game_loop(map_)
    except Exception as e:
        print(e)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
