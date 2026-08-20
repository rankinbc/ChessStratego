from app.engine.movement import advance_turn, has_any_legal_move, legal_moves
from tests.helpers import put, sparse_state

# 2-player board: 12x12, lakes on rows 5-6 at cols 3-4 and 7-8.


def test_pawn_moves_away_from_home_edge_and_captures_diagonally():
    state = sparse_state()
    pawn = put(state, "p1", "chess", "pawn", (9, 5))  # p1 = south, forward = north
    assert legal_moves(state, pawn) == {(8, 5)}
    put(state, "p2", "chess", "pawn", (8, 4))  # enemy on the forward-left diagonal
    put(state, "p1", "chess", "knight", (8, 6))  # own piece on the other diagonal
    assert legal_moves(state, pawn) == {(8, 5), (8, 4)}
    put(state, "p2", "stratego", "scout", (8, 5))  # blocker ahead: no forward, no straight capture
    assert legal_moves(state, pawn) == {(8, 4)}


def test_north_pawn_forward_is_south():
    state = sparse_state()
    pawn = put(state, "p2", "chess", "pawn", (2, 5))
    assert legal_moves(state, pawn) == {(3, 5)}


def test_knight_jumps_over_pieces_and_lakes():
    state = sparse_state()
    knight = put(state, "p1", "chess", "knight", (4, 4))
    put(state, "p1", "chess", "pawn", (4, 5))
    put(state, "p2", "chess", "pawn", (5, 5))
    moves = legal_moves(state, knight)
    assert (6, 5) in moves  # lands beyond the lake square at (5, 4)
    assert (5, 6) in moves
    assert (2, 3) in moves


def test_sliding_pieces_are_blocked_by_lakes():
    state = sparse_state()
    rook = put(state, "p1", "chess", "rook", (5, 2))
    moves = legal_moves(state, rook)
    assert (5, 3) not in moves and (5, 5) not in moves  # lake at (5,3)-(5,4) blocks the ray
    assert {(5, 1), (5, 0), (4, 2), (6, 2)} <= moves


def test_scout_runs_straight_and_stops_at_blockers():
    state = sparse_state()
    scout = put(state, "p1", "stratego", "scout", (9, 0))
    moves = legal_moves(state, scout)
    assert {(r, 0) for r in range(0, 9)} <= moves  # clear column: full run north
    put(state, "p1", "stratego", "miner", (6, 0))
    moves = legal_moves(state, scout)
    assert (7, 0) in moves and (6, 0) not in moves and (5, 0) not in moves


def test_scout_can_strike_at_the_end_of_a_run_but_not_jump_lakes():
    state = sparse_state()
    scout = put(state, "p1", "stratego", "scout", (5, 2))
    put(state, "p2", "chess", "pawn", (2, 2))
    moves = legal_moves(state, scout)
    assert (2, 2) in moves and (1, 2) not in moves  # strike ends the run
    assert (5, 3) not in moves and (5, 5) not in moves  # lake blocks, no jumping


def test_bombs_and_flags_are_immobile():
    state = sparse_state()
    bomb = put(state, "p1", "stratego", "bomb", (9, 5))
    flag = put(state, "p1", "stratego", "flag", (10, 5))
    assert legal_moves(state, bomb) == set()
    assert legal_moves(state, flag) == set()


def test_stratego_pieces_step_one_square_orthogonally():
    state = sparse_state()
    marshal = put(state, "p1", "stratego", "marshal", (9, 5))
    put(state, "p1", "chess", "pawn", (9, 4))  # own piece blocks west
    assert legal_moves(state, marshal) == {(8, 5), (10, 5), (9, 6)}


def test_no_piece_may_leave_the_board_or_enter_a_lake():
    state = sparse_state()
    king = put(state, "p1", "chess", "king", (0, 0))
    assert legal_moves(state, king) == {(0, 1), (1, 0), (1, 1)}
    general = put(state, "p1", "stratego", "general", (5, 2))
    assert (5, 3) not in legal_moves(state, general)  # lake


def test_advance_turn_skips_eliminated_players():
    state = sparse_state(num_players=3)
    put(state, "p1", "chess", "king", (12, 6))
    put(state, "p3", "chess", "king", (1, 6))
    state.players[1].eliminated = True  # p2 (west) is out
    assert advance_turn(state) == []
    assert state.players[state.turn_index].id == "p3"


def test_advance_turn_skips_players_with_no_legal_move():
    state = sparse_state(num_players=3)
    put(state, "p1", "chess", "king", (12, 6))
    put(state, "p2", "stratego", "bomb", (6, 1))  # p2's only piece cannot move
    put(state, "p3", "chess", "king", (1, 6))
    events = advance_turn(state)
    assert events == [{"kind": "turn_skipped", "player_id": "p2"}]
    assert state.players[state.turn_index].id == "p3"
    assert not has_any_legal_move(state, "p2")


def test_advance_turn_declares_a_draw_when_nobody_can_move():
    state = sparse_state()
    put(state, "p1", "stratego", "flag", (11, 0))
    put(state, "p2", "stratego", "bomb", (0, 0))
    events = advance_turn(state)
    assert {"kind": "turn_skipped", "player_id": "p2"} in events
    assert state.phase == "finished"
    assert state.winner is None
