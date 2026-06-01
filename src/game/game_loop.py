from copy import deepcopy
import sys

import pygame as pg
from pygame.locals import QUIT, KEYDOWN, K_q, K_SPACE, K_RIGHT, K_LEFT, K_r

from simulator_step import Simulator
from models.map import Node, Map
from game.camera import Camera


# --- Constants ---
SCREEN_WIDTH: int = 1920
SCREEN_HEIGHT: int = 1080
FPS: int = 60
BG_COLOR: tuple[int, int, int] = (13, 17, 23)

from game.draw import (
    BASE_HUB_DIAMETER,
    scale_value,
    compute_base_hub_pixels,
    build_hub_sprites,
    draw_grid,
    draw_connections,
    draw_auras,
    draw_hub_labels,
    draw_connection_drone_counts,
)


def game_loop(initial_map: Map) -> None:
    screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pg.RESIZABLE)
    pg.display.set_caption("FlyIn")
    clock = pg.time.Clock()

    sim_tick = 0.2
    sim_acc = 0.0
    sim_paused: bool = False

    map_ = deepcopy(initial_map)
    sim = Simulator(map_)  # Live simulator: shows intermediate steps
    sim_running = True
    sim_finished_printed = False

    base_positions = compute_base_hub_pixels(map_, screen)
    camera = Camera(screen, base_positions)

    hubs, hub_by_name = build_hub_sprites(map_, base_positions, camera)
    hub_sprites = pg.sprite.RenderPlain(*hubs)

    dragging = False
    last_mouse = pg.Vector2(0, 0)

    def _rebuild_runtime_state() -> None:
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

    while True:
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
                    print("Simulation " + ("paused" if sim_paused else "running"))
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

        camera.update()

        screen.fill(BG_COLOR)
        draw_grid(screen)

        screen_positions = {name: camera.world_to_screen(base) for name, base in base_positions.items()}

        draw_connections(screen, map_, screen_positions, camera.zoom)

        drone_count_per_hub: dict[str, int] = {}
        for hub in map_.hubs:
            drone_count_per_hub[hub.name] = sum(
                1
                for d_node in sim.drone_positions.values()
                if isinstance(d_node, Node) and d_node.name == hub.name
            )
        
        # Collect drones on connections (in-transit)
        drones_on_connections: dict[tuple[str, str], list[int]] = {}
        for in_transit_entry in sim.in_transit:
            drone_id = in_transit_entry.get('drone_id')
            conn = in_transit_entry.get('conn')
            if drone_id and conn:
                # conn is a tuple (hub1_name, hub2_name)
                key: tuple[str, str] = tuple(sorted(conn))  # type: ignore
                if key not in drones_on_connections:
                    drones_on_connections[key] = []
                if isinstance(drone_id, int):
                    drones_on_connections[key].append(drone_id)

        size_with_zoom = scale_value(BASE_HUB_DIAMETER, camera.zoom)
        for name, sprite in hub_by_name.items():
            pos = screen_positions.get(name)
            if pos is not None:
                sprite.setup(sprite.hub, pos, size=size_with_zoom)

        draw_auras(screen, hub_by_name)
        hub_sprites.draw(screen)
        draw_hub_labels(screen, hub_by_name, camera.zoom, drone_count_per_hub)
        draw_connection_drone_counts(screen, map_, screen_positions, drones_on_connections, camera.zoom)

        pg.display.flip()
        
        dt = clock.tick(FPS) / 500.0
        
        if not sim_paused:
            sim_acc += dt

            if sim_acc >= sim_tick:
                sim_acc -= sim_tick
                
                if sim_running:
                    is_finished, moves = sim.step()
                else:
                    is_finished, moves = True, []
                
                if moves:
                    print(" ".join(moves))
                
                if is_finished and not sim_finished_printed:
                    print(
                        f"Finished in {sim.turn} turns "
                        f"(Delivered: {sim.delivered}/{sim.total}, Failed: {sim.failed})"
                    )
                    sim_finished_printed = True
                    sim_running = False