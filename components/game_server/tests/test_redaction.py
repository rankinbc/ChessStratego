"""THE security test: no unrevealed opponent stratego identity may appear
anywhere in a redacted payload, for any state shape. Expand this file with
every change to the GameState/snapshot shape."""

import json
import random

from app.engine.pieces import STRATEGO_SET_COUNTS, STRATEGO_TYPES
from app.redaction import redact_for_player
from tests.helpers import full_game, play_random_moves, put, sparse_state


def opponent_pieces(payload, viewer_id):
    return [p for p in payload["pieces"].values() if p["owner"] != viewer_id]


def assert_payload_safe(state, viewer_id):
    """Structural guarantee: opponents' unrevealed stratego types are None."""
    payload = redact_for_player(state, viewer_id)
    for piece in opponent_pieces(payload, viewer_id):
        if piece["kind"] == "stratego" and not piece["revealed"]:
            assert piece["type"] is None, "unrevealed opponent stratego rank leaked"
    for piece in payload["pieces"].values():
        if piece["owner"] == viewer_id:
            assert piece["type"] is not None, "own pieces must never be redacted"
    return payload


def test_setup_phase_hides_opponent_placements_entirely():
    state = full_game(num_players=2, seed=5)
    # rewind to a mid-setup shape: one player placed, one not
    state.phase = "setup"
    viewer = state.players[0].id
    payload = redact_for_player(state, viewer)
    assert opponent_pieces(payload, viewer) == []
    own = [p for p in payload["pieces"].values() if p["owner"] == viewer]
    assert len(own) == 30


def test_playing_phase_redacts_unrevealed_and_passes_revealed():
    state = sparse_state()
    put(state, "p1", "chess", "queen", (9, 5))
    put(state, "p1", "stratego", "marshal", (10, 5), revealed=False)
    hidden = put(state, "p2", "stratego", "general", (2, 5), revealed=False)
    shown = put(state, "p2", "stratego", "miner", (3, 5), revealed=True)
    put(state, "p2", "chess", "knight", (1, 1))

    payload = assert_payload_safe(state, "p1")
    by_id = payload["pieces"]
    assert by_id[hidden.id]["type"] is None
    assert by_id[hidden.id]["pos"] == [2, 5]  # position IS public in play
    assert by_id[shown.id]["type"] == "miner"
    assert by_id[hidden.id]["owner"] == "p2"

    # And the mirror view: p2 sees their own general, not p1's marshal.
    payload2 = assert_payload_safe(state, "p2")
    assert payload2["pieces"][hidden.id]["type"] == "general"


def test_pieces_that_died_unrevealed_stay_redacted_forever():
    state = sparse_state()
    put(state, "p1", "chess", "king", (11, 5))
    dead = put(state, "p2", "stratego", "colonel", (2, 5), revealed=False)
    dead.captured = True
    dead.pos = None
    state.phase = "finished"
    payload = assert_payload_safe(state, "p1")
    assert payload["pieces"][dead.id]["type"] is None


def test_no_stratego_rank_string_survives_serialization():
    """String-level proof: viewer owns zero stratego pieces, opponent's are
    all hidden — the full JSON payload must not contain ANY rank name."""
    state = sparse_state()
    put(state, "p1", "chess", "king", (11, 5))
    put(state, "p1", "chess", "pawn", (9, 5))
    board = state.board
    assert board is not None
    zone = board.setup_zones["north"]
    for i, type_ in enumerate(
        t for t, n in STRATEGO_SET_COUNTS.items() for _ in range(n)
    ):
        put(state, "p2", "stratego", type_, zone[i], revealed=False)
    wire = json.dumps(redact_for_player(state, "p1"))
    for rank in STRATEGO_TYPES:
        assert rank not in wire, f"rank string {rank!r} leaked onto the wire"


def test_fuzz_randomized_games_never_leak():
    for seed in range(4):
        num_players = 2 + seed % 3
        state = full_game(num_players=num_players, seed=seed)
        rng = random.Random(seed)
        for _ in range(6):
            play_random_moves(state, rng, max_moves=8)
            for player in state.players:
                payload = assert_payload_safe(state, player.id)
                wire = json.dumps(payload)
                # every unrevealed opponent piece: id present, type null
                for piece in state.pieces.values():
                    if (
                        piece.owner != player.id
                        and piece.kind == "stratego"
                        and not piece.revealed
                    ):
                        assert f'"{piece.id}"' in wire
                        assert payload["pieces"][piece.id]["type"] is None
            if state.phase != "playing":
                break


def test_redaction_does_not_mutate_the_real_state():
    state = full_game(num_players=2, seed=9)
    hidden_types = {
        pid: piece.type for pid, piece in state.pieces.items() if piece.kind == "stratego"
    }
    redact_for_player(state, state.players[0].id)
    for pid, type_ in hidden_types.items():
        assert state.pieces[pid].type == type_
