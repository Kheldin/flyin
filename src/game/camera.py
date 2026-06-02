"""Camera for panning and zooming."""

import pygame as pg

# Camera
MIN_ZOOM: float = 0.25
MAX_ZOOM: float = 6.0
ZOOM_FACTOR: float = 1.15
PAN_SMOOTH: float = 0.1
DEFAULT_ZOOM: float = 1


class Camera:
    """Manages camera zoom and pan."""

    def __init__(self, screen: pg.Surface, base_positions: dict[str, tuple[float, float]]):
        """Initialise the camera."""
        self.screen = screen
        self.zoom = DEFAULT_ZOOM
        self.pan = self._initial_pan(base_positions)
        self.target_pan = pg.Vector2(self.pan)

    def _initial_pan(self, base_positions: dict[str, tuple[float, float]]) -> pg.Vector2:
        """Compute an initial pan so that the hub cluster is centred on screen."""
        if not base_positions:
            return pg.Vector2(0, 0)

        xs = [p[0] for p in base_positions.values()]
        ys = [p[1] for p in base_positions.values()]
        map_center = pg.Vector2(sum(xs) / len(xs), sum(ys) / len(ys))
        screen_center = pg.Vector2(self.screen.get_width() / 2, self.screen.get_height() / 2)
        return screen_center - map_center * self.zoom

    def world_to_screen(self, base: tuple[float, float]) -> tuple[int, int]:
        """Convert a world-space base position to screen-space integer coords."""
        pos = pg.Vector2(base) * self.zoom + self.pan
        return int(pos.x), int(pos.y)

    def handle_zoom_event(self, event: pg.event.Event) -> None:
        """Update zoom and pan after a MOUSEWHEEL event."""
        old_zoom = self.zoom
        factor = ZOOM_FACTOR ** event.y
        self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, self.zoom * factor))

        if old_zoom != 0.0:
            mouse = pg.Vector2(pg.mouse.get_pos())
            world_base = (mouse - self.target_pan) / old_zoom
            self.target_pan = mouse - world_base * self.zoom

    def update(self) -> None:
        """Smoothly update the camera's pan."""
        self.pan = self.pan.lerp(self.target_pan, PAN_SMOOTH)

    def start_pan(self, pos: tuple[int, int]) -> pg.Vector2:
        """Start a pan operation."""
        return pg.Vector2(pos)

    def drag_pan(self, last_mouse: pg.Vector2, event_pos: tuple[int, int]) -> pg.Vector2:
        """Handle dragging pan."""
        mpos = pg.Vector2(event_pos)
        delta = mpos - last_mouse
        self.pan += delta
        self.target_pan += delta
        return mpos
