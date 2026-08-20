"""Movement legality (chess + stratego) and turn order.

Pure module — no FastAPI imports.

CURRENT RULES (v1):
- Chess pieces move per standard chess, with custom-board simplifications:
  no castling, no en passant, no pawn double-step (free-placement setup has
  no "starting square"), and no check rules (see RULES.md section 7 — the
  king is captured like any piece). Pawns move away from their owner's
  home edge and auto-promote to queen on the far row/column.
- Stratego pieces move one square orthogonally; the scout slides straight
  like a rook; bombs and the flag are immobile.
- Lakes block occupation and sliding paths; knights may leap over them.
- Turn order: clockwise round-robin from the game creator, one move per
  turn. Eliminated seats are skipped. A player with no legal move is
  skipped (turn_skipped event); if no active player can move, the game
  ends in a draw (phase "finished", winner None).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.engine.board import FORWARD_BY_EDGE
from app.engine.pieces import Piece, Pos

if TYPE_CHECKING:
    from app.engine.state import GameState, Player

KNIGHT_OFFSETS = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
KING_OFFSETS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
ORTHOGONALS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
DIAGONALS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]


def legal_moves(state: GameState, piece: Piece) -> set[Pos]:
    """All squares `piece` may move to (captures included) right now."""
    board = state.board
    if board is None or piece.pos is None or piece.captured:
        return set()
    occupied: dict[Pos, str] = {
        p.pos: p.owner for p in state.pieces.values() if not p.captured and p.pos is not None
    }

    def open_square(pos: Pos) -> bool:
        return board.on_board(pos) and not board.is_lake(pos)

    def landable(pos: Pos) -> bool:
        return open_square(pos) and occupied.get(pos) != piece.owner

    def slide(directions: list[Pos]) -> set[Pos]:
        moves: set[Pos] = set()
        assert piece.pos is not None
        for dr, dc in directions:
            r, c = piece.pos
            while True:
                r, c = r + dr, c + dc
                if not open_square((r, c)):
                    break
                if (r, c) in occupied:
                    if occupied[(r, c)] != piece.owner:
                        moves.add((r, c))
                    break
                moves.add((r, c))
        return moves

    def steps(offsets: list[Pos]) -> set[Pos]:
        assert piece.pos is not None
        r, c = piece.pos
        return {(r + dr, c + dc) for dr, dc in offsets if landable((r + dr, c + dc))}

    if piece.kind == "chess":
        if piece.type == "pawn":
            return _pawn_moves(state, piece, occupied, open_square)
        if piece.type == "knight":
            return steps(KNIGHT_OFFSETS)
        if piece.type == "bishop":
            return slide(DIAGONALS)
        if piece.type == "rook":
            return slide(ORTHOGONALS)
        if piece.type == "queen":
            return slide(ORTHOGONALS + DIAGONALS)
        return steps(KING_OFFSETS)  # king

    if piece.type in ("bomb", "flag"):
        return set()
    if piece.type == "scout":
        return slide(ORTHOGONALS)
    return steps(ORTHOGONALS)


def _pawn_moves(
    state: GameState,
    piece: Piece,
    occupied: dict[Pos, str],
    open_square: Any,
) -> set[Pos]:
    assert piece.pos is not None
    owner = next(p for p in state.players if p.id == piece.owner)
    dr, dc = FORWARD_BY_EDGE[owner.edge]
    r, c = piece.pos
    moves: set[Pos] = set()
    ahead = (r + dr, c + dc)
    if open_square(ahead) and ahead not in occupied:
        moves.add(ahead)
    # Diagonal captures: forward plus one square perpendicular to forward.
    for perp in ((dc, dr), (-dc, -dr)):
        diag = (r + dr + perp[0], c + dc + perp[1])
        if open_square(diag) and occupied.get(diag) not in (None, piece.owner):
            moves.add(diag)
    return moves


def is_legal_move(state: GameState, from_pos: Pos, to_pos: Pos) -> bool:
    for piece in state.pieces.values():
        if not piece.captured and piece.pos == from_pos:
            return to_pos in legal_moves(state, piece)
    return False


def current_player(state: GameState) -> Player:
    return state.players[state.turn_index]


def has_any_legal_move(state: GameState, player_id: str) -> bool:
    return any(
        legal_moves(state, piece)
        for piece in state.pieces.values()
        if piece.owner == player_id and not piece.captured
    )


def advance_turn(state: GameState) -> list[dict[str, Any]]:
    """Move to the next seat that can act; skip stuck players; draw if none can."""
    events: list[dict[str, Any]] = []
    n = len(state.players)
    for offset in range(1, n + 1):
        candidate = state.players[(state.turn_index + offset) % n]
        if candidate.eliminated:
            continue
        if has_any_legal_move(state, candidate.id):
            state.turn_index = (state.turn_index + offset) % n
            return events
        events.append({"kind": "turn_skipped", "player_id": candidate.id})
    state.phase = "finished"
    state.winner = None
    return events
