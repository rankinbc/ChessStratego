"""Per-game playtest match logs: output/game_server/<YYYY-MM-DD>_<game_id>/.

The match log is a SERVER-SIDE file for post-game rule review. It records
full piece identities (setups, combats, moves) — it must never be sent to
clients or exposed over any route. It is the only place full identities
live outside GameState itself.
"""

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.config import OUTPUT_DIR


def output_base() -> Path:
    """Match-log root; CHESSSTRATEGO_OUTPUT_DIR overrides it (used by tests)."""
    override = os.environ.get("CHESSSTRATEGO_OUTPUT_DIR")
    return Path(override) if override else OUTPUT_DIR


class MatchLog:
    """Append-only JSONL log for one game. Directory is created lazily on
    the first write so abandoned lobbies leave no empty folders behind."""

    def __init__(self, game_id: str):
        self.run_dir = output_base() / f"{date.today().isoformat()}_{game_id}"
        self.path = self.run_dir / "match.jsonl"

    def write(self, event: dict[str, Any]) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        line = json.dumps({"ts": datetime.now().isoformat(timespec="seconds"), **event})
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
