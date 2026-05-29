"""Main game loop and rendering for FlyIn."""

import functools
import sys
from typing import Any

import pygame as pg
from pygame.locals import QUIT, KEYDOWN, K_q, K_SPACE, K_RIGHT, K_LEFT

from game.camera import Camera, DEFAULT_ZOOM
from simulator_step import Simulator
from models.map import Connection, Hub, Map

# --- Constants ---
SCREEN_WIDTH: int = 1920
SCREEN_HEIGHT: int = 1080
FPS: int = 60

BASE_HUB_DIAMETER: int = 100
BASE_CONNECTION_WIDTH: int = 4
BASE_NAME_FONT_SIZE: int = 20
BASE_COUNT_FONT_SIZE: int = 26

BLACK: tuple[int, int, int] = (0, 0, 0)
WHITE: tuple[int, int, int] = (255, 255, 255)
BG_COLOR: tuple[int, int, int] = (13, 17, 23)

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
@functools.lru_cache(maxsize=128)
def _get_aura_surface(radius: int, color_rgb: tuple[int, int, int], alpha: int) -> pg.Surface:
    surf = pg.Surface((radius * 2, radius * 2), pg.SRCALPHA)
    pg.draw.circle(surf, (*color_rgb, alpha), (radius, radius), radius)
    return surf


@functools.lru_cache(maxsize=128)
def _get_ring_surface(size: int, inner_dot_radius: int) -> pg.Surface:
    ring = pg.Surface((size, size), pg.SRCALPHA)
    half = size // 2
    pg.draw.circle(ring, HUB_RING_COLOR, (half, half), max(1, half - 1), width=1)
    pg.draw.circle(ring, (*HUB_INNER_DOT_COLOR, 200), (half, half), inner_dot_radius)
    return ring


# --- Refactored Sprite Classes ---
class HubSprite(pg.sprite.Sprite):
    def __init__(self, *groups: pg.sprite.AbstractGroup[Any]) -> None:
        super().__init__(*groups)
        self.hub: Hub
        self.image: pg.Surface
        self.rect: pg.Rect
        self.aura: pg.Surface | None = None  # FIX: Utilisation cohérente de "aura" (sans tiret bas)
        
        self._last_size: int = -1
        self._last_drone_count: int = -1

    def setup(self, hub: Hub, center: tuple[int, int], size: int = 100) -> None:
        self.hub = hub
        diameter = max(4, int(size))
        
        try:
            color = pg.Color(hub.color)
        except Exception:
            color = pg.Color("red")
            
        color_rgb = (color.r, color.g, color.b)
        drone_count = len(hub.drones or [])

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


# --- Helper functions ---
def _scale_value(base_value: int, zoom: float) -> int:
    return max(1, int(base_value * (zoom / DEFAULT_ZOOM)))


def _get_hub_name(hub_or_str: Hub | str) -> str:
    return hub_or_str.name if isinstance(hub_or_str, Hub) else str(hub_or_str)


def _resolve_hub_color(hub: Hub) -> pg.Color:
    try:
        return pg.Color(hub.color)
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
        s1 = screen_positions.get(_get_hub_name(conn.hub_1))
        s2 = screen_positions.get(_get_hub_name(conn.hub_2))
        if s1 is None or s2 is None:
            continue

        active = len(conn.drone) > 0
        r, g, b = CONNECTION_COLOR_ACTIVE if active else CONNECTION_COLOR_IDLE
        alpha = CONNECTION_ACTIVE_ALPHA if active else CONNECTION_IDLE_ALPHA
        width = _scale_value(BASE_CONNECTION_WIDTH if active else 2, zoom)
        pg.draw.line(surf, (r, g, b, alpha), s1, s2, width)

    screen.blit(surf, (0, 0))


def _draw_auras(screen: pg.Surface, hub_by_name: dict[str, HubSprite]) -> None:
    for sprite in hub_by_name.values():
        if sprite.aura is None:  # FIX appliqué ici
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


def _draw_hub_labels(screen: pg.Surface, hub_by_name: dict[str, HubSprite], zoom: float) -> None:
    name_font = pg.font.Font(None, _scale_value(BASE_NAME_FONT_SIZE, zoom))
    count_font = pg.font.Font(None, _scale_value(BASE_COUNT_FONT_SIZE, zoom))

    for sprite in hub_by_name.values():
        hub = sprite.hub
        c = _resolve_hub_color(hub)
        
        offset = max(18, sprite.rect.height // 2 + LABEL_GAP * 3)
        name_center = (sprite.rect.centerx, sprite.rect.centery - offset)
        count_center = (sprite.rect.centerx, sprite.rect.centery + offset)

        _draw_label(screen, hub.name, name_font, name_center, border_color=LABEL_BORDER_COLOR)

        drone_count = len(hub.drones or [])
        _draw_label(screen, str(drone_count), count_font, count_center, text_color=(c.r, c.g, c.b), border_color=(c.r, c.g, c.b, 160))


def _draw_connection_drone_counts(screen: pg.Surface, map_: Map, screen_positions: dict[str, tuple[int, int]], zoom: float) -> None:
    count_font = pg.font.Font(None, _scale_value(BASE_COUNT_FONT_SIZE, zoom))

    for conn in map_.connections:
        if not conn.drone:
            continue

        s1 = screen_positions.get(_get_hub_name(conn.hub_1))
        s2 = screen_positions.get(_get_hub_name(conn.hub_2))
        if s1 is None or s2 is None:
            continue

        mid = ((s1[0] + s2[0]) // 2, (s1[1] + s2[1]) // 2)
        _draw_label(screen, str(len(conn.drone)), count_font, mid, text_color=CONN_BADGE_TEXT, border_color=CONN_BADGE_BORDER)


# --- Core Game Loop ---
def game_loop(map_: Map) -> None:
    pg.init()
    screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pg.SCALED)
    pg.display.set_caption("FlyIn - Simulation Visualizer")

    clock = pg.time.Clock()
    
    # Paramètres de simulation
    sim_tick: float = 0.5
    sim_acc: float = 0.0
    sim_paused: bool = False  # NOUVEAU: Mettre en pause la simulation
    
    sim = Simulator(map_)
    sim_running = True
    sim_finished_printed = False
    
    base_positions = _compute_base_hub_pixels(map_, screen)
    camera = Camera(screen, base_positions)

    hubs, hub_by_name = _build_hub_sprites(map_, base_positions, camera)
    hub_sprites = pg.sprite.RenderPlain(*hubs)

    # NOUVEAU: OPTIMISATION O(1) - Pré-calculer la carte des connexions
    # Utilisation d'un frozenset pour trouver rapidement une connexion (indépendamment du sens A->B ou B->A)
    connection_map: dict[frozenset[str], Connection] = {
        frozenset([_get_hub_name(c.hub_1), _get_hub_name(c.hub_2)]): c 
        for c in map_.connections
    }

    dragging = False
    last_mouse = pg.Vector2(0, 0)

    while True:
        for event in pg.event.get():
            if event.type == QUIT:
                pg.quit()
                sys.exit()
            elif event.type == KEYDOWN:
                if event.key == K_q:
                    pg.quit()
                    sys.exit()
                elif event.key == K_SPACE:  # Espace pour Play/Pause
                    sim_paused = not sim_paused
                    print("Simulation " + ("en pause" if sim_paused else "reprise"))
                elif event.key == K_RIGHT:  # Accélérer
                    sim_tick = max(0.05, sim_tick - 0.1)
                    print(f"Vitesse simul: {sim_tick:.2f}s/tour")
                elif event.key == K_LEFT:   # Ralentir
                    sim_tick = min(2.0, sim_tick + 0.1)
                    print(f"Vitesse simul: {sim_tick:.2f}s/tour")
            elif event.type == pg.MOUSEWHEEL:
                camera.handle_zoom_event(event)
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                dragging = True
                last_mouse = camera.start_pan(event.pos)
            elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
                dragging = False
            elif event.type == pg.MOUSEMOTION and dragging:
                last_mouse = camera.drag_pan(last_mouse, event.pos)

        camera.update()

        # Render background components
        screen.fill(BG_COLOR)
        _draw_grid(screen)

        screen_positions = {name: camera.world_to_screen(base) for name, base in base_positions.items()}

        _draw_connections(screen, map_, screen_positions, camera.zoom)

        size_with_zoom = _scale_value(BASE_HUB_DIAMETER, camera.zoom)
        for name, sprite in hub_by_name.items():
            pos = screen_positions.get(name)
            if pos is not None:
                sprite.setup(sprite.hub, pos, size=size_with_zoom)

        _draw_auras(screen, hub_by_name)
        hub_sprites.draw(screen)
        _draw_hub_labels(screen, hub_by_name, camera.zoom)
        _draw_connection_drone_counts(screen, map_, screen_positions, camera.zoom)

        pg.display.flip()
        
        # --- Logique de Simulation Temporelle ---
        dt = clock.tick(FPS) / 500.0
        
        if not sim_paused:
            sim_acc += dt

            if sim_acc >= sim_tick:
                sim_acc -= sim_tick
                
                if sim_running:
                    is_finished, moves = sim.step()
                else:
                    is_finished, moves = True, []
                
                # --- OPTIMISATION O(1) appliquée ici ---
                for conn in map_.connections:
                    conn.drone.clear()  # Utilise clear() pour vider la liste sans recréer d'objet
                
                for it in getattr(sim, "in_transit", []):
                    frm = it.get("from")
                    to = it.get("to")
                    # Recherche instantanée du lien
                    conn = connection_map.get(frozenset([frm, to]))
                    if conn is not None:
                        conn.drone.append(it.get("drone"))
                
                # Format de sortie respectant le sujet: "D1-roof1 D2-corridorA"
                if moves:
                    print(" ".join(moves))
                
                if is_finished and not sim_finished_printed:
                    print(f"Finished in {sim.turn} turns (Delivered: {sim.delivered}/{sim.total})")
                    sim_finished_printed = True
                    sim_running = False