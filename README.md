# ChessStratego

A real-time, browser-based board game mixing Chess and Stratego for 2-4 players. Each player commands a full chess set (visible to everyone) plus a reduced Stratego set (hidden until combat reveals it) on an expanded board with lakes in the middle — 12x12 for 2 players, up to 16x16 for 4. Players join from any device via a shared link — no accounts. Rules are experimental by design: the code is modularized and documented so a rule can be changed by asking Claude to edit one small module (see `components/rulebook/RULES.md`).

## Project structure

```
ChessStratego/
├── CLAUDE.md              (rules for Claude — auto-loaded each session)
├── README.md              (this file)
├── .claude/               (settings + slash commands)
├── PRPs/                  (implementation plans)
├── components/
│   ├── game_server/       (FastAPI + websockets: modular rules engine, lobby, redaction)
│   ├── game_client/       (browser board UI — vanilla JS, no build step)
│   └── rulebook/          (living rules doc + playtest decision log)
└── output/
    └── game_server/       (playtest match logs)
```

## Components

- `game_server` — real-time multiplayer server: rules engine, lobby, per-player hidden-info redaction (pattern: api)
- `game_client` — browser board UI served by the server; click-to-move, works on phone (pattern: form_view)
- `rulebook` — living rules document, variants mapped to code modules, playtest decision log (pattern: product_doc)

## How to run

- First time: `pip install -r components/game_server/requirements.txt`
- Server + client: `uvicorn app.main:app --host 127.0.0.1 --port 8000` from `components/game_server/` (any port works if 8000 is busy, e.g. `--port 8765`; use `--host 0.0.0.0` for LAN play), then open the printed URL
- Click "Create a game", share the link, play. Match logs land in `output/game_server/`
- Rulebook: open `components/rulebook/RULES.md`
- Play over the internet without a PC: tap [Deploy to Render](https://render.com/deploy?repo=https://github.com/rankinbc/ChessStratego) (free tier, GitHub login), wait for the build, then open the `https://chessstratego-xxxx.onrender.com` URL it gives you and "Create a game" from there. `render.yaml` holds the config. Free instances sleep after ~15 idle minutes and forget unfinished games; a game in progress keeps them awake

## How to develop with Claude

- New features: `/new-feature` (guided), or manually edit `PRPs/source/INITIAL.md` → `/generate-prp` → `/execute-prp PRPs/<slug>.md`
- Rule tweaks don't need a PRP: ask Claude to change the rule — it edits the one engine module plus `RULES.md` and logs it in `DECISION_LOG.md`

## How to reopen this project in Claude Code

`cd C:\Users\Brian.Rankin\claude-workspace\projects\ChessStratego && claude`
