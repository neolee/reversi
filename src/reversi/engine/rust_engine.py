from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional, Tuple

from reversi.engine.base_engine import BaseEngine
from reversi.engine.board import Board as PyBoard

try:
    from rust_reversi import (
        AlphaBetaSearch,
        Board as RustBoard,
        MctsSearch,
        PieceEvaluator,
        ThunderSearch,
        Turn,
        WinrateEvaluator,
    )
except ImportError as exc:  # pragma: no cover - handled at runtime
    raise ImportError("RustReversiEngine requires the 'rust-reversi' package") from exc


class BaseRustSearchEngine(BaseEngine, ABC):
    """Shared plumbing for engines backed by the rust-reversi package."""

    SUPPORTED_SIZE = 8

    def __init__(self, board_size: int = 8, think_delay: float = 0.05):
        if board_size != self.SUPPORTED_SIZE:
            raise ValueError("Rust engines currently support 8x8 boards only")
        super().__init__(board_size=board_size, think_delay=think_delay)
        self._piece_evaluator = PieceEvaluator()
        self._winrate_evaluator = WinrateEvaluator()

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
        search: Any = self._create_search()

        move_index: Optional[int]
        try:
            move_index = search.get_move(rust_board)
        except Exception:
            move_index = None

        if move_index is None or not self._is_index_valid(move_index):
            return valid[0]

        move = self._index_to_coord(move_index)
        return move if move in valid else valid[0]

    @abstractmethod
    def _create_search(self) -> Any:
        """Return a rust_reversi searcher ready to evaluate positions."""

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


class RustAlphaBetaEngine(BaseRustSearchEngine):
    """Deterministic alpha-beta search implemented in Rust."""

    def __init__(
        self,
        board_size: int = 8,
        search_depth: int = 5,
        think_delay: float = 0.05,
        win_score: int = 100_000,
    ):
        super().__init__(board_size=board_size, think_delay=think_delay)
        self.search_depth = max(1, search_depth)
        self._win_score = win_score

    def _create_search(self):
        return AlphaBetaSearch(self._piece_evaluator, self.search_depth, self._win_score)


class RustThunderEngine(BaseRustSearchEngine):
    """Epsilon-greedy playout searcher (Thunder)."""

    def __init__(
        self,
        board_size: int = 8,
        think_delay: float = 0.05,
        playouts: int = 400,
        epsilon: float = 0.1,
    ):
        super().__init__(board_size=board_size, think_delay=think_delay)
        self.playouts = max(1, playouts)
        self.epsilon = max(0.0, min(1.0, epsilon))

    def _create_search(self):
        return ThunderSearch(self._winrate_evaluator, self.playouts, self.epsilon)


class RustMctsEngine(BaseRustSearchEngine):
    """Monte Carlo Tree Search variant from rust-reversi."""

    def __init__(
        self,
        board_size: int = 8,
        think_delay: float = 0.05,
        playouts: int = 800,
        exploration_constant: float = 1.4,
        expand_threshold: int = 8,
    ):
        super().__init__(board_size=board_size, think_delay=think_delay)
        self.playouts = max(1, playouts)
        self.exploration_constant = max(1e-6, exploration_constant)
        self.expand_threshold = max(1, expand_threshold)

    def _create_search(self):
        return MctsSearch(
            self.playouts,
            self.exploration_constant,
            self.expand_threshold,
        )