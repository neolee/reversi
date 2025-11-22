import asyncio
import flet as ft
from reversi.protocol.interface import EngineInterface
from reversi.protocol.constants import Command, Response
from reversi.ui.components.board import BoardComponent
from reversi.ui.components.replay import ReplayController
from reversi.ui.components.persistence import PersistenceManager
from reversi.ui.components.scoreboard import ScoreboardComponent
from reversi.ui.components.controls import GameControlsComponent

class ReversiApp:
    def __init__(self, engine: EngineInterface, board_size: int = 8):
        self.engine = engine
        self.board_size = board_size
        self.engine.set_callback(self.handle_engine_message)
        self.engine_name = engine.__class__.__name__
        self.player_modes = {"BLACK": "human", "WHITE": "engine"}
        self.human_color = "BLACK"
        self.ai_color = "WHITE"
        self._engine_request_color: str | None = None

        # Components
        self.board_component = BoardComponent(
            board_size=board_size,
            on_click_callback=self.on_board_click
        )

        self.replay_controller = ReplayController(
            page_getter=lambda: getattr(self, "page", None),
            apply_snapshot_callback=self._apply_snapshot,
            get_timeline_len_callback=lambda: len(self.timeline),
            is_game_started_callback=lambda: self.game_started
        )

        self.persistence_manager = PersistenceManager(
            page_getter=lambda: getattr(self, "page", None),
            get_save_payload_callback=self._build_save_payload,
            load_game_data_callback=self._apply_loaded_data,
            log_callback=self.log
        )

        self.scoreboard_component = ScoreboardComponent()

        self.controls_component = GameControlsComponent(
            on_new_game=self.on_new_game,
            on_undo=self.on_undo,
            on_pass=self.on_pass,
            on_player_mode_change=self.on_player_mode_change,
            on_save=self.persistence_manager.request_save,
            on_load=self.persistence_manager.request_load
        )

        # UI State
        self.log_view = ft.ListView(expand=True, spacing=4, padding=0, auto_scroll=True)
        self.current_turn = "BLACK"
        self._update_primary_roles()
        self.game_started = False
        self.undo_expect_updates = 0
        self.board_wrapper = None
        self.latest_scores = {"BLACK": 2, "WHITE": 2}
        self._pending_status_message = None
        self.timeline: list[dict] = []
        self._pending_move_context: dict | None = None
        self._suppress_turn_requests = False
        self._suppress_recording = False

        # Layout Constants
        self.board_padding = 24
        self._last_viewport = (None, None)
        self._board_area_padding_h = 16.0
        self._board_area_padding_v = 16.0
        self._board_column_spacing = 16.0

    def main(self, page: ft.Page):
        self.page = page
        page.title = "Reversi"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window.width = 1180
        page.window.height = 900
        page.padding = 20

        self.persistence_manager.register_pickers(page.overlay)

        # Sidebar
        sidebar = self.controls_component.create_sidebar(self.log_view)

        # Board Area
        board_grid = self.board_component.create_board()
        scoreboard = self.scoreboard_component.create()
        replay_toolbar = self.replay_controller.create_toolbar()

        initial_board_size = self.board_size * self.board_component.cell_size + self.board_padding * 2
        self.board_wrapper = ft.Container(
            content=board_grid,
            width=initial_board_size,
            height=initial_board_size,
            padding=self.board_padding,
            alignment=ft.alignment.center,
            border_radius=24,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=["#0f3d14", "#145a1e"]
            ),
            shadow=ft.BoxShadow(
                blur_radius=25,
                spread_radius=2,
                color="rgba(0,0,0,0.25)",
                offset=ft.Offset(0, 12)
            )
        )

        self.board_stage = ft.Container(
            content=self.board_wrapper,
            alignment=ft.alignment.center,
            expand=True,
        )

        self.board_area = ft.Container(
            content=ft.Column(
                [scoreboard, self.board_stage, replay_toolbar],
                spacing=self._board_column_spacing,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                expand=True,
            ),
            alignment=ft.alignment.center,
            expand=True,
            padding=ft.padding.symmetric(
                horizontal=self._board_area_padding_h,
                vertical=self._board_area_padding_v,
            ),
            bgcolor="grey200"
        )

        # Layout
        page.add(
            ft.Row(
                [
                    sidebar,
                    ft.VerticalDivider(width=1),
                    self.board_area
                ],
                expand=True,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH
            )
        )

        page.update()
        self.adjust_board_size()

        self.reset_board_ui()

        # Start Engine
        self.engine.start()
        self.log("System: Engine started")

        # Auto-start new game
        self.on_new_game(None)

        page.run_task(self._monitor_viewport)

    def on_player_mode_change(self, color: str, mode: str):
        if color not in self.player_modes:
            return
        if mode not in ("human", "engine"):
            return
        previous = self.player_modes.get(color)
        if previous == mode:
            return
        self.player_modes[color] = mode
        self.controls_component.set_player_mode(color, mode)
        self._update_primary_roles()
        self.log(
            f"Settings: {self._color_label(color)} controlled by {self._player_label(color)}"
        )
        if self.game_started and color == self.current_turn:
            self.controls_component.set_pass_disabled(not self._is_human_player(color))
            self._drive_turn_loop()

    def adjust_board_size(self, width: float | None = None, height: float | None = None):
        if not getattr(self, "page", None) or not self.board_wrapper:
            return

        if width is None:
            width = getattr(self.page, "window_width", None) or self.page.width
        if height is None:
            height = getattr(self.page, "window_height", None) or self.page.height
        if width is None or height is None:
            return

        prev_w, prev_h = self._last_viewport
        if prev_w == width and prev_h == height:
            return
        self._last_viewport = (width, height)

        sidebar_container = self.controls_component.container
        sidebar_width = float(sidebar_container.width) if sidebar_container and sidebar_container.width else 0.0
        page_padding = float(getattr(self.page, "padding", 0) or 0)
        divider_width = 1.0
        safety_margin = 36.0
        available_width = max(
            200.0,
            float(width)
            - page_padding * 2
            - sidebar_width
            - divider_width
            - self._board_area_padding_h * 2
            - safety_margin,
        )

        column_gap_total = self._board_column_spacing * 2
        vertical_chrome = (
            page_padding * 2
            + self._board_area_padding_v * 2
            + column_gap_total
            + float(self.scoreboard_component.height)
            + float(self.replay_controller.toolbar_height)
        )
        available_height = max(200.0, float(height) - vertical_chrome)
        board_pixel = min(available_width, available_height)
        usable_space = max(100.0, board_pixel - 2 * self.board_padding)
        new_cell_size = max(32.0, usable_space / self.board_size)

        current_width = float(self.board_wrapper.width or 0)
        current_height = float(self.board_wrapper.height or 0)
        current_cell_size = self.board_component.cell_size

        if abs(new_cell_size - current_cell_size) < 0.5 and abs(current_width - board_pixel) < 0.5 and abs(current_height - board_pixel) < 0.5:
            return

        self.board_wrapper.width = board_pixel
        self.board_wrapper.height = board_pixel
        self.board_wrapper.update()
        self.board_component.resize_cells(new_cell_size)

    async def _monitor_viewport(self):
        await asyncio.sleep(0.2)
        prev_w, prev_h = self._last_viewport
        while True:
            current_w = getattr(self.page, "window_width", None) or self.page.width
            current_h = getattr(self.page, "window_height", None) or self.page.height
            if current_w and current_h:
                if current_w != prev_w or current_h != prev_h:
                    self.adjust_board_size(current_w, current_h)
                    prev_w, prev_h = current_w, current_h
            await asyncio.sleep(0.25)

    def reset_board_ui(self):
        self.board_component.reset()
        self.current_turn = "BLACK"
        self.scoreboard_component.set_status("Waiting for engine...")
        self.controls_component.set_pass_disabled(True)
        self._engine_request_color = None

    def log(self, message: str):
        self.log_view.controls.append(
            ft.Text(message, font_family="monospace", size=10, selectable=True)
        )
        self.log_view.update()

    def handle_engine_message(self, message: str):
        self.log(f"Engine: {message}")

        parts = message.split()
        cmd = parts[0]

        if cmd == Response.BOARD:
            # BOARD <size> <current_player> <state_string>
            if len(parts) > 3:
                size = int(parts[1])
                current_player = parts[2]
                state_str = parts[3]
                self.current_turn = current_player
                self.update_board_from_state(size, state_str)
                self.update_scores_from_state(size, state_str, current_player)
                self._record_board_snapshot(state_str, current_player)
                if self._pending_status_message:
                    self.scoreboard_component.set_status(self._pending_status_message)
                    self._pending_status_message = None
                elif self.game_started:
                    self.scoreboard_component.set_status(
                        f"{self._color_label(self.current_turn)} ({self._player_label(self.current_turn)}) to move"
                    )

                if not self._is_human_player(self.current_turn):
                    self.controls_component.set_pass_disabled(True)

                # Handle Undo Sequence
                if self.undo_expect_updates > 0:
                    self.undo_expect_updates -= 1
                    if self.undo_expect_updates > 0:
                        self.log("System: Waiting for second undo...")
                        return
                    # If we finished undoing, we fall through to normal logic
                    # which will trigger VALID_MOVES for human or GENMOVE for AI

                self._drive_turn_loop()

        elif cmd == Response.VALID_MOVES:
            # VALID_MOVES <c1> <c2> ...
            moves = parts[1:]
            self.board_component.highlight_valid_moves(moves)
            if self.game_started and self._is_human_player(self.current_turn):
                no_moves = len(moves) == 0
                self.controls_component.set_pass_disabled(not no_moves)
                status_text = (
                    f"{self._color_label(self.current_turn)} ({self._player_label(self.current_turn)}) has no moves. Tap Pass."
                    if no_moves
                    else f"{self._color_label(self.current_turn)} ({self._player_label(self.current_turn)}) to move"
                )
                self.scoreboard_component.set_status(status_text)
            else:
                self.controls_component.set_pass_disabled(True)

        elif cmd == Response.MOVE:
            if len(parts) > 1:
                coord = parts[1]
                move_color = self._engine_request_color or self._opponent_color(self.current_turn)
                self._pending_move_context = {
                    "color": move_color,
                    "coord": coord,
                    "type": "move",
                }
                self._engine_request_color = None

        elif cmd == Response.RESULT:
            winner = parts[1]
            self.log(f"GAME OVER: Winner is {winner}")
            self.game_started = False
            self.replay_controller.update_status()
            self.controls_component.set_pass_disabled(True)
            if winner == "DRAW":
                self.scoreboard_component.set_status(
                    f"Draw! {self.latest_scores['BLACK']} - {self.latest_scores['WHITE']}",
                    color="#1b5e20"
                )
            else:
                pretty = self._color_label(winner)
                self.scoreboard_component.set_status(
                    f"{pretty} wins! {self.latest_scores['BLACK']} - {self.latest_scores['WHITE']}",
                    color="#b71c1c"
                )

        elif cmd == Response.PASS:
            color = parts[1] if len(parts) > 1 else "UNKNOWN"
            opponent = "WHITE" if color == "BLACK" else "BLACK"
            if not self._pending_move_context or self._pending_move_context.get("type") != "pass":
                self._pending_move_context = {"color": color, "coord": None, "type": "pass"}
            self._pending_status_message = f"{self._color_label(color)} passes. {self._color_label(opponent)} to move."

    def update_board_from_state(self, size: int, state_str: str):
        if size != self.board_size:
            self.log(f"Error: Board size mismatch {size} vs {self.board_size}")
            return

        for r in range(size):
            for c in range(size):
                idx = r * size + c
                if idx < len(state_str):
                    char = state_str[idx]
                    coord = f"{chr(65+c)}{r+1}"
                    if char == "B":
                        self.board_component.update_piece(coord, "BLACK")
                    elif char == "W":
                        self.board_component.update_piece(coord, "WHITE")
                    else:
                        self.board_component.update_piece(coord, None)

    def on_new_game(self, e):
        self.log("GUI: Starting New Game...")
        self.game_started = True
        self.replay_controller.reset()
        self._reset_timeline()
        self.reset_board_ui()
        self.engine.send_command(Command.NEWGAME)

    def on_undo(self, e):
        self.log("GUI: Sending UNDO")
        undo_count = 1
        opponent = self._opponent_color(self.current_turn)
        if self.game_started and self._is_human_player(self.current_turn) and self._is_engine_player(opponent):
            undo_count = 2
        self.undo_expect_updates = undo_count
        for _ in range(undo_count):
            self.engine.send_command(Command.UNDO)

    def on_board_click(self, coord):
        if not self.game_started:
            return

        if not self._is_human_player(self.current_turn):
            self.log("Warning: Not your turn!")
            return

        if not self.board_component.is_valid_move(coord):
            self.log(f"Warning: Invalid move {coord}. Please choose a highlighted cell.")
            return

        self._pending_move_context = {"color": self.current_turn, "coord": coord, "type": "move"}
        self.log(f"GUI: Clicked {coord}")
        self.board_component.highlight_valid_moves([])
        self.engine.send_command(f"{Command.PLAY} {coord}")

    def on_pass(self, e):
        if not self.game_started or not self._is_human_player(self.current_turn):
            return
        self.log("GUI: Requesting PASS")
        self.controls_component.set_pass_disabled(True)
        self._pending_move_context = {"color": self.current_turn, "coord": None, "type": "pass"}
        self.engine.send_command(f"{Command.PASS} {self.current_turn}")

    def update_scores_from_state(self, size: int, state_str: str, current_player: str):
        black = state_str.count("B")
        white = state_str.count("W")
        self.latest_scores = {"BLACK": black, "WHITE": white}
        self.scoreboard_component.update_scores(black, white)

    def _color_label(self, color: str) -> str:
        if color == "BLACK":
            return "Black"
        if color == "WHITE":
            return "White"
        return color.capitalize()

    def _drive_turn_loop(self):
        if not self.game_started or self._suppress_turn_requests:
            return
        if self._is_engine_player(self.current_turn):
            self.log(
                f"System: {self._player_label(self.current_turn)} turn, requesting move..."
            )
            self._engine_request_color = self.current_turn
            self.engine.send_command(f"{Command.GENMOVE} {self.current_turn}")
        else:
            self.log("System: Human Turn, requesting valid moves...")
            self.engine.send_command(f"{Command.VALID_MOVES} {self.current_turn}")

    def _record_board_snapshot(self, state_str: str, current_player: str):
        if self._suppress_recording:
            return
        if self.undo_expect_updates > 0:
            if self.timeline:
                self.timeline.pop()
                self.replay_controller.sync_index(max(0, len(self.timeline) - 1))
            return
        move = None
        if self._pending_move_context:
            move = self._pending_move_context.copy()
        snapshot = {
            "index": len(self.timeline),
            "board": state_str,
            "current_player": current_player,
            "move": move,
            "scores": dict(self.latest_scores),
        }
        self.timeline.append(snapshot)
        self.replay_controller.sync_index(len(self.timeline) - 1)
        self._pending_move_context = None

    def _reset_timeline(self):
        self.timeline = []
        self._pending_move_context = None
        self._suppress_recording = False
        self.replay_controller.reset()

    def _apply_snapshot(self, index: int):
        if not self.timeline:
            return
        index = max(0, min(index, len(self.timeline) - 1))
        snapshot = self.timeline[index]

        self.update_board_from_state(self.board_size, snapshot["board"])
        self.update_scores_from_state(self.board_size, snapshot["board"], snapshot.get("current_player", "BLACK"))
        self.current_turn = snapshot.get("current_player", "BLACK")
        self.board_component.highlight_valid_moves([])

        if not self.game_started:
            self.scoreboard_component.set_status(f"Replay: move {index} / {len(self.timeline) - 1}")

        self.replay_controller.sync_index(index)

    def _build_save_payload(self):
        return {
            "version": 1,
            "engine": self.engine_name,
            "board_size": self.board_size,
            "human_color": self.human_color,
            "ai_color": self.ai_color,
            "player_modes": dict(self.player_modes),
            "timeline": self.timeline,
        }

    def _apply_loaded_data(self, data: dict):
        if data.get("version") != 1:
            raise ValueError("Unsupported save file version")
        if data.get("board_size") != self.board_size:
            raise ValueError("Board size mismatch in save file")
        timeline = data.get("timeline", [])
        if not timeline:
            raise ValueError("Save file is missing timeline data")
        self.timeline = []
        for entry in timeline:
            move = entry.get("move")
            cloned = {
                "index": entry.get("index", len(self.timeline)),
                "board": entry.get("board", ""),
                "current_player": entry.get("current_player", "BLACK"),
                "move": dict(move) if isinstance(move, dict) else None,
                "scores": dict(entry.get("scores", {})),
            }
            self.timeline.append(cloned)
        self._pending_move_context = None
        self.replay_controller.stop_autoplay()
        loaded_modes = data.get("player_modes")
        if isinstance(loaded_modes, dict):
            merged = {"BLACK": "human", "WHITE": "engine"}
            merged.update({k: v for k, v in loaded_modes.items() if k in merged and v in ("human", "engine")})
            self.player_modes = merged
        else:
            fallback_human = data.get("human_color", "BLACK")
            fallback_ai = data.get("ai_color", "WHITE")
            self.player_modes = {
                "BLACK": "human" if fallback_human == "BLACK" else "engine",
                "WHITE": "human" if fallback_human == "WHITE" else "engine",
            }
            if fallback_ai and fallback_ai != fallback_human:
                self.player_modes[fallback_ai] = "engine"
        self._update_primary_roles()
        self.controls_component.set_player_mode("BLACK", self.player_modes["BLACK"])
        self.controls_component.set_player_mode("WHITE", self.player_modes["WHITE"])

        self._suppress_turn_requests = True
        self._suppress_recording = True
        self.game_started = True
        self.engine.send_command(Command.NEWGAME)
        for snapshot in self.timeline[1:]:
            move = snapshot.get("move")
            if not move:
                continue
            if move.get("type") == "move" and move.get("coord"):
                self.engine.send_command(f"{Command.PLAY} {move['coord']}")
            elif move.get("type") == "pass":
                color = move.get("color", self.current_turn)
                self.engine.send_command(f"{Command.PASS} {color}")
        self._suppress_recording = False
        self._suppress_turn_requests = False
        self._apply_snapshot(len(self.timeline) - 1)
        self._drive_turn_loop()
        self.replay_controller.update_status()

    def _is_human_player(self, color: str) -> bool:
        return self.player_modes.get(color) == "human"

    def _is_engine_player(self, color: str) -> bool:
        return self.player_modes.get(color) == "engine"

    def _player_label(self, color: str) -> str:
        return "Human" if self._is_human_player(color) else self.engine_name

    def _opponent_color(self, color: str) -> str:
        return "WHITE" if color == "BLACK" else "BLACK"

    def _primary_color_for_mode(self, mode: str) -> str | None:
        for color in ("BLACK", "WHITE"):
            if self.player_modes.get(color) == mode:
                return color
        return None

    def _update_primary_roles(self):
        self.human_color = self._primary_color_for_mode("human") or "BLACK"
        self.ai_color = self._primary_color_for_mode("engine") or "WHITE"
