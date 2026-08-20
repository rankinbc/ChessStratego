"""Paths for the game_server component. No secrets — this game has no
accounts, no DB, no auth, so there is nothing to put in a .env file.

Match logs land under OUTPUT_DIR; tests point them elsewhere via the
CHESSSTRATEGO_OUTPUT_DIR env var (read in app/match_log.py).
"""

from pathlib import Path

COMPONENT_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = COMPONENT_DIR.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "game_server"
CLIENT_STATIC_DIR = PROJECT_ROOT / "components" / "game_client"
