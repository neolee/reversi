# Reversi

Cross-platform Reversi with a Flet UI and pluggable engines.

## Current Highlights

- Responsive GUI with marker-based valid move hints, undo-aware turn handling, and log pane streaming.
- Text protocol (INIT/NEWGAME/PLAY/GENMOVE/UNDO/BOARD/VALID_MOVES/RESULT/PASS) between UI and engines.
- Live scoreboard above the board shows running disc counts and declares the winner when play ends.
- Sidebar controls include a Pass Turn button that becomes available when the human has no legal moves, enforcing the official rules.
- `MinimaxEngine` uses Alpha-Beta pruning plus board cloning for strong play; `TrivialEngine` remains as a random baseline.
- `RustReversiEngine` wraps the `rust-reversi` PyPI package for a deeper Alpha-Beta search implemented in Rust.
- Save/Load buttons write human-readable JSON timelines, and a replay toolbar under the board lets you scrub through any finished or loaded match.

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) for dependency management
- Desktop environment supported by [Flet](https://flet.dev)

## Run the UI

```sh
uv run main.py ui --size 8 --engine minimax --search-depth 3
uv run main.py ui --size 8 --engine rust --search-depth 5
```

Engine switches:
- `minimax` (default): Python engine with Alpha-Beta pruning. Tune strength with `--search-depth` (>=1).
- `rust`: Alpha-Beta powered by the `rust-reversi` crate. Shares the `--search-depth` control (>=1) and currently targets 8x8 boards.
- `trivial`: Random legal moves, useful for debugging GUI/protocol flows.

Board size is adjustable with `--size` (defaults to 8). Python engines honor any size; the Rust engine currently supports 8x8 only.

The Controls panel now includes **Save** and **Load** buttons, and the replay toolbar under the board becomes active once a game ends or after you load a saved timeline.

## Save / Load / Replay

- **Save**: Click *Save* anytime to export the entire timeline (initial position plus each snapshot) as a JSON file.
- **Load**: Click *Load* to pick a JSON save. The engine replays every move behind the scenes so you can continue exactly where you left off.
- **Replay**: When no live game is running, use the toolbar beneath the board to jump to the start/end, step through moves, or auto-play the history.

## Development Notes

- GUI and engine remain fully decoupled via the text protocol, easing external engine integration.
- Save files stay human-readable JSON for easy auditing and tooling.
- Additional analysis tools (move suggestions, win rate) are planned once the engine is hardened.

## Upcoming Work

- Design engine-vs-engine workflows: define CLI support (batch runs, match recording), clarify if/when the UI should visualize engine bouts, and outline the GUI changes needed for automated battles.
- Explore auxiliary tooling such as visualizing engine analysis data to aid debugging and teaching.