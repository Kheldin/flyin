"""Camera module providing smooth panning and zooming functionalities."""

import pygame as pg

# Camera configuration constants
MIN_ZOOM: float = 0.25
MAX_ZOOM: float = 6.0
ZOOM_FACTOR: float = 1.15
PAN_SMOOTH: float = 0.1
DEFAULT_ZOOM: float = 1.5


class Camera:
    """Manages 2D camera operations including zooming and panning."""

    def __init__(
        self, screen: pg.Surface,
        base_positions: dict[str, tuple[float, float]]
    ):
        """Initialize the camera with screen reference and initial layout.

        Args:
            screen: The target Pygame Surface representing the display.
            base_positions: Dictionary mapping element names to their raw
                world coordinates.
        """
        self.screen = screen
        self.zoom = DEFAULT_ZOOM
        # Calculate initial offset to center the map elements on screen
        self.pan = self._initial_pan(base_positions)
        # Target pan is used for interpolating smooth transitions
        self.target_pan = pg.Vector2(self.pan)

    def _initial_pan(
        self, base_positions: dict[str, tuple[float, float]]
    ) -> pg.Vector2:
        """Calculate the initial pan offset to center the cluster on screen.

        Args:
            base_positions: Dictionary mapping element names to their raw
                world coordinates.

        Returns:
            A Vector2 offset that aligns the center of the world elements
            with the center of the viewport surface.
        """
        if not base_positions:
            return pg.Vector2(0, 0)

        # Extract coordinates to compute the bounding box center
        xs = [p[0] for p in base_positions.values()]
        ys = [p[1] for p in base_positions.values()]
        map_center = pg.Vector2(sum(xs) / len(xs), sum(ys) / len(ys))
        screen_center = pg.Vector2(
            self.screen.get_width() / 2, self.screen.get_height() / 2
        )
        # Offset calculation taking the initial zoom into account
        return screen_center - map_center * self.zoom

    def world_to_screen(self, base: tuple[float, float]) -> tuple[int, int]:
        """Convert world-space coordinates to integer screen-space pixels.

        Args:
            base: A tuple containing the raw X and Y world coordinates.

        Returns:
            A tuple of integers representing the transformed screen position.
        """
        pos = pg.Vector2(base) * self.zoom + self.pan
        return int(pos.x), int(pos.y)

    def handle_zoom_event(self, event: pg.event.Event) -> None:
        """Adjust zoom level focused on current
            mouse position upon wheel input.

        Args:
            event: The Pygame MOUSEWHEEL event object containing rotation data.
        """
        old_zoom = self.zoom
        factor = ZOOM_FACTOR**event.y
        # Clamp the new zoom within configured boundaries
        self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, self.zoom * factor))

        if old_zoom != 0.0:
            mouse = pg.Vector2(pg.mouse.get_pos())
            # Determine mouse position in world-space before zoom change
            world_base = (mouse - self.target_pan) / old_zoom
            # Re-align target pan so the same world point stays under mouse
            self.target_pan = mouse - world_base * self.zoom

    def update(self) -> None:
        """Smoothly interpolate the current camera position toward the target.

        This should be called once per frame to update the view positions.
        """
        self.pan = self.pan.lerp(self.target_pan, PAN_SMOOTH)

    def start_pan(self, pos: tuple[int, int]) -> pg.Vector2:
        """Record the starting mouse coordinates when a drag action begins.

        Args:
            pos: The initial X and Y pixel position of the cursor.

        Returns:
            A new Vector2 representing the fixed mouse starting position.
        """
        return pg.Vector2(pos)

    def drag_pan(
        self, last_mouse: pg.Vector2, event_pos: tuple[int, int]
    ) -> pg.Vector2:
        """Update pan offset based on mouse displacement during a drag.

        Args:
            last_mouse: Vector2 representing the mouse position during the
                previous frames.
            event_pos: The updated X and Y coordinates of the mouse cursor.

        Returns:
            The current mouse position converted into a Vector2 to be cached
            for the next frame.
        """
        mpos = pg.Vector2(event_pos)
        delta = mpos - last_mouse
        # Apply displacement instantly to both current and target pan
        self.pan += delta
        self.target_pan += delta
        return mpos
