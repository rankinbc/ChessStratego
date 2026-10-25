import pytest

from app.engine.combat import resolve_combat
from app.engine.pieces import STRATEGO_RANKS
from app.engine.state import apply_move
from tests.helpers import make_piece, put, sparse_state


def fight(attacker_kind, attacker_type, defender_kind, defender_type):
    attacker = make_piece("p1", attacker_kind, attacker_type)
    defender = make_piece("p2", defender_kind, defender_type)
    return resolve_combat(attacker, defender)


def test_chess_attacks_chess_is_a_normal_capture():
    outcome = fight("chess", "pawn", "chess", "queen")
    assert (outcome.attacker_survives, outcome.defender_survives) == (True, False)
    assert outcome.special == "chess_capture"


@pytest.mark.parametrize("defender", ["marshal", "spy", "scout", "flag"])
def test_chess_beats_any_stratego_piece_except_a_bomb(defender):
    outcome = fight("chess", "knight", "stratego", defender)
    assert (outcome.attacker_survives, outcome.defender_survives) == (True, False)


def test_bomb_destroys_a_chess_attacker_and_stays():
    outcome = fight("chess", "queen", "stratego", "bomb")
    assert (outcome.attacker_survives, outcome.defender_survives) == (False, True)
    assert outcome.special == "bomb_blast"


def test_stratego_attacker_beats_any_chess_piece():
    for attacker in ["spy", "scout", "marshal"]:
        outcome = fight("stratego", attacker, "chess", "queen")
        assert (outcome.attacker_survives, outcome.defender_survives) == (True, False)


def test_ranks_are_classic_one_is_strongest():
    assert STRATEGO_RANKS["marshal"] == 1
    assert STRATEGO_RANKS["scout"] == 9
    assert STRATEGO_RANKS["miner"] == 8
    assert "spy" not in STRATEGO_RANKS  # pure specialty — no number
    assert "bomb" not in STRATEGO_RANKS and "flag" not in STRATEGO_RANKS


def test_lower_number_wins_a_rank_fight():
    assert fight("stratego", "marshal", "stratego", "general").attacker_survives
    assert fight("stratego", "general", "stratego", "colonel").attacker_survives
    assert fight("stratego", "captain", "stratego", "miner").attacker_survives
    loss = fight("stratego", "scout", "stratego", "colonel")
    assert (loss.attacker_survives, loss.defender_survives) == (False, True)
    assert loss.special == "rank_loss"
    tie = fight("stratego", "scout", "stratego", "scout")
    assert (tie.attacker_survives, tie.defender_survives) == (False, False)
    assert tie.special == "equal_rank"


@pytest.mark.parametrize(
    "defender", ["marshal", "general", "colonel", "major", "captain", "miner", "scout", "spy"]
)
def test_spy_takes_any_piece_it_attacks(defender):
    outcome = fight("stratego", "spy", "stratego", defender)
    assert (outcome.attacker_survives, outcome.defender_survives) == (True, False)
    assert outcome.special == "spy_strike"


@pytest.mark.parametrize("attacker", ["marshal", "captain", "miner", "scout"])
def test_spy_dies_to_anything_that_attacks_it(attacker):
    outcome = fight("stratego", attacker, "stratego", "spy")
    assert (outcome.attacker_survives, outcome.defender_survives) == (True, False)
    assert outcome.special == "spy_exposed"


def test_spy_attacking_a_bomb_still_dies():
    outcome = fight("stratego", "spy", "stratego", "bomb")
    assert (outcome.attacker_survives, outcome.defender_survives) == (False, True)
    assert outcome.special == "bomb_blast"


def test_miner_defuses_bombs_other_ranks_do_not():
    assert fight("stratego", "miner", "stratego", "bomb").attacker_survives
    scout_hit = fight("stratego", "scout", "stratego", "bomb")
    assert (scout_hit.attacker_survives, scout_hit.defender_survives) == (False, True)


def test_combat_through_apply_move_reveals_both_participants():
    state = sparse_state()
    knight = put(state, "p1", "chess", "knight", (8, 5))
    marshal = put(state, "p2", "stratego", "marshal", (6, 6), revealed=False)
    put(state, "p2", "chess", "king", (1, 5))  # p2 needs a legal move afterwards
    events = apply_move(state, "p1", knight.id, (6, 6))
    combat_events = [e for e in events if e["kind"] == "combat"]
    assert len(combat_events) == 1
    event = combat_events[0]
    assert event["attacker"]["type"] == "knight" and event["attacker"]["survived"]
    assert event["defender"]["type"] == "marshal" and not event["defender"]["survived"]
    assert marshal.captured and marshal.revealed and marshal.pos is None
    assert knight.pos == (6, 6)


def test_bomb_stays_on_the_board_after_destroying_an_attacker():
    state = sparse_state()
    queen = put(state, "p1", "chess", "queen", (8, 5))
    bomb = put(state, "p2", "stratego", "bomb", (4, 5), revealed=False)
    put(state, "p2", "chess", "king", (1, 5))
    put(state, "p1", "chess", "rook", (11, 0))  # p1 needs a move left for turn advance
    apply_move(state, "p1", queen.id, (4, 5))
    assert queen.captured and queen.pos is None
    assert not bomb.captured and bomb.pos == (4, 5) and bomb.revealed
