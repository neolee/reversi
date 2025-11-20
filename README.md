# Reversi

Cross-platform Reversi with a Flet UI and pluggable engines.

## Current Highlights

- Responsive GUI with marker-based valid move hints, undo-aware turn handling, and log pane streaming.
- Text protocol (INIT/NEWGAME/PLAY/GENMOVE/UNDO/BOARD/VALID_MOVES/RESULT) between UI and engines.
- `LocalEngine` now uses Minimax with Alpha-Beta pruning and board cloning for stronger AI play.
- `TrivialEngine` provides a baseline random mover for quick regressions and demos.

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
- `trivial`: Random legal moves, useful for debugging GUI/protocol flows.

Board size is adjustable with `--size` (defaults to 8). Both engines honor the configured dimensions.

## Development Notes

- GUI and engine remain fully decoupled via the text protocol, easing external engine integration.
- Save/load format will stay human-readable (JSON or simple move lists).
- Additional analysis tools (move suggestions, win rate) are planned once the engine is hardened.