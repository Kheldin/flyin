"""Main entry point script responsible for initializing the application.

Configures environment properties, compiles layout maps from terminal
arguments, provisions multimedia subsystems, and triggers the active core game
loop framework inside execution blocks.
"""

import os
import argparse
import sys
# Suppress the default Pygame community greeting prompt in standard outputs
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import pygame as pg  # noqa: E402

from game.game_loop import game_loop  # noqa: E402
from parsing.parsing import parse_file  # noqa: E402


if __name__ == "__main__":

    # ArgParse init
    parser = argparse.ArgumentParser(
        description="Multi-Agent Space-Time Drone Simulation Visualizer")
    parser.add_argument("map_file",
                        help="Path to the custom plaintext map file")

    args = parser.parse_args()
    try:
        loaded_map = parse_file(args.map_file)
    except Exception as error:
        print(f"Error parsing map: {error}", file=sys.stderr)
        sys.exit(1)
    pg.init()
    try:
        game_loop(loaded_map, False)
    except KeyboardInterrupt:
        print("\nSimulation aborted by user.", end="")
    finally:
        pg.quit()
