"""In-memory game room registry.

Single-process, single-worker only: ROOMS lives in this module's memory
and is NOT shared across worker processes or machines. Never run this app
with `--workers > 1` or behind multiple uvicorn processes/replicas.

Locking convention: every method that reads or mutates room.state is
called while holding room.lock — including broadcast(), so that all
players' snapshots of one event are rendered from the same state. The
websocket route is responsible for acquiring the lock.
"""

import asyncio
import secrets
from typing import Any

from app.engine.movement import current_player, legal_moves
from app.engine.state import Event, GameState, new_game, player_by_id
from app.match_log import MatchLog
from app.messages import SNAPSHOT, envelope
from app.redaction import redact_for_player

# Unambiguous lowercase alphabet for shareable game ids (no 0/o/1/l).
_ID_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
GAME_ID_LENGTH = 6

ROOMS: dict[str, "GameRoom"] = {}


class GameRoom:
    """One game's live state plus the lock that guards every mutation."""

    def __init__(self, game_id: str):
        self.game_id = game_id
        self.lock = asyncio.Lock()
        self.state: GameState = new_game()
        self.connections: dict[str, Any] = {}  # player_id -> live websocket
        self.tokens: dict[str, str] = {}  # reconnect token -> player_id
        self.seq = 0
        self.log = MatchLog(game_id)

    def mint_token(self, player_id: str) -> str:
        token = secrets.token_hex(16)
        self.tokens[token] = player_id
        return token

    def attach(self, player_id: str, websocket: Any) -> None:
        self.connections[player_id] = websocket
        player_by_id(self.state, player_id).connected = True

    def detach(self, player_id: str, websocket: Any) -> bool:
        """Drop this socket if it is still the player's live one. A stale
        socket (already replaced by a reconnect) must not evict the new one."""
        if self.connections.get(player_id) is not websocket:
            return False
        del self.connections[player_id]
        player_by_id(self.state, player_id).connected = False
        return True

    def _legal_moves_for(self, player_id: str) -> dict[str, list[list[int]]]:
        state = self.state
        if state.phase != "playing":
            return {}
        player = player_by_id(state, player_id)
        if player.eliminated or current_player(state).id != player_id:
            return {}
        moves: dict[str, list[list[int]]] = {}
        for piece in state.pieces.values():
            if piece.owner != player_id or piece.captured:
                continue
            targets = legal_moves(state, piece)
            if targets:
                moves[piece.id] = [[r, c] for r, c in sorted(targets)]
        return moves

    def _snapshot_envelope(self, player_id: str, events: list[Event]) -> dict[str, Any]:
        payload = {
            "you": player_id,
            "state": redact_for_player(self.state, player_id),
            "your_legal_moves": self._legal_moves_for(player_id),
            "events": events,
        }
        return envelope(SNAPSHOT, payload, self.seq)

    async def send_snapshot(self, player_id: str, events: list[Event]) -> None:
        """Send one player a fresh snapshot (join, rejoin, resync). Call
        while holding room.lock."""
        websocket = self.connections.get(player_id)
        if websocket is None:
            return
        try:
            await websocket.send_json(self._snapshot_envelope(player_id, events))
        except Exception:
            self.detach(player_id, websocket)

    async def broadcast(self, events: list[Event]) -> None:
        """Send every connected player their own redacted snapshot. Call
        while holding room.lock so all views render from one state."""
        self.seq += 1
        for player_id, websocket in list(self.connections.items()):
            try:
                await websocket.send_json(self._snapshot_envelope(player_id, events))
            except Exception:
                # Abrupt drop (no clean disconnect frame): forget the socket
                # now or the next broadcast raises on it again.
                self.detach(player_id, websocket)


def create_room() -> GameRoom:
    while True:
        game_id = "".join(secrets.choice(_ID_ALPHABET) for _ in range(GAME_ID_LENGTH))
        if game_id not in ROOMS:
            break
    room = GameRoom(game_id)
    ROOMS[game_id] = room
    return room


def get_room(game_id: str) -> "GameRoom | None":
    return ROOMS.get(game_id)


def remove_room(game_id: str) -> None:
    ROOMS.pop(game_id, None)
