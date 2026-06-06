import pygame as pg
from typing import Any


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
        border_color: tuple[int, int, int, int] = (255, 255, 255, 28),
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
        pg.draw.rect(self.image, bg_color,
                     self.image.get_rect(),
                     border_radius=6)
        pg.draw.rect(
            self.image, border_color,
            self.image.get_rect(), width=1,
            border_radius=6
        )

        # Center the text directly onto the badge image
        text_offset = text_surface.get_rect(center=(width // 2, height // 2))
        self.image.blit(text_surface, text_offset)

        # Position sprite anchor relative to screen pixels
        self.rect = self.image.get_rect(center=center)

    def update(self) -> None:
        pass
