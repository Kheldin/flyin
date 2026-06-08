*This project has been created as part of the 42 curriculum by kacherch.*

# flyin

A map-based flight simulation visualizer written in Python. The program parses a custom map format describing hubs and connections, then runs a real-time graphical simulation using pygame.

---

## Description

**flyin** is a 2D simulation and visualization project built as part of the 42 school curriculum. It models a directed graph of **hubs** (nodes) connected by **routes** (edges), simulates the movement of objects along those routes, and renders the whole system in an interactive graphical window.

The project is structured around three concerns:

- **Parsing** — reading and validating a custom plaintext map format into an in-memory graph model
- **Simulation** — advancing the state of the system one step at a time (`simulator_step`)
- **Visualization** — rendering the map, objects, and camera state to the screen using pygame

### Goal

Given a map file describing an aerial network of hubs and connections, the program must:
1. Parse and validate the map
2. Display the network graphically with a scrollable/zoomable camera
3. Animate objects moving along connections between hubs at each simulation step

---

## Algorithm explanation and Choices & Implementation Strategy

### Graph Model (`models/map.py`)

The map is represented as a directed graph. Hubs are nodes with a name and 2D position; connections are directed edges with a capacity and travel time. The model is kept pure (no rendering logic), making it easy to test and reuse.

### Routing & Collision Avoidance Strategy (`src/simulator_step.py` & `src/models/`)

To prevent entities from overlapping and violating graph capacities, the project implements a **Space-Time Cooperative Pathfinding** approach combined with an isolated reservation ledger:

1. **Perfect Heuristic (Backward Dijkstra):** Before routing individual entities, a reverse Dijkstra traversal is computed backward from the `end_hub` across the entire map. This populates a static lookup table with the exact topological distance remaining to the destination from any given node, ensuring an optimal, Cul-de-sac-free lookahead for the pathfinder.
2. **Space-Time A\* Search (4D Routing):** Paths are evaluated in a four-dimensional continuum `(Node/Connection, Time)`. At each discrete step, an entity evaluates two scenarios: moving to an adjacent unblocked hub or waiting in place to let traffic pass. The search honors zone specificities, doubling the traversal time inside `RESTRICTED` tracks, while favoring `PRIORITY` paths through heuristic bonuses.
3. **Sequential Reservation Ledger:** Once a non-conflicting path is found for an entity, its full timeline is locked into a global space-time reservation register. For subsequent entities, these locked windows act as dynamic, impassable obstacles. This multi-agent decomposition avoids exponential computational explosions $\mathcal{O}(V^D)$ and maintains a polynomial runtime, allowing hundreds of entities to synchronize smoothly in real-time.

### Parsing (`parsing/`)

The parser is split into focused modules:

| Module | Responsibility |
|---|---|
| `parsing.py` | Top-level entry point, orchestrates the full parse |
| `parse_hub.py` | Parses hub definitions and their bracket syntax |
| `parse_connection.py` | Parses directed connection declarations |
| `parse_brackets.py` | Low-level bracket/token extraction utility |
| `errors.py` | Custom exception types for parse errors |

The strategy is a **single-pass line-by-line parser**: each line is categorised (hub, connection, comment, blank) and dispatched to the appropriate sub-parser. Errors are raised early and carry the offending line number, making debugging map files straightforward.

### Simulation (`simulator_step.py`)

Each call to `simulator_step` advances the world by one tick. Objects in transit along a connection have their progress incremented; objects that arrive at a hub are queued for dispatch along the next available connection according to the routing logic. The step function is kept stateless with respect to rendering — it receives the current map state and returns the updated state.

### Rendering (`game/`)

| Module | Responsibility |
|---|---|
| `camera.py` | Tracks pan/zoom state; converts world coordinates to screen coordinates |
| `draw.py` | Draws hubs, connections, moving objects, and labels each frame |
| `game_object.py` | Data class representing a moving entity (position, route, progress) |
| `game_loop.py` | Main loop: event handling → simulate step → draw → flip |

Rendering is entirely separate from the model and simulation. The camera transform is applied at draw time, so the simulation works in world-space coordinates throughout.

---

## Visual Representation Features

The graphical interface enhances the user experience in several ways:

- **Camera pan & zoom** — click-drag to pan the view, scroll wheel to zoom in/out, letting you explore large networks comfortably
- **Hub labels** — each hub renders its name above its node circle, making the graph readable at a glance
- **Connection** — connections are drawn as lines

These choices keep the simulation legible even for dense maps with many overlapping connections.

---

## Instructions

### Requirements

- Python 3.13+
- [`uv`](https://github.com/astral-sh/uv) (recommended)
- pygame

### Installation

**With uv (recommended):**
```bash
git clone https://github.com/Kheldin/flyin.git
cd flyin
make run
```

### Running

```bash
# With uv
make run
```

### Type checking (optional)

```bash
make lint
make lint-strict
```

Requires the following in `pyproject.toml`:
```toml
[tool.mypy]
mypy_path = "src"
explicit_package_bases = true
```
---

## Project Structure

```
flyin/
├── maps/                   # Map input files
├── src/
│   ├── main.py             # Entry point
│   ├── simulator_step.py   # Simulation tick logic
│   ├── models/
│   │   └── map.py          # Graph data model (hubs + connections)
│   ├── parsing/
│   │   ├── parsing.py      # Top-level parser
│   │   ├── parse_hub.py    # Hub parser
│   │   ├── parse_connection.py  # Connection parser
│   │   ├── parse_brackets.py   # Token utilities
│   │   └── errors.py       # Parse error types
│   └── game/
│       ├── camera.py       # Pan/zoom camera
│       ├── draw.py         # Rendering
│       ├── game_loop.py    # Main game loop
│       └── game_object.py  # Moving entity data class
├── pyproject.toml
├── uv.lock
└── Makefile
```

---

## Resources

### Documentation & References

- [pygame documentation](https://www.pygame.org/docs/) — the rendering and event loop library used for the graphical interface
- [Python type hints — mypy docs](https://mypy.readthedocs.io/en/stable/) — used for static type checking across the project
- [Graph theory — Wikipedia](https://en.wikipedia.org/wiki/Graph_theory) — background on directed graphs, the core data structure of the map model
- [uv — Python package manager](https://github.com/astral-sh/uv) — used for dependency management and virtual environments
- [PEP 8 — Python style guide](https://peps.python.org/pep-0008/) — coding conventions followed throughout

### AI Usage

AI was used in the following parts of this project:

- **Debugging mypy import errors** — diagnosing the `import-not-found` errors caused by mypy not knowing `src/` was the package root, and identifying the correct `pyproject.toml` configuration fix (`mypy_path = "src"`, `explicit_package_bases = true`)
- **README writing** — structuring and drafting this README to meet the 42 curriculum requirements
- **Drawing** — Visual aspect of the simulation
- **Docstrings** — Ruff complient docstrings