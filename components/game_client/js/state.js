// Single client state object — the source of truth render.js draws from.
// All authoritative game state lives in game_server; the `server` half of
// this object is a redacted mirror overwritten wholesale by every
// snapshot. Opponent stratego pieces arrive with type: null until combat
// reveals them — the client never infers or caches an identity.

export const state = {
  connected: false,
  gameId: null,
  you: null, // your player_id, from the "joined" envelope
  token: null, // reconnect token — kept in localStorage per game

  // Redacted server snapshot mirror.
  phase: "lobby", // lobby | setup | playing | finished
  players: [],
  board: null, // {size, num_players, lakes, edges, setup_zones}
  pieces: {}, // piece_id -> {id, owner, kind, type|null, revealed, pos, captured}
  turnIndex: 0,
  winner: null,
  yourLegalMoves: {}, // piece_id -> [[r,c], ...] (only on your turn)
  events: [], // events carried by the latest snapshot
  eventLog: [], // client-side rolling feed of recent events
  seq: 0,

  // Local UI state.
  selection: null, // selected piece_id during play
  setup: {
    placements: {}, // piece_id -> [r,c], local until submitted
    trayPieceId: null, // piece picked from the tray, waiting for a square
  },
  error: null, // {code, message} — shown as a toast, then cleared
};

export function applySnapshot(payload) {
  const server = payload.state;
  state.you = payload.you;
  state.phase = server.phase;
  state.players = server.players;
  state.board = server.board;
  state.pieces = server.pieces;
  state.turnIndex = server.turn_index;
  state.winner = server.winner;
  state.yourLegalMoves = payload.your_legal_moves || {};
  state.events = payload.events || [];
  state.eventLog.push(...state.events);
  if (state.eventLog.length > 30) state.eventLog.splice(0, state.eventLog.length - 30);
  state.seq = payload.seq ?? state.seq;
  if (state.selection && !state.yourLegalMoves[state.selection]) {
    state.selection = null;
  }
  if (state.phase !== "setup") {
    state.setup.trayPieceId = null;
  }
}

export function playerById(id) {
  return state.players.find((p) => p.id === id) || null;
}

export function yourPlayer() {
  return playerById(state.you);
}

export function isYourTurn() {
  const current = state.players[state.turnIndex];
  return state.phase === "playing" && current && current.id === state.you;
}

export function ownPieces() {
  return Object.values(state.pieces).filter((p) => p.owner === state.you && !p.captured);
}

export function seatIndex(playerId) {
  return state.players.findIndex((p) => p.id === playerId);
}
