"""Main game loop for FlyIn."""

import sys

import pygame as pg
from pygame.locals import QUIT

from game.camera import Camera, DEFAULT_ZOOM
from game.game_object import HubSprite
from models.map import Map

# Colours
BLACK: tuple[int, int, int] = (0, 0, 0)
WHITE: tuple[int, int, int] = (255, 255, 255)

# Display
SCREEN_WIDTH: int = 1920
SCREEN_HEIGHT: int = 1080

# Physics
FPS: int = 60
BASE_HUB_DIAMETER: int = 100
BASE_CONNECTION_WIDTH: int = 4
BASE_NAME_FONT_SIZE: int = 20
BASE_COUNT_FONT_SIZE: int = 26
LABEL_PADDING_X: int = 10
LABEL_PADDING_Y: int = 5
LABEL_GAP: int = 4
LABEL_BG_COLOR: tuple[int, int, int, int] = (20, 24, 30, 190)
LABEL_BORDER_COLOR: tuple[int, int, int, int] = (255, 255, 255, 60)
LABEL_TEXT_COLOR: tuple[int, int, int] = (255, 255, 255)
LABEL_OUTLINE_COLOR: tuple[int, int, int] = (0, 0, 0)
CONNECTION_COLOR: tuple[int, int, int] = (165, 172, 184)
HUB_RING_COLOR: tuple[int, int, int, int] = (255, 255, 255, 70)
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


def _draw_connections(
    screen: pg.Surface,
    map_: Map,
    screen_positions: dict[str, tuple[int, int]],
    zoom: float,
) -> None:
    """Draw edges between connected hubs using precomputed integer positions.

    The line width is derived from the capacity of the first connection that
    touches the map's start hub, falling back to the first connection overall.

    Args:
        screen:           The pygame surface to draw on.
        map_:             The game map whose connections are rendered.
        screen_positions: Integer screen coordinates keyed by hub name.
    """
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

        width = _scale_value(BASE_CONNECTION_WIDTH, zoom)
        pg.draw.aaline(screen, CONNECTION_COLOR, s1, s2)
        pg.draw.line(screen, CONNECTION_COLOR, s1, s2, width=width)


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


def _update_hub_sprite_sizes(
    hub_by_name: dict[str, HubSprite],
    zoom: float,
) -> None:
    """Regenerate hub surfaces so their size tracks the camera zoom."""
    size = _scale_value(BASE_HUB_DIAMETER, zoom)
    for sprite in hub_by_name.values():
        sprite.setup(sprite.hub, sprite.rect.center, size=size)
        ring = pg.Surface(sprite.image.get_size(), pg.SRCALPHA)
        pg.draw.circle(
            ring,
            HUB_RING_COLOR,
            (sprite.rect.width // 2, sprite.rect.height // 2),
            max(1, sprite.rect.width // 2 - 2),
            width=2,
        )
        sprite.image.blit(ring, (0, 0))


def _draw_hub_drone_counts(
    screen: pg.Surface,
    hub_by_name: dict[str, HubSprite],
    zoom: float,
) -> None:
    """Draw the hub name and drone count inside each hub sprite."""
    name_font = pg.font.Font(None, _scale_value(BASE_NAME_FONT_SIZE, zoom))
    count_font = pg.font.Font(None, _scale_value(BASE_COUNT_FONT_SIZE, zoom))

    def draw_label(text: str, font: pg.font.Font, center: tuple[int, int]) -> None:
        text_surface = font.render(text, True, LABEL_TEXT_COLOR)
        text_outline = font.render(text, True, LABEL_OUTLINE_COLOR)
        text_rect = text_surface.get_rect(center=center)
        padding_x = LABEL_PADDING_X
        padding_y = LABEL_PADDING_Y
        bg_rect = text_rect.inflate(padding_x * 2, padding_y * 2)
        background = pg.Surface(bg_rect.size, pg.SRCALPHA)
        pg.draw.rect(background, LABEL_BG_COLOR, background.get_rect(), border_radius=6)
        pg.draw.rect(background, LABEL_BORDER_COLOR, background.get_rect(), width=1, border_radius=6)
        screen.blit(background, bg_rect)

        outline_offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for offset_x, offset_y in outline_offsets:
            screen.blit(
                text_outline,
                text_outline.get_rect(center=(center[0] + offset_x, center[1] + offset_y)),
            )
        screen.blit(text_surface, text_rect)

    for sprite in hub_by_name.values():
        hub = sprite.hub
        drone_count = len(hub.drones or [])
        offset = max(18, sprite.rect.height // 2 + LABEL_GAP * 3)
        name_center = (sprite.rect.centerx, sprite.rect.centery - offset)
        count_center = (sprite.rect.centerx, sprite.rect.centery + offset)
        draw_label(hub.name, name_font, name_center)
        draw_label(str(drone_count), count_font, count_center)


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

        screen.fill(WHITE)

        screen_positions: dict[str, tuple[int, int]] = {
            name: camera.world_to_screen(base)
            for name, base in base_positions.items()
        }

        _draw_connections(screen, map_, screen_positions, camera.zoom)
        _update_sprite_positions(hub_by_name, screen_positions)
        _update_hub_sprite_sizes(hub_by_name, camera.zoom)
        hub_sprites.draw(screen)
        _draw_hub_drone_counts(screen, hub_by_name, camera.zoom)

        pg.display.flip()
        clock.tick(FPS)