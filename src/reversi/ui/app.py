import sys
import asyncio
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTextEdit, QPushButton, QHBoxLayout, QLabel, QFileDialog
from PySide6.QtCore import Qt, Signal, Slot
from qasync import QEventLoop

from reversi.protocol.interface import EngineInterface
from reversi.protocol.constants import Command, Response
from .components.board import BoardWidget
from .components.scoreboard import ScoreboardWidget
from .components.persistence import PersistenceManager
from .components.replay import ReplayController
from .components import game_state_serializer
from reversi.engine.metadata import get_engine_metadata

class ReversiApp(QMainWindow):
    message_received = Signal(str)

    def __init__(self, engine: EngineInterface, board_size: int = 8):
        super().__init__()
        self.engine = engine
        self.board_size = board_size
        self.setWindowTitle(f"Reversi {board_size}x{board_size} (PySide6)")
        self.resize(1180, 900)

        # State
        self.current_turn = "BLACK"
        self.game_started = False
        self._score_black = 2
        self._score_white = 2
        self.undo_expect_updates = 0
        self.timeline = []
        self.current_valid_moves = []

        # Player configuration (will be managed by sidebar later)
        self.players = {
            "BLACK": {"name": "Human", "is_human": True},
            "WHITE": {"name": "Minimax", "is_human": False}
        }
        self.ai_engine_settings = {
            "WHITE": {"key": "minimax", "params": {"depth": 4}} # Placeholder
        }

        # Components
        self.persistence_manager = PersistenceManager(
            self,
            self.get_save_payload,
            self.load_game_data,
            self.log
        )

        self.replay_controller = ReplayController(
            self.apply_snapshot,
            lambda: len(self.timeline),
            lambda: self.game_started
        )

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
            #app_title {
                font-size: 32px;
                font-weight: 900;
                color: #1B5E20;
                margin-bottom: 5px;
            }
            #section_header {
                font-size: 11px;
                font-weight: bold;
                color: #888;
                margin-top: 15px;
                margin-bottom: 5px;
                letter-spacing: 1px;
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
                font-size: 10px;
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
            QPushButton:disabled {
                background-color: #f0f0f0;
                color: #bbbbbb;
                border: 1px solid #e0e0e0;
            }
            #action_button {
                font-size: 12px;
                min-height: 24px;
            }
            #primary_button {
                background-color: #2e7d32;
                color: white;
                border: none;
                font-size: 12px;
                min-height: 24px;
            }
            #primary_button:hover {
                background-color: #388e3c;
            }
            #primary_button:disabled {
                background-color: #a5d6a7;
                color: #ffffff;
            }
        """)

        sidebar = QWidget()
        sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)

        # 1. Header
        title = QLabel("REVERSI")
        title.setObjectName("app_title")
        sidebar_layout.addWidget(title)

        # 2. Game Settings Placeholder
        settings_header = QLabel("GAME SETTINGS")
        settings_header.setObjectName("section_header")
        sidebar_layout.addWidget(settings_header)

        settings_box = QWidget()
        settings_box.setMinimumHeight(80)
        settings_box.setStyleSheet("background: #e0e0e0; border-radius: 8px; border: 1px dashed #bbb;")
        sidebar_layout.addWidget(settings_box)

        sidebar_layout.addSpacing(10)

        # 3. Primary Actions
        self.btn_new_game = QPushButton("New Game")
        self.btn_new_game.setObjectName("primary_button")
        self.btn_new_game.clicked.connect(self.start_new_game)
        sidebar_layout.addWidget(self.btn_new_game)

        # 4. Secondary Actions (Grid)
        actions_grid = QWidget()
        actions_layout = QVBoxLayout(actions_grid)
        actions_layout.setContentsMargins(0, 5, 0, 5)
        actions_layout.setSpacing(8)

        row1 = QHBoxLayout()
        self.undo_btn = QPushButton("Undo")
        self.undo_btn.setObjectName("action_button")
        self.undo_btn.clicked.connect(self.undo_move)
        self.pass_btn = QPushButton("Pass")
        self.pass_btn.setObjectName("action_button")
        self.pass_btn.clicked.connect(self.pass_turn)
        row1.addWidget(self.undo_btn)
        row1.addWidget(self.pass_btn)

        row2 = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("action_button")
        self.save_btn.clicked.connect(self.persistence_manager.request_save)
        self.load_btn = QPushButton("Load")
        self.load_btn.setObjectName("action_button")
        self.load_btn.clicked.connect(self.persistence_manager.request_load)
        row2.addWidget(self.save_btn)
        row2.addWidget(self.load_btn)

        actions_layout.addLayout(row1)
        actions_layout.addLayout(row2)
        sidebar_layout.addWidget(actions_grid)

        # 5. Engine Log
        log_header = QLabel("ENGINE LOG")
        log_header.setObjectName("section_header")
        sidebar_layout.addWidget(log_header)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        sidebar_layout.addWidget(self.log_view, stretch=1)

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

        # Replay toolbar below board
        right_layout.addWidget(self.replay_controller)

        main_layout.addWidget(right_area, stretch=1)

        # Engine setup
        self.engine.set_callback(self.on_engine_message)
        self.message_received.connect(self.process_message)

        # Initial UI state update
        self.update_ui_state()

    def log(self, text):
        self.log_view.append(text)

    def on_engine_message(self, message):
        self.message_received.emit(message)

    @Slot(str)
    def process_message(self, message):
        parts = message.split()
        if not parts: return

        cmd = parts[0]

        # 1. Broad logging of engine communication
        if cmd in (Response.MOVE, Response.PASS, Response.READY, Response.RESULT):
            self.log(f"Engine: {message}")
        elif cmd == Response.ERROR:
            self.log(f"ERROR: {message}")
        elif cmd == Response.ANALYSIS:
            self.log(f"Engine: ANALYSIS received ({len(parts)-1} scores)")
        elif cmd == Response.INFO:
            # Info can be scores or other technical details
            if not any(k in message for k in ["SCORE_BLACK", "SCORE_WHITE"]):
                self.log(f"Engine: {message}")
        # OK and BOARD are typically not logged to keep entries meaningful

        # 2. Command processing
        if cmd == Response.MOVE or cmd == Response.PASS:
            self.current_valid_moves = []

        if cmd == Response.BOARD:
            if len(parts) >= 4:
                size = int(parts[1])
                turn = parts[2]
                state_str = parts[3]
                self.current_turn = turn
                self.update_board_ui(size, state_str)

                player = self.players[turn]
                self.scoreboard.set_status(turn, player["name"], player["is_human"])

                # If we are in the middle of an undo sequence, don't trigger AI turns until it's finished
                processed_undo = False
                if self.undo_expect_updates > 0:
                    self.undo_expect_updates -= 1
                    if self.undo_expect_updates > 0:
                        self.log("System: Waiting for second undo board update...")
                        return
                    self.log("System: Undo completed")
                    processed_undo = True
                    self.replay_controller.sync_index(max(0, len(self.timeline) - 1))

                # Capture timeline snapshot if game is active and we're not just reverting
                if self.game_started and not processed_undo:
                    snapshot = {
                        "index": len(self.timeline),
                        "board": state_str,
                        "current_player": turn,
                        "scores": {"BLACK": self._score_black, "WHITE": self._score_white}
                    }
                    self.timeline.append(snapshot)
                    self.replay_controller.sync_index(len(self.timeline) - 1)

                self.update_ui_state()

                if self.game_started and self.current_turn == "WHITE":
                    self.send_command(f"{Command.GENMOVE} WHITE")
                elif self.game_started and self.current_turn == "BLACK":
                    self.send_command(Command.VALID_MOVES)
                    self.send_command(f"{Command.ANALYZE} BLACK")

        elif cmd == Response.VALID_MOVES:
            moves = parts[1:]
            self.current_valid_moves = moves
            self.board_widget.set_valid_moves(moves)
            self.update_ui_state()

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
            self.update_ui_state()

    def pass_turn(self):
        if not self.game_started: return
        self.send_command(f"{Command.PASS} {self.current_turn}")
        self.log(f"GUI: {self.current_turn} passed")

    def get_save_payload(self) -> dict:
        snapshot = game_state_serializer.GameStateSnapshot(
            board_size=self.board_size,
            human_color="BLACK", # Simplified
            ai_color="WHITE",
            player_modes={k: ("human" if v["is_human"] else "engine") for k,v in self.players.items()},
            ai_engine_settings=self.ai_engine_settings,
            timeline=self.timeline
        )
        return game_state_serializer.serialize(snapshot)

    def load_game_data(self, data: dict):
        try:
            # Clear current board before loading
            self.board_widget.set_state({})
            self.board_widget.set_valid_moves([])
            self.board_widget.set_analysis({})

            loaded = game_state_serializer.deserialize(
                data,
                board_size=self.board_size,
                default_engine_provider=lambda key: {"key": key, "params": {}}, # Basic provider
            )

            self.timeline = loaded.timeline

            # Map player modes
            for color, mode in loaded.player_modes.items():
                self.players[color]["is_human"] = (mode == "human")

            self.ai_engine_settings = loaded.ai_engine_settings
            self.scoreboard.set_players(self.players["BLACK"]["name"], self.players["WHITE"]["name"])

            if self.timeline:
                last_snapshot = self.timeline[-1]
                # Check if game was already finished in the save file
                # If board is full or no moves, it might be over.
                # For now, let's assume if it was saved it might or might not be active.
                # Standard behavior: resume if not obviously finished.
                self.game_started = True

                # Apply last state
                self.apply_snapshot(len(self.timeline) - 1)

                # If human's turn, request valid moves to enable input
                if self.players[self.current_turn]["is_human"]:
                    self.send_command(Command.VALID_MOVES)

            self.log("System: Game loaded successfully")
            self.update_ui_state()
        except Exception as e:
            self.log(f"Error loading game: {e}")

    def apply_snapshot(self, index: int):
        if not (0 <= index < len(self.timeline)):
            return

        snapshot = self.timeline[index]
        self.replay_controller.sync_index(index)

        # Sync the engine state
        board_str = snapshot["board"]
        turn = snapshot["current_player"]

        # We tell the engine to FORCE set this board state
        self.send_command(f"{Command.BOARD} {self.board_size} {turn} {board_str}")

        # Update UI directly
        self.current_turn = turn
        self.update_board_ui(self.board_size, board_str)
        # Re-update player status and button states
        player = self.players[turn]
        self.scoreboard.set_status(turn, player["name"], player["is_human"])
        self.update_ui_state()

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
        self.timeline = []
        # Clear board display thoroughly
        self.board_widget.set_state({})
        self.board_widget.set_valid_moves([])
        self.board_widget.set_analysis({})

        self.send_command(f"{Command.INIT} {self.board_size}")
        self.send_command(Command.NEWGAME)
        self.log("Started New Game")
        self.update_ui_state()

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

        # Truncate timeline
        for _ in range(undo_count):
            if self.timeline:
                self.timeline.pop()

        for _ in range(undo_count):
            self.send_command(Command.UNDO)
        self.log(f"Undo requested ({undo_count} steps)")

    def update_ui_state(self):
        is_human_turn = self.players.get(self.current_turn, {}).get("is_human", False)
        has_moves = len(self.timeline) > 0
        is_undoing = self.undo_expect_updates > 0

        # Undo is allowed if game is active AND it's human's turn AND we have moves AND not processing another undo
        can_undo = self.game_started and is_human_turn and has_moves and not is_undoing
        self.undo_btn.setEnabled(can_undo)

        # Save is allowed if we have at least one move recorded
        self.save_btn.setEnabled(has_moves)

        # Pass is allowed if game is active AND it's human's turn AND human has NO legal moves
        can_pass = self.game_started and is_human_turn and (len(self.current_valid_moves) == 0) and not is_undoing
        self.pass_btn.setEnabled(can_pass)
        self.replay_controller.setEnabled(not self.game_started)
        self.replay_controller.update_status()

    def send_command(self, cmd):
        # Log move and analysis requests
        if cmd.startswith(Command.PLAY) or cmd.startswith(Command.GENMOVE) or cmd.startswith(Command.ANALYZE):
            self.log(f"GUI: Sending {cmd}")
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
