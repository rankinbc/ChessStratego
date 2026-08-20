// Entry point — wires state, render, and the websocket together.
// Flow: no ?game= param -> home screen (create/join). With ?game= -> open
// the websocket; a stored reconnect token auto-rejoins, otherwise the
// lobby shows the join form. Every server snapshot triggers a full
// re-render; reconnects resync from a full snapshot (never delta replay).

import { MSG } from "./protocol.js";
import { render } from "./render.js";
import { applySnapshot, state } from "./state.js";
import { connectSocket } from "./ws.js";

let socket = null;
let toastTimer = null;

const params = new URLSearchParams(location.search);
state.gameId = params.get("game");

function tokenKey() {
  return `chessstratego_token_${state.gameId}`;
}

function rerender() {
  render(actions);
}

function showError(payload) {
  state.error = payload;
  rerender();
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    state.error = null;
    rerender();
  }, 4000);
}

const actions = {
  async createGame() {
    const response = await fetch("/games", { method: "POST" });
    const data = await response.json();
    location.href = `/?game=${data.game_id}`;
  },
  joinByCode(code) {
    const trimmed = (code || "").trim();
    if (trimmed) location.href = `/?game=${trimmed}`;
  },
  join(name) {
    const trimmed = (name || "").trim();
    if (trimmed) socket.send(MSG.JOIN, { name: trimmed });
  },
  start() {
    socket.send(MSG.START_GAME, {});
  },
  autoSetup() {
    socket.send(MSG.SETUP_AUTO, {});
  },
  submitSetup() {
    const placements = Object.entries(state.setup.placements).map(([pieceId, pos]) => ({
      piece_id: pieceId,
      pos,
    }));
    socket.send(MSG.SETUP_SUBMIT, { placements });
  },
  clearSetup() {
    state.setup.placements = {};
    state.setup.trayPieceId = null;
    rerender();
  },
  pickTray(pieceId) {
    state.setup.trayPieceId = state.setup.trayPieceId === pieceId ? null : pieceId;
    rerender();
  },
  tapSetup(r, c) {
    const you = state.players.find((p) => p.id === state.you);
    if (!you || you.setup_done) return;
    const zone = state.board.setup_zones[you.edge] || [];
    const inZone = zone.some(([zr, zc]) => zr === r && zc === c);
    const placements = state.setup.placements;
    const occupantId = Object.keys(placements).find(
      (id) => placements[id][0] === r && placements[id][1] === c
    );
    if (state.setup.trayPieceId) {
      if (!inZone) return;
      if (occupantId) delete placements[occupantId];
      placements[state.setup.trayPieceId] = [r, c];
      // Auto-advance to the next unplaced piece to keep setup quick.
      const next = Object.values(state.pieces).find(
        (p) => p.owner === state.you && !placements[p.id]
      );
      state.setup.trayPieceId = next ? next.id : null;
      rerender();
    } else if (occupantId) {
      delete placements[occupantId];
      state.setup.trayPieceId = occupantId;
      rerender();
    }
  },
  tapPlay(r, c) {
    if (state.phase !== "playing") return;
    if (state.selection) {
      const targets = state.yourLegalMoves[state.selection] || [];
      if (targets.some(([tr, tc]) => tr === r && tc === c)) {
        socket.send(MSG.MOVE, { piece_id: state.selection, to: [r, c] });
        state.selection = null;
        rerender();
        return;
      }
    }
    const here = Object.values(state.pieces).find(
      (p) => !p.captured && p.pos && p.pos[0] === r && p.pos[1] === c
    );
    if (here && here.owner === state.you && state.yourLegalMoves[here.id]) {
      state.selection = state.selection === here.id ? null : here.id;
    } else {
      state.selection = null;
    }
    rerender();
  },
  async copyLink(text) {
    try {
      await navigator.clipboard.writeText(text);
      showError({ code: "copied", message: "Link copied — send it to your opponents" });
    } catch {
      showError({ code: "copy_failed", message: "Copy failed — long-press the link instead" });
    }
  },
};

function onMessage(envelope) {
  if (envelope.type === MSG.JOINED) {
    state.you = envelope.payload.player_id;
    state.token = envelope.payload.token;
    // sessionStorage, NOT localStorage: it is per-tab, so two tabs on one
    // device stay two different players, while a reload/reconnect in the
    // same tab still finds its token.
    sessionStorage.setItem(tokenKey(), state.token);
    rerender();
  } else if (envelope.type === MSG.SNAPSHOT) {
    applySnapshot(envelope.payload);
    rerender();
  } else if (envelope.type === MSG.ERROR) {
    if (envelope.payload.code === "bad_token") {
      // Stale token (e.g. server restarted): fall back to a fresh join.
      state.token = null;
      sessionStorage.removeItem(tokenKey());
      rerender();
      return;
    }
    showError(envelope.payload);
  }
}

function onStatus(connected) {
  state.connected = connected;
  if (connected && state.token) {
    socket.send(MSG.REJOIN, { token: state.token });
  }
  rerender();
}

if (state.gameId) {
  state.token = sessionStorage.getItem(tokenKey());
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  socket = connectSocket({
    url: `${scheme}://${location.host}/ws/${state.gameId}`,
    onMessage,
    onStatus,
  });
}

rerender();
