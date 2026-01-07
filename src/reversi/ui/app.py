import sys
import asyncio
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTextEdit, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, Signal, Slot
from qasync import QEventLoop

from reversi.protocol.interface import EngineInterface
from reversi.protocol.constants import Command, Response
from .components.board import BoardWidget
from .components.scoreboard import ScoreboardWidget

class ReversiApp(QMainWindow):
    message_received = Signal(str)

    def __init__(self, engine: EngineInterface, board_size: int = 8):
        super().__init__()
        self.engine = engine
        self.board_size = board_size
        self.setWindowTitle(f"Reversi {board_size}x{board_size} (PySide6)")
        self.resize(1100, 800)

        # State
        self.current_turn = "BLACK"
        self.game_started = False
        self._score_black = 2
        self._score_white = 2
        self.undo_expect_updates = 0

        # Player configuration (will be managed by sidebar later)
        self.players = {
            "BLACK": {"name": "Human", "is_human": True},
            "WHITE": {"name": "Minimax", "is_human": False}
        }

        # UI Setup
        central_widget = QWidget()
        central_widget.setObjectName("central_widget")
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Stylesheet
        self.setStyleSheet("""
            #central_widget {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #202020;
            }
            QTextEdit {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                font-family: 'SF Mono', 'Courier New', monospace;
                font-size: 11px;
            }
            QPushButton {
                background-color: #e8e8e8;
                border: 1px solid #c8c8c8;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #dcdcdc;
            }
            QPushButton:pressed {
                background-color: #cfcfcf;
            }
        """)
        sidebar = QWidget()
        sidebar.setFixedWidth(300)
        sidebar_layout = QVBoxLayout(sidebar)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        sidebar_layout.addWidget(self.log_view)

        btn_new_game = QPushButton("New Game")
        btn_new_game.clicked.connect(self.start_new_game)
        sidebar_layout.addWidget(btn_new_game)

        btn_undo = QPushButton("Undo")
        btn_undo.clicked.connect(self.undo_move)
        sidebar_layout.addWidget(btn_undo)

        main_layout.addWidget(sidebar)

        # Right Area
        right_area = QWidget()
        right_layout = QVBoxLayout(right_area)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        self.scoreboard = ScoreboardWidget()
        self.scoreboard.set_players(self.players["BLACK"]["name"], self.players["WHITE"]["name"])
        right_layout.addWidget(self.scoreboard)

        self.board_widget = BoardWidget(board_size)
        self.board_widget.clicked.connect(self.handle_board_click)
        right_layout.addWidget(self.board_widget, stretch=1)

        main_layout.addWidget(right_area, stretch=1)

        # Engine setup
        self.engine.set_callback(self.on_engine_message)
        self.message_received.connect(self.process_message)

    def log(self, text):
        self.log_view.append(text)

    def on_engine_message(self, message):
        self.message_received.emit(message)

    @Slot(str)
    def process_message(self, message):
        parts = message.split()
        if not parts: return

        cmd = parts[0]

        if cmd == Response.BOARD:
            if len(parts) >= 4:
                size = int(parts[1])
                turn = parts[2]
                state_str = parts[3]
                self.current_turn = turn
                self.update_board_ui(size, state_str)

                player = self.players[turn]
                self.scoreboard.set_status(turn, player["name"], player["is_human"])

                # If we are in the middle of an undo sequence, don't trigger AI turns
                if self.undo_expect_updates > 0:
                    self.undo_expect_updates -= 1
                    if self.undo_expect_updates > 0:
                        self.log("System: Waiting for second undo...")
                        return

                if self.game_started and self.current_turn == "WHITE":
                    self.send_command(f"{Command.GENMOVE} WHITE")
                elif self.game_started and self.current_turn == "BLACK":
                    self.send_command(Command.VALID_MOVES)
                    self.send_command(f"{Command.ANALYZE} BLACK")

        elif cmd == Response.VALID_MOVES:
            moves = parts[1:]
            self.board_widget.set_valid_moves(moves)

        elif cmd == Response.ANALYSIS:
            scores = {}
            for item in parts[1:]:
                if ":" in item:
                    coord, score = item.split(":", 1)
                    scores[coord] = score
            self.board_widget.set_analysis(scores)

        elif cmd == Response.INFO:
            if len(parts) >= 3:
                key, value = parts[1], parts[2]
                if key == "SCORE_BLACK":
                    self._score_black = value
                elif key == "SCORE_WHITE":
                    self._score_white = value
                self.scoreboard.update_scores(self._score_black, self._score_white)

        elif cmd == Response.RESULT:
            self.game_started = False
            winner = parts[1]
            self.log(f"Game Over: {winner}")
            self.scoreboard.set_status_text(f"GAME OVER: WINNER IS {winner}")
            # Clear helpers
            self.board_widget.set_valid_moves([])
            self.board_widget.set_analysis({})

    def update_board_ui(self, size, state_str):
        state = {}
        idx = 0
        black_count = 0
        white_count = 0
        for r in range(size):
            for c in range(size):
                char = state_str[idx]
                coord = f"{chr(65+c)}{r+1}"
                if char == 'B':
                    state[coord] = "BLACK"
                    black_count += 1
                elif char == 'W':
                    state[coord] = "WHITE"
                    white_count += 1
                idx += 1

        self.board_widget.set_state(state)
        self._score_black = black_count
        self._score_white = white_count
        self.scoreboard.update_scores(black_count, white_count)

    def handle_board_click(self, coord):
        if not self.game_started or self.current_turn != "BLACK":
            return
        self.send_command(f"{Command.PLAY} {coord}")

    def start_new_game(self):
        self.game_started = True
        self.board_widget.set_valid_moves([])
        self.board_widget.set_analysis({})
        self.send_command(f"{Command.INIT} {self.board_size}")
        self.send_command(Command.NEWGAME)
        self.log("Started New Game")

    def undo_move(self):
        if not self.game_started:
            self.log("System: Cannot undo when game is not active.")
            return

        # Determine undo count
        other_turn = "WHITE" if self.current_turn == "BLACK" else "BLACK"
        is_human_vs_ai = (self.players[self.current_turn]["is_human"] != self.players[other_turn]["is_human"])

        undo_count = 1
        if is_human_vs_ai and self.players[self.current_turn]["is_human"]:
            undo_count = 2

        self.undo_expect_updates = undo_count
        for _ in range(undo_count):
            self.send_command(Command.UNDO)
        self.log(f"Undo requested ({undo_count} steps)")

    def send_command(self, cmd):
        self.engine.send_command(cmd)

    def closeEvent(self, event):
        self.engine.stop()
        super().closeEvent(event)

def run_app(engine: EngineInterface, board_size: int = 8):
    app = QApplication.instance() or QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    reversi_app = ReversiApp(engine, board_size)
    reversi_app.show()

    engine.start()

    with loop:
        loop.run_forever()
