"""Shared state factories for engine, redaction, and websocket tests."""

import random
import secrets

from app.engine import state as engine
from app.engine.board import build_board
from app.engine.pieces import Piece, Pos
from app.engine.state import GameState, Player


def make_piece(
    owner: str, kind: str, type_: str, pos: Pos | None = None, revealed: bool | None = None
) -> Piece:
    if revealed is None:
        revealed = kind == "chess"
    return Piece(
        id=secrets.token_hex(4), owner=owner, kind=kind, type=type_, pos=pos, revealed=revealed
    )


def sparse_state(num_players: int = 2, phase: str = "playing") -> GameState:
    """A started game with NO pieces — tests place exactly what they need."""
    board = build_board(num_players)
    players = [
        Player(
            id=f"p{i + 1}",
            name=f"P{i + 1}",
            edge=board.edges[i],
            is_host=i == 0,
            setup_done=True,
        )
        for i in range(num_players)
    ]
    return GameState(phase=phase, players=players, board=board, turn_index=0)


def put(
    state: GameState,
    owner: str,
    kind: str,
    type_: str,
    pos: Pos,
    revealed: bool | None = None,
) -> Piece:
    piece = make_piece(owner, kind, type_, (pos[0], pos[1]), revealed)
    state.pieces[piece.id] = piece
    return piece


def full_game(num_players: int = 2, seed: int = 1) -> GameState:
    """A real game: joined, started, auto-setup for everyone, phase=playing."""
    state = engine.new_game()
    for i in range(num_players):
        engine.add_player(state, f"P{i + 1}")
    engine.start_game(state, state.players[0].id)
    rng = random.Random(seed)
    for player in state.players:
        engine.auto_setup(state, player.id, rng)
    return state


def find_piece(state: GameState, owner: str, type_: str) -> Piece:
    for piece in state.pieces.values():
        if piece.owner == owner and piece.type == type_:
            return piece
    raise AssertionError(f"no {type_} owned by {owner}")


def play_random_moves(state: GameState, rng: random.Random, max_moves: int) -> int:
    """Drive a live game with random legal moves; returns moves actually made."""
    from app.engine.movement import current_player, legal_moves

    made = 0
    while state.phase == "playing" and made < max_moves:
        mover = current_player(state)
        options = []
        for piece in state.pieces.values():
            if piece.owner == mover.id and not piece.captured:
                options.extend((piece.id, to) for to in sorted(legal_moves(state, piece)))
        assert options, "current player must always have a legal move"
        piece_id, to = rng.choice(options)
        engine.apply_move(state, mover.id, piece_id, to)
        made += 1
    return made
