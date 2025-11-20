import random
from typing import Iterable, Optional, Tuple

from reversi.engine.base_engine import BaseEngine
from reversi.engine.board import Board


class TrivialEngine(BaseEngine):
    """Random-move engine used for testing and baseline comparisons."""

    def __init__(self, board_size: int = 8, think_delay: float = 0.2):
        super().__init__(board_size=board_size, think_delay=think_delay)

    def _pick_move(
        self,
        board_snapshot: Board,
        color: str,
        valid_moves: Iterable[Tuple[int, int]],
    ) -> Optional[Tuple[int, int]]:
        _ = board_snapshot, color  # unused for the random baseline
        valid_moves = list(valid_moves)
        return random.choice(valid_moves) if valid_moves else None
