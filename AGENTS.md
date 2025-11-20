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
- **UI Framework**: Undecided (Candidates: Flet or NiceGUI). When implementing UI, check for existing decisions or ask the user.

## Key Features to Implement
- Human vs AI and AI vs AI modes.
- Undo/Redo functionality.
- Real-time analysis (move suggestions, win rate).
- Game save/load (human-readable format) and replay.
- Headless mode for simulations.

## Coding Conventions
- **Protocol**: Keep the engine communication protocol simple and text-based.
- **File Formats**: Save files should be simple and human-readable (e.g., JSON or plain text moves).
- **Documentation**: Document the protocol clearly.

## Current Status
- **UI**: Basic Flet-based GUI implemented (`src/reversi/ui`).
- **Engine**: `MockEngine` implemented for testing; `EngineInterface` defined.
- **Protocol**: Basic text-based protocol defined (`src/reversi/protocol`).
- **Entry Point**: `main.py` created with CLI support (e.g., `uv run main.py ui --size 8`).
- **Dependencies**: `flet` added to `pyproject.toml`.

## Design Decisions
- **Rule Management**: The Engine is the "Source of Truth" for game rules (valid moves, win conditions). The UI will query the engine for valid moves to guide the user.
- **Board Size**: Parameterized (default 8x8), supported by both UI and Engine.