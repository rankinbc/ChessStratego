# rulebook

**Purpose**: The living rules document for ChessStratego, a hybrid chess + stratego board game for 2-4 players. Documents mixed-army mechanics (chess pieces always visible, stratego pieces hidden until combat reveals them), the expanded board with stratego-style lakes, setup, turn order, combat resolution, win conditions, and check handling — with each rule section paired to the exact `game_server` engine module that implements it, so the doc and code stay in lockstep as rules evolve through playtesting.

**Inputs**: None (playtest experience — not a data file — feeds `DECISION_LOG.md`)

**Outputs**: None in the project's `output/` sense — `RULES.md` and `DECISION_LOG.md` in this folder ARE the deliverables. They're maintained in place as living documents, not versioned publish artifacts.

**Pattern**: `product_doc.md`

**Stack**: Markdown only. No runtime, no code, no export step (this component doesn't need PDF export).

## How to run

Open `RULES.md` and `DECISION_LOG.md` directly in any editor — there's no build step. After a playtest session, add a row to `DECISION_LOG.md`, then edit the relevant `RULES.md` section together with the code module named in its `Implemented in:` line.

## Structure

- `RULES.md` — the living rulebook. Sections marked **DECIDED** (overview, combat resolution, win conditions, check rules) are written in full, including documented-but-inactive variants. Sections marked **PARTIALLY DECIDED** or **STUB** (board geometry, setup mechanics, turn order) have the locked parts written out and open questions flagged as `[/execute-prp fills this in]`.
- `DECISION_LOG.md` — table of playtest-driven rule changes: date, what felt broken, rule change made, code module edited.

---

**To extend this component**: edit `PRPs/source/INITIAL.md` and run `/generate-prp`. Don't modify files here directly for new work — let the PRP drive it.
