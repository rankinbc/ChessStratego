// CSS Grid board build + square tap handlers. Tap-tap select/move only —
// native HTML5 drag-and-drop has no touch support, so it is never used.
// The grid is sized from the snapshot's board dimension (12/14/16 —
// never hardcoded) and renders redacted opponent stratego pieces
// null-safely: type === null draws a face-down back, nothing more.

import { seatIndex, state } from "./state.js";

const CHESS_GLYPHS = {
  pawn: "♟",
  knight: "♞",
  bishop: "♝",
  rook: "♜",
  queen: "♛",
  king: "♚",
};

// Classic 1-is-strongest Stratego labels: Marshal 1 ... Scout 9, plus
// F(lag), B(omb), S(py). Must stay in step with STRATEGO_RANKS in
// game_server/app/engine/pieces.py — the server never sends the number.
const STRATEGO_LABELS = {
  flag: "F",
  bomb: "B",
  spy: "S",
  marshal: "1",
  general: "2",
  colonel: "3",
  major: "4",
  captain: "5",
  miner: "8",
  scout: "9",
};

export function pieceLabel(piece) {
  if (piece.kind === "chess") return CHESS_GLYPHS[piece.type] || "?";
  if (piece.type === null) return "?"; // redacted — face-down back
  return STRATEGO_LABELS[piece.type] || "?";
}

export function describePiece(piece) {
  if (piece.kind === "stratego" && piece.type === null) return "hidden stratego piece";
  return `${piece.kind} ${piece.type}`;
}

function keyOf(pos) {
  return `${pos[0]},${pos[1]}`;
}

// options: {onCellTap(r,c), highlights: Set<"r,c">, zone: Set<"r,c">,
//           flash: Set<"r,c">, selectedKey: "r,c"|null,
//           extraPieces: Map<"r,c", piece>} — extraPieces lets the setup
//           phase draw locally-placed pieces the server has not seen yet.
export function buildBoard(options = {}) {
  const board = state.board;
  const wrap = document.createElement("div");
  wrap.className = "board-wrap";
  if (!board) return wrap;

  const lakes = new Set(board.lakes.map(keyOf));
  const byPos = new Map();
  for (const piece of Object.values(state.pieces)) {
    if (!piece.captured && piece.pos) byPos.set(keyOf(piece.pos), piece);
  }
  if (options.extraPieces) {
    for (const [key, piece] of options.extraPieces) byPos.set(key, piece);
  }

  const grid = document.createElement("div");
  grid.className = "board";
  grid.style.gridTemplateColumns = `repeat(${board.size}, 1fr)`;
  grid.style.setProperty("--n", board.size);
  grid.setAttribute("role", "grid");
  grid.setAttribute("aria-label", `game board, ${board.size} by ${board.size}`);

  for (let r = 0; r < board.size; r += 1) {
    for (let c = 0; c < board.size; c += 1) {
      const key = `${r},${c}`;
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "cell";
      cell.classList.add((r + c) % 2 === 0 ? "light" : "dark");
      if (lakes.has(key)) cell.classList.add("lake");
      if (options.zone && options.zone.has(key)) cell.classList.add("zone");
      if (options.highlights && options.highlights.has(key)) cell.classList.add("target");
      if (options.flash && options.flash.has(key)) cell.classList.add("flash");
      if (options.selectedKey === key) cell.classList.add("selected");

      const piece = byPos.get(key);
      let label = lakes.has(key) ? "lake" : "empty";
      if (piece) {
        const seat = seatIndex(piece.owner);
        const chip = document.createElement("span");
        chip.className = `piece seat-${seat >= 0 ? seat : "x"} ${piece.kind}`;
        if (piece.kind === "stratego" && piece.type === null) chip.classList.add("facedown");
        if (piece.kind === "stratego" && piece.revealed) chip.classList.add("revealed");
        chip.textContent = pieceLabel(piece);
        cell.appendChild(chip);
        label = describePiece(piece);
      }
      cell.setAttribute("aria-label", `row ${r + 1}, column ${c + 1}: ${label}`);
      cell.dataset.r = r;
      cell.dataset.c = c;
      if (options.onCellTap) {
        cell.addEventListener("click", () => options.onCellTap(r, c));
      }
      grid.appendChild(cell);
    }
  }
  wrap.appendChild(grid);
  return wrap;
}

export { keyOf };
