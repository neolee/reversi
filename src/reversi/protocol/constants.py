class Command:
    INIT = "INIT"
    NEWGAME = "NEWGAME"
    PLAY = "PLAY"       # PLAY <coord> (e.g., PLAY D3)
    GENMOVE = "GENMOVE" # GENMOVE <color>
    UNDO = "UNDO"
    QUIT = "QUIT"

class Response:
    READY = "READY"
    OK = "OK"
    MOVE = "MOVE"       # MOVE <coord>
    PASS = "PASS"
    ERROR = "ERROR"     # ERROR <msg>
    INFO = "INFO"       # INFO <key> <value> (e.g., INFO SCORE_BLACK 2)
    RESULT = "RESULT"   # RESULT <winner>
