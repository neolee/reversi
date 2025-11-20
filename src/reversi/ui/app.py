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
        self.current_turn = "BLACK" # Track whose turn it is for simple UI updates

    def main(self, page: ft.Page):
        self.page = page
        page.title = "Reversi"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window.width = 800
        page.window.height = 800

        # Header
        header = ft.Row(
            [
                ft.Text("Reversi", size=30, weight=ft.FontWeight.BOLD),
                ft.ElevatedButton("New Game", on_click=self.on_new_game),
                ft.ElevatedButton("Undo", on_click=self.on_undo),
                ft.ElevatedButton("AI Move", on_click=self.on_gen_move),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        # Board
        self.board_grid = self.create_board()

        # Log Area
        log_container = ft.Container(
            content=self.log_view,
            border=ft.border.all(1, "grey400"),
            border_radius=5,
            padding=10,
            expand=True
        )

        # Layout
        page.add(
            ft.Column(
                [
                    header,
                    ft.Divider(),
                    ft.Row([self.board_grid], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Divider(),
                    ft.Text("Protocol Log:"),
                    log_container
                ],
                expand=True
            )
        )

        self.reset_board_ui() # Initialize starting position - NOW SAFE TO CALL

        # Start Engine
        self.engine.start()
        self.log("System: Engine started")

    def create_board(self):
        # Grid
        rows = []
        for r in range(self.board_size):
            row_controls = []
            for c in range(self.board_size):
                coord = f"{chr(65+c)}{r+1}"

                # Piece container (circle)
                piece = ft.Container(
                    width=40,
                    height=40,
                    border_radius=20,
                    bgcolor=None, # Transparent initially
                )

                cell = ft.Container(
                    content=piece,
                    width=50,
                    height=50,
                    bgcolor="green700",
                    border=ft.border.all(1, "black"),
                    on_click=lambda e, coord=coord: self.on_board_click(coord),
                    alignment=ft.alignment.center,
                    data=coord # Store coord in data
                )

                self.board_cells[coord] = piece
                row_controls.append(cell)
            rows.append(ft.Row(row_controls, spacing=0))
        return ft.Column(rows, spacing=0)

    def update_piece(self, coord, color):
        if coord in self.board_cells:
            piece = self.board_cells[coord]
            if color == "BLACK":
                piece.bgcolor = "black"
            elif color == "WHITE":
                piece.bgcolor = "white"
            else:
                piece.bgcolor = None
            piece.update()

    def reset_board_ui(self):
        # Clear all
        for coord in self.board_cells:
            self.update_piece(coord, None)

        # Initial position (center 4 pieces)
        mid = self.board_size // 2
        # Coordinates are 1-based, so mid is the lower index of the center pair
        # e.g. size 8, mid=4. Center is (4,4), (5,5), (4,5), (5,4) -> D4, E5, D5, E4

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
        self.log_view.controls.append(ft.Text(message, font_family="monospace"))
        self.page.update()

    def handle_engine_message(self, message: str):
        self.log(f"Engine: {message}")

        parts = message.split()
        cmd = parts[0]

        if cmd == Response.MOVE:
            # MOVE <coord>
            if len(parts) > 1:
                coord = parts[1]
                # For now, just place the piece for the current turn
                # In a real app, we need to know whose turn it is or get full board state
                self.update_piece(coord, self.current_turn)
                self.toggle_turn()

        elif cmd == Response.OK:
            # If we just sent a PLAY command, we should update the board too
            # But for now, let's assume the engine sends MOVE back or we update optimistically
            pass

        # elif cmd == Response.NEWGAME: # Or if we reset
        #      self.reset_board_ui()

    def toggle_turn(self):
        self.current_turn = "WHITE" if self.current_turn == "BLACK" else "BLACK"

    def on_new_game(self, e):
        self.log("GUI: Sending NEWGAME")
        self.reset_board_ui()
        self.engine.send_command(Command.NEWGAME)

    def on_undo(self, e):
        self.log("GUI: Sending UNDO")
        self.engine.send_command(Command.UNDO)

    def on_gen_move(self, e):
        self.log("GUI: Sending GENMOVE")
        self.engine.send_command(Command.GENMOVE)

    def on_board_click(self, coord):
        self.log(f"GUI: Clicked {coord}")
        # Optimistic update for human move
        self.update_piece(coord, self.current_turn)
        self.toggle_turn()
        self.engine.send_command(f"{Command.PLAY} {coord}")
