"""Main game loop for FlyIn."""

import sys

import pygame as pg
from pygame.locals import QUIT

from game.camera import Camera, DEFAULT_ZOOM
from game.game_object import HubSprite
from models.map import Map

# Display
SCREEN_WIDTH: int = 1920
SCREEN_HEIGHT: int = 1080

# Physics
FPS: int = 60
BASE_HUB_DIAMETER: int = 100
BASE_CONNECTION_WIDTH: int = 4
BASE_NAME_FONT_SIZE: int = 20
BASE_COUNT_FONT_SIZE: int = 26

# Colours
BLACK: tuple[int, int, int] = (0, 0, 0)
WHITE: tuple[int, int, int] = (255, 255, 255)
BG_COLOR: tuple[int, int, int] = (13, 17, 23)          # deep dark background

# Connection visuals
CONNECTION_COLOR_ACTIVE: tuple[int, int, int] = (173, 216, 230)   # light blue (RGB)
CONNECTION_COLOR_IDLE: tuple[int, int, int] = (173, 216, 230)     # use same light blue for idle
CONNECTION_ACTIVE_ALPHA: int = 160    # semi-opaque (0-255)
CONNECTION_IDLE_ALPHA: int = 100      # lighter opacity when idle

# Hub ring / glow
HUB_RING_COLOR: tuple[int, int, int, int] = (255, 255, 255, 55)
HUB_INNER_DOT_COLOR: tuple[int, int, int] = (255, 255, 255)
HUB_GLOW_ALPHA: int = 60               # radial glow radius multiplier applied in draw

# Label style
LABEL_PADDING_X: int = 8
LABEL_PADDING_Y: int = 4
LABEL_GAP: int = 6
LABEL_BG_COLOR: tuple[int, int, int, int] = (13, 17, 23, 220)
LABEL_BORDER_COLOR: tuple[int, int, int, int] = (255, 255, 255, 28)
LABEL_TEXT_COLOR: tuple[int, int, int] = (241, 245, 249)      # slate-100
LABEL_OUTLINE_COLOR: tuple[int, int, int] = (0, 0, 0)

# Count badge: uses hub color as border tint (passed at draw time)
COUNT_BADGE_BG: tuple[int, int, int, int] = (13, 17, 23, 220)

# Connection count badge: amber tint
CONN_BADGE_BORDER: tuple[int, int, int, int] = (245, 158, 11, 130)  # amber-400 semi
CONN_BADGE_TEXT: tuple[int, int, int] = (251, 191, 36)               # amber-300

# Grid overlay
GRID_COLOR: tuple[int, int, int, int] = (255, 255, 255, 8)
GRID_SPACING: int = 48

WORLD_SPREAD: float = 1.6


def _compute_base_hub_pixels(
    map_: Map,
    screen: pg.Surface,
    padding: int = 20,
    spread: float = WORLD_SPREAD,
) -> dict[str, tuple[float, float]]:
    """Compute world-space pixel positions for hubs before camera transforms.

    Maps each hub name to (x, y) pixel coordinates fitted inside the screen
    with the given padding. These values are later transformed by the camera
    (zoom + pan) to produce final screen positions.

    Args:
        map_:    The game map containing hubs.
        screen:  The pygame surface used to derive drawable dimensions.
        padding: Pixel margin on each side of the drawable area.

    Returns:
        A dict mapping ``hub.name`` to ``(x_pixels, y_pixels)``.
    """
    if not map_.hubs:
        return {}

    min_x = min(hub.x for hub in map_.hubs)
    max_x = max(hub.x for hub in map_.hubs)
    min_y = min(hub.y for hub in map_.hubs)
    max_y = max(hub.y for hub in map_.hubs)

    drawable_w = max(1, screen.get_width() - 2 * padding)
    drawable_h = max(1, screen.get_height() - 2 * padding)

    range_x = max(1, max_x - min_x)
    range_y = max(1, max_y - min_y)

    # initial pixel positions
    base_positions = {
        hub.name: (
            padding + (hub.x - min_x) / range_x * drawable_w,
            padding + (hub.y - min_y) / range_y * drawable_h,
        )
        for hub in map_.hubs
    }

    # spread points away from the map center to reduce compactness
    xs = [p[0] for p in base_positions.values()]
    ys = [p[1] for p in base_positions.values()]
    if not xs or not ys:
        return base_positions

    center_x = sum(xs) / len(xs)
    center_y = sum(ys) / len(ys)

    def spread_coord(x: float, center: float) -> float:
        return center + (x - center) * float(spread)

    return {
        name: (int(spread_coord(px, center_x)), int(spread_coord(py, center_y)))
        for name, (px, py) in base_positions.items()
    }


def _hub_name(hub_ref: object) -> str:
    """Resolve a connection hub reference to a name string.

    Accepts either a ``Hub`` object (with a ``.name`` attribute) or a plain
    string.

    Args:
        hub_ref: A Hub instance or any object whose str() yields a useful name.

    Returns:
        The hub name as a string.
    """
    return getattr(hub_ref, "name", None) or str(hub_ref)


def _build_hub_sprites(
    map_: Map,
    base_positions: dict[str, tuple[float, float]],
    camera: Camera,
) -> tuple[list[HubSprite], dict[str, HubSprite]]:
    """Instantiate and position hub sprites from the map data.

    Args:
        map_:           The game map containing hub definitions.
        base_positions: World-space hub positions keyed by hub name.
        camera:         The game camera.

    Returns:
        A tuple of (list of HubSprite, dict mapping hub name to HubSprite).
    """
    hubs: list[HubSprite] = []
    hub_by_name: dict[str, HubSprite] = {}

    for hub in map_.hubs:
        sprite = HubSprite()
        screen_pos = camera.world_to_screen(
            base_positions.get(hub.name, (0.0, 0.0))
        )
        sprite.setup(hub, screen_pos)
        hubs.append(sprite)
        hub_by_name[hub.name] = sprite

    return hubs, hub_by_name


def _scale_value(base_value: int, zoom: float) -> int:
    """Scale a base size by zoom while keeping a readable minimum."""
    return max(1, int(base_value * (zoom / DEFAULT_ZOOM)))


def _update_sprite_positions(
    hub_by_name: dict[str, HubSprite],
    screen_positions: dict[str, tuple[int, int]],
) -> None:
    """Reposition every hub sprite using already-computed screen positions.

    Args:
        hub_by_name:      Hub sprites keyed by hub name.
        screen_positions: Integer screen coordinates keyed by hub name.
    """
    for name, sprite in hub_by_name.items():
        pos = screen_positions.get(name)
        if pos is not None:
            sprite.rect.center = pos


def _draw_grid(screen: pg.Surface) -> None:
    """Draw a faint dot/line grid on the background."""
    surf = pg.Surface(screen.get_size(), pg.SRCALPHA)
    w, h = screen.get_size()
    for x in range(0, w, GRID_SPACING):
        pg.draw.line(surf, GRID_COLOR, (x, 0), (x, h), 1)
    for y in range(0, h, GRID_SPACING):
        pg.draw.line(surf, GRID_COLOR, (0, y), (w, y), 1)
    screen.blit(surf, (0, 0))


def _draw_connections(
    screen: pg.Surface,
    map_: Map,
    screen_positions: dict[str, tuple[int, int]],
    zoom: float,
) -> None:
    surf = pg.Surface(screen.get_size(), pg.SRCALPHA)
    connections: list[object] = getattr(map_, "connections", None) or []
    if not connections:
        return

    for conn in connections:
        name1 = _hub_name(getattr(conn, "hub_1", ""))
        name2 = _hub_name(getattr(conn, "hub_2", ""))
        s1 = screen_positions.get(name1)
        s2 = screen_positions.get(name2)
        if s1 is None or s2 is None:
            continue

        # Pick color based on whether either hub has drones in transit
        drones: list[object] = getattr(conn, "drone", None) or []
        active = len(drones) > 0
        r, g, b = CONNECTION_COLOR_ACTIVE if active else CONNECTION_COLOR_IDLE
        alpha = CONNECTION_ACTIVE_ALPHA if active else CONNECTION_IDLE_ALPHA
        width = _scale_value(BASE_CONNECTION_WIDTH if active else 2, zoom)

        pg.draw.line(surf, (r, g, b, alpha), s1, s2, width)
    screen.blit(surf, (0, 0))


def _update_hub_sprite_sizes(
    hub_by_name: dict[str, HubSprite],
    zoom: float,
) -> None:
    """Regenerate hub surfaces — adds glow aura for active hubs."""
    size = _scale_value(BASE_HUB_DIAMETER, zoom)
    for sprite in hub_by_name.values():
        hub = sprite.hub
        has_drones = len(hub.drones or []) > 0

        # Aura surface (slightly larger, drawn under the hub)
        aura_r = max(1, size // 2 + _scale_value(14, zoom))
        aura_surf = pg.Surface((aura_r * 2, aura_r * 2), pg.SRCALPHA)
        if has_drones:
            try:
                raw_color = getattr(hub.color, "value", hub.color)
                c = pg.Color(str(raw_color))
                aura_color = (c.r, c.g, c.b, HUB_GLOW_ALPHA)
            except Exception:
                aura_color = (110, 231, 183, HUB_GLOW_ALPHA)
            pg.draw.circle(aura_surf, aura_color, (aura_r, aura_r), aura_r)
        sprite._aura = aura_surf  # type: ignore[attr-defined]
        sprite._aura_offset = aura_r - size // 2  # type: ignore[attr-defined]

        # Main circle
        sprite.setup(hub, sprite.rect.center, size=size)

        # White rim ring
        ring = pg.Surface(sprite.image.get_size(), pg.SRCALPHA)
        pg.draw.circle(
            ring, HUB_RING_COLOR,
            (sprite.rect.width // 2, sprite.rect.height // 2),
            max(1, sprite.rect.width // 2 - 1),
            width=1,
        )
        # Inner white dot
        pg.draw.circle(
            ring, (*HUB_INNER_DOT_COLOR, 200),
            (sprite.rect.width // 2, sprite.rect.height // 2),
            max(1, _scale_value(4, zoom)),
        )
        sprite.image.blit(ring, (0, 0))


def _draw_hub_drone_counts(
    screen: pg.Surface,
    hub_by_name: dict[str, HubSprite],
    zoom: float,
) -> None:
    """Draw name label above, drone count badge below each hub.
    
    The drone count badge border is tinted with the hub's own color.
    Aura is blitted first (underneath), then the hub sprite is re-drawn here
    so the aura doesn't occlude the label.
    """
    name_font = pg.font.Font(None, _scale_value(BASE_NAME_FONT_SIZE, zoom))
    count_font = pg.font.Font(None, _scale_value(BASE_COUNT_FONT_SIZE, zoom))

    for sprite in hub_by_name.values():
        hub = sprite.hub

        # Blit aura under the hub
        aura = getattr(sprite, "_aura", None)
        if aura:
            screen.blit(aura, (sprite.rect.centerx - aura.get_width() // 2,
                                sprite.rect.centery - aura.get_height() // 2))

        drone_count = len(hub.drones or [])
        offset = max(18, sprite.rect.height // 2 + LABEL_GAP * 3)
        name_center = (sprite.rect.centerx, sprite.rect.centery - offset)
        count_center = (sprite.rect.centerx, sprite.rect.centery + offset)

        _draw_label(screen, hub.name, name_font, name_center)

        # Count badge — tinted border from hub color
        try:
            raw_color = getattr(hub.color, "value", hub.color)
            c = pg.Color(str(raw_color))
            tint_border = (c.r, c.g, c.b, 100)
        except Exception:
            tint_border = LABEL_BORDER_COLOR

        _draw_label(screen, str(drone_count), count_font, count_center,
                    border_color=tint_border, text_color_override=None)


def _draw_label(
    screen: pg.Surface,
    text: str,
    font: pg.font.Font,
    center: tuple[int, int],
    border_color: tuple[int, int, int, int] = LABEL_BORDER_COLOR,
    text_color_override: tuple[int, int, int] | None = None,
) -> None:
    text_color = text_color_override or LABEL_TEXT_COLOR
    text_surface = font.render(text, True, text_color)
    text_rect = text_surface.get_rect(center=center)
    bg_rect = text_rect.inflate(LABEL_PADDING_X * 2, LABEL_PADDING_Y * 2)

    background = pg.Surface(bg_rect.size, pg.SRCALPHA)
    pg.draw.rect(background, LABEL_BG_COLOR, background.get_rect(), border_radius=5)
    pg.draw.rect(background, border_color, background.get_rect(), width=1, border_radius=5)
    screen.blit(background, bg_rect)
    screen.blit(text_surface, text_rect)


def _draw_connection_drone_counts(
    screen: pg.Surface,
    map_: Map,
    screen_positions: dict[str, tuple[int, int]],
    zoom: float,
) -> None:
    connections: list[object] = getattr(map_, "connections", None) or []
    if not connections:
        return

    count_font = pg.font.Font(None, _scale_value(BASE_COUNT_FONT_SIZE, zoom))

    for conn in connections:
        name1 = _hub_name(getattr(conn, "hub_1", ""))
        name2 = _hub_name(getattr(conn, "hub_2", ""))
        s1 = screen_positions.get(name1)
        s2 = screen_positions.get(name2)
        if s1 is None or s2 is None:
            continue

        drones: list[object] = getattr(conn, "drone", None) or []
        if not drones:
            continue   # only show badge when drones are actually in transit

        mid_x = (s1[0] + s2[0]) // 2
        mid_y = (s1[1] + s2[1]) // 2

        _draw_label(
            screen, str(len(drones)), count_font, (mid_x, mid_y),
            border_color=CONN_BADGE_BORDER,
            text_color_override=CONN_BADGE_TEXT,
        )


def game_loop(map_: Map) -> None:
    """Run the main game loop.

    Initialises the display, builds hub sprites, then enters the event/render
    loop until the window is closed.

    Args:
        map_: The game map to display.
    """
    screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pg.SCALED)
    pg.display.set_caption("FlyIn")

    clock = pg.time.Clock()

    base_positions: dict[str, tuple[float, float]] = _compute_base_hub_pixels(
        map_, screen
    )

    camera = Camera(screen, base_positions)

    hubs: list[HubSprite]
    hub_by_name: dict[str, HubSprite]
    hubs, hub_by_name = _build_hub_sprites(map_, base_positions, camera)
    hub_sprites: pg.sprite.RenderPlain = pg.sprite.RenderPlain(*hubs)

    dragging: bool = False
    last_mouse: pg.Vector2 = pg.Vector2(0, 0)

    while True:
        keys = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == QUIT or keys[pg.K_q]:
                pg.quit()
                sys.exit()

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

        screen.fill(BG_COLOR)
        _draw_grid(screen)

        screen_positions: dict[str, tuple[int, int]] = {
            name: camera.world_to_screen(base)
            for name, base in base_positions.items()
        }

        _draw_connections(screen, map_, screen_positions, camera.zoom)
        _update_sprite_positions(hub_by_name, screen_positions)
        _update_hub_sprite_sizes(hub_by_name, camera.zoom)
        hub_sprites.draw(screen)
        _draw_hub_drone_counts(screen, hub_by_name, camera.zoom)
        _draw_connection_drone_counts(screen, map_, screen_positions, camera.zoom)

        pg.display.flip()
        clock.tick(60)