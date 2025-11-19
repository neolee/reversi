# Reversi

A Reversi game with AI engine for both educational and entertainment purposes.

## Features

- GUI and engine separated architecture
- Dual engines support
  - Built-in engine using Minimax with Alpha-Beta Pruning for educational purpose
  - Third party high-performance engine e.g. [rust-reversi](https://github.com/neodymium6/rust_reversi)
- Clean and user-friendly GUI supporting mouse and keyboard inputs
  - Support human vs AI and AI vs AI modes
  - Support undo/redo moves
  - Real-time game analysis with move suggestions and win rate display
- Cross-platform support (Windows, macOS, Linux)

## Developmenting

- Python 3.8+
- uv
- UI framework
  - TUI framework ??? or GUI framework ??? or web based ???