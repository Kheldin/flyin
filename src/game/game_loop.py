"""Main game loop for FlyIn."""

import sys

import pygame as pg
from pygame.locals import QUIT

from game.game_object import HubSprite
from models.map import Map

# Colours
BLACK: tuple[int, int, int] = (0, 0, 0)
WHITE: tuple[int, int, int] = (255, 255, 255)

# Display
SCREEN_WIDTH: int = 1280
SCREEN_HEIGHT: int = 720

# Camera
MIN_ZOOM: float = 0.25
MAX_ZOOM: float = 6.0
ZOOM_FACTOR: float = 1.15
PAN_SMOOTH: float = 0.1
DEFAULT_ZOOM: float = 0.90

# Physics
FPS: int = 60


def _compute_base_hub_pixels(
    map_: Map,
    screen: pg.Surface,
    padding: int = 20,
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

    return {
        hub.name: (
            padding + (hub.x - min_x) / range_x * drawable_w,
            padding + (hub.y - min_y) / range_y * drawable_h,
        )
        for hub in map_.hubs
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


def _world_to_screen(
    base: tuple[float, float],
    zoom: float,
    pan: pg.Vector2,
) -> tuple[int, int]:
    """Convert a world-space base position to screen-space integer coords.

    Args:
        base: World-space (x, y) position.
        zoom: Current camera zoom factor.
        pan:  Current camera pan offset in screen pixels.

    Returns:
        Integer (x, y) screen coordinates.
    """
    pos = pg.Vector2(base) * zoom + pan
    return int(pos.x), int(pos.y)


def _initial_pan(
    base_positions: dict[str, tuple[float, float]],
    zoom: float,
    screen: pg.Surface,
) -> pg.Vector2:
    """Compute an initial pan so that the hub cluster is centred on screen.

    Args:
        base_positions: World-space hub positions keyed by hub name.
        zoom:           Initial camera zoom factor.
        screen:         The pygame surface whose dimensions define the centre.

    Returns:
        A Vector2 pan offset that centres the hub cluster on screen.
    """
    if not base_positions:
        return pg.Vector2(0, 0)

    xs = [p[0] for p in base_positions.values()]
    ys = [p[1] for p in base_positions.values()]
    map_center = pg.Vector2(sum(xs) / len(xs), sum(ys) / len(ys))
    screen_center = pg.Vector2(screen.get_width() / 2, screen.get_height() / 2)
    return screen_center - map_center * zoom


def _build_hub_sprites(
    map_: Map,
    base_positions: dict[str, tuple[float, float]],
    zoom: float,
    pan: pg.Vector2,
) -> tuple[list[HubSprite], dict[str, HubSprite]]:
    """Instantiate and position hub sprites from the map data.

    Args:
        map_:           The game map containing hub definitions.
        base_positions: World-space hub positions keyed by hub name.
        zoom:           Initial camera zoom factor.
        pan:            Initial camera pan offset.

    Returns:
        A tuple of (list of HubSprite, dict mapping hub name to HubSprite).
    """
    hubs: list[HubSprite] = []
    hub_by_name: dict[str, HubSprite] = {}

    for hub in map_.hubs:
        sprite = HubSprite()
        screen_pos = _world_to_screen(
            base_positions.get(hub.name, (0.0, 0.0)), zoom, pan
        )
        sprite.setup(hub, screen_pos)
        hubs.append(sprite)
        hub_by_name[hub.name] = sprite

    return hubs, hub_by_name


def _draw_connections(
    screen: pg.Surface,
    map_: Map,
    screen_positions: dict[str, tuple[int, int]],
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

    # Determine reference width from the start hub's connection, or first conn.
    ref_width: int = 1
    start_hub = next(
        (h for h in map_.hubs if getattr(h, "start_hub", False)), None
    )
    if start_hub is not None:
        for conn in connections:
            n1 = _hub_name(getattr(conn, "hub_1", ""))
            n2 = _hub_name(getattr(conn, "hub_2", ""))
            if n1 == start_hub.name or n2 == start_hub.name:
                ref_width = max(1, int(getattr(conn, "max_link_capacity", 1)))
                break
    else:
        first = connections[0]
        ref_width = max(1, int(getattr(first, "max_link_capacity", 1)))

    for conn in connections:
        name1 = _hub_name(getattr(conn, "hub_1", ""))
        name2 = _hub_name(getattr(conn, "hub_2", ""))
        s1 = screen_positions.get(name1)
        s2 = screen_positions.get(name2)
        if s1 is None or s2 is None:
            continue

        pg.draw.line(screen, BLACK, s1, s2, width=ref_width)


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


def _handle_zoom_event(
    event: pg.event.Event,
    current_zoom: float,
    target_pan: pg.Vector2,
) -> tuple[float, pg.Vector2]:
    """Return updated (new_zoom, target_pan) after a MOUSEWHEEL event.

    Zoom is applied immediately (no smoothing). The pan is adjusted so that
    the point under the mouse cursor remains stationary after the zoom.

    Args:
        event:        The MOUSEWHEEL pygame event.
        current_zoom: The zoom level active at the time of the event.
        target_pan:   The pan offset to adjust.

    Returns:
        A tuple of (new_zoom, adjusted target_pan).
    """
    old_zoom = current_zoom
    factor = ZOOM_FACTOR ** event.y
    new_zoom = max(MIN_ZOOM, min(MAX_ZOOM, current_zoom * factor))

    if old_zoom != 0.0:
        mouse = pg.Vector2(pg.mouse.get_pos())
        world_base = (mouse - target_pan) / old_zoom
        target_pan = mouse - world_base * new_zoom

    return new_zoom, target_pan


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

    zoom: float = DEFAULT_ZOOM
    pan: pg.Vector2 = _initial_pan(base_positions, zoom, screen)
    target_pan = pg.Vector2(pan)

    hubs: list[HubSprite]
    hub_by_name: dict[str, HubSprite]
    hubs, hub_by_name = _build_hub_sprites(map_, base_positions, zoom, pan)
    all_sprites: pg.sprite.RenderPlain = pg.sprite.RenderPlain(*hubs)

    dragging: bool = False
    last_mouse: pg.Vector2 = pg.Vector2(0, 0)

    while True:
        for event in pg.event.get():
            keys = pg.key.get_pressed()
            if event.type == QUIT or keys[pg.K_q]:
                pg.quit()
                sys.exit()

            elif event.type == pg.MOUSEWHEEL:
                zoom, target_pan = _handle_zoom_event(event, zoom, target_pan)

            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                dragging = True
                last_mouse = pg.Vector2(event.pos)

            elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
                dragging = False

            elif event.type == pg.MOUSEMOTION and dragging:
                mpos = pg.Vector2(event.pos)
                delta = mpos - last_mouse
                pan += delta
                target_pan += delta
                last_mouse = mpos

        # Smooth pan interpolation
        pan = pan.lerp(target_pan, PAN_SMOOTH)

        screen.fill(WHITE)

        # Round pan to integer pixels to avoid sub-pixel jitter
        round_pan: pg.Vector2 = pg.Vector2(round(pan.x), round(pan.y))

        # Compute integer screen positions once per frame and reuse
        screen_positions: dict[str, tuple[int, int]] = {
            name: _world_to_screen(base, zoom, round_pan)
            for name, base in base_positions.items()
        }

        _draw_connections(screen, map_, screen_positions)
        _update_sprite_positions(hub_by_name, screen_positions)
        all_sprites.draw(screen)

        pg.display.flip()
        clock.tick(FPS)