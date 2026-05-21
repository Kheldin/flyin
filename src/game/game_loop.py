import pygame
from pygame.locals import QUIT
import sys
from game.utils import load_image

clock = pygame.time.Clock()
clock.tick(60)

BLUE  = (0, 0, 255)
RED   = (255, 0, 0)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

SCREEN_WIDTH = 400
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((1920, 1080))
pygame.display.set_caption("FlyIn")



speed = [20, 20]

def game_loop() -> None:
    # dronerect = drone.get_rect()
    # drone = pygame.image.load("src/game/assets/drone/Forward.png")
    # drone = pygame.transform.scale(drone, (200, 200))
    drone, dronerect = load_image("drone/Forward.png", scale=5)

    while (True):
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
        screen.fill(GREEN)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            dronerect = dronerect.move([0, -20])
        if keys[pygame.K_s]:
            dronerect = dronerect.move([0, 20])
        if keys[pygame.K_a]:
            dronerect = dronerect.move([-20, 0])
        if keys[pygame.K_d]:
            dronerect = dronerect.move([20, 0])

        
        clock.tick(60)
        screen.blit(drone, dronerect)
        pygame.display.flip()