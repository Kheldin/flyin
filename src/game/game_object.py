"""User interface text component rendering system.

Provides specialized sprite extensions designed to build, composition-layer,
and position uniform text badges on top of active scenes.
"""

from typing import Any

import pygame as pg


class LabelSprite(pg.sprite.Sprite):
    """Label sprite class for structural UI text badge elements."""

    def __init__(self, *groups: pg.sprite.AbstractGroup[Any]) -> None:
        """Initialize the base sprite structural containers.

        Args:
            *groups: Target abstract sprite layer groups to register with.
        """
        super().__init__(*groups)
        self.image: pg.Surface
        self.rect: pg.Rect

    def setup(
        self,
        text: str,
        font: pg.font.Font,
        center: tuple[int, int],
        text_color: tuple[int, int, int] = (241, 245, 249),
        bg_color: tuple[int, int, int, int] = (13, 17, 23, 220),
        border_color: tuple[int, int, int, int] = (255, 255, 255, 28),
    ) -> None:
        """Construct surface graphics and assign screen anchor points.

        Args:
            text: Raw string characters to overlay into the center window.
            font: Target Pygame Font style to execute internal blit renders.
            center: Coordinate pixel destination anchoring the final sprite.
            text_color: RGB collection parameters setting typography color.
            bg_color: RGBA parameters assigning card backplate fill options.
            border_color: RGBA metrics configuring layout profile line cuts.
        """
        text_surface = font.render(text, True, text_color)
        text_rect = text_surface.get_rect()

        # Dynamic box scaling based on character dimensions and padding
        padding_x, padding_y = 10, 5
        width = text_rect.width + padding_x * 2
        height = text_rect.height + padding_y * 2

        # Create localized transparent canvas profile
        self.image = pg.Surface((width, height), pg.SRCALPHA)

        # Draw background fill layer and fine alignment borders
        pg.draw.rect(
            self.image, bg_color, self.image.get_rect(), border_radius=6
        )
        pg.draw.rect(
            self.image,
            border_color,
            self.image.get_rect(),
            width=1,
            border_radius=6,
        )

        # Center text coordinates on top of the background composition canvas
        text_offset = text_surface.get_rect(center=(width // 2, height // 2))
        self.image.blit(text_surface, text_offset)

        # Align sprite frame rect variables down to pixel targets
        self.rect = self.image.get_rect(center=center)

    def update(self) -> None:
        """Process cyclic frame transformations."""
