import pygame as pg
from typing import Any
from models.map import Hub
from models.map import Drone, Hub


class HubSprite(pg.sprite.Sprite):
    """Hub sprite class"""
    
    def __init__(self, *groups: pg.sprite.AbstractGroup[Any]) -> None:
        super().__init__(*groups)

    def setup(self, hub: Hub, center: tuple[int, int], size: int = 100) -> None:
        """Initialize sprite visuals using hub properties.

        - `size` controls the surface size (diameter) used for the circle.
        - Hub color is respected using the `hub.color` value.
        """
        self.hub = hub
        diameter = max(4, int(size))
        self.image = pg.Surface((diameter, diameter), pg.SRCALPHA)
        try:
            color = pg.Color(hub.color.value)
        except Exception:
            color = (0, 0, 255)
        pg.draw.circle(self.image, color, (diameter // 2, diameter // 2), diameter // 2)
        self.rect = self.image.get_rect(center=center)

    def update(self):
        pass


class DroneSprite(pg.sprite.Sprite):
    """Drone sprite class"""

    def __init__(self, *groups: pg.sprite.AbstractGroup[Any]) -> None:
        super().__init__(*groups)

    def setup(self, drone: Drone, center: tuple[int, int], size: int = 10) -> None:
        """Initialize a compact square marker for a drone."""
        self.drone = drone
        edge = max(4, int(size))
        self.image = pg.Surface((edge, edge), pg.SRCALPHA)
        rect = self.image.get_rect()
        pg.draw.rect(self.image, (35, 35, 35), rect, border_radius=2)
        pg.draw.rect(self.image, (255, 255, 255), rect, width=1, border_radius=2)
        self.rect = self.image.get_rect(center=center)

    def update(self):
        pass

# class HubGroup(pg.sprite.Group):
#     def __init__(self, *sprites: HubSprite) -> None:
#         super().__init__(*sprites)