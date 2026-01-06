from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QRadialGradient, QBrush, QPen, QFont

class BoardWidget(QWidget):
    clicked = Signal(str)  # Emits coordinate like "D4"

    def __init__(self, board_size: int = 8):
        super().__init__()
        self.board_size = board_size
        self.cell_size = 60
        self.board_padding = 20  # Space between grid and board edge
        self.board_state = {}  # coord -> color ("BLACK", "WHITE")
        self.valid_moves = set()
        self.analysis_scores = {} # coord -> score string
        self.setMouseTracking(True)
        # Allow control to fill available space
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_state(self, state: dict):
        self.board_state = state
        self.update()

    def set_valid_moves(self, moves: list):
        self.valid_moves = set(moves)
        self.update()

    def set_analysis(self, scores: dict):
        self.analysis_scores = scores
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()

    def _get_board_rect(self):
        # Calculate board rect centered in the widget
        width = self.width()
        height = self.height()
        side = min(width, height) * 0.95

        # grid side is smaller than full board side by padding
        grid_side = side - (self.board_padding * 2)
        cell_size = grid_side / self.board_size

        offset_x = (width - side) / 2
        offset_y = (height - side) / 2
        return QRectF(offset_x, offset_y, side, side), cell_size

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        board_rect, self.cell_size = self._get_board_rect()

        # 1. Draw outer background (The "Stage")
        painter.save()
        # Draw a large soft outer shadow
        for i in range(15, 0, -1):
            alpha = int(30 * (1 - i/15))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, alpha))
            painter.drawRoundedRect(board_rect.adjusted(-i, -i, i, i), 20, 20)

        # Draw board base
        painter.setBrush(QColor("#0d3011")) # Deep green base
        painter.setPen(QPen(QColor(255, 255, 255, 30), 2))
        painter.drawRoundedRect(board_rect, 12, 12)
        painter.restore()

        # 2. Draw each cell (Offset by board_padding)
        grid_origin_x = board_rect.left() + self.board_padding
        grid_origin_y = board_rect.top() + self.board_padding

        for r in range(self.board_size):
            for c in range(self.board_size):
                x = grid_origin_x + c * self.cell_size
                y = grid_origin_y + r * self.cell_size
                rect = QRectF(x, y, self.cell_size, self.cell_size)

                coord = f"{chr(65+c)}{r+1}"

                # Draw cell background
                painter.save()
                base_color = QColor("#1B5E20") if (r + c) % 2 == 0 else QColor("#215732")
                painter.setBrush(base_color)
                painter.setPen(QPen(QColor(0, 0, 0, 40), 1))
                painter.drawRect(rect)
                painter.restore()

                # Draw pieces
                if coord in self.board_state:
                    self._draw_piece(painter, rect, self.board_state[coord])

                # Draw valid move markers (The Glow)
                if coord in self.valid_moves:
                    self._draw_marker(painter, rect)

                # Draw analysis scores
                if coord in self.analysis_scores:
                    self._draw_analysis(painter, rect, self.analysis_scores[coord])

    def _draw_piece(self, painter, rect, color):
        painter.save()
        margin = self.cell_size * 0.12
        piece_rect = rect.adjusted(margin, margin, -margin, -margin)

        # Shadow moved to bottom-right (simulating top-left light source)
        offset = self.cell_size * 0.04
        shadow_rect = piece_rect.translated(offset, offset)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 150))
        painter.drawEllipse(shadow_rect)

        if color == "BLACK":
            # Soft grey-black with very subtle gradient
            grad = QRadialGradient(piece_rect.center(), piece_rect.width())
            grad.setColorAt(0, QColor("#444444"))
            grad.setColorAt(1, QColor("#2a2a2a"))
            painter.setBrush(grad)
            painter.setPen(QPen(QColor("#1a1a1a"), 1.0))
        else:
            # Soft off-white with very subtle gradient
            grad = QRadialGradient(piece_rect.center(), piece_rect.width())
            grad.setColorAt(0, QColor("#f5f5f5"))
            grad.setColorAt(1, QColor("#e0e0e0"))
            painter.setBrush(grad)
            painter.setPen(QPen(QColor("#cccccc"), 1.5))

        painter.drawEllipse(piece_rect)
        painter.restore()

    def _draw_marker(self, painter, rect):
        painter.save()
        # Keep large radius but control the blur area
        radius = self.cell_size * 0.45
        center = rect.center()

        glow = QRadialGradient(center, radius)
        # Large central area with deep charcoal/grey
        glow.setColorAt(0, QColor(0, 0, 0, 200))
        # Transition to a dark forest green that matches board tones
        glow.setColorAt(0.8, QColor(33, 87, 50, 150))
        # Keep the edge sharp but slightly feathered for blending
        glow.setColorAt(0.9, QColor(33, 87, 50, 100))
        glow.setColorAt(1.0, QColor(33, 87, 50, 50))

        painter.setBrush(glow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, radius, radius)
        painter.restore()

    def _draw_analysis(self, painter, rect, score):
        painter.save()
        # Larger font size for better visibility
        font_size = max(8, int(self.cell_size * 0.22))
        font = QFont("Arial", font_size)
        font.setBold(True)
        painter.setFont(font)

        score_text = str(score)

        # Enhanced shadow for the larger text
        painter.setPen(QColor(0, 0, 0, 180))
        painter.drawText(rect.adjusted(1, 1, 1, 1), Qt.AlignmentFlag.AlignCenter, score_text)

        # Center-aligned bright foreground
        painter.setPen(QColor(222, 222, 222, 220))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, score_text)
        painter.restore()

    def mousePressEvent(self, event):
        board_rect, _ = self._get_board_rect()
        grid_origin_x = board_rect.left() + self.board_padding
        grid_origin_y = board_rect.top() + self.board_padding

        rel_x = event.position().x() - grid_origin_x
        rel_y = event.position().y() - grid_origin_y

        grid_size = self.cell_size * self.board_size
        if 0 <= rel_x < grid_size and 0 <= rel_y < grid_size:
            c = int(rel_x / self.cell_size)
            r = int(rel_y / self.cell_size)
            if 0 <= r < self.board_size and 0 <= c < self.board_size:
                coord = f"{chr(65+c)}{r+1}"
                self.clicked.emit(coord)
