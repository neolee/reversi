import asyncio
import json
from datetime import datetime
from typing import cast
from urllib.parse import quote

import flet as ft
from reversi.protocol.interface import EngineInterface
from reversi.protocol.constants import Command, Response

class ReversiApp:
    def __init__(self, engine: EngineInterface, board_size: int = 8):
        self.engine = engine
        self.board_size = board_size
        self.engine.set_callback(self.handle_engine_message)
        self.engine_name = engine.__class__.__name__
        self.log_view = ft.ListView(expand=True, spacing=4, padding=0, auto_scroll=True)
        self.board_grid = None
        self.board_cells = {} # Map coord -> Container
        self.cell_containers = {} # Map coord -> Cell Container (for highlighting)
        self.cell_base_colors = {}
        self.highlight_markers = {}
        self.current_turn = "BLACK" # Track whose turn it is for simple UI updates
        self.human_color = "BLACK" # Default human color
        self.ai_color = "WHITE"
        self.game_started = False
        self.undo_expect_updates = 0 # Counter to suppress auto-moves during undo sequence
        self.board_wrapper = None
        self.cell_size = 60
        self.board_padding = 24
        self._last_viewport = (None, None)
        self.pass_button = None
        self.black_score_text = None
        self.white_score_text = None
        self.status_text = None
        self.latest_scores = {"BLACK": 2, "WHITE": 2}
        self._pending_status_message = None
        self._current_valid_moves: list[str] = []
        self.timeline: list[dict] = []
        self._pending_move_context: dict | None = None
        self._suppress_turn_requests = False
        self._suppress_recording = False
        self.replay_index = 0
        self.replay_playing = False
        self._replay_task: asyncio.Task | None = None
        self.replay_status_text: ft.Text | None = None
        self.replay_buttons: dict[str, ft.IconButton] = {}
        self.save_picker: ft.FilePicker | None = None
        self.load_picker: ft.FilePicker | None = None
        self.color_selector: ft.RadioGroup | None = None
        self._scoreboard_height = 82
        self._replay_toolbar_height = 58
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
        self.save_picker = ft.FilePicker(on_result=self._handle_save_dialog)
        self.load_picker = ft.FilePicker(on_result=self._handle_load_dialog)
        page.overlay.extend([self.save_picker, self.load_picker])

        # Log Area
        log_container = ft.Container(
            content=self.log_view,
            border=ft.border.all(1, "grey400"),
            border_radius=5,
            padding=5,
            expand=True,
            bgcolor="grey100"
        )
        
        # Sidebar
        self.pass_button = ft.ElevatedButton(
            "Pass Turn",
            on_click=self.on_pass,
            disabled=True,
            expand=1
        )
        self.color_selector = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="BLACK", label="Play as Black (First)"),
                ft.Radio(value="WHITE", label="Play as White (Second)")
            ]),
            on_change=self.on_color_change,
            value="BLACK"
        )
        control_row = ft.Row(
            [
                ft.ElevatedButton("Undo", on_click=self.on_undo, expand=1),
                self.pass_button
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            spacing=10
        )
        save_row = ft.Row(
            [
                ft.ElevatedButton("Save", on_click=self.on_save_game, expand=1),
                ft.ElevatedButton("Load", on_click=self.on_load_game, expand=1)
            ],
            spacing=10
        )
        self.sidebar = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Reversi", size=30, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Text("Game Settings", size=20, weight=ft.FontWeight.BOLD),
                    self.color_selector,
                    ft.ElevatedButton("Start New Game", on_click=self.on_new_game, width=200),
                    ft.Divider(),
                    ft.Text("Controls", size=20, weight=ft.FontWeight.BOLD),
                    control_row,
                    save_row,
                    ft.Divider(),
                    ft.Text("Engine Log", size=16, weight=ft.FontWeight.BOLD),
                    log_container
                ],
                spacing=10,
                expand=True,
            ),
            width=300,
            padding=10,
            bgcolor="grey50"
        )

        # Board Area
        self.board_grid = self.create_board()
        self.scoreboard = self.create_scoreboard()
        self.replay_toolbar = self.create_replay_toolbar()
        initial_board_size = self.board_size * self.cell_size + self.board_padding * 2
        self.board_wrapper = ft.Container(
            content=self.board_grid,
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
                [self.scoreboard, self.board_stage, self.replay_toolbar],
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
                    self.sidebar,
                    ft.VerticalDivider(width=1),
                    self.board_area
                ],
                expand=True,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH
            )
        )

        page.update()
        self.adjust_board_size()

        self.reset_board_ui() # Initialize starting position

        # Start Engine
        self.engine.start()
        self.log("System: Engine started")
        
        # Auto-start new game
        self.on_new_game(None)

        page.run_task(self._monitor_viewport)

    def on_color_change(self, e):
        self.human_color = e.control.value
        self.ai_color = "WHITE" if self.human_color == "BLACK" else "BLACK"
        self.log(f"Settings: Human is {self.human_color}")

    def create_board(self):
        # Grid
        rows = []
        for r in range(self.board_size):
            row_controls = []
            for c in range(self.board_size):
                coord = f"{chr(65+c)}{r+1}"
                piece_size = int(self.cell_size * 0.72)
                base_color = "#1B5E20" if (r + c) % 2 == 0 else "#215732"
                piece = ft.Container(
                    width=piece_size,
                    height=piece_size,
                    border_radius=piece_size / 2,
                    bgcolor=None,
                )

                marker_size = max(12, int(self.cell_size * 0.5))
                marker = ft.Container(
                    width=marker_size,
                    height=marker_size,
                    border_radius=marker_size / 2,
                    bgcolor="rgba(235,235,235,0.88)",
                    shadow=ft.BoxShadow(
                        blur_radius=10,
                        spread_radius=1,
                        color="rgba(255,255,255,0.55)",
                        offset=ft.Offset(0, 0)
                    ),
                    opacity=0,
                    animate_opacity=300
                )

                stack = ft.Stack(
                    [piece, marker],
                    alignment=ft.alignment.center
                )

                cell = ft.Container(
                    content=stack,
                    width=self.cell_size,
                    height=self.cell_size,
                    bgcolor=base_color,
                    border=ft.border.all(1, "black"),
                    on_click=lambda e, coord=coord: self.on_board_click(coord),
                    alignment=ft.alignment.center,
                    data=coord # Store coord in data
                )

                self.board_cells[coord] = piece
                self.cell_containers[coord] = cell
                self.cell_base_colors[coord] = base_color
                self.highlight_markers[coord] = marker
                row_controls.append(cell)
            rows.append(ft.Row(row_controls, spacing=0, tight=True))
        return ft.Column(rows, spacing=0)

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

        sidebar_width = float(self.sidebar.width or 0)
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
            + float(self._scoreboard_height)
            + float(self._replay_toolbar_height)
        )
        available_height = max(200.0, float(height) - vertical_chrome)
        board_pixel = min(available_width, available_height)
        usable_space = max(100.0, board_pixel - 2 * self.board_padding)
        new_cell_size = max(32.0, usable_space / self.board_size)

        current_width = float(self.board_wrapper.width or 0)
        current_height = float(self.board_wrapper.height or 0)
        if abs(new_cell_size - self.cell_size) < 0.5 and abs(current_width - board_pixel) < 0.5 and abs(current_height - board_pixel) < 0.5:
            return

        self.cell_size = new_cell_size
        self.board_wrapper.width = board_pixel
        self.board_wrapper.height = board_pixel
        self.board_wrapper.update()
        self.apply_cell_size()


    def apply_cell_size(self):
        if not self.board_cells:
            return

        piece_size = max(12, int(self.cell_size * 0.72))
        for coord, cell in self.cell_containers.items():
            cell.width = self.cell_size
            cell.height = self.cell_size
            piece = self.board_cells[coord]
            piece.width = piece_size
            piece.height = piece_size
            piece.border_radius = piece_size / 2
            marker = self.highlight_markers.get(coord)
            if marker:
                marker_size = max(12, int(self.cell_size * 0.5))
                marker.width = marker_size
                marker.height = marker_size
                marker.border_radius = marker_size / 2

        if self.board_grid:
            self.board_grid.update()

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

    def update_piece(self, coord, color):
        if coord in self.board_cells:
            piece = self.board_cells[coord]
            if color == "BLACK":
                piece.bgcolor = "#0f0f0f"
                piece.gradient = ft.RadialGradient(
                    radius=1.2,
                    colors=["#2f2f2f", "#060606"]
                )
                piece.border = ft.border.all(1, "#4f4f4f")
                piece.shadow = ft.BoxShadow(
                    blur_radius=20,
                    spread_radius=1,
                    color="rgba(0,0,0,0.55)",
                    offset=ft.Offset(0, 6)
                )
            elif color == "WHITE":
                piece.bgcolor = "#f4f4f4"
                piece.gradient = ft.RadialGradient(
                    radius=1.2,
                    colors=["#ffffff", "#d5d5d5"]
                )
                piece.border = ft.border.all(1, "#c5c5c5")
                piece.shadow = ft.BoxShadow(
                    blur_radius=16,
                    spread_radius=1,
                    color="rgba(0,0,0,0.35)",
                    offset=ft.Offset(0, 4)
                )
            else:
                piece.bgcolor = None
                piece.gradient = None
                piece.border = None
                piece.shadow = None
            piece.update()

    def highlight_valid_moves(self, moves):
        self._current_valid_moves = list(moves)
        move_set = set(moves)
        for coord, cell in self.cell_containers.items():
            cell.border = ft.border.all(1, "black")
            cell.bgcolor = self.cell_base_colors.get(coord, "#1B5E20")
            cell.shadow = None
            marker = self.highlight_markers.get(coord)
            if marker:
                marker.opacity = 1 if coord in move_set else 0
        if self.board_grid:
            self.board_grid.update()

    def reset_board_ui(self):
        # Clear all
        for coord in self.board_cells:
            self.update_piece(coord, None)
        
        # Clear highlights
        self.highlight_valid_moves([])

        # Initial position (center 4 pieces)
        mid = self.board_size // 2
        c1 = chr(65 + mid - 1) # D
        c2 = chr(65 + mid)     # E
        r1 = mid               # 4
        r2 = mid + 1           # 5

        self.update_piece(f"{c1}{r1}", "WHITE")
        self.update_piece(f"{c2}{r2}", "WHITE")
        self.update_piece(f"{c2}{r1}", "BLACK")
        self.update_piece(f"{c1}{r2}", "BLACK")
        self.current_turn = "BLACK"
        self.set_status("Waiting for engine...")
        if self.pass_button:
            self.pass_button.disabled = True
            self.pass_button.update()

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
                    self.set_status(self._pending_status_message)
                    self._pending_status_message = None
                elif self.game_started:
                    self.set_status(f"{self._color_label(self.current_turn)} to move")

                if self.pass_button and self.current_turn != self.human_color:
                    self.pass_button.disabled = True
                    self.pass_button.update()
                
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
            self.highlight_valid_moves(moves)
            if self.pass_button:
                if self.game_started and self.current_turn == self.human_color:
                    no_moves = len(moves) == 0
                    self.pass_button.disabled = not no_moves
                    status_text = f"{self._color_label(self.human_color)} has no moves. Tap Pass." if no_moves else f"{self._color_label(self.human_color)} to move"
                    self.set_status(status_text)
                else:
                    self.pass_button.disabled = True
                self.pass_button.update()
            
        elif cmd == Response.MOVE:
            if len(parts) > 1:
                coord = parts[1]
                self._pending_move_context = {
                    "color": self.ai_color,
                    "coord": coord,
                    "type": "move",
                }

        elif cmd == Response.RESULT:
            winner = parts[1]
            self.log(f"GAME OVER: Winner is {winner}")
            self.game_started = False
            self._update_replay_status()
            if self.pass_button:
                self.pass_button.disabled = True
                self.pass_button.update()
            if winner == "DRAW":
                self.set_status(
                    f"Draw! {self.latest_scores['BLACK']} - {self.latest_scores['WHITE']}",
                    color="#1b5e20"
                )
            else:
                pretty = self._color_label(winner)
                self.set_status(
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
                        self.update_piece(coord, "BLACK")
                    elif char == "W":
                        self.update_piece(coord, "WHITE")
                    else:
                        self.update_piece(coord, None)

    def on_new_game(self, e):
        self.log("GUI: Starting New Game...")
        self.game_started = True
        self._update_replay_status()
        self._stop_replay_autoplay()
        self._reset_timeline()
        self.reset_board_ui()
        self.engine.send_command(Command.NEWGAME)

    def on_undo(self, e):
        self.log("GUI: Sending UNDO")
        
        # Determine how many undos we need
        # If playing against AI and it's Human's turn, we need to undo AI's move AND Human's move (2 steps)
        # If it's AI's turn (rare, maybe AI is thinking), we might just undo Human's move (1 step)
        undo_count = 1
        if self.game_started and self.current_turn == self.human_color:
             undo_count = 2
        
        self.undo_expect_updates = undo_count
        
        # Send commands
        for _ in range(undo_count):
            self.engine.send_command(Command.UNDO)

    def on_board_click(self, coord):
        if not self.game_started:
            return
            
        if self.current_turn != self.human_color:
            self.log("Warning: Not your turn!")
            return

        if self._current_valid_moves and coord not in self._current_valid_moves:
            self.log("Warning: Invalid move, choose a highlighted square.")
            return

        self._pending_move_context = {"color": self.human_color, "coord": coord, "type": "move"}
        self.log(f"GUI: Clicked {coord}")
        # Clear highlights immediately so the newly placed stone doesn't overlap
        self.highlight_valid_moves([])
        self.engine.send_command(f"{Command.PLAY} {coord}")

    def on_pass(self, e):
        if not self.game_started or self.current_turn != self.human_color:
            return
        self.log("GUI: Requesting PASS")
        if self.pass_button:
            self.pass_button.disabled = True
            self.pass_button.update()
        self._pending_move_context = {"color": self.human_color, "coord": None, "type": "pass"}
        self.engine.send_command(f"{Command.PASS} {self.human_color}")

    def create_scoreboard(self):
        self.black_score_text = ft.Text("● Black 2", size=22, weight=ft.FontWeight.BOLD, color="#111111")
        self.white_score_text = ft.Text("○ White 2", size=22, weight=ft.FontWeight.BOLD, color="#444444")
        self.status_text = ft.Text("Waiting for engine...", size=13, color="#333333", weight=ft.FontWeight.BOLD)

        header_row = ft.Row(
            [
                ft.Text("BLACK", size=11, color="#666666"),
                self.status_text,
                ft.Text("WHITE", size=11, color="#666666")
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        score_row = ft.Row(
            [self.black_score_text, ft.Container(width=12), self.white_score_text],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        return ft.Container(
            content=ft.Column(
                [header_row, score_row],
                spacing=4,
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH
            ),
            padding=ft.padding.symmetric(vertical=6, horizontal=14),
            bgcolor="#f9f9f9",
            border_radius=14,
            border=ft.border.all(1, "#e0e0e0"),
            shadow=ft.BoxShadow(
                blur_radius=6,
                color="rgba(0,0,0,0.08)",
                offset=ft.Offset(0, 3)
            ),
            height=self._scoreboard_height,
            alignment=ft.alignment.center
        )

    def update_scores_from_state(self, size: int, state_str: str, current_player: str):
        black = state_str.count("B")
        white = state_str.count("W")
        self.latest_scores = {"BLACK": black, "WHITE": white}
        if self.black_score_text and self.white_score_text:
            self.black_score_text.value = f"● Black {black}"
            self.white_score_text.value = f"○ White {white}"
            self.black_score_text.update()
            self.white_score_text.update()

    def set_status(self, message: str, color: str = "#333333"):
        if self.status_text:
            self.status_text.value = message
            self.status_text.color = color
            self.status_text.update()

    def _color_label(self, color: str) -> str:
        if color == "BLACK":
            return "Black"
        if color == "WHITE":
            return "White"
        return color.capitalize()

    def _drive_turn_loop(self):
        if not self.game_started or self._suppress_turn_requests:
            return
        if self.current_turn == self.ai_color:
            self.log("System: AI Turn, requesting move...")
            self.engine.send_command(f"{Command.GENMOVE} {self.ai_color}")
        else:
            self.log("System: Human Turn, requesting valid moves...")
            self.engine.send_command(f"{Command.VALID_MOVES} {self.human_color}")

    def _record_board_snapshot(self, state_str: str, current_player: str):
        if self._suppress_recording:
            return
        if self.undo_expect_updates > 0:
            if self.timeline:
                self.timeline.pop()
                self.replay_index = max(0, len(self.timeline) - 1)
                self._update_replay_status()
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
        self.replay_index = len(self.timeline) - 1
        self._pending_move_context = None
        self._update_replay_status()

    def _reset_timeline(self):
        self.timeline = []
        self._pending_move_context = None
        self.replay_index = 0
        self.replay_playing = False
        self._suppress_recording = False
        self._stop_replay_autoplay()
        self._update_replay_status()

    def create_replay_toolbar(self):
        self.replay_status_text = ft.Text("Replay 0 / 0", size=12, color="#333333")
        self.replay_buttons = {
            "start": ft.IconButton(icon="first_page", on_click=self.on_replay_start, tooltip="Jump to start"),
            "prev": ft.IconButton(icon="chevron_left", on_click=self.on_replay_prev, tooltip="Step back"),
            "play": ft.IconButton(icon="play_arrow", on_click=self.on_replay_play_pause, tooltip="Play/Pause replay"),
            "next": ft.IconButton(icon="chevron_right", on_click=self.on_replay_next, tooltip="Step forward"),
            "end": ft.IconButton(icon="last_page", on_click=self.on_replay_end, tooltip="Jump to end"),
        }
        toolbar = ft.Row(
            [
                self.replay_buttons["start"],
                self.replay_buttons["prev"],
                self.replay_buttons["play"],
                self.replay_buttons["next"],
                self.replay_buttons["end"],
                ft.Container(width=16),
                self.replay_status_text,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=6,
        )
        container = ft.Container(
            content=toolbar,
            padding=ft.padding.symmetric(vertical=6, horizontal=16),
            bgcolor="#f1f1f1",
            border_radius=12,
            border=ft.border.all(1, "#dcdcdc"),
            height=self._replay_toolbar_height,
            alignment=ft.alignment.center
        )
        self._update_replay_status()
        return container

    def _apply_snapshot(self, index: int):
        if not self.timeline:
            return
        index = max(0, min(index, len(self.timeline) - 1))
        snapshot = self.timeline[index]
        self.replay_index = index
        self.update_board_from_state(self.board_size, snapshot["board"])
        self.update_scores_from_state(self.board_size, snapshot["board"], snapshot.get("current_player", "BLACK"))
        self.current_turn = snapshot.get("current_player", "BLACK")
        self.highlight_valid_moves([])
        if not self.game_started:
            self.set_status(f"Replay: move {index} / {len(self.timeline) - 1}")
        self._update_replay_status()

    def on_replay_start(self, e):
        if self.game_started or not self.timeline:
            return
        self._stop_replay_autoplay()
        self._apply_snapshot(0)

    def on_replay_prev(self, e):
        if self.game_started or not self.timeline:
            return
        self._stop_replay_autoplay()
        self._apply_snapshot(max(0, self.replay_index - 1))

    def on_replay_next(self, e):
        if self.game_started or not self.timeline:
            return
        self._stop_replay_autoplay()
        self._apply_snapshot(min(len(self.timeline) - 1, self.replay_index + 1))

    def on_replay_end(self, e):
        if self.game_started or not self.timeline:
            return
        self._stop_replay_autoplay()
        self._apply_snapshot(len(self.timeline) - 1)

    def on_replay_play_pause(self, e):
        if self.game_started or not self.timeline:
            return
        if self.replay_playing:
            self._stop_replay_autoplay()
        else:
            self._start_replay_autoplay()

    def _start_replay_autoplay(self):
        if self.replay_playing or not self.timeline:
            return
        self.replay_playing = True
        self._update_replay_play_button()
        if getattr(self, "page", None):
            self._replay_task = cast(asyncio.Task, self.page.run_task(self._replay_autoplay))
        else:
            self._replay_task = asyncio.create_task(self._replay_autoplay())

    def _stop_replay_autoplay(self):
        if self._replay_task and not self._replay_task.done():
            self._replay_task.cancel()
        self._replay_task = None
        if self.replay_playing:
            self.replay_playing = False
            self._update_replay_play_button()

    async def _replay_autoplay(self):
        try:
            while self.replay_playing and self.replay_index < len(self.timeline) - 1:
                await asyncio.sleep(1.0)
                self._apply_snapshot(self.replay_index + 1)
            self.replay_playing = False
            self._update_replay_play_button()
        except asyncio.CancelledError:
            pass

    def _update_replay_play_button(self):
        play_btn = self.replay_buttons.get("play")
        if play_btn:
            play_btn.icon = "pause" if self.replay_playing else "play_arrow"
            if getattr(play_btn, "page", None):
                play_btn.update()

    def _update_replay_status(self):
        total = len(self.timeline)
        status = f"Replay {self.replay_index} / {max(total - 1, 0)}" if total else "Replay 0 / 0"
        if self.replay_status_text:
            self.replay_status_text.value = status
            if getattr(self.replay_status_text, "page", None):
                self.replay_status_text.update()
        disabled = self.game_started or total == 0
        for btn in self.replay_buttons.values():
            btn.disabled = disabled
            if getattr(btn, "page", None):
                btn.update()

    def on_save_game(self, e):
        if not self.timeline:
            self.log("Warning: Nothing to save yet. Play or load a game first.")
            return
        if not self.save_picker:
            return
        self.log(f"GUI: Save requested (timeline entries: {len(self.timeline)})")
        default_name = f"reversi-{datetime.now():%Y%m%d-%H%M%S}.json"
        self.save_picker.save_file(file_name=default_name, allowed_extensions=["json"])
        if getattr(self, "page", None):
            self.page.update()

    def _handle_save_dialog(self, e: ft.FilePickerResultEvent):
        if not e.path and not e.files:
            self.log("Save canceled")
            return
        payload = self._build_save_payload()
        if e.path:
            try:
                self._save_game_to_path(e.path, payload)
                self.log(f"Saved game to {e.path}")
            except Exception as exc:
                self.log(f"Error saving game: {exc}")
            return

        file_name = e.files[0].name if e.files else f"reversi-{datetime.now():%Y%m%d-%H%M%S}.json"
        self._download_payload(payload, file_name)
        self.log(f"Saved game as download {file_name}")

    def _save_game_to_path(self, path: str, payload: dict | None = None):
        if payload is None:
            payload = self._build_save_payload()
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)

    def _build_save_payload(self):
        return {
            "version": 1,
            "engine": self.engine_name,
            "board_size": self.board_size,
            "human_color": self.human_color,
            "ai_color": self.ai_color,
            "timeline": self.timeline,
        }

    def _download_payload(self, payload: dict, file_name: str):
        if not getattr(self, "page", None):
            return
        json_str = json.dumps(payload, indent=2)
        data_url = "data:application/json;charset=utf-8," + quote(json_str)
        self.page.launch_url(data_url, web_window_name=file_name)

    def on_load_game(self, e):
        if not self.load_picker:
            return
        self.log("GUI: Load requested")
        self.load_picker.pick_files(allow_multiple=False, allowed_extensions=["json"])
        if getattr(self, "page", None):
            self.page.update()

    def _handle_load_dialog(self, e: ft.FilePickerResultEvent):
        if not e.files:
            self.log("Load canceled")
            return
        file_info = e.files[0]
        if file_info.path:
            try:
                self._load_game_from_path(file_info.path)
                self.log(f"Loaded game from {file_info.path}")
            except Exception as exc:
                self.log(f"Error loading game: {exc}")
            return
        file_bytes = getattr(file_info, "bytes", None)
        if file_bytes:
            try:
                self._load_game_from_bytes(file_bytes)
                display_name = file_info.name or "selected file"
                self.log(f"Loaded game from {display_name} (download)")
            except Exception as exc:
                self.log(f"Error loading game: {exc}")
            return
        self.log("Error loading game: picker returned no usable data")

    def _load_game_from_path(self, path: str):
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self._apply_loaded_payload(data)

    def _load_game_from_bytes(self, data_bytes: bytes):
        decoded = data_bytes.decode("utf-8")
        data = json.loads(decoded)
        self._apply_loaded_payload(data)

    def _apply_loaded_payload(self, data: dict):
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
        self._stop_replay_autoplay()
        self.human_color = data.get("human_color", "BLACK")
        self.ai_color = data.get("ai_color", "WHITE")
        if self.color_selector:
            self.color_selector.value = self.human_color
            self.color_selector.update()
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
        self._update_replay_status()

