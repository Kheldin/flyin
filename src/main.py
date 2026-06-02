import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
from parsing.parsing import parse_file
from game.game_loop import game_loop


def main():
    try:
        map = parse_file()

        pygame.init()
        game_loop(map)
    except Exception as e:
        print(e)


if __name__ == "__main__":
    # try:
    #     main()
    # except Exception as e:
    #     print(e)
    main()