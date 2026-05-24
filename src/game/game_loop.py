import pygame as pg
from pygame.locals import QUIT
import sys
from game.utils import load_image
from game.game_object import HubSprite
from models.map import Map


clock = pg.time.Clock()
clock.tick(60)

BLUE  = (0, 0, 255)
RED   = (255, 0, 0)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

SCREEN_WIDTH = 400
SCREEN_HEIGHT = 600
screen = pg.display.set_mode((1280, 720), pg.SCALED)
pg.display.set_caption("FlyIn")



speed = [20, 20]


def _scale_hub_positions(map: Map, screen: pg.Surface, padding: int = 40) -> dict[str, tuple[int, int]]:
    if not map.hubs:
        return {}

    min_x = min(hub.x for hub in map.hubs)
    max_x = max(hub.x for hub in map.hubs)
    min_y = min(hub.y for hub in map.hubs)
    max_y = max(hub.y for hub in map.hubs)

    drawable_w = max(1, screen.get_width() - (2 * padding))
    drawable_h = max(1, screen.get_height() - (2 * padding))

    range_x = max(1, max_x - min_x)
    range_y = max(1, max_y - min_y)

    positions: dict[str, tuple[int, int]] = {}
    for hub in map.hubs:
        scaled_x = padding + int(((hub.x - min_x) / range_x) * drawable_w)
        scaled_y = padding + int(((hub.y - min_y) / range_y) * drawable_h)
        positions[hub.name] = (scaled_x, scaled_y)

    return positions

def game_loop(map: Map) -> None:
    drone, dronerect = load_image("drone/Forward.png", scale=5)

    scaled_positions = _scale_hub_positions(map, screen)

    hubs: list[HubSprite] = []
    for hub in map.hubs:
        hub_sprite = HubSprite()
        hub_sprite.setup(hub, scaled_positions[hub.name])
        hubs.append(hub_sprite)

    allsprites = pg.sprite.RenderPlain(*hubs)

    while (True):
        for event in pg.event.get():
            if event.type == QUIT:
                pg.quit()
                sys.exit()
        screen.fill(GREEN)

        # keys = pg.key.get_pressed()
        # if keys[pg.K_w]:
        #     dronerect = dronerect.move([0, -20])
        # if keys[pg.K_s]:
        #     dronerect = dronerect.move([0, 20])
        # if keys[pg.K_a]:
        #     dronerect = dronerect.move([-20, 0])
        # if keys[pg.K_d]:
        #     dronerect = dronerect.move([20, 0])

        
        clock.tick(60)
        allsprites.draw(screen)
        screen.blit(drone, dronerect)
        pg.display.flip()