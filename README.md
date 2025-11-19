# Reversi

A Reversi game with AI engine for both educational and entertainment purposes.

## Features

- GUI and engine separated architecture
  - A simplified protocol for communication between GUI and engine
- Dual engines support
  - Built-in engine using Minimax with Alpha-Beta Pruning for educational purpose
  - Third party high-performance engine e.g. [rust-reversi](https://github.com/neodymium6/rust_reversi)
- Clean and user-friendly GUI supporting mouse and keyboard inputs
  - Support human vs AI and AI vs AI modes
  - Support undo/redo moves
  - Real-time game analysis with move suggestions and win rate display
- Cross-platform support (Windows, macOS, Linux)
- Game save/load and replay functionality
- Headless mode for AI matches and simulations

## Developing

### Technical notes

- Engine protocol design inspired by UCI (Universal Chess Interface) or GTP (Go Text Protocol)
- Game save format designed to be simple and human-readable
- Minimax with Alpha-Beta Pruning algorithm for built-in AI engine
- GUI implemented using Flet or NiceGUI for rapid development and cross-platform compatibility

### Environment

- Python 3.8+
- uv
- UI framework
  - Flet or NiceGUI?
