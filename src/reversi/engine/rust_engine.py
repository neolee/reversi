from __future__ import annotations

from typing import Iterable, Optional, Tuple

from reversi.engine.base_engine import BaseEngine
from reversi.engine.board import Board as PyBoard

try:
    from rust_reversi import AlphaBetaSearch, Board as RustBoard, PieceEvaluator, Turn
except ImportError as exc:  # pragma: no cover - handled at runtime
    raise ImportError("RustReversiEngine requires the 'rust-reversi' package") from exc


class RustReversiEngine(BaseEngine):
    """Wrapper around the rust-reversi alpha-beta searcher."""

    def __init__(
        self,
        board_size: int = 8,
        search_depth: int = 5,
        think_delay: float = 0.05,
        win_score: int = 100_000,
    ):
        if board_size != 8:
            raise ValueError("RustReversiEngine currently supports 8x8 boards only")

        super().__init__(board_size=board_size, think_delay=think_delay)
        self.search_depth = max(1, search_depth)
        self._win_score = win_score
        self._evaluator = PieceEvaluator()

    def _pick_move(
        self,
        board_snapshot: PyBoard,
        color: str,
        valid_moves: Iterable[Tuple[int, int]],
    ) -> Optional[Tuple[int, int]]:
        valid = list(valid_moves)
        if not valid:
            return None

        rust_board = self._build_rust_board(board_snapshot, color)
        search = AlphaBetaSearch(self._evaluator, self.search_depth, self._win_score)

        move_index: Optional[int]
        try:
            move_index = search.get_move(rust_board)
        except Exception:
            move_index = None

        if move_index is None or not self._is_index_valid(move_index):
            return valid[0]

        move = self._index_to_coord(move_index)
        return move if move in valid else valid[0]

    # ------------------------------------------------------------------
    # Rust board helpers
    # ------------------------------------------------------------------
    def _build_rust_board(self, board_snapshot: PyBoard, color: str) -> RustBoard:
        board_line = self._board_to_line(board_snapshot)
        rust_board = RustBoard()
        turn = Turn.BLACK if color == PyBoard.BLACK else Turn.WHITE
        rust_board.set_board_str(board_line, turn)
        return rust_board

    def _board_to_line(self, board_snapshot: PyBoard) -> str:
        chars = []
        for r in range(self.board_size):
            for c in range(self.board_size):
                piece = board_snapshot.get_piece(r, c)
                if piece == PyBoard.BLACK:
                    chars.append("X")
                elif piece == PyBoard.WHITE:
                    chars.append("O")
                else:
                    chars.append("-")
        return "".join(chars)

    def _is_index_valid(self, index: int) -> bool:
        return 0 <= index < self.board_size * self.board_size

    def _index_to_coord(self, index: int) -> Tuple[int, int]:
        row, col = divmod(index, self.board_size)
        return row, col
