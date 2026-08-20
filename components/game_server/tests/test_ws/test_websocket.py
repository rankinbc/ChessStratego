"""End-to-end websocket flow: join, start, setup, move, redaction on the
wire, typed errors, disconnect + token rejoin, match log on disk."""

import json
from datetime import date


def recv_snapshot(ws):
    message = ws.receive_json()
    assert message["type"] == "snapshot", f"expected snapshot, got {message['type']}"
    return message["payload"]


def join(ws, name):
    ws.send_json({"type": "join", "payload": {"name": name}, "seq": 1})
    joined = ws.receive_json()
    assert joined["type"] == "joined"
    return joined["payload"], recv_snapshot(ws)


def assert_opponent_stratego_hidden(payload):
    you = payload["you"]
    for piece in payload["state"]["pieces"].values():
        if piece["owner"] != you and piece["kind"] == "stratego" and not piece["revealed"]:
            assert piece["type"] is None


def test_unknown_game_gets_typed_error(client):
    with client.websocket_connect("/ws/zzzzzz") as ws:
        message = ws.receive_json()
        assert message["type"] == "error"
        assert message["payload"]["code"] == "unknown_game"


def test_full_two_player_game_flow(client, tmp_path):
    game_id = client.post("/games").json()["game_id"]
    with client.websocket_connect(f"/ws/{game_id}") as alice:
        alice_info, _ = join(alice, "Alice")
        with client.websocket_connect(f"/ws/{game_id}") as bob:
            bob_info, _ = join(bob, "Bob")
            recv_snapshot(alice)  # bob's join broadcast

            # Non-host cannot start the game — typed error, loop survives.
            bob.send_json({"type": "start_game", "payload": {}, "seq": 2})
            error = bob.receive_json()
            assert error["type"] == "error" and error["payload"]["code"] == "host_only"

            alice.send_json({"type": "start_game", "payload": {}, "seq": 2})
            setup_a = recv_snapshot(alice)
            setup_b = recv_snapshot(bob)
            assert setup_a["state"]["phase"] == "setup"
            assert setup_a["events"][0]["kind"] == "game_started"
            # setup phase: opponents' pieces are not in the payload at all
            assert all(p["owner"] == alice_info["player_id"]
                       for p in setup_a["state"]["pieces"].values())
            assert len(setup_b["state"]["pieces"]) == 30

            alice.send_json({"type": "setup_auto", "payload": {}, "seq": 3})
            recv_snapshot(alice)
            recv_snapshot(bob)
            bob.send_json({"type": "setup_auto", "payload": {}, "seq": 2})
            play_a = recv_snapshot(alice)
            play_b = recv_snapshot(bob)
            assert play_a["state"]["phase"] == "playing"
            assert any(e["kind"] == "play_began" for e in play_a["events"])

            # Redaction on the wire, both directions.
            assert_opponent_stratego_hidden(play_a)
            assert_opponent_stratego_hidden(play_b)
            # Host moves first and only the mover gets legal moves.
            assert play_a["your_legal_moves"] and not play_b["your_legal_moves"]

            # Out-of-turn move: typed error to Bob only.
            bob_piece = next(pid for pid, p in play_b["state"]["pieces"].items()
                             if p["owner"] == bob_info["player_id"])
            bob.send_json({"type": "move",
                           "payload": {"piece_id": bob_piece, "to": [0, 0]}, "seq": 3})
            error = bob.receive_json()
            assert error["type"] == "error" and error["payload"]["code"] == "not_your_turn"

            # A legal move broadcasts a new snapshot to everyone. Pick a
            # move onto an EMPTY square so the outcome is deterministic.
            occupied = {tuple(p["pos"]) for p in play_a["state"]["pieces"].values()
                        if p["pos"] is not None}
            piece_id, target = next(
                (pid, to)
                for pid, targets in play_a["your_legal_moves"].items()
                for to in targets
                if tuple(to) not in occupied
            )
            alice.send_json({"type": "move",
                            "payload": {"piece_id": piece_id, "to": target}, "seq": 4})
            after_a = recv_snapshot(alice)
            after_b = recv_snapshot(bob)
            assert after_b["state"]["pieces"][piece_id]["pos"] == target
            assert after_a["events"][0]["kind"] == "move"
            assert_opponent_stratego_hidden(after_b)
            assert after_b["your_legal_moves"], "turn should have passed to Bob"

        # Bob's socket closed: Alice hears about the disconnect.
        gone = recv_snapshot(alice)
        assert any(e["kind"] == "player_disconnected" for e in gone["events"])

        # Rejoin by token restores a correctly-redacted mid-game snapshot.
        with client.websocket_connect(f"/ws/{game_id}") as bob2:
            bob2.send_json({"type": "rejoin",
                            "payload": {"token": bob_info["token"]}, "seq": 1})
            rejoined = bob2.receive_json()
            assert rejoined["type"] == "joined"
            assert rejoined["payload"]["player_id"] == bob_info["player_id"]
            back = recv_snapshot(bob2)
            assert back["state"]["phase"] == "playing"
            assert back["your_legal_moves"], "it is still Bob's turn after reconnect"
            assert_opponent_stratego_hidden(back)
            recv_snapshot(alice)  # reconnect broadcast

    # Match log written server-side with full identities.
    log_path = tmp_path / f"{date.today().isoformat()}_{game_id}" / "match.jsonl"
    assert log_path.exists()
    entries = [json.loads(line) for line in log_path.read_text().splitlines()]
    kinds = {entry["kind"] for entry in entries}
    assert {"game_created", "player_joined", "game_started", "setup"} <= kinds
    setup_entry = next(e for e in entries if e["kind"] == "setup")
    assert all(p["type"] for p in setup_entry["placements"])


def test_malformed_and_early_messages_get_typed_errors(client):
    game_id = client.post("/games").json()["game_id"]
    with client.websocket_connect(f"/ws/{game_id}") as ws:
        ws.send_text("this is not json")
        error = ws.receive_json()
        assert error["type"] == "error" and error["payload"]["code"] == "bad_message"
        ws.send_json({"type": "move", "payload": {"piece_id": "x", "to": [0, 0]}, "seq": 1})
        error = ws.receive_json()
        assert error["payload"]["code"] == "join_required"
        # The loop survived all of it: a join still works.
        payload, snapshot = join(ws, "Late Larry")
        assert payload["player_id"]
        assert snapshot["state"]["phase"] == "lobby"


def test_bad_token_rejected(client):
    game_id = client.post("/games").json()["game_id"]
    with client.websocket_connect(f"/ws/{game_id}") as ws:
        ws.send_json({"type": "rejoin", "payload": {"token": "nope"}, "seq": 1})
        error = ws.receive_json()
        assert error["type"] == "error" and error["payload"]["code"] == "bad_token"
