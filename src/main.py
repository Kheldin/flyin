"""Main entry point script responsible for initializing the application.

Configures environment properties, compiles layout maps from terminal
arguments, provisions multimedia subsystems, and triggers the active core game
loop framework inside execution blocks.
"""

import os
import argparse
import sys
# Suppress the default Pygame community greeting prompt in standard outputs
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import pygame as pg  # noqa: E402

from game.game_loop import game_loop  # noqa: E402
from parsing.parsing import parse_file  # noqa: E402


def main() -> None:
    """Orchestrate compilation and subsystem allocations sequentially.

    Parses target asset definitions, signals driver starts, and passes control
    mechanics to background viewport pipelines inside isolated boundaries.
    """
    try:
        map_ = parse_file()
        pg.init()
        game_loop(map_)
    except Exception as e:
        print(e)


# === LE POINT D'ENTRÉE DU SCRIPT EXÉCUTABLE DANS main.py ===
if __name__ == "__main__":
    from parsing.parsing import parse_file  # Importation de parse_file avec le bon nom

    # Initialisation du gestionnaire d'arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="FlyIn — Multi-Agent Space-Time Drone Simulation Visualizer")
    parser.add_argument("map_file", help="Path to the custom plaintext map file")
    parser.add_argument(
        "--capacity-info", 
        action="store_true", 
        help="Display capacity utilization diagnostics for zones and links at every turn"
    )
    
    args = parser.parse_args()
    
    # Validation et lecture du fichier de carte passé en argument
    try:
        loaded_map = parse_file(args.map_file) # Appel avec le bon nom de fonction et l'argument
    except Exception as error:
        print(f"Error parsing map: {error}", file=sys.stderr)
        sys.exit(1)
        
    # Initialisation de Pygame et lancement du jeu
    pg.init()
    try:
        game_loop(loaded_map, show_capacity=args.capacity_info)
    except KeyboardInterrupt:
        print("\nSimulation aborted by user.")
    finally:
        pg.quit()