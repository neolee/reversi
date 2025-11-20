import time
import threading
import random
from reversi.protocol.interface import EngineInterface
from reversi.protocol.constants import Command, Response

class MockEngine(EngineInterface):
    """
    A mock engine for UI testing.
    It simply responds to commands with valid protocol messages.
    """
    def __init__(self, board_size: int = 8):
        super().__init__()
        self.board_size = board_size
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._emit(f"{Response.READY}")

    def stop(self):
        self._running = False

    def send_command(self, command: str):
        if not self._running:
            return

        parts = command.split()
        cmd = parts[0]

        if cmd == Command.INIT:
            self._emit(Response.READY)

        elif cmd == Command.NEWGAME:
            self._emit(Response.OK)

        elif cmd == Command.PLAY:
            # Simulate processing time then confirm
            # In a real engine, this would update internal board state
            self._emit(Response.OK)

        elif cmd == Command.GENMOVE:
            # Simulate thinking
            threading.Thread(target=self._simulate_thinking).start()

        elif cmd == Command.UNDO:
            self._emit(Response.OK)

    def _simulate_thinking(self):
        time.sleep(1.0) # Fake thinking time
        # Just return a random coordinate for now
        cols = [chr(65+i) for i in range(self.board_size)]
        rows = [str(i+1) for i in range(self.board_size)]
        move = f"{random.choice(cols)}{random.choice(rows)}"
        self._emit(f"{Response.MOVE} {move}")
