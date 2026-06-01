from parsing.parsing import parse_file
import pygame
from game.game_loop import game_loop
from simulator_step import PathFinder, PathError


def main():
    try:
        map = parse_file()
        
        # Compute drone paths using the pathfinder
        print(f"Finding paths for {map.nb_drones} drones...", flush=True)
        try:
            pathfinder = PathFinder(map)
            # pathfinder.route_all_drones()
            # print(f"Successfully computed paths for {len(pathfinder.drones_paths)} drones", flush=True)
            for drone_id, path in sorted(pathfinder.drones_paths.items()):
                print(f"  Drone {drone_id}: {len(path)} steps")
        except PathError as e:
            print(f"Pathfinding error: {e}", flush=True)
        
        pygame.init()
        game_loop(map)
    except Exception as e:
        print(e)


if __name__ == "__main__":
    # try:
    #     main()
    # except Exception as e:
    #     print(e)
    main()