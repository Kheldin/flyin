"""Main orchestration module handling the primary gameplay loop.

Manages window lifecycles, user inputs, simulation timing step advancements,
and coordinates the camera updates alongside the rendering pipelines.
"""

from copy import deepcopy
import sys
import pygame as pg
from pygame.locals import KEYDOWN, K_LEFT, K_RIGHT, K_SPACE, K_q, K_r, QUIT

from game.camera import Camera
from game.draw import (
    BASE_HUB_DIAMETER,
    build_hub_sprites,
    compute_base_hub_pixels,
    draw_auras,
    draw_connections,
    draw_drone_on_connections,
    draw_grid,
    draw_hub_labels,
    scale_value,
)
from models.map import Map, Node
from simulator_step import Simulator

# --- Window & Environment Constants ---
SCREEN_WIDTH: int = 1920
SCREEN_HEIGHT: int = 1080
FPS: int = 60
BG_COLOR: tuple[int, int, int] = (13, 17, 23)


def game_loop(initial_map: Map, show_capacity: bool = False) -> None:
    """Execute the core lifecycle loop of the application.

    Args:
        initial_map: Immutable template configuration representing the original
            unaltered world data layout.
        show_capacity: If True, prints diagnostics about zones and connections
            capacities to the terminal on each step.
    """
    screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pg.RESIZABLE)
    pg.display.set_caption("FlyIn")
    clock = pg.time.Clock()

    # Simulation step interval and accumulator parameters
    sim_tick = 0.5
    sim_acc = 0.0
    sim_paused: bool = True

    # Simulation engine instance creation
    map_ = deepcopy(initial_map)
    sim = Simulator(map_)
    sim_running = True
    sim_finished_printed = False

    # Position calculations and viewport system initializations
    base_positions = compute_base_hub_pixels(map_, screen)
    camera = Camera(screen, base_positions)

    # Sprite framework setup for structural hub management
    hubs, hub_by_name = build_hub_sprites(map_, base_positions, camera)
    hub_sprites = pg.sprite.RenderPlain(*hubs)

    # Click-and-drag camera state trackers
    dragging = False
    last_mouse = pg.Vector2(0, 0)

    def _rebuild_runtime_state() -> None:
        """Reset and rebuild all runtime data back to initial parameters."""
        nonlocal map_, sim, sim_running, sim_finished_printed, sim_acc
        nonlocal base_positions, hubs, hub_by_name, hub_sprites

        map_ = deepcopy(initial_map)
        sim = Simulator(map_)
        sim_running = True
        sim_finished_printed = False
        sim_acc = 0.0

        base_positions = compute_base_hub_pixels(map_, screen)
        hubs, hub_by_name = build_hub_sprites(map_, base_positions, camera)
        hub_sprites = pg.sprite.RenderPlain(*hubs)
        clock.tick(FPS)

    clock.tick(FPS)

    # Primary continuous application runtime execution loop
    while True:
        # Process structural events gathered by the OS window server
        for event in pg.event.get():
            if event.type == QUIT:
                pg.quit()
                sys.exit()
            elif event.type == KEYDOWN:
                if event.key == K_q:
                    pg.quit()
                    sys.exit()
                elif event.key == K_SPACE:
                    sim_paused = not sim_paused
                    status = "paused" if sim_paused else "running"
                    print(f"Simulation {status}")
                elif event.key == K_RIGHT:
                    sim_tick = max(0.05, sim_tick - 0.1)
                    print(f"speed: {sim_tick:.2f}s/turn")
                elif event.key == K_LEFT:
                    sim_tick = min(2.0, sim_tick + 0.1)
                    print(f"speed: {sim_tick:.2f}s/turn")
                elif event.key == K_r:
                    _rebuild_runtime_state()
                    dragging = False
                    last_mouse = pg.Vector2(0, 0)
                    print("Restarting Simulation")
            elif event.type == pg.MOUSEWHEEL:
                camera.handle_zoom_event(event)
            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                dragging = True
                last_mouse = camera.start_pan(event.pos)
            elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
                dragging = False
            elif event.type == pg.MOUSEMOTION and dragging:
                last_mouse = camera.drag_pan(last_mouse, event.pos)

        # Delta time calculation expressed in fractional seconds
        dt = clock.tick(FPS) / 500.0

        # Accumulate time slices and step simulation forward upon intervals
        if not sim_paused:
            sim_acc += dt
            if sim_acc >= sim_tick:
                sim_acc -= sim_tick
                if sim_running:
                    is_finished, moves = sim.step()
                    if moves:
                        print(" ".join(moves))

                    # --- Output Capacity Log Metrics ---
                    if show_capacity:
                        print(f"\n--- Turn {sim.turn} Capacity Usage ---")
                        # 1. Evaluate Hub nodes capacity metrics
                        for hub in map_.hubs:
                            max_z = hub.metadata.max_drones if hub.metadata.max_drones else 1
                            current_z = sum(
                                1 for pos in sim.drone_positions.values()
                                if isinstance(pos, Node) and pos.name == hub.name
                            )
                            print(f"Zone {hub.name}: {current_z}/{max_z} drones")

                        # 2. Evaluate Link paths capacity metrics
                        for conn in map_.connections:
                            max_c = conn.metadata.max_link_capacity if conn.metadata.max_link_capacity else 1
                            current_c = sum(
                                1 for pos in sim.drone_positions.values()
                                if pos == conn
                            )
                            print(
                                f"Connection {conn.node1.name}-{conn.node2.name}: "
                                f"{current_c}/{max_c} capacity used"
                            )
                        print("-" * 40)

                    # Print analytics upon reaching the termination conditions
                    if is_finished and not sim_finished_printed:
                        print(
                            f"Finished in {sim.turn - 1} turns "
                            f"(Delivered: {sim.delivered}/{sim.total} "
                            f"Failed: {sim.failed})"
                        )
                        sim_finished_printed = True
                        sim_running = False

        camera.update()

        # Update absolute world positions to localized screen space coordinates
        screen_positions = {
            name: camera.world_to_screen(base)
            for name, base in base_positions.items()
        }

        # Tabulate static drone volume data resting inside nodes
        drone_count_per_hub: dict[str, int] = {}
        for hub in map_.hubs:
            drone_count_per_hub[hub.name] = sum(
                1
                for d_node in sim.drone_positions.values()
                if isinstance(d_node, Node) and d_node.name == hub.name
            )

        # Classify and map moving transit items down to line keys
        drones_on_connections: dict[tuple[str, str], list[int]] = {}
        for in_transit_entry in sim.in_transit:
            drone_id = in_transit_entry.get("drone_id")
            conn = in_transit_entry.get("conn")
            if drone_id and conn:
                key: tuple[str, str] = tuple(sorted(conn))  # type: ignore
                if key not in drones_on_connections:
                    drones_on_connections[key] = []
                if isinstance(drone_id, int):
                    drones_on_connections[key].append(drone_id)

        # Synchronize dimensions and re-center graphic sprite instances
        size_with_zoom = scale_value(BASE_HUB_DIAMETER, camera.zoom)
        for name, sprite in hub_by_name.items():
            pos = screen_positions.get(name)
            if pos is not None:
                count = drone_count_per_hub.get(name, 0)
                sprite.setup(
                    sprite.hub, pos, size=size_with_zoom, drone_count=count
                )

        hub_sprites.update()

        # Render graphics components sequentially to ensure layered display
        screen.fill(BG_COLOR)
        draw_grid(screen)
        draw_connections(screen, map_, screen_positions, camera.zoom)
        draw_auras(screen, hub_by_name)
        hub_sprites.draw(screen)
        draw_hub_labels(screen, hub_by_name, camera.zoom, drone_count_per_hub)
        draw_drone_on_connections(
            screen, map_, screen_positions, drones_on_connections, camera.zoom
        )

        pg.display.flip()