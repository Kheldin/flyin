"""Rendering helpers and sprite classes moved out of game_loop."""
from __future__ import annotations
import functools
from typing import Any

import pygame as pg

from game.camera import Camera, DEFAULT_ZOOM
from models.map import Node, Map

# --- Constants (used by drawing utilities) ---
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


# --- Smart Surfaces Caching ---
@functools.cache
def _get_aura_surface(radius: int, color_rgb: tuple[int, int, int], alpha: int) -> pg.Surface:
    surf = pg.Surface((radius * 2, radius * 2), pg.SRCALPHA)
    pg.draw.circle(surf, (*color_rgb, alpha), (radius, radius), radius)
    return surf


@functools.cache
def _get_ring_surface(size: int, inner_dot_radius: int) -> pg.Surface:
    ring = pg.Surface((size, size), pg.SRCALPHA)
    half = size // 2
    pg.draw.circle(ring, HUB_RING_COLOR, (half, half), max(1, half - 1), width=1)
    pg.draw.circle(ring, (*HUB_INNER_DOT_COLOR, 200), (half, half), inner_dot_radius)
    return ring


class HubSprite(pg.sprite.Sprite):
    def __init__(self, *groups: pg.sprite.AbstractGroup[Any]) -> None:
        super().__init__(*groups)
        self.hub: Node
        self.image: pg.Surface
        self.rect: pg.Rect
        self.aura: pg.Surface | None = None
        
        self._last_size: int = -1
        self._last_drone_count: int = -1

    def setup(self, hub: Node, center: tuple[int, int], size: int = 100) -> None:
        self.hub = hub
        diameter = max(4, int(size))
        
        try:
            color_str = hub.metadata.color if hub.metadata.color else "red"
            color = pg.Color(color_str)
        except Exception:
            color = pg.Color("red")
            
        color_rgb = (color.r, color.g, color.b)
        drone_count = 0

        if drone_count > 0:
            aura_r = max(1, diameter // 2 + (diameter // 5))
            self.aura = _get_aura_surface(aura_r, color_rgb, HUB_GLOW_ALPHA)
        else:
            self.aura = None

        if self._last_size != diameter or self._last_drone_count != drone_count:
            self.image = pg.Surface((diameter, diameter), pg.SRCALPHA)
            pg.draw.circle(self.image, color, (diameter // 2, diameter // 2), diameter // 2)
            
            inner_dot_r = max(1, diameter // 12)
            ring_surf = _get_ring_surface(diameter, inner_dot_r)
            self.image.blit(ring_surf, (0, 0))
            
            self._last_size = diameter
            self._last_drone_count = drone_count

        self.rect = self.image.get_rect(center=center)


def _scale_value(base_value: int, zoom: float) -> int:
    return max(1, int(base_value * (zoom / DEFAULT_ZOOM)))


def _get_hub_name(hub_or_str: Node | str) -> str:
    return hub_or_str.name if isinstance(hub_or_str, Node) else str(hub_or_str)


def _resolve_hub_color(hub: Node) -> pg.Color:
    try:
        color_str = hub.metadata.color if hub.metadata.color else "red"
        return pg.Color(color_str)
    except Exception:
        return pg.Color("red")


def _compute_base_hub_pixels(map_: Map, screen: pg.Surface, padding: int = 20, spread: float = WORLD_SPREAD) -> dict[str, tuple[float, float]]:
    if not map_.hubs:
        return {}

    min_x, max_x = min(h.x for h in map_.hubs), max(h.x for h in map_.hubs)
    min_y, max_y = min(h.y for h in map_.hubs), max(h.y for h in map_.hubs)

    drawable_w = max(1, screen.get_width() - 2 * padding)
    drawable_h = max(1, screen.get_height() - 2 * padding)
    range_x, range_y = max(1, max_x - min_x), max(1, max_y - min_y)

    base_positions = {
        hub.name: (padding + (hub.x - min_x) / range_x * drawable_w, padding + (hub.y - min_y) / range_y * drawable_h)
        for hub in map_.hubs
    }

    xs = [p[0] for p in base_positions.values()]
    ys = [p[1] for p in base_positions.values()]
    center_x, center_y = sum(xs) / len(xs), sum(ys) / len(ys)

    return {
        name: (center_x + (px - center_x) * spread, center_y + (py - center_y) * spread)
        for name, (px, py) in base_positions.items()
    }


def _build_hub_sprites(map_: Map, base_positions: dict[str, tuple[float, float]], camera: Camera) -> tuple[list[HubSprite], dict[str, HubSprite]]:
    hubs: list[HubSprite] = []
    hub_by_name: dict[str, HubSprite] = {}

    for hub in map_.hubs:
        sprite = HubSprite()
        screen_pos = camera.world_to_screen(base_positions.get(hub.name, (0.0, 0.0)))
        sprite.setup(hub, screen_pos, size=BASE_HUB_DIAMETER)
        hubs.append(sprite)
        hub_by_name[hub.name] = sprite

    return hubs, hub_by_name


def _draw_grid(screen: pg.Surface) -> None:
    surf = pg.Surface(screen.get_size(), pg.SRCALPHA)
    w, h = screen.get_size()
    for x in range(0, w, GRID_SPACING):
        pg.draw.line(surf, GRID_COLOR, (x, 0), (x, h), 1)
    for y in range(0, h, GRID_SPACING):
        pg.draw.line(surf, GRID_COLOR, (0, y), (w, y), 1)
    screen.blit(surf, (0, 0))


def _draw_connections(screen: pg.Surface, map_: Map, screen_positions: dict[str, tuple[int, int]], zoom: float) -> None:
    surf = pg.Surface(screen.get_size(), pg.SRCALPHA)
    for conn in map_.connections:
        s1 = screen_positions.get(_get_hub_name(conn.node1))
        s2 = screen_positions.get(_get_hub_name(conn.node2))
        if s1 is None or s2 is None:
            continue

        active = False  # Connection status will be updated from simulator
        r, g, b = CONNECTION_COLOR_ACTIVE if active else CONNECTION_COLOR_IDLE
        alpha = CONNECTION_ACTIVE_ALPHA if active else CONNECTION_IDLE_ALPHA
        width = _scale_value(BASE_CONNECTION_WIDTH if active else 2, zoom)
        pg.draw.line(surf, (r, g, b, alpha), s1, s2, width)

    screen.blit(surf, (0, 0))


def _draw_auras(screen: pg.Surface, hub_by_name: dict[str, HubSprite]) -> None:
    for sprite in hub_by_name.values():
        if sprite.aura is None:
            continue
        ax = sprite.rect.centerx - sprite.aura.get_width() // 2
        ay = sprite.rect.centery - sprite.aura.get_height() // 2
        screen.blit(sprite.aura, (ax, ay))


def _draw_label(screen: pg.Surface, text: str, font: pg.font.Font, center: tuple[int, int], text_color: tuple[int, int, int] = LABEL_TEXT_COLOR, border_color: tuple[int, int, int, int] = LABEL_BORDER_COLOR, bg_color: tuple[int, int, int, int] = LABEL_BG_COLOR) -> None:
    text_surface = font.render(text, True, text_color)
    text_rect = text_surface.get_rect(center=center)
    bg_rect = text_rect.inflate(LABEL_PADDING_X * 2, LABEL_PADDING_Y * 2)

    background = pg.Surface(bg_rect.size, pg.SRCALPHA)
    pg.draw.rect(background, bg_color, background.get_rect(), border_radius=6)
    pg.draw.rect(background, border_color, background.get_rect(), width=1, border_radius=6)
    screen.blit(background, bg_rect)
    screen.blit(text_surface, text_rect)


def _draw_hub_labels(screen: pg.Surface, hub_by_name: dict[str, HubSprite], zoom: float, drone_count_per_hub: dict[str, int] | None = None) -> None:
    if drone_count_per_hub is None:
        drone_count_per_hub = {}
    
    name_font = pg.font.Font(None, _scale_value(BASE_NAME_FONT_SIZE, zoom))
    count_font = pg.font.Font(None, _scale_value(BASE_COUNT_FONT_SIZE, zoom))

    for sprite in hub_by_name.values():
        hub = sprite.hub
        c = _resolve_hub_color(hub)
        
        offset = max(18, sprite.rect.height // 2 + LABEL_GAP * 3)
        name_center = (sprite.rect.centerx, sprite.rect.centery - offset)
        count_center = (sprite.rect.centerx, sprite.rect.centery + offset)

        _draw_label(screen, hub.name, name_font, name_center, border_color=LABEL_BORDER_COLOR)

        drone_count = drone_count_per_hub.get(hub.name, 0)
        _draw_label(screen, str(drone_count), count_font, count_center, text_color=(c.r, c.g, c.b), border_color=(c.r, c.g, c.b, 160))


def _draw_connection_drone_counts(screen: pg.Surface, map_: Map, screen_positions: dict[str, tuple[int, int]], zoom: float) -> None:
    # Drone count visualization for connections is no longer supported by the dataclass-based Map structure
    pass


# Public aliases (avoid importing private names from this module)
scale_value = _scale_value
get_hub_name = _get_hub_name
resolve_hub_color = _resolve_hub_color
compute_base_hub_pixels = _compute_base_hub_pixels
build_hub_sprites = _build_hub_sprites
draw_grid = _draw_grid
draw_connections = _draw_connections
draw_auras = _draw_auras
draw_label = _draw_label
draw_hub_labels = _draw_hub_labels
draw_connection_drone_counts = _draw_connection_drone_counts
