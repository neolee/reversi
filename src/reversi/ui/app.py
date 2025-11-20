import asyncio

import flet as ft
from reversi.protocol.interface import EngineInterface
from reversi.protocol.constants import Command, Response

class ReversiApp:
    def __init__(self, engine: EngineInterface, board_size: int = 8):
        self.engine = engine
        self.board_size = board_size
        self.engine.set_callback(self.handle_engine_message)
        self.log_view = ft.Column(scroll=ft.ScrollMode.ALWAYS, height=200)
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

    def main(self, page: ft.Page):
        self.page = page
        page.title = "Reversi"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window.width = 1000
        page.window.height = 800
        page.padding = 20

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
        self.sidebar = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Reversi", size=30, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Text("Game Settings", size=20, weight=ft.FontWeight.BOLD),
                    ft.RadioGroup(
                        content=ft.Column([
                            ft.Radio(value="BLACK", label="Play as Black (First)"),
                            ft.Radio(value="WHITE", label="Play as White (Second)")
                        ]),
                        on_change=self.on_color_change,
                        value="BLACK"
                    ),
                    ft.ElevatedButton("Start New Game", on_click=self.on_new_game, width=200),
                    ft.Divider(),
                    ft.Text("Controls", size=20, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton("Undo", on_click=self.on_undo, width=200),
                    ft.Divider(),
                    ft.Text("Engine Log", size=16, weight=ft.FontWeight.BOLD),
                    log_container
                ],
                spacing=10,
                expand=True
            ),
            width=300,
            padding=10,
            bgcolor="grey50"
        )

        # Board Area
        self.board_grid = self.create_board()
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

        self.board_area = ft.Container(
            content=self.board_wrapper,
            alignment=ft.alignment.center,
            expand=True,
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
        available_width = max(200.0, float(width) - sidebar_width - 80)
        available_height = max(200.0, float(height) - 120)
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
        # Reset all highlights first
        for coord, cell in self.cell_containers.items():
            cell.border = ft.border.all(1, "black")
            cell.bgcolor = self.cell_base_colors.get(coord, "#1B5E20")
            cell.shadow = None
            marker = self.highlight_markers.get(coord)
            if marker:
                marker.opacity = 0
                marker.update()
            cell.update()
        
        # Highlight valid moves
        for coord in moves:
            if coord in self.cell_containers:
                marker = self.highlight_markers.get(coord)
                if marker:
                    marker.opacity = 1
                    marker.update()
                self.cell_containers[coord].update()

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

    def log(self, message: str):
        self.log_view.controls.append(ft.Text(message, font_family="monospace", size=10))
        self.log_view.scroll_to(offset=-1, duration=100) # Auto scroll to bottom
        self.page.update()

    def handle_engine_message(self, message: str):
        self.log(f"Engine: {message}")

        parts = message.split()
        cmd = parts[0]

        if cmd == Response.MOVE:
            # MOVE <coord>
            # Engine made a move. Board update will follow usually, or we request it.
            # But our engine sends BOARD update after move automatically now.
            pass

        elif cmd == Response.BOARD:
            # BOARD <size> <current_player> <state_string>
            if len(parts) > 3:
                size = int(parts[1])
                current_player = parts[2]
                state_str = parts[3]
                self.current_turn = current_player
                self.update_board_from_state(size, state_str)
                
                # Handle Undo Sequence
                if self.undo_expect_updates > 0:
                    self.undo_expect_updates -= 1
                    if self.undo_expect_updates > 0:
                        self.log("System: Waiting for second undo...")
                        return
                    # If we finished undoing, we fall through to normal logic
                    # which will trigger VALID_MOVES for human or GENMOVE for AI
                
                # Game Logic Loop
                if self.game_started:
                    if self.current_turn == self.ai_color:
                        # AI's turn
                        self.log("System: AI Turn, requesting move...")
                        self.engine.send_command(f"{Command.GENMOVE} {self.ai_color}")
                    else:
                        # Human's turn
                        self.log("System: Human Turn, requesting valid moves...")
                        self.engine.send_command(f"{Command.VALID_MOVES} {self.human_color}")

        elif cmd == Response.VALID_MOVES:
            # VALID_MOVES <c1> <c2> ...
            moves = parts[1:]
            self.highlight_valid_moves(moves)
            
        elif cmd == Response.RESULT:
            winner = parts[1]
            self.log(f"GAME OVER: Winner is {winner}")
            self.game_started = False

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
        self.reset_board_ui()
        self.engine.send_command(Command.NEWGAME)
        
        # If AI is Black (First), we need to trigger it.
        # But NEWGAME response is OK. Engine doesn't send BOARD automatically on NEWGAME usually?
        # Let's check LocalEngine. It sends OK then emit_board_update.
        # So handle_engine_message will get BOARD and trigger the loop.
        pass

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

        self.log(f"GUI: Clicked {coord}")
        # Clear highlights immediately so the newly placed stone doesn't overlap
        self.highlight_valid_moves([])
        self.engine.send_command(f"{Command.PLAY} {coord}")
