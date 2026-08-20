"""Redact hidden Stratego info before a state snapshot goes on the wire.

Pure function of (state, player_id) -> redacted dict. An opponent's
unrevealed piece rank must NEVER appear in the returned payload — treat a
leak here as a security bug, not a display bug.

Redaction rules:
- lobby/setup phases: opponents' pieces are omitted entirely (their
  placements are private until play begins; army composition is public
  knowledge anyway, so omission leaks nothing).
- playing/finished phases: opponents' unrevealed stratego pieces keep
  {id, owner, kind, pos, captured} but their `type` becomes None. Chess
  pieces and revealed stratego pieces pass through untouched.
- Pieces stay redacted even after capture-by-elimination: a piece that
  died unrevealed is never disclosed by the server (the server-side match
  log is the only place full identities live).

tests/test_redaction.py fuzzes this against randomized states and must be
kept green — expand it with every state-shape change.
"""

from typing import Any

from app.engine.state import GameState


def redact_for_player(state: GameState, player_id: str) -> dict[str, Any]:
    """Return a JSON-safe copy of state that is safe to send to player_id."""
    data: dict[str, Any] = state.model_dump(mode="json")
    pieces: dict[str, dict[str, Any]] = data["pieces"]
    if state.phase in ("lobby", "setup"):
        data["pieces"] = {
            piece_id: piece for piece_id, piece in pieces.items() if piece["owner"] == player_id
        }
        return data
    for piece in pieces.values():
        if piece["owner"] != player_id and piece["kind"] == "stratego" and not piece["revealed"]:
            piece["type"] = None
    return data
