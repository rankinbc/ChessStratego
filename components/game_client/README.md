# game_client

**Purpose**: Browser client for ChessStratego — a hybrid chess+stratego board game, 2-4 players each on their own device, real-time over websockets. Renders the lobby, private secret-piece setup, the play board (tap-tap select/move), combat reveal, and game-over phases. All authoritative game state lives server-side; this client is a thin, redraw-per-message UI.

**Inputs**: None (self-contained; state arrives over the game_server websocket connection)

**Outputs**: None (UI only — no files produced; all durable state lives in the sibling `game_server` component)

**Pattern**: `form_view.md`, heavily adapted — this is a client-rendered realtime game board, not a server-rendered form/DB app. No Python, no Jinja, no SQLAlchemy, no DB in this component.

**Stack**: Zero-dependency vanilla JavaScript (ES modules) + HTML + CSS. No bundler, no `package.json`, no node_modules, no CDN dependencies. Static files are served by the sibling `game_server` component (FastAPI `StaticFiles`).

## How to run

This component has no standalone server. Start the sibling `game_server` component (see `components/game_server/README.md`), then open the URL it prints — in **two browser tabs** (or one desktop + one phone) to exercise multiplayer.

ES modules require `http://` — opening `index.html` via `file://` will fail silently on the `import` statements.

## Structure

```
components/game_client/
├── index.html       # entry page; loads js/main.js as a module
├── css/style.css     # minimal reset + board/banner styling
├── js/
│   ├── main.js        # entry point — wires state, render, ws together
│   ├── state.js        # single client state object
│   ├── render.js        # full re-render per phase
│   ├── board.js          # CSS Grid board build + square click handlers
│   ├── ws.js               # websocket connect/reconnect + resync
│   └── protocol.js          # message type constants (shared contract w/ game_server)
└── tests/            # empty; /execute-prp adds DOM-free logic tests here if modules grow
```

## Manual smoke test (no JS test framework)

1. Start `game_server`, open the client URL in **tab A** and **tab B**.
2. Join with different names in each tab — both should reach the lobby and see each other.
3. Kill the server, confirm both tabs show the "reconnecting…" banner; restart the server and confirm both tabs resync to the current state.
4. Tap-select a piece in one tab, tap-move it — confirm the other tab's board updates.
5. Confirm an opponent's stratego pieces render face-down (never leak `type`) until revealed by combat.

Syntax gate (no framework needed): `node --check components/game_client/js/<file>.js` for each module. If logic modules (e.g. state transitions) grow complex, add `node --test` files under `tests/`.

---

**To extend this component**: edit `PRPs/source/INITIAL.md` and run `/generate-prp`. Don't modify files here directly for new work — let the PRP drive it.
