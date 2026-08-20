// Message type constants — THE wire contract shared with game_server.
// Mirrors components/game_server/app/messages.py exactly; change both
// sides together or not at all.
// Envelope shape (all directions): { type, payload, seq }

export const MSG = {
  // client -> server
  JOIN: "join",
  REJOIN: "rejoin",
  START_GAME: "start_game",
  SETUP_SUBMIT: "setup_submit",
  SETUP_AUTO: "setup_auto",
  MOVE: "move",
  RESYNC: "resync",
  // server -> client
  SNAPSHOT: "snapshot",
  JOINED: "joined",
  ERROR: "error",
};
