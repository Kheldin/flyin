"""Rendering helpers and sprite classes moved out of game_loop."""
import functools
from typing import Any

import pygame as pg

from game.camera import Camera, DEFAULT_ZOOM
from models.map import Node, Map
from game.game_object import LabelSprite

# --- Constants ---
BASE_HUB_DIAMETER: int = 100
BASE_CONNECTION_WIDTH: int = 4
BASE_NAME_FONT_SIZE: int = 20
BASE_COUNT_FONT_SIZE: int = 26

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


# --- Caching Mechanisms ---
@functools.cache
def get_font(size: int) -> pg.font.Font:
    """Prevents continuous system calls by caching Font objects globally."""
    return pg.font.Font(None, size)


@functools.cache
def _get_aura_surface(radius: int, color_rgb: tuple[int, int, int], alpha: int) -> pg.Surface:
    """Generates and caches glow aura effects for active hubs."""
    surf = pg.Surface((radius * 2, radius * 2), pg.SRCALPHA)
    pg.draw.circle(surf, (*color_rgb, alpha), (radius, radius), radius)
    return surf


@functools.cache
def _get_ring_surface(size: int, inner_dot_radius: int) -> pg.Surface:
    """Generates and caches decorative inner overlay rings for hubs."""
    ring = pg.Surface((size, size), pg.SRCALPHA)
    half = size // 2
    pg.draw.circle(ring, HUB_RING_COLOR, (half, half), max(1, half - 1), width=1)
    pg.draw.circle(ring, (*HUB_INNER_DOT_COLOR, 200), (half, half), inner_dot_radius)
    return ring


# --- Utility Functions ---
def scale_value(base_value: int, zoom: float) -> int:
    return max(1, int(base_value * (zoom / DEFAULT_ZOOM)))


def get_hub_name(hub_or_str: Node | str) -> str:
    return hub_or_str.name if isinstance(hub_or_str, Node) else str(hub_or_str)


def resolve_hub_color(hub: Node) -> pg.Color:
    """Resolves string types to pg.Color instances, computing dynamic HSV spectrums for rainbows."""
    color_str = (hub.metadata.color or "red").lower()
    
    if color_str == "rainbow":
        ticks = pg.time.get_ticks()
        hue = (ticks // 4) % 360  # Modulates cycle animation speed
        color = pg.Color(0)
        color.hsva = (hue, 90, 100, 100)
        return color
        
    try:
        return pg.Color(color_str)
    except ValueError:
        return pg.Color("red")


class HubSprite(pg.sprite.Sprite):
    def __init__(self, *groups: pg.sprite.AbstractGroup[Any]) -> None:
        super().__init__(*groups)
        self.hub: Node
        self.image: pg.Surface = pg.Surface((0, 0))
        self.rect: pg.Rect = pg.Rect(0, 0, 0, 0)
        self.aura: pg.Surface | None = None
        self.is_rainbow: bool = False
        
        # --- FIXED: All state tracking fields properly isolated and initialized ---
        self.last_size: int = -1
        self.last_drone_count: int = -1
        self.last_label_drone_count: int = -1
        self.last_zoom: float = -1.0
        
        # Cached label entities attached to this sprite instance
        self.name_label: LabelSprite | None = None
        self.count_label: LabelSprite | None = None

    def setup(self, hub: Node, center: tuple[int, int], size: int = 100, drone_count: int = 0) -> None:
        self.hub = hub
        self.is_rainbow = (hub.metadata.color or "").lower() == "rainbow"
        diameter = max(4, int(size))
        color = resolve_hub_color(hub)
        color_rgb = (color.r, color.g, color.b)

        # Dynamic aura assignment
        if drone_count > 0:
            aura_r = max(1, diameter // 2 + (diameter // 5))
            self.aura = _get_aura_surface(aura_r, color_rgb, HUB_GLOW_ALPHA)
        else:
            self.aura = None

        # Re-render sprite circles only when geometric sizes shift
        if self.last_size != diameter or self.last_drone_count != drone_count or self.is_rainbow:
            self.image = pg.Surface((diameter, diameter), pg.SRCALPHA)
            pg.draw.circle(self.image, color, (diameter // 2, diameter // 2), diameter // 2)
            
            inner_dot_r = max(1, diameter // 12)
            ring_surf = _get_ring_surface(diameter, inner_dot_r)
            self.image.blit(ring_surf, (0, 0))
            
            self.last_size = diameter
            self.last_drone_count = drone_count

        self.rect = self.image.get_rect(center=center)

    def update(self, *args: Any, **kwargs: Any) -> None:
        """Forces runtime surface modifications if the entity's state requires real-time shifts."""
        if self.is_rainbow:
            diameter = max(4, self.rect.width)
            color = resolve_hub_color(self.hub)
            
            # Re-render shifting base canvas profile
            self.image = pg.Surface((diameter, diameter), pg.SRCALPHA)
            pg.draw.circle(self.image, color, (diameter // 2, diameter // 2), diameter // 2)
            
            inner_dot_r = max(1, diameter // 12)
            ring_surf = _get_ring_surface(diameter, inner_dot_r)
            self.image.blit(ring_surf, (0, 0))
            
            # Keep glow matching spectrum changes
            if self.last_drone_count > 0:
                aura_r = max(1, diameter // 2 + (diameter // 5))
                self.aura = _get_aura_surface(aura_r, (color.r, color.g, color.b), HUB_GLOW_ALPHA)

# --- Core Logic & Map Drawing Loops ---
def compute_base_hub_pixels(map_: Map, screen: pg.Surface, padding: int = 20, spread: float = WORLD_SPREAD) -> dict[str, tuple[float, float]]:
    if not map_.hubs:
        return {}

    hubs = map_.hubs
    min_x, max_x = min(h.x for h in hubs), max(h.x for h in hubs)
    min_y, max_y = min(h.y for h in hubs), max(h.y for h in hubs)

    drawable_w = max(1, screen.get_width() - 2 * padding)
    drawable_h = max(1, screen.get_height() - 2 * padding)
    range_x, range_y = max(1, max_x - min_x), max(1, max_y - min_y)

    base_positions = {
        hub.name: (padding + (hub.x - min_x) / range_x * drawable_w, padding + (hub.y - min_y) / range_y * drawable_h)
        for hub in hubs
    }

    total_x = sum(p[0] for p in base_positions.values())
    total_y = sum(p[1] for p in base_positions.values())
    count = len(base_positions)
    center_x, center_y = total_x / count, total_y / count

    return {
        name: (center_x + (px - center_x) * spread, center_y + (py - center_y) * spread)
        for name, (px, py) in base_positions.items()
    }


def build_hub_sprites(map_: Map, base_positions: dict[str, tuple[float, float]], camera: Camera) -> tuple[list[HubSprite], dict[str, HubSprite]]:
    hubs: list[HubSprite] = []
    hub_by_name: dict[str, HubSprite] = {}

    for hub in map_.hubs:
        sprite = HubSprite()
        screen_pos = camera.world_to_screen(base_positions.get(hub.name, (0.0, 0.0)))
        sprite.setup(hub, screen_pos, size=BASE_HUB_DIAMETER)
        hubs.append(sprite)
        hub_by_name[hub.name] = sprite

    return hubs, hub_by_name


def draw_grid(screen: pg.Surface) -> None:
    w, h = screen.get_size()
    surf = pg.Surface((w, h), pg.SRCALPHA)
    for x in range(0, w, GRID_SPACING):
        pg.draw.line(surf, GRID_COLOR, (x, 0), (x, h), 1)
    for y in range(0, h, GRID_SPACING):
        pg.draw.line(surf, GRID_COLOR, (0, y), (w, y), 1)
    screen.blit(surf, (0, 0))


def draw_connections(screen: pg.Surface, map_: Map, screen_positions: dict[str, tuple[int, int]], zoom: float) -> None:
    surf = pg.Surface(screen.get_size(), pg.SRCALPHA)
    for conn in map_.connections:
        s1 = screen_positions.get(get_hub_name(conn.node1))
        s2 = screen_positions.get(get_hub_name(conn.node2))
        if s1 is None or s2 is None:
            continue

        active = getattr(conn, "active", False)
        r, g, b = CONNECTION_COLOR_ACTIVE if active else CONNECTION_COLOR_IDLE
        alpha = CONNECTION_ACTIVE_ALPHA if active else CONNECTION_IDLE_ALPHA
        width = scale_value(BASE_CONNECTION_WIDTH if active else 2, zoom)
        pg.draw.line(surf, (r, g, b, alpha), s1, s2, width)

    screen.blit(surf, (0, 0))


def draw_auras(screen: pg.Surface, hub_by_name: dict[str, HubSprite]) -> None:
    for sprite in hub_by_name.values():
        if sprite.aura is None:
            continue
        ax = sprite.rect.centerx - sprite.aura.get_width() // 2
        ay = sprite.rect.centery - sprite.aura.get_height() // 2
        screen.blit(sprite.aura, (ax, ay))


def draw_hub_labels(screen: pg.Surface, hub_by_name: dict[str, HubSprite], zoom: float, drone_count_per_hub: dict[str, int] | None = None) -> None:
    if drone_count_per_hub is None:
        drone_count_per_hub = {}

    for sprite in hub_by_name.values():
        hub = sprite.hub
        drone_count = drone_count_per_hub.get(hub.name, 0)
        
        offset = max(18, sprite.rect.height // 2 + LABEL_GAP * 3)
        name_center = (sprite.rect.centerx, sprite.rect.centery - offset)
        count_center = (sprite.rect.centerx, sprite.rect.centery + offset)
        
        # Uses isolated label property tracking
        if (sprite.last_zoom != zoom or 
            sprite.last_label_drone_count != drone_count or 
            sprite.is_rainbow or
            sprite.name_label is None or 
            sprite.count_label is None):
            
            c = resolve_hub_color(hub)
            name_font = get_font(scale_value(BASE_NAME_FONT_SIZE, zoom))
            count_font = get_font(scale_value(BASE_COUNT_FONT_SIZE, zoom))
            
            sprite.name_label = LabelSprite()
            sprite.name_label.setup(hub.name, name_font, center=name_center, border_color=LABEL_BORDER_COLOR)
            
            sprite.count_label = LabelSprite()
            sprite.count_label.setup(
                text=str(drone_count), 
                font=count_font, 
                center=count_center, 
                text_color=(c.r, c.g, c.b), 
                border_color=(c.r, c.g, c.b, 160)
            )
            sprite.last_zoom = zoom
            sprite.last_label_drone_count = drone_count
        else:
            sprite.name_label.rect.center = name_center
            sprite.count_label.rect.center = count_center

        screen.blit(sprite.name_label.image, sprite.name_label.rect)
        screen.blit(sprite.count_label.image, sprite.count_label.rect)


def draw_drone_on_connections(screen: pg.Surface, map_: Map, screen_positions: dict[str, tuple[int, int]], drones_on_connections: dict[tuple[str, str], list[int]] | None = None, zoom: float = 1.0) -> None:
    if drones_on_connections is None:
        drones_on_connections = {}
    
    surf = pg.Surface(screen.get_size(), pg.SRCALPHA)
    font = get_font(max(12, int(14 * (zoom / 1.0))))
    
    for conn in map_.connections:
        s1 = screen_positions.get(get_hub_name(conn.node1))
        s2 = screen_positions.get(get_hub_name(conn.node2))
        if s1 is None or s2 is None:
            continue
        
        # Pylance Fix: Array unpacked to discrete variables first to prevent tuple-size ambiguity
        n1, n2 = sorted([get_hub_name(conn.node1), get_hub_name(conn.node2)])
        conn_key: tuple[str, str] = (n1, n2)
        drone_ids = drones_on_connections.get(conn_key, [])
        
        if drone_ids:
            mid_x, mid_y = (s1[0] + s2[0]) // 2, (s1[1] + s2[1]) // 2
            text = f"x{len(drone_ids)}"
            text_surf = font.render(text, True, CONN_BADGE_TEXT)
            text_rect = text_surf.get_rect(center=(mid_x, mid_y))
            
            badge_rect = text_rect.inflate(8, 6)
            pg.draw.rect(surf, (*CONN_BADGE_BORDER[:3], 200), badge_rect, border_radius=4)
            pg.draw.rect(surf, CONN_BADGE_BORDER, badge_rect, width=1, border_radius=4)
            surf.blit(text_surf, text_rect)
    
    screen.blit(surf, (0, 0))