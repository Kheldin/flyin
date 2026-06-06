"""Rendering engine module for managing, scaling, and drawing map graphics.

Handles the procedural visualization of nodes (hubs), links (connections),
ambient animations, and text interfaces on top of a dynamic camera system.
"""

import functools
from typing import Any

import pygame as pg

from game.camera import Camera, DEFAULT_ZOOM
from game.game_object import LabelSprite
from models.map import Map, Node

# --- Geometric & Rendering Constants ---
BASE_HUB_DIAMETER: int = 100
BASE_CONNECTION_WIDTH: int = 4
BASE_NAME_FONT_SIZE: int = 20
BASE_COUNT_FONT_SIZE: int = 26

# --- Color Palettes & Transparency Profiles (RGBA/RGB) ---
CONNECTION_COLOR_ACTIVE: tuple[int, int, int] = (173, 216, 230)
CONNECTION_COLOR_IDLE: tuple[int, int, int] = (173, 216, 230)
CONNECTION_ACTIVE_ALPHA: int = 160
CONNECTION_IDLE_ALPHA: int = 60

HUB_RING_COLOR: tuple[int, int, int, int] = (255, 255, 255, 55)
HUB_INNER_DOT_COLOR: tuple[int, int, int] = (255, 255, 255)
HUB_GLOW_ALPHA: int = 80

LABEL_PADDING_X: int = 10
LABEL_PADDING_Y: int = 5
LABEL_GAP: int = 6
LABEL_BG_COLOR: tuple[int, int, int, int] = (13, 17, 23, 220)
LABEL_BORDER_COLOR: tuple[int, int, int, int] = (255, 255, 255, 28)
LABEL_TEXT_COLOR: tuple[int, int, int] = (241, 245, 249)

CONN_BADGE_BORDER: tuple[int, int, int, int] = (245, 158, 11, 180)
CONN_BADGE_TEXT: tuple[int, int, int] = (251, 191, 36)

GRID_COLOR: tuple[int, int, int, int] = (255, 255, 255, 8)
GRID_SPACING: int = 48
WORLD_SPREAD: float = 1.6


# --- Performance Optimization Caching Mechanisms ---
@functools.cache
def get_font(size: int) -> pg.font.Font:
    """Cache font assets globally to bypass continuous filesystem calls.

    Args:
        size: The desired point size of the font.

    Returns:
        The cached Pygame Font object instance.
    """
    return pg.font.Font(None, size)


@functools.cache
def _get_aura_surface(
    radius: int, color_rgb: tuple[int, int, int], alpha: int
) -> pg.Surface:
    """Generate and cache a translucent glowing aura for active hubs.

    Args:
        radius: The circle radius of the glow canvas.
        color_rgb: Base color spectrum to apply on the aura.
        alpha: Transparency value from 0 to 255.

    Returns:
        The transparent cached Surface containing the circle.
    """
    surf = pg.Surface((radius * 2, radius * 2), pg.SRCALPHA)
    pg.draw.circle(surf, (*color_rgb, alpha), (radius, radius), radius)
    return surf


@functools.cache
def _get_ring_surface(size: int, inner_dot_radius: int) -> pg.Surface:
    """Generate and cache decorative sub-elements embedded within hubs.

    Args:
        size: The bounding box dimensions of the target ring canvas.
        inner_dot_radius: The size of the inner center accent point.

    Returns:
        A transparent Surface overlaying the hub body texture.
    """
    ring = pg.Surface((size, size), pg.SRCALPHA)
    half = size // 2
    pg.draw.circle(
        ring, HUB_RING_COLOR, (half, half), max(1, half - 1), width=1
    )
    pg.draw.circle(
        ring, (*HUB_INNER_DOT_COLOR, 200), (half, half), inner_dot_radius
    )
    return ring


# --- Arithmetic & Utility Functions ---
def scale_value(base_value: int, zoom: float) -> int:
    """Scale an integer asset property proportionally to the camera zoom.

    Args:
        base_value: The unscaled pixel length property.
        zoom: Current zoom magnification factor of the active camera.

    Returns:
        The scaled integer boundary value, clamped to a minimum of 1.
    """
    return max(1, int(base_value * (zoom / DEFAULT_ZOOM)))


def get_hub_name(hub_or_str: Node | str) -> str:
    """Extract string identifier safely from either a Node or raw string.

    Args:
        hub_or_str: Target reference to extract identification values from.

    Returns:
        The extracted string name representation.
    """
    return hub_or_str.name if isinstance(hub_or_str, Node) else str(hub_or_str)


def resolve_hub_color(hub: Node) -> pg.Color:
    """Resolve metadata tags into Pygame Color objects with HSV animation.

    Args:
        hub: The node instance whose metadata profile contains the color keys.

    Returns:
        The computed Pygame Color instance representation.
    """
    color_str = (hub.metadata.color or "red").lower()

    if color_str == "rainbow":
        # Cycle through colors smoothly based on running execution ticks
        ticks = pg.time.get_ticks()
        hue = (ticks // 4) % 360
        color = pg.Color(0)
        color.hsva = (hue, 90, 100, 100)
        return color

    try:
        return pg.Color(color_str)
    except ValueError:
        return pg.Color("red")


class HubSprite(pg.sprite.Sprite):
    """Graphical representation of a map Node tracking structural changes."""

    def __init__(self, *groups: pg.sprite.AbstractGroup[Any]) -> None:
        """Initialize sprite properties and dirty-flag state records."""
        super().__init__(*groups)
        self.hub: Node
        self.image: pg.Surface = pg.Surface((0, 0))
        self.rect: pg.Rect = pg.Rect(0, 0, 0, 0)
        self.aura: pg.Surface | None = None
        self.is_rainbow: bool = False

        # Structural flags used to skip redundant blits/re-renders
        self.last_size: int = -1
        self.last_drone_count: int = -1
        self.last_label_drone_count: int = -1
        self.last_zoom: float = -1.0

        self.name_label: LabelSprite | None = None
        self.count_label: LabelSprite | None = None

    def setup(
        self,
        hub: Node,
        center: tuple[int, int],
        size: int = 100,
        drone_count: int = 0,
    ) -> None:
        """Configure internal states and update geometric bounds.

        Args:
            hub: The structural map node source object.
            center: Coordinate pair to pin down sprite center on viewport.
            size: Base diameter size of the circular graphic.
            drone_count: Total active items stationed within this point.
        """
        self.hub = hub
        self.is_rainbow = (hub.metadata.color or "").lower() == "rainbow"
        diameter = max(4, int(size))
        color = resolve_hub_color(hub)
        color_rgb = (color.r, color.g, color.b)

        # Allocate glow map size if occupied by drones
        if drone_count > 0:
            aura_r = max(1, diameter // 2 + (diameter // 5))
            self.aura = _get_aura_surface(aura_r, color_rgb, HUB_GLOW_ALPHA)
        else:
            self.aura = None

        # Re-draw the canvas textures only if attributes or cycle shifts
        if (
            self.last_size != diameter
            or self.last_drone_count != drone_count
            or self.is_rainbow
        ):
            self.image = pg.Surface((diameter, diameter), pg.SRCALPHA)
            pg.draw.circle(
                self.image,
                color,
                (diameter // 2, diameter // 2),
                diameter // 2,
            )

            inner_dot_r = max(1, diameter // 12)
            ring_surf = _get_ring_surface(diameter, inner_dot_r)
            self.image.blit(ring_surf, (0, 0))

            self.last_size = diameter
            self.last_drone_count = drone_count

        self.rect = self.image.get_rect(center=center)

    def update(self, *args: Any, **kwargs: Any) -> None:
        """Process real-time canvas mutations such as active color cycles.

        Args:
            *args: Arbitrary positional arguments forwarded by groups.
            **kwargs: Arbitrary keyword arguments forwarded by groups.
        """
        if self.is_rainbow:
            diameter = max(4, self.rect.width)
            color = resolve_hub_color(self.hub)

            # Re-render shifting base canvas profile
            self.image = pg.Surface((diameter, diameter), pg.SRCALPHA)
            pg.draw.circle(
                self.image,
                color,
                (diameter // 2, diameter // 2),
                diameter // 2,
            )

            inner_dot_r = max(1, diameter // 12)
            ring_surf = _get_ring_surface(diameter, inner_dot_r)
            self.image.blit(ring_surf, (0, 0))

            # Maintain glow synchronization with rainbow cycles
            if self.last_drone_count > 0:
                aura_r = max(1, diameter // 2 + (diameter // 5))
                self.aura = _get_aura_surface(
                    aura_r, (color.r, color.g, color.b), HUB_GLOW_ALPHA
                )


# --- Core Pipeline Calculations & Drawing Functions ---
def compute_base_hub_pixels(
    map_: Map,
    screen: pg.Surface,
    padding: int = 20,
    spread: float = WORLD_SPREAD,
) -> dict[str, tuple[float, float]]:
    """Normalize raw node positions into balanced screen coordinates.

    Args:
        map_: Source dictionary map structure detailing global components.
        screen: Render target target surface tracking view constraints.
        padding: Safe viewport boundary margins protecting border clipping.
        spread: Dispersion multiplier stretching elements away from origin.

    Returns:
        A map collection of screen positions matching unique names.
    """
    if not map_.hubs:
        return {}

    hubs = map_.hubs
    min_x, max_x = min(h.x for h in hubs), max(h.x for h in hubs)
    min_y, max_y = min(h.y for h in hubs), max(h.y for h in hubs)

    drawable_w = max(1, screen.get_width() - 2 * padding)
    drawable_h = max(1, screen.get_height() - 2 * padding)
    range_x, range_y = max(1, max_x - min_x), max(1, max_y - min_y)

    # Perform linear distribution across accessible surface pixels
    base_positions = {
        hub.name: (
            padding + (hub.x - min_x) / range_x * drawable_w,
            padding + (hub.y - min_y) / range_y * drawable_h,
        )
        for hub in hubs
    }

    # Center-outward multiplication to scatter compressed nodes
    total_x = sum(p[0] for p in base_positions.values())
    total_y = sum(p[1] for p in base_positions.values())
    count = len(base_positions)
    center_x, center_y = total_x / count, total_y / count

    return {
        name: (
            center_x + (px - center_x) * spread,
            center_y + (py - center_y) * spread,
        )
        for name, (px, py) in base_positions.items()
    }


def build_hub_sprites(
    map_: Map, base_positions: dict[str, tuple[float, float]], camera: Camera
) -> tuple[list[HubSprite], dict[str, HubSprite]]:
    """Construct sprite instances using initial layout calculations.

    Args:
        map_: Data storage structure parsing geographic elements.
        base_positions: Standard coordinate values mapping items to map center.
        camera: Device model projecting position metrics.

    Returns:
        A tracking structure collection organizing graphic entities.
    """
    hubs: list[HubSprite] = []
    hub_by_name: dict[str, HubSprite] = {}

    for hub in map_.hubs:
        sprite = HubSprite()
        screen_pos = camera.world_to_screen(
            base_positions.get(hub.name, (0.0, 0.0))
        )
        sprite.setup(hub, screen_pos, size=BASE_HUB_DIAMETER)
        hubs.append(sprite)
        hub_by_name[hub.name] = sprite

    return hubs, hub_by_name


def draw_grid(screen: pg.Surface) -> None:
    """Render a faint background tracking grid for ambient depth.

    Args:
        screen: Main view target canvas receiving raw grid pixel line outputs.
    """
    w, h = screen.get_size()
    surf = pg.Surface((w, h), pg.SRCALPHA)
    for x in range(0, w, GRID_SPACING):
        pg.draw.line(surf, GRID_COLOR, (x, 0), (x, h), 1)
    for y in range(0, h, GRID_SPACING):
        pg.draw.line(surf, GRID_COLOR, (0, y), (w, y), 1)
    screen.blit(surf, (0, 0))


def draw_connections(
    screen: pg.Surface,
    map_: Map,
    screen_positions: dict[str, tuple[int, int]],
    zoom: float,
) -> None:
    """Draw straight vector paths connecting dependent hub units.

    Args:
        screen: View target frame container surface.
        map_: Map model layout holding relational connections data.
        screen_positions: Evaluated viewport matrix data tracking locations.
        zoom: Relative scale context setting line width constraints.
    """
    surf = pg.Surface(screen.get_size(), pg.SRCALPHA)
    for conn in map_.connections:
        s1 = screen_positions.get(get_hub_name(conn.node1))
        s2 = screen_positions.get(get_hub_name(conn.node2))
        if s1 is None or s2 is None:
            continue

        # Adjust dimensions and alpha profile according to path state
        active = getattr(conn, "active", False)
        r, g, b = CONNECTION_COLOR_ACTIVE if active else CONNECTION_COLOR_IDLE
        alpha = CONNECTION_ACTIVE_ALPHA if active else CONNECTION_IDLE_ALPHA
        width = scale_value(BASE_CONNECTION_WIDTH if active else 2, zoom)
        pg.draw.line(surf, (r, g, b, alpha), s1, s2, width)

    screen.blit(surf, (0, 0))


def draw_auras(screen: pg.Surface, hub_by_name: dict[str, HubSprite]) -> None:
    """Draw cached ambient halos under nodes carrying active drone units.

    Args:
        screen: Base rendering surface canvas profile layer.
        hub_by_name: Data structure tracking individual graphic instances.
    """
    for sprite in hub_by_name.values():
        if sprite.aura is None:
            continue
        ax = sprite.rect.centerx - sprite.aura.get_width() // 2
        ay = sprite.rect.centery - sprite.aura.get_height() // 2
        screen.blit(sprite.aura, (ax, ay))


def draw_hub_labels(
    screen: pg.Surface,
    hub_by_name: dict[str, HubSprite],
    zoom: float,
    drone_count_per_hub: dict[str, int] | None = None,
) -> None:
    """Render descriptive UI identity tags and numbers around nodes.

    Args:
        screen: Primary scene canvas window layer target.
        hub_by_name: Active node catalog map collection index tracker.
        zoom: Magnification parameter scale tracking text size limits.
        drone_count_per_hub: Mapping data assigning unit logs across names.
    """
    if drone_count_per_hub is None:
        drone_count_per_hub = {}

    for sprite in hub_by_name.values():
        hub = sprite.hub
        drone_count = drone_count_per_hub.get(hub.name, 0)

        # Dynamic spacing off center to prevent overlay clipping
        offset = max(18, sprite.rect.height // 2 + LABEL_GAP * 3)
        name_center = (sprite.rect.centerx, sprite.rect.centery - offset)
        count_center = (sprite.rect.centerx, sprite.rect.centery + offset)

        # Regenerate label textures if zoom or states fluctuate
        if (
            sprite.last_zoom != zoom
            or sprite.last_label_drone_count != drone_count
            or sprite.is_rainbow
            or sprite.name_label is None
            or sprite.count_label is None
        ):
            c = resolve_hub_color(hub)
            name_font = get_font(scale_value(BASE_NAME_FONT_SIZE, zoom))
            count_font = get_font(scale_value(BASE_COUNT_FONT_SIZE, zoom))

            sprite.name_label = LabelSprite()
            sprite.name_label.setup(
                hub.name,
                name_font,
                center=name_center,
                border_color=LABEL_BORDER_COLOR,
            )

            sprite.count_label = LabelSprite()
            sprite.count_label.setup(
                text=str(drone_count),
                font=count_font,
                center=count_center,
                text_color=(c.r, c.g, c.b),
                border_color=(c.r, c.g, c.b, 160),
            )
            sprite.last_zoom = zoom
            sprite.last_label_drone_count = drone_count
        else:
            sprite.name_label.rect.center = name_center
            sprite.count_label.rect.center = count_center

        screen.blit(sprite.name_label.image, sprite.name_label.rect)
        screen.blit(sprite.count_label.image, sprite.count_label.rect)


def draw_drone_on_connections(
    screen: pg.Surface,
    map_: Map,
    screen_positions: dict[str, tuple[int, int]],
    drones_on_connections: dict[tuple[str, str], list[int]] | None = None,
    zoom: float = 1.0,
) -> None:
    """Render numeric badge indicators in the geometric center of paths.

    Args:
        screen: Destination window render surface canvas.
        map_: Structural relationship path network tracker reference.
        screen_positions: Pixel coordinates mapping graph endpoints.
        drones_on_connections: Lookup dictionary tracking transit lists.
        zoom: Camera scale parameter determining context text fonts bounds.
    """
    if drones_on_connections is None:
        drones_on_connections = {}

    surf = pg.Surface(screen.get_size(), pg.SRCALPHA)
    font = get_font(max(12, int(14 * (zoom / 1.0))))

    for conn in map_.connections:
        s1 = screen_positions.get(get_hub_name(conn.node1))
        s2 = screen_positions.get(get_hub_name(conn.node2))
        if s1 is None or s2 is None:
            continue

        # Sort names alphabetically to match structured transit lookups
        n1, n2 = sorted([get_hub_name(conn.node1), get_hub_name(conn.node2)])
        conn_key: tuple[str, str] = (n1, n2)
        drone_ids = drones_on_connections.get(conn_key, [])

        if drone_ids:
            # Pin down exact midpoint between connected hubs
            mid_x, mid_y = (s1[0] + s2[0]) // 2, (s1[1] + s2[1]) // 2
            text = f"x{len(drone_ids)}"
            text_surf = font.render(text, True, CONN_BADGE_TEXT)
            text_rect = text_surf.get_rect(center=(mid_x, mid_y))

            badge_rect = text_rect.inflate(8, 6)
            pg.draw.rect(
                surf, (*CONN_BADGE_BORDER[:3], 200),
                badge_rect, border_radius=4
            )
            pg.draw.rect(
                surf,
                CONN_BADGE_BORDER,
                badge_rect,
                width=1,
                border_radius=4,
            )
            surf.blit(text_surf, text_rect)

    screen.blit(surf, (0, 0))
