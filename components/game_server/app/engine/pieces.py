"""Piece definitions: the chess set plus the v1 reduced Stratego set.

Pure module — no FastAPI imports.

CURRENT ARMY (v1): 16 chess (standard) + 14 stratego per player:
1 flag, 3 bombs, 1 spy, 2 scouts, 2 miners, 1 marshal, 1 general,
1 colonel, 1 major, 1 captain. 30 pieces fit every setup zone.

DOCUMENTED VARIANT (not active): the full classic 40-piece stratego set.
It cannot fit alongside the chess set at 12x12/14x14 (56 pieces per player
overflows the 3-row setup zones), but is viable at 16x16 with a 4-row
setup zone (64 squares >= 56 pieces). To activate: replace
STRATEGO_SET_COUNTS below with the classic counts (1 flag, 6 bombs, 1 spy,
8 scouts, 5 miners, 4 sergeants, 4 lieutenants, 4 captains, 3 majors,
2 colonels, 1 general, 1 marshal — adding the missing rank types), deepen
the setup zones in board.py, and log the change in DECISION_LOG.md.

Piece ids are opaque random hex — an id must never encode the piece's
type, or it would leak hidden ranks through the redacted wire format.
"""

import secrets
from typing import Literal

from pydantic import BaseModel

PieceKind = Literal["chess", "stratego"]

CHESS_TYPES = ("pawn", "knight", "bishop", "rook", "queen", "king")
STRATEGO_TYPES = (
    "flag", "bomb", "spy", "scout", "miner",
    "captain", "major", "colonel", "general", "marshal",
)

# Classic stratego ranks for the types in the v1 reduced set. Flag and bomb
# have no rank — they never win a rank comparison (specialty rules only).
STRATEGO_RANKS: dict[str, int] = {
    "spy": 1,
    "scout": 2,
    "miner": 3,
    "captain": 6,
    "major": 7,
    "colonel": 8,
    "general": 9,
    "marshal": 10,
}

CHESS_SET_COUNTS: dict[str, int] = {
    "pawn": 8, "knight": 2, "bishop": 2, "rook": 2, "queen": 1, "king": 1,
}

STRATEGO_SET_COUNTS: dict[str, int] = {
    "flag": 1, "bomb": 3, "spy": 1, "scout": 2, "miner": 2,
    "marshal": 1, "general": 1, "colonel": 1, "major": 1, "captain": 1,
}

ARMY_SIZE = sum(CHESS_SET_COUNTS.values()) + sum(STRATEGO_SET_COUNTS.values())  # 30

Pos = tuple[int, int]  # (row, col); row 0 is the north (top) edge


class Piece(BaseModel):
    id: str
    owner: str
    kind: PieceKind
    type: str
    revealed: bool = False
    pos: Pos | None = None  # None while unplaced (setup) — never after setup
    captured: bool = False


def _new_id() -> str:
    return secrets.token_hex(4)


def create_army(owner: str) -> list[Piece]:
    """Build one player's full army (chess visible, stratego hidden), unplaced."""
    army: list[Piece] = []
    for type_, count in CHESS_SET_COUNTS.items():
        for _ in range(count):
            # Chess pieces are public information at all times.
            army.append(Piece(id=_new_id(), owner=owner, kind="chess", type=type_, revealed=True))
    for type_, count in STRATEGO_SET_COUNTS.items():
        for _ in range(count):
            army.append(Piece(id=_new_id(), owner=owner, kind="stratego", type=type_))
    return army


def all_piece_types() -> dict[str, tuple[str, ...]]:
    """The full chess + stratego piece type catalogue, by kind."""
    return {"chess": CHESS_TYPES, "stratego": STRATEGO_TYPES}
