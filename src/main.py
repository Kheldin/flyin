import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
import pygame  # noqa: E402
from parsing.parsing import parse_file  # noqa: E402
from game.game_loop import game_loop  # noqa: E402


def main() -> None:
    try:
        map = parse_file()
        pygame.init()
        game_loop(map)
    except Exception as e:
        print(e)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
