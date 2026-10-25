from app.engine.state import apply_move
from app.engine.win_conditions import check_elimination, check_game_over, eliminate
from tests.helpers import put, sparse_state


def _capture(piece):
    piece.captured = True
    piece.pos = None


def test_losing_only_the_flag_does_not_eliminate():
    state = sparse_state()
    flag = put(state, "p2", "stratego", "flag", (1, 5))
    put(state, "p2", "chess", "king", (0, 0))
    _capture(flag)
    assert check_elimination(state, "p2") is None


def test_losing_only_the_king_does_not_eliminate():
    state = sparse_state()
    put(state, "p2", "stratego", "flag", (1, 5))
    king = put(state, "p2", "chess", "king", (0, 0))
    _capture(king)
    assert check_elimination(state, "p2") is None


def test_losing_both_flag_and_king_eliminates_in_either_order():
    state = sparse_state()
    flag = put(state, "p2", "stratego", "flag", (1, 5))
    king = put(state, "p2", "chess", "king", (0, 0))
    _capture(king)
    _capture(flag)
    assert check_elimination(state, "p2") == "flag_and_king_captured"


def test_elimination_removes_all_remaining_pieces():
    state = sparse_state()
    survivor_side = put(state, "p1", "chess", "king", (11, 5))
    doomed = [
        put(state, "p2", "stratego", "marshal", (1, 1), revealed=False),
        put(state, "p2", "chess", "queen", (1, 2)),
    ]
    event = eliminate(state, "p2", "flag_and_king_captured")
    assert event == {
        "kind": "elimination", "player_id": "p2", "reason": "flag_and_king_captured",
    }
    assert state.players[1].eliminated
    assert all(piece.captured and piece.pos is None for piece in doomed)
    assert not doomed[0].revealed  # dying unrevealed does NOT reveal the identity
    assert not survivor_side.captured


def test_game_over_when_one_player_stands():
    state = sparse_state()
    assert check_game_over(state) is None
    state.players[1].eliminated = True
    assert check_game_over(state) == "p1"


def test_flag_capture_alone_keeps_a_two_player_game_going():
    state = sparse_state()
    knight = put(state, "p1", "chess", "knight", (3, 4))
    put(state, "p2", "stratego", "flag", (1, 5), revealed=False)
    put(state, "p2", "chess", "king", (0, 0))
    put(state, "p1", "chess", "king", (11, 5))
    events = apply_move(state, "p1", knight.id, (1, 5))
    kinds = [event["kind"] for event in events]
    assert kinds == ["combat"]
    assert state.phase == "playing" and state.winner is None
    assert not state.players[1].eliminated


def test_taking_the_king_after_the_flag_ends_a_two_player_game():
    state = sparse_state()
    rook = put(state, "p1", "chess", "rook", (5, 0))
    flag = put(state, "p2", "stratego", "flag", (1, 5), revealed=False)
    _capture(flag)  # already fell earlier in the game
    put(state, "p2", "chess", "king", (0, 0))
    put(state, "p1", "chess", "king", (11, 5))
    events = apply_move(state, "p1", rook.id, (0, 0))
    kinds = [event["kind"] for event in events]
    assert kinds == ["combat", "elimination", "game_over"]
    assert state.phase == "finished"
    assert state.winner == "p1"
    assert all(p.captured for p in state.pieces.values() if p.owner == "p2")


def test_taking_the_flag_after_the_king_also_ends_the_game():
    state = sparse_state()
    knight = put(state, "p1", "chess", "knight", (3, 4))
    put(state, "p2", "stratego", "flag", (1, 5), revealed=False)
    king = put(state, "p2", "chess", "king", (0, 0))
    _capture(king)
    put(state, "p2", "stratego", "scout", (0, 11), revealed=False)  # p2 still has an army
    put(state, "p1", "chess", "king", (11, 5))
    events = apply_move(state, "p1", knight.id, (1, 5))
    kinds = [event["kind"] for event in events]
    assert kinds == ["combat", "elimination", "game_over"]
    assert state.winner == "p1"


def test_king_lost_to_a_bomb_does_not_eliminate_while_the_flag_stands():
    state = sparse_state()
    king = put(state, "p1", "chess", "king", (5, 5))
    put(state, "p1", "stratego", "flag", (11, 0))
    put(state, "p1", "chess", "rook", (11, 11))  # p1 keeps fighting with this
    put(state, "p2", "stratego", "bomb", (4, 5), revealed=False)
    put(state, "p2", "chess", "king", (0, 0))
    events = apply_move(state, "p1", king.id, (4, 5))
    kinds = [event["kind"] for event in events]
    assert kinds == ["combat"]
    assert king.captured
    assert not state.players[0].eliminated and state.phase == "playing"


def test_three_player_game_continues_after_one_elimination():
    state = sparse_state(num_players=3)
    rook = put(state, "p1", "chess", "rook", (7, 6))
    put(state, "p2", "stratego", "flag", (3, 1), revealed=False)  # west player's flag
    king = put(state, "p2", "chess", "king", (13, 1))
    _capture(king)  # west already lost the king; the flag is the last condition
    put(state, "p3", "chess", "king", (0, 6))
    put(state, "p1", "chess", "king", (13, 6))
    events = apply_move(state, "p1", rook.id, (7, 1))
    assert "elimination" not in [event["kind"] for event in events]
    # rook only reached the column; now take the flag next turn cycle
    state.turn_index = 0
    events = apply_move(state, "p1", rook.id, (3, 1))
    kinds = [event["kind"] for event in events]
    assert "elimination" in kinds and "game_over" not in kinds
    assert state.phase == "playing"
    assert not state.players[0].eliminated and not state.players[2].eliminated
    assert state.players[state.turn_index].id == "p3"  # p2's seat is skipped
