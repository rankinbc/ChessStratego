import random

import pytest

from app.engine import state as engine
from app.engine.pieces import ARMY_SIZE
from app.engine.state import RuleViolation
from tests.helpers import find_piece, full_game, play_random_moves


def test_lobby_join_flow_and_host():
    state = engine.new_game()
    host = engine.add_player(state, "Brian")
    second = engine.add_player(state, "Brother")
    assert host.is_host and not second.is_host
    assert [p.name for p in state.players] == ["Brian", "Brother"]


def test_lobby_rejects_bad_joins():
    state = engine.new_game()
    with pytest.raises(RuleViolation) as excinfo:
        engine.add_player(state, "   ")
    assert excinfo.value.code == "bad_name"
    for i in range(4):
        engine.add_player(state, f"P{i}")
    with pytest.raises(RuleViolation) as excinfo:
        engine.add_player(state, "fifth")
    assert excinfo.value.code == "game_full"


def test_start_game_requires_host_and_enough_players():
    state = engine.new_game()
    host = engine.add_player(state, "Host")
    with pytest.raises(RuleViolation) as excinfo:
        engine.start_game(state, host.id)
    assert excinfo.value.code == "not_enough_players"
    guest = engine.add_player(state, "Guest")
    with pytest.raises(RuleViolation) as excinfo:
        engine.start_game(state, guest.id)
    assert excinfo.value.code == "host_only"
    engine.start_game(state, host.id)
    assert state.phase == "setup"
    assert len(state.pieces) == 2 * ARMY_SIZE
    assert {p.edge for p in state.players} == {"south", "north"}


def test_setup_validation_rejects_bad_placements():
    state = engine.new_game()
    host = engine.add_player(state, "A")
    engine.add_player(state, "B")
    engine.start_game(state, host.id)
    own = [p for p in state.pieces.values() if p.owner == host.id]
    assert state.board is not None
    zone = state.board.setup_zones["south"]

    partial = {own[0].id: zone[0]}
    with pytest.raises(RuleViolation) as excinfo:
        engine.submit_setup(state, host.id, partial)
    assert excinfo.value.code == "bad_placements"

    stacked = {piece.id: zone[0] for piece in own}
    with pytest.raises(RuleViolation):
        engine.submit_setup(state, host.id, stacked)

    outside = {piece.id: cell for piece, cell in zip(own, zone)}
    outside[own[0].id] = (0, 0)  # north zone square — not ours
    with pytest.raises(RuleViolation):
        engine.submit_setup(state, host.id, outside)


def test_auto_setup_fills_the_zone_and_starts_play_when_all_done():
    state = full_game(num_players=2, seed=7)
    assert state.phase == "playing"
    assert state.players[state.turn_index].id == state.players[0].id
    for player in state.players:
        assert state.board is not None
        zone = set(state.board.setup_zones[player.edge])
        own = [p for p in state.pieces.values() if p.owner == player.id]
        assert len(own) == ARMY_SIZE
        assert all(piece.pos in zone for piece in own)
        # flag placed on the very back row by the auto-placer
        flag = find_piece(state, player.id, "flag")
        assert flag.pos is not None


def test_apply_move_rejects_wrong_turn_wrong_piece_and_illegal_targets():
    state = full_game(num_players=2, seed=3)
    p1, p2 = state.players[0].id, state.players[1].id
    p2_piece = next(p for p in state.pieces.values() if p.owner == p2)
    with pytest.raises(RuleViolation) as excinfo:
        engine.apply_move(state, p2, p2_piece.id, (6, 6))
    assert excinfo.value.code == "not_your_turn"
    with pytest.raises(RuleViolation) as excinfo:
        engine.apply_move(state, p1, p2_piece.id, (6, 6))
    assert excinfo.value.code == "bad_piece"
    flag = find_piece(state, p1, "flag")
    with pytest.raises(RuleViolation) as excinfo:
        engine.apply_move(state, p1, flag.id, (6, 6))
    assert excinfo.value.code == "illegal_move"


@pytest.mark.parametrize("num_players", [2, 3, 4])
def test_random_full_games_keep_invariants(num_players):
    rng = random.Random(num_players * 11)
    state = full_game(num_players=num_players, seed=num_players)
    play_random_moves(state, rng, max_moves=120)
    occupied = [p.pos for p in state.pieces.values() if not p.captured]
    assert len(occupied) == len(set(occupied)), "two live pieces share a square"
    assert state.board is not None
    for piece in state.pieces.values():
        if piece.captured:
            assert piece.pos is None
        else:
            assert piece.pos is not None
            assert state.board.on_board(piece.pos)
            assert not state.board.is_lake(piece.pos)
    if state.phase == "finished" and state.winner:
        winner = next(p for p in state.players if p.id == state.winner)
        assert not winner.eliminated
