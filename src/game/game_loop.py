"""Main game loop for FlyIn."""

import sys

import pygame as pg
from pygame.locals import QUIT

from game.camera import Camera
from game.game_object import HubSprite
from models.map import Map

# Colours
BLACK: tuple[int, int, int] = (0, 0, 0)
WHITE: tuple[int, int, int] = (255, 255, 255)

# Display
SCREEN_WIDTH: int = 1280
SCREEN_HEIGHT: int = 720

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

    for conn in connections:
        name1 = _hub_name(getattr(conn, "hub_1", ""))
        name2 = _hub_name(getattr(conn, "hub_2", ""))
        s1 = screen_positions.get(name1)
        s2 = screen_positions.get(name2)
        if s1 is None or s2 is None:
            continue

        pg.draw.line(screen, BLACK, s1, s2, width=5)


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
    all_sprites: pg.sprite.RenderPlain = pg.sprite.RenderPlain(*hubs)

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

        _draw_connections(screen, map_, screen_positions)
        _update_sprite_positions(hub_by_name, screen_positions)
        all_sprites.draw(screen)

        pg.display.flip()
        clock.tick(FPS)