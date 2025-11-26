from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from concurrent.futures import TimeoutError
from typing import Any, Iterable, Optional, Tuple

from reversi.engine.base_engine import BaseEngine
from reversi.engine.board import Board as PyBoard
from reversi.engine.process_pool import get_executor, shutdown_executor

logger = logging.getLogger(__name__)

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


def _run_rust_analysis(engine_cls, init_kwargs, board_snapshot, color):
    """Worker function to run analysis in a separate process."""
    try:
        # Re-instantiate engine
        engine = engine_cls(**init_kwargs)
        # Inject the board state
        engine.board = board_snapshot
        # Call the synchronous implementation
        return engine._analyze_impl(color)
    except Exception:
        logger.exception("Error in Rust analysis worker")
        raise


class BaseRustEngine(BaseEngine, ABC):
    """Shared plumbing for engines backed by the rust-reversi package."""

    SUPPORTED_SIZE = 8

    def __init__(self, board_size: int = 8, think_delay: float = 0.05):
        if board_size != self.SUPPORTED_SIZE:
            raise ValueError("Rust engines currently support 8x8 boards only")
        super().__init__(board_size=board_size, think_delay=think_delay)
        self._piece_evaluator = PieceEvaluator()
        self._winrate_evaluator = WinrateEvaluator()

    def stop(self):
        super().stop()
        try:
            shutdown_executor(wait=True)
        except Exception:
            logger.exception("Error shutting down Rust process pool")

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

    def analyze(self, color: str) -> list[tuple[tuple[int, int], float]]:
        """
        Run analysis in a separate process to avoid blocking the UI thread.
        This is necessary because rust-reversi functions might hold the GIL.
        """
        executor = get_executor()

        # Prepare init kwargs for reconstruction
        init_kwargs = self._get_init_kwargs()

        # If iterative deepening updated search_depth, pass it along
        if hasattr(self, "search_depth"):
            init_kwargs["search_depth"] = self.search_depth

        future = executor.submit(
            _run_rust_analysis,
            self.__class__,
            init_kwargs,
            self.board,  # Board is picklable
            color,
        )

        # Wait for result (releases GIL) while allowing cancellation
        try:
            while True:
                try:
                    return future.result(timeout=0.1)
                except TimeoutError:
                    if not self._analyzing:
                        future.cancel()
                        return []
        except Exception:
            logger.exception("Error waiting for Rust analysis result")
            return []

    def _analyze_impl(self, color: str) -> list[tuple[tuple[int, int], float]]:
        """Synchronous implementation of analysis logic."""
        valid_moves = self.board.get_valid_moves(color)
        if not valid_moves:
            return []

        results = []
        search = self._create_search()

        for r, c in valid_moves:
            # Clone and play move
            board_snapshot = self.board.clone()
            board_snapshot.play_move(r, c, color)

            # Determine next player and check for game over/pass
            next_player = board_snapshot.current_player

            # If next player has no moves
            if not board_snapshot.has_valid_move(next_player):
                # Try to pass
                if board_snapshot.pass_turn(next_player):
                    # Passed. Now it is 'color' turn again (or whoever is next)
                    pass
                else:
                    # Game Over
                    score = self._get_terminal_score(board_snapshot, color)
                    results.append(((r, c), score))
                    continue

            # Build Rust board for the current state (after move and potential pass)
            current_turn_color = board_snapshot.current_player
            if not board_snapshot.has_valid_move(current_turn_color):
                score = self._get_terminal_score(board_snapshot, color)
                results.append(((r, c), score))
                continue
            rust_board = self._build_rust_board(board_snapshot, current_turn_color)

            try:
                raw_score = search.get_search_score(rust_board)
                if raw_score is None:
                    continue

                # raw_score is for current_turn_color.
                # We want score for 'color'.
                if current_turn_color == color:
                    my_score = raw_score
                else:
                    my_score = self._invert_score(raw_score)
                results.append(((r, c), my_score))
            except Exception:
                logger.exception("Error getting search score from Rust")
                pass

        return results

    @abstractmethod
    def _get_init_kwargs(self) -> dict:
        """Return kwargs needed to reconstruct this engine instance."""

    @abstractmethod
    def _invert_score(self, score: float) -> float:
        """Invert score from opponent's perspective to ours."""

    @abstractmethod
    def _get_terminal_score(self, board: PyBoard, color: str) -> float:
        """Calculate terminal score for the given color."""

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


class RustAlphaBetaEngine(BaseRustEngine):
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

    def _get_init_kwargs(self) -> dict:
        return {
            "board_size": self.board_size,
            "search_depth": self.search_depth,
            "think_delay": self.think_delay,
            "win_score": self._win_score,
        }

    def _invert_score(self, score: float) -> float:
        return -score

    def _get_terminal_score(self, board: PyBoard, color: str) -> float:
        scores = board.get_score()
        my_score = scores[color]
        opp_score = scores[PyBoard.WHITE if color == PyBoard.BLACK else PyBoard.BLACK]
        if my_score > opp_score:
            return float(self._win_score)
        elif my_score < opp_score:
            return -float(self._win_score)
        return 0.0


class RustThunderEngine(BaseRustEngine):
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
        # Disable iterative deepening in BaseEngine analysis loop
        if hasattr(self, "search_depth"):
            del self.search_depth

    def _create_search(self):
        return ThunderSearch(self._winrate_evaluator, self.playouts, self.epsilon)

    def _get_init_kwargs(self) -> dict:
        return {
            "board_size": self.board_size,
            "think_delay": self.think_delay,
            "playouts": self.playouts,
            "epsilon": self.epsilon,
        }

    def _invert_score(self, score: float) -> float:
        return 1.0 - score

    def _get_terminal_score(self, board: PyBoard, color: str) -> float:
        scores = board.get_score()
        my_score = scores[color]
        opp_score = scores[PyBoard.WHITE if color == PyBoard.BLACK else PyBoard.BLACK]
        if my_score > opp_score:
            return 1.0
        elif my_score < opp_score:
            return 0.0
        return 0.5


class RustMctsEngine(BaseRustEngine):
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
        # Disable iterative deepening in BaseEngine analysis loop
        if hasattr(self, "search_depth"):
            del self.search_depth

    def _create_search(self):
        return MctsSearch(
            self.playouts,
            self.exploration_constant,
            self.expand_threshold,
        )

    def _get_init_kwargs(self) -> dict:
        return {
            "board_size": self.board_size,
            "think_delay": self.think_delay,
            "playouts": self.playouts,
            "exploration_constant": self.exploration_constant,
            "expand_threshold": self.expand_threshold,
        }

    def _invert_score(self, score: float) -> float:
        return 1.0 - score

    def _get_terminal_score(self, board: PyBoard, color: str) -> float:
        scores = board.get_score()
        my_score = scores[color]
        opp_score = scores[PyBoard.WHITE if color == PyBoard.BLACK else PyBoard.BLACK]
        if my_score > opp_score:
            return 1.0
        elif my_score < opp_score:
            return 0.0
        return 0.5