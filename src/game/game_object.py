import pygame as pg
from typing import Any
from models.map import Node


class HubSprite(pg.sprite.Sprite):
    def __init__(self, *groups: pg.sprite.AbstractGroup[Any]) -> None:
        super().__init__(*groups)
        self.hub: Node
        self.image: pg.Surface = pg.Surface((0, 0))
        self.rect: pg.Rect = pg.Rect(0, 0, 0, 0)
        self.aura: pg.Surface | None = None
        self.is_rainbow: bool = False
        
        # State tracking fields decoupled to avoid cache collision
        self.last_size: int = -1
        self.last_hub_drone_count: int = -1
        self.last_label_drone_count: int = -1
        self.last_zoom: float = -1.0
        
        self.name_label: LabelSprite | None = None
        self.count_label: LabelSprite | None = None

    def setup(self, hub: Node, center: tuple[int, int], size: int = 100, drone_count: int = 0) -> None:
        self.hub = hub
        self.is_rainbow = (hub.metadata.color or "").lower() == "rainbow"
        diameter = max(4, int(size))
        color = resolve_hub_color(hub)
        color_rgb = (color.r, color.g, color.b)

        if drone_count > 0:
            aura_r = max(1, diameter // 2 + (diameter // 5))
            self.aura = _get_aura_surface(aura_r, color_rgb, HUB_GLOW_ALPHA)
        else:
            self.aura = None

        # Uses isolated hub property tracking
        if self.last_size != diameter or self.last_hub_drone_count != drone_count or self.is_rainbow:
            self.image = pg.Surface((diameter, diameter), pg.SRCALPHA)
            pg.draw.circle(self.image, color, (diameter // 2, diameter // 2), diameter // 2)
            
            inner_dot_r = max(1, diameter // 12)
            ring_surf = _get_ring_surface(diameter, inner_dot_r)
            self.image.blit(ring_surf, (0, 0))
            
            self.last_size = diameter
            self.last_hub_drone_count = drone_count

        self.rect = self.image.get_rect(center=center)

    def update(self, *args: Any, **kwargs: Any) -> None:
        if self.is_rainbow:
            diameter = max(4, self.rect.width)
            color = resolve_hub_color(self.hub)
            self.image = pg.Surface((diameter, diameter), pg.SRCALPHA)
            pg.draw.circle(self.image, color, (diameter // 2, diameter // 2), diameter // 2)
            inner_dot_r = max(1, diameter // 12)
            ring_surf = _get_ring_surface(diameter, inner_dot_r)
            self.image.blit(ring_surf, (0, 0))
            if self.last_hub_drone_count > 0:
                aura_r = max(1, diameter // 2 + (diameter // 5))
                self.aura = _get_aura_surface(aura_r, (color.r, color.g, color.b), HUB_GLOW_ALPHA)

class DroneSprite(pg.sprite.Sprite):
    """Drone sprite class"""

    def __init__(self, *groups: pg.sprite.AbstractGroup[Any]) -> None:
        super().__init__(*groups)

    def setup(self, drone_id: int, center: tuple[int, int], size: int = 10) -> None:
        self.drone_id = drone_id
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


class LabelSprite(pg.sprite.Sprite):
    """Label sprite class for UI text elements."""

    def __init__(self, *groups: pg.sprite.AbstractGroup[Any]) -> None:
        super().__init__(*groups)

    def setup(
        self,
        text: str,
        font: pg.font.Font,
        center: tuple[int, int],
        text_color: tuple[int, int, int] = (241, 245, 249),     
        bg_color: tuple[int, int, int, int] = (13, 17, 23, 220),
        border_color: tuple[int, int, int, int] = (255, 255, 255, 28)
    ) -> None:
        """Initialize label graphics and positioning."""
        text_surface = font.render(text, True, text_color)
        text_rect = text_surface.get_rect()

        # Dynamic size based on text dimension + layout constants
        padding_x, padding_y = 10, 5
        width = text_rect.width + padding_x * 2
        height = text_rect.height + padding_y * 2

        # Create base canvas surface
        self.image = pg.Surface((width, height), pg.SRCALPHA)
        
        # Draw background and thin outline borders
        pg.draw.rect(self.image, bg_color, self.image.get_rect(), border_radius=6)
        pg.draw.rect(self.image, border_color, self.image.get_rect(), width=1, border_radius=6)
        
        # Center the text directly onto the badge image
        text_offset = text_surface.get_rect(center=(width // 2, height // 2))
        self.image.blit(text_surface, text_offset)
        
        # Position sprite anchor relative to screen pixels
        self.rect = self.image.get_rect(center=center)

    def update(self) -> None:
        pass