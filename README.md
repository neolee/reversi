# Reversi


Cross-platform Reversi with a Flet UI and pluggable engines.


## Current Highlights


- Responsive GUI with marker-based valid move hints, undo-aware turn handling, and log pane streaming.
- Text protocol (INIT/NEWGAME/PLAY/GENMOVE/UNDO/BOARD/VALID_MOVES/RESULT/PASS) between UI and engines.
- Live scoreboard above the board shows running disc counts and declares the winner when play ends.
- Sidebar controls include a Pass Turn button that becomes available when the human has no legal moves, enforcing the official rules.
- `MinimaxEngine` uses Alpha-Beta pruning plus board cloning for strong play; `TrivialEngine` remains as a random baseline.
- `RustReversiEngine` wraps the `rust-reversi` PyPI package for a deeper Alpha-Beta search implemented in Rust.


## Requirements


- Python 3.11+
- [uv](https://github.com/astral-sh/uv) for dependency management
- Desktop environment supported by [Flet](https://flet.dev)


## Run the UI


```bash
uv run main.py ui --size 8 --engine minimax --search-depth 3
```


Engine switches:
- `minimax` (default): Python engine with Alpha-Beta pruning. Tune strength with `--search-depth` (>=1).
- `rust`: Alpha-Beta powered by the `rust-reversi` crate. Shares the `--search-depth` control (>=1) and currently targets 8x8 boards.
- `trivial`: Random legal moves, useful for debugging GUI/protocol flows.


Board size is adjustable with `--size` (defaults to 8). Python engines honor any size; the Rust engine currently supports 8x8 only.


## Development Notes


- GUI and engine remain fully decoupled via the text protocol, easing external engine integration.
- Save/load format will stay human-readable (JSON or simple move lists).
- Additional analysis tools (move suggestions, win rate) are planned once the engine is hardened.