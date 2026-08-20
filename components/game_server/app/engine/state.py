"""GameState: players + board + pieces + phase, and the orchestration of a
turn (movement legality -> combat -> elimination -> next turn).

Pure module — no FastAPI imports. This is the single source of truth the
websocket layer mutates (under a per-room asyncio.Lock) and the only
object redact_for_player() is ever allowed to read from.

Rule domains live in their own modules (board/movement/combat/
win_conditions); this module only sequences them and enforces phase and
turn structure. Rule violations raise RuleViolation with a stable `code`
the wire layer forwards as a typed error — messages here must never
include hidden piece identities.
"""

from __future__ import annotations

import random
import secrets
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.engine import combat, movement, win_conditions
from app.engine.board import Board, build_board, promotion_reached
from app.engine.pieces import ARMY_SIZE, Piece, Pos, create_army

Phase = Literal["lobby", "setup", "playing", "finished"]
Event = dict[str, Any]

MIN_PLAYERS = 2
MAX_PLAYERS = 4


class RuleViolation(Exception):
    """A client request the rules reject. `code` is stable for the wire."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class Player(BaseModel):
    id: str
    name: str
    edge: str = ""  # assigned at start_game
    is_host: bool = False
    setup_done: bool = False
    eliminated: bool = False
    connected: bool = True


class GameState(BaseModel):
    phase: Phase = "lobby"
    players: list[Player] = Field(default_factory=list)
    board: Board | None = None
    pieces: dict[str, Piece] = Field(default_factory=dict)
    turn_index: int = 0
    winner: str | None = None


def new_game() -> GameState:
    return GameState()


def player_by_id(state: GameState, player_id: str) -> Player:
    for player in state.players:
        if player.id == player_id:
            return player
    raise RuleViolation("unknown_player", "no such player in this game")


def piece_at(state: GameState, pos: Pos) -> Piece | None:
    for piece in state.pieces.values():
        if not piece.captured and piece.pos == pos:
            return piece
    return None


def add_player(state: GameState, name: str) -> Player:
    if state.phase != "lobby":
        raise RuleViolation("game_started", "this game has already started")
    if len(state.players) >= MAX_PLAYERS:
        raise RuleViolation("game_full", f"this game already has {MAX_PLAYERS} players")
    name = name.strip()
    if not name:
        raise RuleViolation("bad_name", "display name must not be empty")
    player = Player(id=f"p{secrets.token_hex(3)}", name=name[:20], is_host=not state.players)
    state.players.append(player)
    return player


def start_game(state: GameState, requested_by: str) -> None:
    player = player_by_id(state, requested_by)
    if not player.is_host:
        raise RuleViolation("host_only", "only the game creator can start the game")
    if state.phase != "lobby":
        raise RuleViolation("game_started", "this game has already started")
    if len(state.players) < MIN_PLAYERS:
        raise RuleViolation("not_enough_players", f"need at least {MIN_PLAYERS} players")
    state.board = build_board(len(state.players))
    for player_, edge in zip(state.players, state.board.edges):
        player_.edge = edge
    for player_ in state.players:
        for piece in create_army(player_.id):
            state.pieces[piece.id] = piece
    state.phase = "setup"


def submit_setup(state: GameState, player_id: str, placements: dict[str, Pos]) -> list[Event]:
    """Validate and apply one player's full army placement."""
    if state.phase != "setup":
        raise RuleViolation("not_setup_phase", "setup is not open")
    player = player_by_id(state, player_id)
    board = state.board
    assert board is not None
    own_ids = {pid for pid, piece in state.pieces.items() if piece.owner == player_id}
    if set(placements) != own_ids:
        raise RuleViolation(
            "bad_placements", f"must place exactly your {ARMY_SIZE} pieces, no more, no less"
        )
    zone = set(board.setup_zones[player.edge])
    positions = list(placements.values())
    if len(set(positions)) != len(positions):
        raise RuleViolation("bad_placements", "two pieces on the same square")
    for pos in positions:
        if pos not in zone:
            raise RuleViolation("bad_placements", f"square {pos} is outside your setup zone")
    for pid, pos in placements.items():
        state.pieces[pid].pos = pos
    player.setup_done = True
    events: list[Event] = [{"kind": "setup_done", "player_id": player_id}]
    if all(p.setup_done for p in state.players):
        state.phase = "playing"
        state.turn_index = 0
        events.append({"kind": "play_began", "first_player": state.players[0].id})
    return events


def auto_setup(state: GameState, player_id: str, rng: random.Random | None = None) -> list[Event]:
    """Random-but-sane placement: flag on the back row, bombs and king deep."""
    if state.phase != "setup":
        raise RuleViolation("not_setup_phase", "setup is not open")
    rng = rng or random.Random()
    player = player_by_id(state, player_id)
    board = state.board
    assert board is not None
    zone = list(board.setup_zones[player.edge])

    def depth(pos: Pos) -> int:
        r, c = pos
        return {
            "south": board.size - 1 - r,
            "north": r,
            "west": c,
            "east": board.size - 1 - c,
        }[player.edge]

    cells = sorted(zone, key=lambda p: (depth(p), p))
    own = [piece for piece in state.pieces.values() if piece.owner == player_id]
    by_type: dict[str, list[Piece]] = {}
    for piece in own:
        by_type.setdefault(piece.type, []).append(piece)

    placements: dict[str, Pos] = {}
    free = list(cells)
    back = [p for p in free if depth(p) == 0]
    deep = [p for p in free if depth(p) <= 1]

    def take(pool: list[Pos]) -> Pos:
        pos = rng.choice([p for p in pool if p in free])
        free.remove(pos)
        return pos

    placements[by_type["flag"][0].id] = take(back)
    placements[by_type["king"][0].id] = take(deep)
    for bomb in by_type["bomb"]:
        placements[bomb.id] = take(deep)
    rest = [piece for piece in own if piece.id not in placements]
    rng.shuffle(free)
    for piece, pos in zip(rest, free):
        placements[piece.id] = pos
    return submit_setup(state, player_id, placements)


def apply_move(state: GameState, player_id: str, piece_id: str, to: Pos) -> list[Event]:
    """Validate and apply one move; returns the public events it produced."""
    if state.phase != "playing":
        raise RuleViolation("not_playing", "the game is not in the playing phase")
    player = player_by_id(state, player_id)
    if player.eliminated:
        raise RuleViolation("eliminated", "you have been eliminated")
    if movement.current_player(state).id != player_id:
        raise RuleViolation("not_your_turn", "it is not your turn")
    piece = state.pieces.get(piece_id)
    if piece is None or piece.owner != player_id or piece.captured:
        raise RuleViolation("bad_piece", "that is not one of your pieces on the board")
    to = (to[0], to[1])
    if to not in movement.legal_moves(state, piece):
        raise RuleViolation("illegal_move", "that piece cannot move there")

    events: list[Event] = []
    origin = piece.pos
    defender = piece_at(state, to)
    if defender is None:
        piece.pos = to
        events.append(
            {"kind": "move", "piece_id": piece.id, "owner": player_id, "from": origin, "to": to}
        )
    else:
        events.append(_apply_combat(state, piece, defender, origin, to))

    if (
        piece.type == "pawn"
        and not piece.captured
        and state.board is not None
        and promotion_reached(player.edge, to, state.board.size)
    ):
        piece.type = "queen"
        events.append({"kind": "promotion", "piece_id": piece.id, "owner": player_id, "pos": to})

    for owner_id in {piece.owner, defender.owner if defender else piece.owner}:
        reason = win_conditions.check_elimination(state, owner_id)
        if reason:
            events.append(win_conditions.eliminate(state, owner_id, reason))

    winner = win_conditions.check_game_over(state)
    if winner is not None:
        state.phase = "finished"
        state.winner = winner
        events.append({"kind": "game_over", "winner": winner})
    else:
        events.extend(movement.advance_turn(state))
        if state.phase == "finished":  # stalemate: nobody left can move
            events.append({"kind": "game_over", "winner": None})
    return events


def _apply_combat(
    state: GameState, attacker: Piece, defender: Piece, origin: Pos | None, to: Pos
) -> Event:
    outcome = combat.resolve_combat(attacker, defender)
    # Combat reveals both participants to everyone, win or lose.
    attacker.revealed = True
    defender.revealed = True
    if not outcome.defender_survives:
        defender.captured = True
        defender.pos = None
    if outcome.attacker_survives:
        attacker.pos = to
    else:
        attacker.captured = True
        attacker.pos = None
    return {
        "kind": "combat",
        "at": to,
        "from": origin,
        "special": outcome.special,
        "attacker": _combatant(attacker, outcome.attacker_survives),
        "defender": _combatant(defender, outcome.defender_survives),
    }


def _combatant(piece: Piece, survived: bool) -> dict[str, Any]:
    return {
        "piece_id": piece.id,
        "owner": piece.owner,
        "kind": piece.kind,
        "type": piece.type,
        "survived": survived,
    }
