import asyncio
import flet as ft

class BoardComponent:
    def __init__(self, board_size: int, on_click_callback, cell_size: float = 60):
        self.board_size = board_size
        self.on_click = on_click_callback
        self.cell_size = cell_size

        # State
        self.board_cells = {} # Map coord -> Piece Container
        self.cell_containers = {} # Map coord -> Cell Container
        self.cell_base_colors = {}
        self.highlight_markers = {}
        self.board_grid = None
        self._current_valid_moves = []

    def create_board(self) -> ft.Column:
        rows = []
        for r in range(self.board_size):
            row_controls = []
            for c in range(self.board_size):
                coord = f"{chr(65+c)}{r+1}"
                piece_size = int(self.cell_size * 0.72)
                base_color = "#1B5E20" if (r + c) % 2 == 0 else "#215732"

                # Piece (Disc)
                piece = ft.Container(
                    width=piece_size,
                    height=piece_size,
                    border_radius=piece_size / 2,
                    bgcolor=None,
                )

                # Valid Move Marker
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
                    on_click=lambda e, coord=coord: self.on_click(coord),
                    alignment=ft.alignment.center,
                    data=coord
                )

                self.board_cells[coord] = piece
                self.cell_containers[coord] = cell
                self.cell_base_colors[coord] = base_color
                self.highlight_markers[coord] = marker
                row_controls.append(cell)
            rows.append(ft.Row(row_controls, spacing=0, tight=True))

        self.board_grid = ft.Column(rows, spacing=0)
        return self.board_grid

    def update_piece(self, coord: str, color: str | None):
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

    def highlight_valid_moves(self, moves: list[str]):
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

    def is_valid_move(self, coord: str) -> bool:
        return coord in self._current_valid_moves

    def resize_cells(self, new_cell_size: float):
        self.cell_size = new_cell_size
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

    def reset(self):
        # Clear all pieces
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
