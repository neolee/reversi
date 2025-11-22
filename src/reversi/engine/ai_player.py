from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from reversi.engine.board import Board
from reversi.engine.registry import build_engine_instance


@dataclass
class EngineSpec:
    key: str
    label: str
    search_depth: int | None = None
    think_delay: float | None = 0.0
    options: dict | None = None


class EnginePlayer:
    def __init__(self, spec: EngineSpec, board_size: int):
        self.spec = spec
        self.board_size = board_size
        self._engine = self._build_engine()

    def _build_engine(self):
        options = self.spec.options or {}
        return build_engine_instance(
            self.spec.key,
            board_size=self.board_size,
            search_depth=self.spec.search_depth,
            think_delay=self.spec.think_delay,
            **options,
        )

    def choose_move(self, board: Board, color: str) -> Optional[Tuple[int, int]]:
        snapshot = board.clone()
        valid_moves = snapshot.get_valid_moves(color)
        if not valid_moves:
            return None
        move = self._engine._pick_move(snapshot, color, valid_moves)  # type: ignore[attr-defined]
        return move if move in valid_moves else valid_moves[0]


def board_from_state_string(board_size: int, state: str, current_player: str) -> Board:
    board = Board(board_size)
    for r in range(board_size):
        for c in range(board_size):
            idx = r * board_size + c
            piece = state[idx] if idx < len(state) else "."
            if piece == "B":
                board.grid[r][c] = Board.BLACK
            elif piece == "W":
                board.grid[r][c] = Board.WHITE
            else:
                board.grid[r][c] = None
    board.current_player = current_player
    return board
