import pygame as pg
from typing import Any
from models.map import Hub


class HubSprite(pg.sprite.Sprite):
    """Hub sprite class"""
    
    def __init__(self, *groups: pg.sprite.AbstractGroup[Any]) -> None:
        super().__init__(*groups)

    def setup(self, hub: Hub, center: tuple[int, int]) -> None:
        self.hub = hub
        self.image = pg.Surface((40, 40), pg.SRCALPHA)
        pg.draw.circle(self.image, (0, 0, 255), (20, 20), 20)
        self.rect = self.image.get_rect(center=center)

    def update(self):
        pass

# class HubGroup(pg.sprite.Group):
#     def __init__(self, *sprites: HubSprite) -> None:
#         super().__init__(*sprites)