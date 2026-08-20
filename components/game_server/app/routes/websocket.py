"""/ws/{game_id} — the real-time game connection.

Loop contract:
- every receive is parsed through the ClientMessage union; malformed input
  gets a typed "error" envelope back, never a crashed loop.
- every state mutation happens under room.lock, and so does the broadcast
  that follows it, so all players' views render from one state.
- every outbound snapshot goes through redact_for_player() (inside
  GameRoom.broadcast/send_snapshot) — nothing else may serialize state.
- WebSocketDisconnect (and any abrupt drop) detaches the socket; the seat
  and reconnect token survive for rejoin.
"""

from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.engine import state as engine
from app.engine.state import Event, RuleViolation
from app.messages import (
    ERROR,
    JOINED,
    JoinMessage,
    MoveMessage,
    RejoinMessage,
    ResyncMessage,
    SetupAutoMessage,
    SetupSubmitMessage,
    StartGameMessage,
    envelope,
    parse_client_message,
)
from app.rooms import GameRoom, get_room

router = APIRouter()


async def _send_error(websocket: WebSocket, code: str, message: str) -> None:
    await websocket.send_json(envelope(ERROR, {"code": code, "message": message}, 0))


@router.websocket("/ws/{game_id}")
async def game_socket(websocket: WebSocket, game_id: str) -> None:
    await websocket.accept()
    room = get_room(game_id)
    if room is None:
        await _send_error(websocket, "unknown_game", "no game with that id — check the link")
        await websocket.close()
        return
    player_id: str | None = None
    try:
        player_id = await _join_phase(room, websocket)
        await _play_loop(room, websocket, player_id)
    except WebSocketDisconnect:
        pass
    finally:
        if player_id is not None:
            async with room.lock:
                if room.detach(player_id, websocket):
                    await room.broadcast(
                        [{"kind": "player_disconnected", "player_id": player_id}]
                    )


async def _join_phase(room: GameRoom, websocket: WebSocket) -> str:
    """Loop until this socket becomes a seated player (join or rejoin)."""
    while True:
        raw = await websocket.receive_text()
        try:
            message = parse_client_message(raw)
        except ValidationError:
            await _send_error(websocket, "bad_message", "malformed message envelope")
            continue

        if isinstance(message, JoinMessage):
            async with room.lock:
                try:
                    player = engine.add_player(room.state, message.payload.name)
                except RuleViolation as exc:
                    await _send_error(websocket, exc.code, str(exc))
                    continue
                token = room.mint_token(player.id)
                room.attach(player.id, websocket)
                room.log.write(
                    {"kind": "player_joined", "player_id": player.id, "name": player.name}
                )
                await websocket.send_json(
                    envelope(
                        JOINED,
                        {"player_id": player.id, "token": token, "game_id": room.game_id},
                        room.seq,
                    )
                )
                await room.broadcast(
                    [{"kind": "player_joined", "player_id": player.id, "name": player.name}]
                )
            return player.id

        if isinstance(message, RejoinMessage):
            async with room.lock:
                rejoin_id = room.tokens.get(message.payload.token)
                if rejoin_id is None:
                    await _send_error(websocket, "bad_token", "unknown reconnect token")
                    continue
                room.attach(rejoin_id, websocket)
                await websocket.send_json(
                    envelope(
                        JOINED,
                        {
                            "player_id": rejoin_id,
                            "token": message.payload.token,
                            "game_id": room.game_id,
                        },
                        room.seq,
                    )
                )
                await room.broadcast(
                    [{"kind": "player_reconnected", "player_id": rejoin_id}]
                )
            return rejoin_id

        await _send_error(websocket, "join_required", "send a join or rejoin message first")


async def _play_loop(room: GameRoom, websocket: WebSocket, player_id: str) -> None:
    while True:
        raw = await websocket.receive_text()
        try:
            message = parse_client_message(raw)
        except ValidationError:
            await _send_error(websocket, "bad_message", "malformed message envelope")
            continue
        try:
            async with room.lock:
                if isinstance(message, ResyncMessage):
                    await room.send_snapshot(player_id, [])
                    continue
                events = _dispatch(room, player_id, message)
                await room.broadcast(events)
        except RuleViolation as exc:
            await _send_error(websocket, exc.code, str(exc))


def _dispatch(room: GameRoom, player_id: str, message: Any) -> list[Event]:
    """Apply one game action under the room lock; returns public events."""
    state = room.state

    if isinstance(message, (JoinMessage, RejoinMessage)):
        raise RuleViolation("already_joined", "you are already seated in this game")

    if isinstance(message, StartGameMessage):
        engine.start_game(state, player_id)
        assert state.board is not None
        room.log.write(
            {
                "kind": "game_started",
                "num_players": len(state.players),
                "board_size": state.board.size,
                "players": [
                    {"player_id": p.id, "name": p.name, "edge": p.edge} for p in state.players
                ],
            }
        )
        return [
            {
                "kind": "game_started",
                "num_players": len(state.players),
                "board_size": state.board.size,
            }
        ]

    if isinstance(message, SetupSubmitMessage):
        items = message.payload.placements
        placements = {item.piece_id: item.pos for item in items}
        if len(placements) != len(items):
            raise RuleViolation("bad_placements", "duplicate piece ids in placements")
        events = engine.submit_setup(state, player_id, placements)
        _log_setup(room, player_id)
        _log_events(room, events)
        return events

    if isinstance(message, SetupAutoMessage):
        events = engine.auto_setup(state, player_id)
        _log_setup(room, player_id)
        _log_events(room, events)
        return events

    if isinstance(message, MoveMessage):
        events = engine.apply_move(state, player_id, message.payload.piece_id, message.payload.to)
        _log_move_events(room, events)
        return events

    raise RuleViolation("bad_message", "unsupported message type")


def _log_setup(room: GameRoom, player_id: str) -> None:
    # Full identities — server-side match log only, never broadcast.
    room.log.write(
        {
            "kind": "setup",
            "player_id": player_id,
            "placements": [
                {"piece_id": p.id, "type": p.type, "piece_kind": p.kind, "pos": list(p.pos)}
                for p in room.state.pieces.values()
                if p.owner == player_id and p.pos is not None
            ],
        }
    )


def _log_events(room: GameRoom, events: list[Event]) -> None:
    for event in events:
        room.log.write(event)


def _log_move_events(room: GameRoom, events: list[Event]) -> None:
    for event in events:
        if event["kind"] == "move":
            piece = room.state.pieces[event["piece_id"]]
            # The broadcast move event carries no type (a hidden stratego
            # move must stay hidden); the log gets the full identity.
            room.log.write({**event, "piece_type": piece.type, "piece_kind": piece.kind})
        else:
            room.log.write(event)
