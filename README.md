# Reversi

Cross-platform Reversi with a Flet UI and pluggable engines.

## Current Highlights

- Responsive GUI with marker-based valid move hints, undo-aware turn handling, and log pane streaming.
- Text protocol (INIT/NEWGAME/PLAY/GENMOVE/UNDO/BOARD/VALID_MOVES/RESULT/PASS) between UI and engines.
- Live scoreboard above the board shows running disc counts, labels each side with the selected Human/engine, and declares the winner when play ends.
- Sidebar controls include a Pass Turn button that becomes available when the human has no legal moves, enforcing the official rules.
- `MinimaxEngine` uses Alpha-Beta pruning plus board cloning for strong play; `TrivialEngine` remains as a random baseline.
- `RustAlphaBetaEngine`, `RustThunderEngine`, and `RustMctsEngine` wrap the `rust-reversi` PyPI package for deterministic alpha-beta, epsilon-greedy playout, and Monte Carlo tree search playstyles.
- Save/Load buttons write human-readable JSON timelines, and a replay toolbar under the board lets you scrub through any finished or loaded match.
- Engine configuration is metadata-driven (`src/reversi/engine/metadata.py`) so the GUI dialog and CLI duel runner share the same parameter definitions; `src/reversi/engine/ai_player.py` exposes reusable `EngineSpec`/`EnginePlayer` helpers for automated play.

```sh
uv run main.py ui --size 8
```

The GUI always boots with the default protocol engine and lets you pick per-color opponents from the sidebar dropdowns. Tap the gear icon next to **Black** or **White** to open the metadata-driven configuration dialog, then tweak depth/delay/epsilon/etc. as exposed by that engine's definition in `src/reversi/engine/metadata.py`. Board size remains configurable via `--size` (default 8).

The Controls panel includes **Save** / **Load** buttons, and the replay toolbar under the board becomes active once a game ends or after you load a saved timeline.

## Run Engine Duels from the CLI

Use the duel command when you want fully automated match series without the GUI:

```shell
uv run main.py duel \
  --size 8 \
  --games 4 \
  --black-engine minimax --black-depth 4 --black-delay 0.0 \
  --white-engine rust-alpha --white-depth 5 --white-delay 0.1
```

Each side takes its own engine/depth/delay parameters via the shared `EngineSpec` utilities.

## Save / Load / Replay

- **Save**: Click *Save* anytime to export the entire timeline (initial position plus each snapshot) as a JSON file.
- **Load**: Click *Load* to pick a JSON save. The engine replays every move behind the scenes so you can continue exactly where you left off.
- **Replay**: When no live game is running, use the toolbar beneath the board to jump to the start/end, step through moves, or auto-play the history.

## Development Notes

- GUI and engine remain fully decoupled via the text protocol, easing external engine integration.
- Save files stay human-readable JSON for easy auditing and tooling.
- The GUI now exposes per-color engine selection/configuration, replacing the older CLI flags; scoreboard labels reflect the active player type.
- CLI duel workflows rely on `EngineSpec`/`EnginePlayer` helpers plus the metadata registry to stay in sync with the GUI dialog.

## Roadmap

- Headless/automated engine-vs-engine workflows inside the GUI (batch runs, match recording, spectator view).
- Additional analysis tooling (move suggestions, win-rate overlays) to aid debugging and teaching.
- Optional board-size and engine presets synced between CLI and GUI for one-click tournament setups.