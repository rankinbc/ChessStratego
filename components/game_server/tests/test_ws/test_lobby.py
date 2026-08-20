from app.rooms import GAME_ID_LENGTH, ROOMS


def test_create_game_returns_short_id_and_join_url(client):
    response = client.post("/games")
    assert response.status_code == 200
    data = response.json()
    assert len(data["game_id"]) == GAME_ID_LENGTH
    assert data["join_url"].endswith(f"/?game={data['game_id']}")
    assert data["game_id"] in ROOMS


def test_game_info_reports_lobby_state(client):
    game_id = client.post("/games").json()["game_id"]
    info = client.get(f"/games/{game_id}").json()
    assert info == {"game_id": game_id, "phase": "lobby", "num_players": 0, "players": []}


def test_unknown_game_info_is_404(client):
    assert client.get("/games/nosuch").status_code == 404
