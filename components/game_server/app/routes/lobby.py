"""Lobby routes: create a game, peek at a game's join info.

POST /games mints a short shareable game id; the reconnect token itself is
minted per player on their websocket join (routes/websocket.py) and
returned exactly once in the "joined" envelope.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.rooms import create_room, get_room

router = APIRouter()


@router.post("/games")
async def create_game(request: Request) -> dict[str, str]:
    room = create_room()
    room.log.write({"kind": "game_created", "game_id": room.game_id})
    base = str(request.base_url).rstrip("/")
    return {"game_id": room.game_id, "join_url": f"{base}/?game={room.game_id}"}


@router.get("/games/{game_id}")
async def game_info(game_id: str) -> dict[str, Any]:
    room = get_room(game_id)
    if room is None:
        raise HTTPException(status_code=404, detail="no such game")
    state = room.state
    return {
        "game_id": room.game_id,
        "phase": state.phase,
        "num_players": len(state.players),
        "players": [
            {"name": p.name, "connected": p.connected, "eliminated": p.eliminated}
            for p in state.players
        ],
    }
