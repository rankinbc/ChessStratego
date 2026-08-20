"""Per-player elimination and overall win conditions.

Pure module — no FastAPI imports.

CURRENT RULE (v1): a player is eliminated when their flag is captured OR
their king is captured (either is sufficient). On elimination all their
remaining pieces are removed from the board (not frozen). Play continues
among the rest; the last player still standing wins. If no active player
can move, the game ends in a draw (handled by movement.advance_turn).

DOCUMENTED VARIANTS (NOT ACTIVE):
- Flag-only: only flag capture eliminates; a king-less player keeps
  playing and the king stops being special. Swap: drop "king" from
  CRITICAL_TYPES.
- King-only: only king capture eliminates (chess-style); the flag becomes
  a pure decoy with no game effect. Swap: drop "flag" from CRITICAL_TYPES.
Flip the labels in RULES.md section 6 and log in DECISION_LOG.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.engine.state import GameState

CRITICAL_TYPES = ("flag", "king")


def check_elimination(state: GameState, player_id: str) -> str | None:
    """Return the elimination reason ("flag_captured"/"king_captured") or None."""
    player = next(p for p in state.players if p.id == player_id)
    if player.eliminated:
        return None
    for critical in CRITICAL_TYPES:
        for piece in state.pieces.values():
            if piece.owner == player_id and piece.type == critical and piece.captured:
                return f"{critical}_captured"
    return None


def eliminate(state: GameState, player_id: str, reason: str) -> dict[str, Any]:
    """Mark the player eliminated and remove all their remaining pieces."""
    player = next(p for p in state.players if p.id == player_id)
    player.eliminated = True
    for piece in state.pieces.values():
        if piece.owner == player_id and not piece.captured:
            piece.captured = True
            piece.pos = None
    return {"kind": "elimination", "player_id": player_id, "reason": reason}


def check_game_over(state: GameState) -> str | None:
    """Return the winner's player id once only one player stands, else None."""
    active = [p for p in state.players if not p.eliminated]
    if len(active) == 1:
        return active[0].id
    return None
