import pygame
from pygame.locals import *
import sys

FPS = pygame.time.Clock()
FPS.tick(60)

BLUE  = (0, 0, 255)
RED   = (255, 0, 0)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

SCREEN_WIDTH = 400
SCREEN_HEIGHT = 600

DISPLAYSURF = pygame.display.set_mode((1200, 800))
DISPLAYSURF.fill(WHITE)
pygame.display.set_caption("FlyIn")

def game_loop() -> None:
    while (True):
       
        for event in pygame.event.get():
            if event.type == quit:
                pygame.quit()
                sys.exit()
        pygame.display.update()