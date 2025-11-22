# Reversi Project Context

This file provides context for AI agents working on the Reversi project.

## Project Goal
Develop a cross-platform Reversi game featuring a clean GUI and a powerful AI engine. The project aims to serve both educational purposes (via a built-in Minimax engine) and entertainment/competitive needs (via support for high-performance third-party engines).

## Architecture
- **Separation of Concerns**: The GUI and the Game Engine must be decoupled.
- **Communication Protocol**: Use a simplified text-based protocol for communication between the GUI and the Engine, inspired by UCI (Universal Chess Interface) or GTP (Go Text Protocol).
- **Engine Support**:
  - **Built-in**: Python-based Minimax algorithm with Alpha-Beta Pruning.
  - **External**: Support for external executables (e.g., Rust-based engines).

## Tech Stack
- **Language**: Python 3.11+ (as per pyproject.toml).
- **Package Manager**: `uv`.
- **UI Framework**: Flet (desktop/web).

## Key Features
- Human vs AI and AI vs AI modes with per-color engine selection from the GUI.
- Undo/Redo workflow that issues double `UNDO` when needed to keep Human vs AI turns aligned.
- Real-time analysis hooks (minimax evaluation, playout engines) exposed via the metadata registry.
- Game save/load (human-readable JSON) and replay timeline with toolbar controls.
- Headless duel runner (`main.py duel`) to script batches of engine-vs-engine games.

## Coding Conventions
- **Protocol**: Keep the engine communication protocol simple and text-based.
- **File Formats**: Save files should be simple and human-readable (e.g., JSON or plain text moves).
- **Documentation**: Document the protocol clearly.

## Current Status
- **UI**: Flet GUI with responsive board sizing, polished pieces, marker-based valid-move highlights, live score readouts, undo/pass-aware turn handling, and scoreboard labels that track whether a side is Human or which engine is in use.
- **Engine**: `MinimaxEngine` evaluates positions with Alpha-Beta (tunable depth); `TrivialEngine` provides a random baseline; `RustAlphaBetaEngine`, `RustThunderEngine`, and `RustMctsEngine` wrap the Rust implementation for deterministic and stochastic searches.
- **Engine Config**: `src/reversi/engine/metadata.py` centralizes engine parameter metadata and powers both the GUI dialog and CLI helpers. `src/reversi/engine/ai_player.py` defines reusable `EngineSpec`/`EnginePlayer` helpers shared by the duel runner and upcoming GUI integration.
- **Protocol**: Text-based command set (INIT/NEWGAME/PLAY/GENMOVE/VALID_MOVES/PASS/UNDO/BOARD/RESULT) implemented under `src/reversi/protocol`.
- **Entry Point**: `main.py` CLI offers `ui` (always boots the GUI with the default protocol engine and lets the sidebar configure per-color engines) plus `duel` for scripted engine-vs-engine runs with independent specs.
- **Persistence**: Sidebar Save/Load buttons export/import JSON timelines (v2 schema), and the replay toolbar under the board replays any finished or loaded match.
- **Dependencies**: `flet` and `rust-reversi` declared in `pyproject.toml`.

## Design Decisions
- **Rule Management**: The Engine is the "Source of Truth" for game rules (valid moves, win conditions). The UI will query the engine for valid moves to guide the user.
- **Board Size**: Parameterized (default 8x8), supported by both UI and Engine.

## Recent Notes
- UI auto-starts games and listens for engine responses; all turn transitions are driven by `BOARD`/`VALID_MOVES` messages.
- Responsive sizing handled via an async viewport monitor that recalculates cell dimensions and keeps the board square next to the sidebar.
- Valid moves are indicated with stacked glow markers (no border changes) and are cleared immediately once the human plays.
- Undo button issues two `UNDO` commands when needed so human turns always resume correctly in Human vs AI mode.
- Log pane autoscrolls and only re-renders itself for new messages to limit UI churn.
- Pass button activates only when the human has no legal moves and sends `PASS <color>`; engines also auto-pass when they are out of moves, leading to a `RESULT` once both colors are stuck.
- Engine selection dialog lets each color choose/configure its engine; `ai_engine_settings` is persisted alongside player modes so replays/loadouts stay in sync.
- CLI `ui` command no longer exposes `--engine`/`--search-depth`; the GUI is now the single source of truth for engine selection, while the duel command keeps per-side options.
- Headless duel runner leverages the shared `EngineSpec` and metadata registry so both CLI and GUI stay aligned when adding new engines.

## Roadmap
- Design spectator/visualization workflows for engine-vs-engine matches inside the GUI (live analysis overlays, match recording).
- Expand board/engine presets to streamline tournament or teaching setups.
- Explore auxiliary tooling such as visualizing engine analysis data to aid debugging and teaching.

## Known Issues
- **Flet FilePicker Bug**: Flet version 0.28.3 has a bug where the FilePicker dialog does not appear. This is fixed in 0.28.2 (rollback required) or future versions.