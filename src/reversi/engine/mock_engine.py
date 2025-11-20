from typing import Iterable, Optional, Tuple

from reversi.engine.base_engine import BaseEngine
from reversi.engine.board import Board


class MockEngine(BaseEngine):
    """Deterministic, fast engine useful for UI smoke testing."""

    def __init__(self, board_size: int = 8, think_delay: float = 0.0):
        super().__init__(board_size=board_size, think_delay=think_delay)

    def _pick_move(
        self,
        board_snapshot: Board,
        color: str,
        valid_moves: Iterable[Tuple[int, int]],
    ) -> Optional[Tuple[int, int]]:
        _ = board_snapshot, color
        moves = list(valid_moves)
        return moves[0] if moves else None
