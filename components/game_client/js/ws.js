// WebSocket connect + reconnect. Envelope: { type, payload, seq }.
// Reconnect uses capped exponential backoff with jitter; after every
// reconnect the server replies to "rejoin" with a FULL redacted snapshot
// (no delta replay — seq only detects ordering, it is not a patch log).

const BASE_DELAY_MS = 500;
const MAX_DELAY_MS = 8000;

export function connectSocket({ url, onMessage, onStatus }) {
  let socket = null;
  let closedForGood = false;
  let attempt = 0;
  let seqOut = 0;

  function open() {
    socket = new WebSocket(url);
    socket.addEventListener("open", () => {
      attempt = 0;
      onStatus(true);
    });
    socket.addEventListener("message", (event) => {
      let envelope;
      try {
        envelope = JSON.parse(event.data);
      } catch {
        return; // never let one bad frame kill the client
      }
      onMessage(envelope);
    });
    socket.addEventListener("close", () => {
      onStatus(false);
      if (!closedForGood) scheduleRetry();
    });
    socket.addEventListener("error", () => {
      try {
        socket.close();
      } catch {
        /* already closed */
      }
    });
  }

  function scheduleRetry() {
    attempt += 1;
    const backoff = Math.min(MAX_DELAY_MS, BASE_DELAY_MS * 2 ** attempt);
    const jitter = Math.random() * 300;
    setTimeout(() => {
      if (!closedForGood) open();
    }, backoff + jitter);
  }

  open();

  return {
    send(type, payload) {
      if (socket && socket.readyState === WebSocket.OPEN) {
        seqOut += 1;
        socket.send(JSON.stringify({ type, payload, seq: seqOut }));
        return true;
      }
      return false;
    },
    close() {
      closedForGood = true;
      if (socket) socket.close();
    },
  };
}
