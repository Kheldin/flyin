import pygame as pg
from typing import Any, cast
from models.map import Drone, Hub


class HubSprite(pg.sprite.Sprite):
    """Hub sprite class"""
    
    def __init__(self, *groups: pg.sprite.AbstractGroup[Any]) -> None:
        super().__init__(*groups)
        self.aura: pg.Surface | None = None
        self.aura_offset: int = 0

    def setup(self, hub: Hub, center: tuple[int, int], size: int = 100) -> None:
        """Initialize sprite visuals using hub properties.

        - `size` controls the surface size (diameter) used for the circle.
        - Hub color is respected using the `hub.color` value.
        """
        self.hub = hub
        diameter = max(4, int(size))
        self.image = pg.Surface((diameter, diameter), pg.SRCALPHA)
        try:
            raw_color = cast(str, getattr(hub.color, "value", hub.color))
            color = pg.Color(raw_color)
        except Exception:
            color = pg.Color("red")
        pg.draw.circle(self.image, color, (diameter // 2, diameter // 2), diameter // 2)
        self.rect = self.image.get_rect(center=center)

    def update(self):
        pass


class DroneSprite(pg.sprite.Sprite):
    """Drone sprite class"""

    def __init__(self, *groups: pg.sprite.AbstractGroup[Any]) -> None:
        super().__init__(*groups)

    def setup(self, drone: Drone, center: tuple[int, int], size: int = 10) -> None:
        self.drone = drone
        edge = max(4, int(size))
        self.image = pg.Surface((edge, edge), pg.SRCALPHA)
        # Soft dark square with white outline
        pg.draw.rect(self.image, (20, 28, 40, 230), self.image.get_rect(), border_radius=3)
        pg.draw.rect(self.image, (255, 255, 255, 180), self.image.get_rect(), width=1, border_radius=3)
        # Small center dot
        mid = edge // 2
        pg.draw.circle(self.image, (200, 220, 255, 200), (mid, mid), max(1, edge // 5))
        self.rect = self.image.get_rect(center=center)

    def update(self):
        pass