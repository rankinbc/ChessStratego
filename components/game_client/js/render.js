// Full re-render per phase: home -> lobby -> setup -> play -> game over.
// Reads the shared state object; all interaction goes through the actions
// object main.js passes in. Hidden-info safety: anything drawn for an
// opponent stratego piece goes through board.js's null-safe label path —
// this module never touches piece.type of a redacted piece.

import { buildBoard, keyOf, pieceLabel } from "./board.js";
import { isYourTurn, playerById, state, yourPlayer } from "./state.js";

const SEAT_NAMES = ["Blue", "Red", "Green", "Orange"];

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function button(label, className, onClick, disabled = false) {
  const node = el("button", className, label);
  node.type = "button";
  node.disabled = disabled;
  node.addEventListener("click", onClick);
  return node;
}

function nameOf(playerId) {
  const player = playerById(playerId);
  return player ? player.name : "someone";
}

export function describeEvent(event) {
  switch (event.kind) {
    case "player_joined":
      return `${event.name} joined the game`;
    case "player_disconnected":
      return `${nameOf(event.player_id)} disconnected`;
    case "player_reconnected":
      return `${nameOf(event.player_id)} reconnected`;
    case "game_started":
      return `Game started — ${event.board_size}x${event.board_size} board`;
    case "setup_done":
      return `${nameOf(event.player_id)} finished setup`;
    case "play_began":
      return `Battle begins — ${nameOf(event.first_player)} moves first`;
    case "move":
      return `${nameOf(event.owner)} moved a piece`;
    case "combat": {
      const attacker = `${nameOf(event.attacker.owner)}'s ${event.attacker.type}`;
      const defender = `${nameOf(event.defender.owner)}'s ${event.defender.type}`;
      let result;
      if (event.attacker.survived) result = `${event.attacker.type} wins`;
      else if (event.defender.survived) result = `${event.defender.type} wins`;
      else result = "both pieces fall";
      return `⚔ ${attacker} attacked ${defender} — ${result}`;
    }
    case "promotion":
      return `${nameOf(event.owner)}'s pawn was promoted to a queen`;
    case "elimination":
      return `${nameOf(event.player_id)} is eliminated (${event.reason.replace("_", " ")})`;
    case "turn_skipped":
      return `${nameOf(event.player_id)} has no legal move — turn skipped`;
    case "game_over":
      return event.winner ? `${nameOf(event.winner)} wins the game!` : "Draw — nobody can move";
    default:
      return null;
  }
}

function combatFlashCells() {
  const cells = new Set();
  for (const event of state.events) {
    if (event.kind === "combat" && event.at) cells.add(keyOf(event.at));
  }
  return cells;
}

function renderHome(root, actions) {
  const box = el("div", "panel center");
  box.appendChild(el("h1", "title", "ChessStratego"));
  box.appendChild(
    el("p", "hint", "Chess armies you can see, stratego armies you can't. 2-4 players.")
  );
  box.appendChild(button("Create a game", "primary big", actions.createGame));
  const row = el("div", "join-row");
  const input = el("input", "code-input");
  input.placeholder = "…or enter a game code";
  input.maxLength = 8;
  row.appendChild(input);
  row.appendChild(button("Join", "secondary", () => actions.joinByCode(input.value)));
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") actions.joinByCode(input.value);
  });
  box.appendChild(row);
  root.appendChild(box);
}

function renderLobby(root, actions) {
  const you = yourPlayer();
  const box = el("div", "panel");
  box.appendChild(el("h1", "title", "ChessStratego"));

  if (!you) {
    const form = el("div", "join-row");
    const input = el("input", "code-input");
    input.placeholder = "your display name";
    input.maxLength = 20;
    input.id = "name-input";
    form.appendChild(input);
    form.appendChild(button("Join game", "primary", () => actions.join(input.value)));
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") actions.join(input.value);
    });
    box.appendChild(form);
  }

  const list = el("ul", "player-list");
  state.players.forEach((player, i) => {
    const item = el("li", `player seat-${i}`);
    item.appendChild(el("span", "dot", ""));
    item.appendChild(
      el("span", "", `${player.name}${player.is_host ? " (host)" : ""}${player.id === state.you ? " — you" : ""}`)
    );
    if (!player.connected) item.appendChild(el("span", "muted", " · offline"));
    list.appendChild(item);
  });
  if (!state.players.length) box.appendChild(el("p", "hint", "Nobody has joined yet."));
  box.appendChild(list);

  const share = el("div", "share-row");
  const link = el("input", "code-input");
  link.readOnly = true;
  link.value = `${location.origin}/?game=${state.gameId}`;
  share.appendChild(link);
  share.appendChild(button("Copy link", "secondary", () => actions.copyLink(link.value)));
  box.appendChild(el("p", "hint", "Share this link — friends open it on their own device:"));
  box.appendChild(share);

  if (you && you.is_host) {
    box.appendChild(
      button(
        state.players.length >= 2 ? "Start game" : "Start game (need 2+ players)",
        "primary big",
        actions.start,
        state.players.length < 2
      )
    );
  } else if (you) {
    box.appendChild(el("p", "hint", "Waiting for the host to start the game…"));
  }
  root.appendChild(box);
}

function renderSetup(root, actions) {
  const you = yourPlayer();
  const box = el("div", "game-layout");
  box.appendChild(el("h2", "subtitle", "Secret setup"));
  if (!you) {
    box.appendChild(el("p", "hint", "This game has already started."));
    root.appendChild(box);
    return;
  }

  if (you.setup_done) {
    box.appendChild(el("p", "hint", "Setup submitted. Waiting for the others…"));
    box.appendChild(statusList());
    box.appendChild(buildBoard({}));
    root.appendChild(box);
    return;
  }

  const zone = new Set((state.board.setup_zones[you.edge] || []).map(keyOf));
  const placements = state.setup.placements;
  const extra = new Map();
  for (const [pieceId, pos] of Object.entries(placements)) {
    extra.set(keyOf(pos), state.pieces[pieceId]);
  }
  const placedCount = Object.keys(placements).length;
  const own = Object.values(state.pieces).filter((p) => p.owner === state.you);

  box.appendChild(
    el(
      "p",
      "hint",
      "Arrange all 30 pieces inside your highlighted zone. Opponents will see your chess pieces but never your stratego ranks. Tap a tray piece, then a square; tap a placed piece to pick it back up."
    )
  );

  const tray = el("div", "tray");
  for (const piece of own) {
    if (placements[piece.id]) continue;
    const chip = button(pieceLabel(piece), `tray-piece ${piece.kind}`, () =>
      actions.pickTray(piece.id)
    );
    chip.title = `${piece.kind} ${piece.type}`;
    if (state.setup.trayPieceId === piece.id) chip.classList.add("selected");
    tray.appendChild(chip);
  }
  box.appendChild(tray);

  box.appendChild(
    buildBoard({
      zone,
      extraPieces: extra,
      onCellTap: actions.tapSetup,
    })
  );

  const controls = el("div", "controls");
  controls.appendChild(el("span", "hint", `${placedCount} / 30 placed`));
  controls.appendChild(button("Auto-arrange & submit", "secondary", actions.autoSetup));
  controls.appendChild(button("Clear", "secondary", actions.clearSetup, placedCount === 0));
  controls.appendChild(button("Submit setup", "primary", actions.submitSetup, placedCount !== own.length));
  box.appendChild(controls);
  box.appendChild(statusList());
  root.appendChild(box);
}

function statusList() {
  const list = el("ul", "player-list compact");
  state.players.forEach((player, i) => {
    const item = el("li", `player seat-${i}`);
    item.appendChild(el("span", "dot", ""));
    const bits = [player.name];
    if (state.phase === "setup") bits.push(player.setup_done ? "ready" : "placing…");
    item.appendChild(el("span", "", bits.join(" — ")));
    if (player.eliminated) item.classList.add("eliminated");
    if (!player.connected) item.appendChild(el("span", "muted", " · offline"));
    list.appendChild(item);
  });
  return list;
}

function renderPlay(root, actions) {
  const box = el("div", "game-layout");
  const current = state.players[state.turnIndex];
  const banner = el(
    "div",
    `turn-banner${isYourTurn() ? " yours" : ""}`,
    state.phase === "finished"
      ? state.winner
        ? `🏆 ${nameOf(state.winner)} wins!`
        : "Draw — nobody can move"
      : isYourTurn()
        ? "Your turn — tap a piece"
        : `${current ? current.name : "…"}'s turn`
  );
  box.appendChild(banner);

  const highlights = new Set();
  let selectedKey = null;
  if (state.selection && state.yourLegalMoves[state.selection]) {
    for (const target of state.yourLegalMoves[state.selection]) highlights.add(keyOf(target));
    const piece = state.pieces[state.selection];
    if (piece && piece.pos) selectedKey = keyOf(piece.pos);
  }

  box.appendChild(
    buildBoard({
      onCellTap: state.phase === "playing" ? actions.tapPlay : undefined,
      highlights,
      selectedKey,
      flash: combatFlashCells(),
    })
  );

  box.appendChild(statusList());

  const feed = el("ul", "event-feed");
  for (const entry of state.eventLog.slice(-5).reverse()) {
    const text = describeEvent(entry);
    if (text) feed.appendChild(el("li", entry.kind === "combat" ? "combat" : "", text));
  }
  box.appendChild(feed);

  if (state.phase === "finished") {
    const again = el("a", "primary big linkbtn", "New game");
    again.href = "/";
    box.appendChild(again);
  }
  root.appendChild(box);
}

export function render(actions) {
  const root = document.getElementById("app");
  root.textContent = "";
  if (!state.gameId) {
    renderHome(root, actions);
  } else if (state.phase === "lobby") {
    renderLobby(root, actions);
  } else if (state.phase === "setup") {
    renderSetup(root, actions);
  } else {
    renderPlay(root, actions);
  }
  const bannerEl = document.getElementById("reconnect-banner");
  bannerEl.hidden = state.connected || !state.gameId;
  const toast = document.getElementById("toast");
  if (state.error) {
    toast.textContent = state.error.message || state.error.code;
    toast.hidden = false;
  } else {
    toast.hidden = true;
  }
}
