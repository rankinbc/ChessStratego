"""FastAPI entrypoint: lobby + websocket routers, plus the game_client
static site. See CLAUDE.md for the Windows .js mimetype gotcha this file
must fix before mounting StaticFiles.

Run single-worker only (see app/rooms.py):
    cd components/game_server && uvicorn app.main:app --host 127.0.0.1 --port 8000
For LAN play use --host 0.0.0.0 and share the printed LAN address.
"""

import mimetypes

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import CLIENT_STATIC_DIR
from app.routes import lobby, websocket

mimetypes.add_type("text/javascript", ".js")  # Windows serves .js as text/plain otherwise

app = FastAPI(title="ChessStratego game_server")
app.include_router(lobby.router)
app.include_router(websocket.router)

if CLIENT_STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=CLIENT_STATIC_DIR, html=True), name="client")
