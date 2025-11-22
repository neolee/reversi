# Reversi Engine Protocol


This document describes the text-based communication protocol between the Reversi GUI and the Engine. The protocol is inspired by UCI (Universal Chess Interface) and GTP (Go Text Protocol).


## Overview


- Transport: stdin/stdout for external engines, direct method calls for in-process engines via `EngineInterface`.
- The GUI (client) issues **Commands**; the engine answers with **Responses**.
- Every message is a single line of UTF-8 text with tokens separated by spaces.
- Coordinates are in "A1" notation (file letter A-H, rank number 1-8 by default).


### Minimal Handshake Example

```text
GUI> INIT
ENG> READY
GUI> NEWGAME
ENG> BOARD 8 BLACK ...........................BW......WB...........................
GUI> GENMOVE BLACK
ENG> MOVE D3
ENG> BOARD 8 WHITE ...........B...........BW......WB...........................

GUI> VALID_MOVES WHITE
ENG> VALID_MOVES C3 C5 E3 F4
GUI> PASS WHITE
ENG> OK
ENG> BOARD 8 BLACK ...........B...........BW......WB...........................
```


## Commands (GUI -> Engine)


### `INIT`
Reset the engine to a clean state. Should not start a game automatically.
- **Expected response**: `READY`


### `NEWGAME`
Start a fresh game on the current board size and emit the canonical board snapshot.
- **Expected response**:
  - `BOARD <size> <current_player> <state_string>` (preferred so the GUI can sync instantly)
  - or `OK` followed by a `BOARD` push


### `PLAY <coord>`
Apply a move for the side whose turn it currently is.
- **Arguments**: `<coord>` such as `D3`.
- **Responses**:
  - `OK` if accepted (engine should also push an updated `BOARD`).
  - `ERROR <msg>` if illegal or malformed.

**Example**
```text
GUI> PLAY F5
ENG> OK
ENG> BOARD 8 WHITE ........F........BW......WB...........................
```


### `GENMOVE <color>`
Ask the engine to produce and play a move for `color`. The engine may update its internal board immediately.
- **Arguments**: `BLACK` or `WHITE`.
- **Responses**:
  - `MOVE <coord>` when a move is found.
  - `PASS <color>` if no moves exist for that color.
  - After responding, the engine should send a `BOARD` snapshot reflecting the updated state.

**Example**
```text
GUI> GENMOVE BLACK
ENG> MOVE D3
ENG> BOARD 8 WHITE ...........B...........BW......WB...........................
```


### `VALID_MOVES [color]`
Request the list of legal moves. If `color` is omitted, use the engine's current player.
- **Response**: `VALID_MOVES <coord1> <coord2> ...` (empty list means no legal moves).

**Example**
```text
GUI> VALID_MOVES WHITE
ENG> VALID_MOVES C3 C5 E3 F4
```


### `PASS <color>`
Force `color` to pass when no moves exist.
- **Response**: `OK` (plus an updated `BOARD`).
- Engines may send `ERROR <msg>` if legal moves still exist.

### `UNDO`
Undo the most recent move. When the GUI needs to revert to a human turn it may issue two `UNDO`s in a row.
- **Response**: `OK`, followed by a `BOARD` snapshot reflecting the rolled-back position.

### `BOARD`
Explicitly request the current board.
- **Response**: `BOARD <size> <current_player> <state_string>` where `state_string` is `size*size` chars (`B`, `W`, or `.`) listed row-by-row starting at A1.

### `QUIT`
Shut down gracefully. Engines should release resources and stop emitting output.


## Responses (Engine -> GUI)


### `READY`
Acknowledges `INIT`.


### `OK`
Generic success acknowledgement used by `PLAY`, `PASS`, `UNDO`, etc. Should normally be followed by a `BOARD` push so the GUI can stay in sync.


### `BOARD <size> <current_player> <state_string>`
Describes the full board and whose turn is next. Emitted after `NEWGAME`, `PLAY`, `GENMOVE`, `PASS`, `UNDO`, and on explicit `BOARD` requests.


### `MOVE <coord>`
Move produced for the last `GENMOVE` request. The engine should subsequently update the GUI with a `BOARD` snapshot reflecting the move.


### `PASS <color>`
Signals that `color` has no legal moves and must pass. Often emitted right after a `GENMOVE` request that yielded no moves.


### `VALID_MOVES <coord1> <coord2> ...`
Lists legal moves in response to a `VALID_MOVES` command. An empty payload indicates there are none.


### `ERROR <msg>`
Indicates an invalid command, illegal move, or internal failure. The GUI logs these messages for debugging.


### `INFO <key> <value>` (optional)
Auxiliary telemetry such as search depth, score, nodes, etc.
- Example: `INFO SCORE_BLACK 24`


### `RESULT <winner>`
Announces the end of the game. `<winner>` is `BLACK`, `WHITE`, or `DRAW`. Engines typically send a final `BOARD` snapshot beforehand so the GUI can display final scores.