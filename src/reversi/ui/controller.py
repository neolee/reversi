from PySide6.QtCore import QObject, Signal, Slot, Qt
from reversi.protocol.interface import EngineInterface
from reversi.protocol.constants import Command, Response

class EngineBroker(QObject):
    """
    Handles communication with the Reversi engine via the text protocol.
    Translates raw string responses into high-level Qt signals.
    """
    message_logged = Signal(str)
    error_occurred = Signal(str)
    board_received = Signal(int, str, str)  # size, turn, state_str
    valid_moves_received = Signal(list)
    analysis_received = Signal(dict)
    scores_received = Signal(int, int) # black (or -1), white (or -1)
    game_over = Signal(str) # winner
    raw_message_received = Signal(str)

    def __init__(self, engine: EngineInterface):
        super().__init__()
        self.engine = engine
        self.engine.set_callback(self.on_raw_message)
        # Use QueuedConnection to ensure that engine responses are processed in the 
        # next event loop tick, preventing blocking the UI thread during a command chain.
        self.raw_message_received.connect(self.process_response, Qt.ConnectionType.QueuedConnection)

    def on_raw_message(self, message: str):
        self.raw_message_received.emit(message)

    @Slot(str)
    def process_response(self, message: str):
        parts = message.split()
        if not parts: return
        cmd = parts[0]

        # 1. Logging Logic
        if cmd in (Response.MOVE, Response.PASS, Response.READY, Response.RESULT):
            self.message_logged.emit(f"Engine: {message}")
        elif cmd == Response.ERROR:
            self.error_occurred.emit(message)
        elif cmd == Response.ANALYSIS:
            self.message_logged.emit(f"Engine: ANALYSIS received ({len(parts)-1} scores)")
        elif cmd == Response.INFO:
            if not any(k in message for k in ["SCORE_BLACK", "SCORE_WHITE"]):
                self.message_logged.emit(f"Engine: {message}")

        # 2. Logic Dispatch
        if cmd == Response.BOARD:
            if len(parts) >= 4:
                size = int(parts[1])
                turn = parts[2]
                state_str = parts[3]
                self.board_received.emit(size, turn, state_str)

        elif cmd == Response.VALID_MOVES:
            self.valid_moves_received.emit(parts[1:])

        elif cmd == Response.ANALYSIS:
            scores = {}
            for item in parts[1:]:
                if ":" in item:
                    coord, score = item.split(":", 1)
                    scores[coord] = score
            self.analysis_received.emit(scores)

        elif cmd == Response.INFO:
            if len(parts) >= 3:
                key, value = parts[1], parts[2]
                if key == "SCORE_BLACK":
                    self.scores_received.emit(int(value), -1)
                elif key == "SCORE_WHITE":
                    self.scores_received.emit(-1, int(value))

        elif cmd == Response.RESULT:
            self.game_over.emit(parts[1])

    def send_command(self, cmd: str):
        self.engine.send_command(cmd)

    def start(self):
        self.engine.start()

    def stop(self):
        self.engine.stop()
