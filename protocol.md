# Reversi Engine Protocol

This document describes the text-based communication protocol between the Reversi GUI and the Engine. The protocol is inspired by UCI (Universal Chess Interface) and GTP (Go Text Protocol).

## Overview

- Communication happens via standard input/output (stdin/stdout) for external engines, or direct method calls for internal Python engines (wrapped by `EngineInterface`).
- The GUI sends **Commands**.
- The Engine sends **Responses**.
- All commands and responses are single lines of text.

## Commands (GUI -> Engine)

### `INIT`
Initialize the engine. The engine should reset its internal state and prepare for a new session.
- **Response**: `READY`

### `NEWGAME`
Start a new game. Clears the board to the initial state.
- **Response**: `OK`

### `PLAY <coord>`
Place a piece at the specified coordinate for the current player.
- **Arguments**:
  - `<coord>`: Coordinate string (e.g., `D3`, `E4`).
- **Response**:
  - `OK`: Move accepted.
  - `ERROR <msg>`: Move illegal or invalid format.

### `GENMOVE <color>`
Request the engine to generate a move for the specified color.
- **Arguments**:
  - `<color>`: `BLACK` or `WHITE`.
- **Response**:
  - `MOVE <coord>`: The engine's chosen move.
  - `PASS`: If no legal moves are available.
  - `RESIGN`: If the engine gives up.

### `UNDO`
Undo the last move (both players).
- **Response**: `OK`

### `BOARD`
Request the current board state.
- **Response**: 
  - `BOARD <size> <state_string>`
  - `state_string`: A string of length size*size, row by row. `.` for empty, `B` for Black, `W` for White.

### `QUIT`
Terminate the engine session.

## Responses (Engine -> GUI)

### `READY`
Sent in response to `INIT`.

### `OK`
Generic success response.

### `MOVE <coord>`
Sent in response to `GENMOVE`.

### `PASS`
Sent in response to `GENMOVE` if no moves are possible.

### `BOARD <size> <state_string>`
Sent in response to `BOARD` or as an update.

### `ERROR <msg>`
Sent when a command fails or is invalid.

### `INFO <key> <value>`
Sent to provide auxiliary information (e.g., score, depth, pv).
- Example: `INFO SCORE_BLACK 2`

### `RESULT <winner>`
Sent when the game ends.
- `<winner>`: `BLACK`, `WHITE`, or `DRAW`.