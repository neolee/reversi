from __future__ import annotations

import math
import random
from typing import Iterable, List, Optional, Sequence, Tuple

from reversi.engine.base_engine import BaseEngine
from reversi.engine.board import Board


class MinimaxEngine(BaseEngine):
    def __init__(
        self,
        board_size: int = 8,
        search_depth: int = 3,
        think_delay: float = 0.2,
        selection_top_k: int = 2,
        selection_temperature: float = 0.15,
        randomize_moves: bool = True,
        rng_seed: int | None = None,
    ):
        super().__init__(board_size=board_size, think_delay=think_delay)
        self.search_depth = max(1, search_depth)
        self._search_color = Board.BLACK
        self.selection_top_k = max(1, selection_top_k)
        self.selection_temperature = max(1e-6, selection_temperature)
        self.randomize_moves = randomize_moves
        self._rng = random.Random(rng_seed)

    def _pick_move(
        self,
        board_snapshot: Board,
        color: str,
        valid_moves: Iterable[Tuple[int, int]],
    ) -> Optional[Tuple[int, int]]:
        self._search_color = color
        move_scores = self._score_moves(board_snapshot, color)
        if not move_scores:
            return None
        return self._select_weighted_move(move_scores)

    def _score_moves(self, board_snapshot: Board, color: str) -> List[Tuple[Tuple[int, int], float]]:
        moves = board_snapshot.get_valid_moves(color)
        if not moves:
            return []

        move_scores: List[Tuple[Tuple[int, int], float]] = []
        for move in moves:
            child = board_snapshot.clone()
            child.play_move(move[0], move[1], color)
            _, score = self._minimax(
                child,
                child.current_player,
                self.search_depth - 1,
                -math.inf,
                math.inf,
            )
            move_scores.append((move, score))
        return move_scores

    def _select_weighted_move(self, move_scores: Sequence[Tuple[Tuple[int, int], float]]):
        if not self.randomize_moves or len(move_scores) == 1:
            return max(move_scores, key=lambda item: item[1])[0]

        candidates = self._top_candidates(move_scores)
        if len(candidates) == 1:
            return candidates[0][0]

        weights = self._softmax_weights(candidates)
        choices = [move for move, _ in candidates]
        return self._rng.choices(choices, weights=weights, k=1)[0]

    def _top_candidates(self, move_scores: Sequence[Tuple[Tuple[int, int], float]]):
        ordered = sorted(move_scores, key=lambda item: item[1], reverse=True)
        cutoff_index = min(len(ordered), self.selection_top_k) - 1
        cutoff_score = ordered[cutoff_index][1]
        return [item for item in ordered if item[1] >= cutoff_score]

    def _softmax_weights(self, candidates: Sequence[Tuple[Tuple[int, int], float]]):
        max_score = max(score for _, score in candidates)
        exps = [math.exp((score - max_score) / self.selection_temperature) for _, score in candidates]
        total = sum(exps)
        if total <= 0:
            return [1.0 for _ in candidates]
        return [value / total for value in exps]

    def _minimax(self, board: Board, player: str, depth: int, alpha: float, beta: float):
        opponent = Board.WHITE if player == Board.BLACK else Board.BLACK
        valid_moves = board.get_valid_moves(player)

        if depth <= 0 or board.is_game_over():
            return None, self._evaluate_board(board)

        if not valid_moves:
            if board.has_valid_move(opponent):
                board_pass = board.clone()
                board_pass.current_player = opponent
                return self._minimax(board_pass, opponent, depth - 1, alpha, beta)
            return None, self._evaluate_board(board)

        maximizing = player == self._search_color
        best_move = None

        if maximizing:
            value = -math.inf
            for move in valid_moves:
                child = board.clone()
                child.play_move(move[0], move[1], player)
                _, score = self._minimax(child, child.current_player, depth - 1, alpha, beta)
                if score > value:
                    value = score
                    best_move = move
                alpha = max(alpha, value)
                if beta <= alpha:
                    break
            return best_move, value
        else:
            value = math.inf
            for move in valid_moves:
                child = board.clone()
                child.play_move(move[0], move[1], player)
                _, score = self._minimax(child, child.current_player, depth - 1, alpha, beta)
                if score < value:
                    value = score
                    best_move = move
                beta = min(beta, value)
                if beta <= alpha:
                    break
            return best_move, value

    def _evaluate_board(self, board: Board) -> float:
        opponent = Board.WHITE if self._search_color == Board.BLACK else Board.BLACK
        scores = board.get_score()
        disc_balance = scores[self._search_color] - scores[opponent]

        my_moves = len(board.get_valid_moves(self._search_color))
        opp_moves = len(board.get_valid_moves(opponent))
        mobility = my_moves - opp_moves

        corner_score = self._corner_heuristic(board, self._search_color) - self._corner_heuristic(board, opponent)

        return disc_balance * 1.5 + mobility * 5 + corner_score * 25

    def _corner_heuristic(self, board: Board, player: str) -> int:
        corners = [
            (0, 0),
            (0, board.size - 1),
            (board.size - 1, 0),
            (board.size - 1, board.size - 1),
        ]
        score = 0
        for r, c in corners:
            piece = board.get_piece(r, c)
            if piece == player:
                score += 1
        return score
