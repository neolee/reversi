class Command:
    INIT = "INIT"
    NEWGAME = "NEWGAME"
    PLAY = "PLAY"       # PLAY <coord> (e.g., PLAY D3)
    GENMOVE = "GENMOVE" # GENMOVE <color>
    UNDO = "UNDO"
    BOARD = "BOARD"     # Request board state
    VALID_MOVES = "VALID_MOVES" # Request valid moves
    QUIT = "QUIT"

class Response:
    READY = "READY"
    OK = "OK"
    MOVE = "MOVE"       # MOVE <coord>
    PASS = "PASS"
    BOARD = "BOARD"     # BOARD <size> <current_player> <state_string>
    VALID_MOVES = "VALID_MOVES" # VALID_MOVES <coord1> <coord2> ...
    ERROR = "ERROR"     # ERROR <msg>
    INFO = "INFO"       # INFO <key> <value> (e.g., INFO SCORE_BLACK 2)
    RESULT = "RESULT"   # RESULT <winner>
