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
from .controller import EngineBroker
from .state import GameState
from .styles import get_main_stylesheet

class ReversiApp(QMainWindow):
    def __init__(self, engine: EngineInterface, board_size: int = 8):
        super().__init__()
        self.broker = EngineBroker(engine)
        self.state = GameState(board_size=board_size)

        self.setWindowTitle(f"Reversi {board_size}x{board_size} (PySide6)")
        self.resize(1080, 900)

        # Components
        self.persistence_manager = PersistenceManager(
            self,
            self.get_save_payload,
            self.load_game_data,
            self.log
        )

        self.replay_controller = ReplayController(
            self.apply_snapshot,
            lambda: len(self.state.timeline),
            lambda: self.state.game_started
        )

        self._setup_ui()
        self._connect_signals()
        self.update_ui_state()

    def _setup_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("central_widget")
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.setStyleSheet(get_main_stylesheet())

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
        self.scoreboard.set_players(self.state.players["BLACK"]["name"], self.state.players["WHITE"]["name"])
        right_layout.addWidget(self.scoreboard)

        self.board_widget = BoardWidget(self.state.board_size)
        self.board_widget.clicked.connect(self.handle_board_click)
        right_layout.addWidget(self.board_widget, stretch=1)

        # Replay toolbar below board
        right_layout.addWidget(self.replay_controller)

        main_layout.addWidget(right_area, stretch=1)

    def _connect_signals(self):
        self.broker.message_logged.connect(self.log)
        self.broker.error_occurred.connect(lambda msg: self.log(f"ERROR: {msg}"))
        self.broker.board_received.connect(self.on_board_received)
        self.broker.valid_moves_received.connect(self.on_valid_moves_received)
        self.broker.analysis_received.connect(self.board_widget.set_analysis)
        self.broker.scores_received.connect(self.on_scores_received)
        self.broker.game_over.connect(self.on_game_over)

    def log(self, text):
        self.log_view.append(text)

    def on_board_received(self, size, turn, state_str):
        self.state.current_turn = turn
        self.state.current_valid_moves = []
        self.update_board_ui(size, state_str)

        player = self.state.players[turn]
        self.scoreboard.set_status(turn, player["name"], player["is_human"])

        # Undo sequence handling
        processed_undo = False
        if self.state.undo_expect_updates > 0:
            self.state.undo_expect_updates -= 1
            if self.state.undo_expect_updates > 0:
                self.log("System: Waiting for second undo board update...")
                return
            self.log("System: Undo completed")
            processed_undo = True
            self.replay_controller.sync_index(max(0, len(self.state.timeline) - 1))

        # Capture timeline snapshot if game is active and we're not just reverting
        if self.state.game_started and not processed_undo:
            snapshot = {
                "index": len(self.state.timeline),
                "board": state_str,
                "current_player": turn,
                "scores": {"BLACK": self.state.score_black, "WHITE": self.state.score_white}
            }
            self.state.timeline.append(snapshot)
            self.replay_controller.sync_index(len(self.state.timeline) - 1)

        self.update_ui_state()

        if self.state.game_started:
            if self.state.current_turn == "WHITE":
                self.send_command(f"{Command.GENMOVE} WHITE")
            elif self.state.current_turn == "BLACK":
                self.send_command(Command.VALID_MOVES)
                self.send_command(f"{Command.ANALYZE} BLACK")

    def on_valid_moves_received(self, moves):
        self.state.current_valid_moves = moves
        self.board_widget.set_valid_moves(moves)
        self.update_ui_state()

    def on_scores_received(self, black, white):
        if black != -1: self.state.score_black = black
        if white != -1: self.state.score_white = white
        self.scoreboard.update_scores(self.state.score_black, self.state.score_white)

    def on_game_over(self, winner):
        self.state.game_started = False
        self.log(f"Game Over: {winner}")
        self.scoreboard.set_status_text(f"GAME OVER: WINNER IS {winner}")
        self.board_widget.set_valid_moves([])
        self.board_widget.set_analysis({})
        self.update_ui_state()

    def pass_turn(self):
        if not self.state.game_started: return
        self.send_command(f"{Command.PASS} {self.state.current_turn}")
        self.log(f"GUI: {self.state.current_turn} passed")

    def get_save_payload(self) -> dict:
        snapshot = game_state_serializer.GameStateSnapshot(
            board_size=self.state.board_size,
            human_color="BLACK", # Simplified
            ai_color="WHITE",
            player_modes={k: ("human" if v["is_human"] else "engine") for k,v in self.state.players.items()},
            ai_engine_settings=self.state.ai_engine_settings,
            timeline=self.state.timeline
        )
        return game_state_serializer.serialize(snapshot)

    def load_game_data(self, data: dict):
        try:
            self.board_widget.set_state({})
            self.board_widget.set_valid_moves([])
            self.board_widget.set_analysis({})

            loaded = game_state_serializer.deserialize(
                data,
                board_size=self.state.board_size,
                default_engine_provider=lambda key: {"key": key, "params": {}},
            )

            self.state.timeline = loaded.timeline

            # Map player modes
            for color, mode in loaded.player_modes.items():
                self.state.players[color]["is_human"] = (mode == "human")

            self.state.ai_engine_settings = loaded.ai_engine_settings
            self.scoreboard.set_players(self.state.players["BLACK"]["name"], self.state.players["WHITE"]["name"])

            if self.state.timeline:
                self.state.game_started = True
                self.apply_snapshot(len(self.state.timeline) - 1)
                if self.state.players[self.state.current_turn]["is_human"]:
                    self.send_command(Command.VALID_MOVES)

            self.log("System: Game loaded successfully")
            self.update_ui_state()
        except Exception as e:
            self.log(f"Error loading game: {e}")

    def apply_snapshot(self, index: int):
        if not (0 <= index < len(self.state.timeline)):
            return

        snapshot = self.state.timeline[index]
        self.replay_controller.sync_index(index)

        board_str = snapshot["board"]
        turn = snapshot["current_player"]

        self.send_command(f"{Command.BOARD} {self.state.board_size} {turn} {board_str}")
        self.state.current_turn = turn
        self.update_board_ui(self.state.board_size, board_str)
        player = self.state.players[turn]
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
        self.state.score_black = black_count
        self.state.score_white = white_count
        self.scoreboard.update_scores(black_count, white_count)

    def handle_board_click(self, coord):
        if not self.state.game_started or self.state.current_turn != "BLACK":
            return
        self.send_command(f"{Command.PLAY} {coord}")

    def start_new_game(self):
        self.state.reset(self.state.board_size)
        self.board_widget.set_state({})
        self.board_widget.set_valid_moves([])
        self.board_widget.set_analysis({})

        self.send_command(f"{Command.INIT} {self.state.board_size}")
        self.send_command(Command.NEWGAME)
        self.log("Started New Game")
        self.update_ui_state()

    def undo_move(self):
        if not self.state.game_started:
            self.log("System: Cannot undo when game is not active.")
            return

        other_turn = "WHITE" if self.state.current_turn == "BLACK" else "BLACK"
        is_human_vs_ai = (self.state.players[self.state.current_turn]["is_human"] != self.state.players[other_turn]["is_human"])

        undo_count = 1
        if is_human_vs_ai and self.state.players[self.state.current_turn]["is_human"]:
            undo_count = 2

        self.state.undo_expect_updates = undo_count
        for _ in range(undo_count):
            if self.state.timeline:
                self.state.timeline.pop()

        for _ in range(undo_count):
            self.send_command(Command.UNDO)
        self.log(f"Undo requested ({undo_count} steps)")

    def update_ui_state(self):
        is_human_turn = self.state.players.get(self.state.current_turn, {}).get("is_human", False)
        has_moves = len(self.state.timeline) > 0
        is_undoing = self.state.undo_expect_updates > 0

        can_undo = self.state.game_started and is_human_turn and has_moves and not is_undoing
        self.undo_btn.setEnabled(can_undo)
        self.save_btn.setEnabled(has_moves)
        can_pass = self.state.game_started and is_human_turn and (len(self.state.current_valid_moves) == 0) and not is_undoing
        self.pass_btn.setEnabled(can_pass)
        self.replay_controller.setEnabled(not self.state.game_started)
        self.replay_controller.update_status()

    def send_command(self, cmd):
        if cmd.startswith(Command.PLAY) or cmd.startswith(Command.GENMOVE) or cmd.startswith(Command.ANALYZE):
            self.log(f"GUI: Sending {cmd}")
        self.broker.send_command(cmd)

    def closeEvent(self, event):
        self.broker.stop()
        super().closeEvent(event)

def run_app(engine: EngineInterface, board_size: int = 8):
    app = QApplication.instance() or QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    reversi_app = ReversiApp(engine, board_size)
    reversi_app.show()

    reversi_app.broker.start()

    with loop:
        loop.run_forever()
