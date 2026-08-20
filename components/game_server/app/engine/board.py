"""Board geometry: size by player count, lakes, edge layouts, setup zones.

Pure module — no FastAPI imports.

CURRENT RULE (v1):
- Board size scales with player count: 12x12 (2p), 14x14 (3p), 16x16 (4p).
  One tunable table: BOARD_SIZE_BY_PLAYER_COUNT.
- Lakes are 2x2 impassable blocks, symmetric around the board center:
  two blocks at 12x12, four blocks at 14x14 and 16x16 (LAKES_BY_SIZE).
- Edge layouts, clockwise from the game creator (who is always south):
  2p = south/north, 3p = south/west/north (east empty), 4p = all four.
- Setup zone = your own edge, 3 rows (or columns) deep, full length.
  Where two occupied zones would overlap in a 3x3 corner, the corner
  belongs to exactly one of them (CORNER_OWNER below: NW->north, NE->east,
  SE->south, SW->west — a pinwheel, so 4p zones stay congruent). A corner
  bordering an unoccupied edge stays with the occupied neighbor. Every
  zone holds >= 33 squares, enough for the 30-piece army (pieces.py).
"""

from pydantic import BaseModel

from app.engine.pieces import Pos

Edge = str  # "north" | "south" | "east" | "west"

BOARD_SIZE_BY_PLAYER_COUNT: dict[int, int] = {2: 12, 3: 14, 4: 16}

# Clockwise seating from the creator (south edge, bottom of the screen).
EDGES_BY_PLAYER_COUNT: dict[int, list[Edge]] = {
    2: ["south", "north"],
    3: ["south", "west", "north"],
    4: ["south", "west", "north", "east"],
}

SETUP_ZONE_DEPTH = 3

# Which edge owns each contested 3x3 corner (pinwheel assignment).
CORNER_OWNER: dict[tuple[Edge, Edge], Edge] = {
    ("north", "west"): "north",
    ("north", "east"): "east",
    ("south", "east"): "south",
    ("south", "west"): "west",
}

# "Forward" for each edge's pawns: the direction away from the home edge.
FORWARD_BY_EDGE: dict[Edge, Pos] = {
    "south": (-1, 0),
    "north": (1, 0),
    "west": (0, 1),
    "east": (0, -1),
}


def _lake_blocks(size: int) -> list[Pos]:
    """2x2 lake blocks, symmetric around the center of a size x size board."""
    cells: list[Pos] = []
    if size == 12:
        # Two blocks on the center rows, mirrored across the vertical axis.
        for r in (5, 6):
            for c in (3, 4, 7, 8):
                cells.append((r, c))
    else:
        # Four blocks in a symmetric square pattern around the center.
        lo, hi = (4, 8) if size == 14 else (5, 9)
        for r0 in (lo, hi):
            for c0 in (lo, hi):
                for r in (r0, r0 + 1):
                    for c in (c0, c0 + 1):
                        cells.append((r, c))
    return cells


LAKES_BY_SIZE: dict[int, list[Pos]] = {s: _lake_blocks(s) for s in (12, 14, 16)}


class Board(BaseModel):
    size: int
    num_players: int
    lakes: list[Pos]
    edges: list[Edge]  # edges[i] is player-seat i's home edge
    setup_zones: dict[Edge, list[Pos]]

    def on_board(self, pos: Pos) -> bool:
        r, c = pos
        return 0 <= r < self.size and 0 <= c < self.size

    def is_lake(self, pos: Pos) -> bool:
        return pos in self.lake_set

    @property
    def lake_set(self) -> set[Pos]:
        return set(self.lakes)


def _edge_band(edge: Edge, size: int) -> set[Pos]:
    depth = SETUP_ZONE_DEPTH
    if edge == "north":
        return {(r, c) for r in range(depth) for c in range(size)}
    if edge == "south":
        return {(r, c) for r in range(size - depth, size) for c in range(size)}
    if edge == "west":
        return {(r, c) for r in range(size) for c in range(depth)}
    return {(r, c) for r in range(size) for c in range(size - depth, size)}


def _corner_cells(vertical: Edge, horizontal: Edge, size: int) -> set[Pos]:
    return _edge_band(vertical, size) & _edge_band(horizontal, size)


def _setup_zones(edges: list[Edge], size: int) -> dict[Edge, list[Pos]]:
    zones = {edge: _edge_band(edge, size) for edge in edges}
    for (vertical, horizontal), owner in CORNER_OWNER.items():
        if vertical not in zones or horizontal not in zones:
            continue  # corner borders an unoccupied edge — occupied neighbor keeps it
        corner = _corner_cells(vertical, horizontal, size)
        loser = horizontal if owner == vertical else vertical
        zones[loser] -= corner
    return {edge: sorted(cells) for edge, cells in zones.items()}


def build_board(num_players: int) -> Board:
    """Return the board layout (size, lakes, setup zones) for num_players."""
    if num_players not in BOARD_SIZE_BY_PLAYER_COUNT:
        raise ValueError(f"unsupported player count: {num_players}")
    size = BOARD_SIZE_BY_PLAYER_COUNT[num_players]
    edges = EDGES_BY_PLAYER_COUNT[num_players]
    return Board(
        size=size,
        num_players=num_players,
        lakes=LAKES_BY_SIZE[size],
        edges=edges,
        setup_zones=_setup_zones(edges, size),
    )


def promotion_reached(edge: Edge, pos: Pos, size: int) -> bool:
    """True when a pawn from `edge` stands on its promotion row/column."""
    r, c = pos
    if edge == "south":
        return r == 0
    if edge == "north":
        return r == size - 1
    if edge == "west":
        return c == size - 1
    return c == 0
