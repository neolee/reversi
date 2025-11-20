from math import inf
from typing import Iterable, Optional, Tuple

from reversi.engine.base_engine import BaseEngine
from reversi.engine.board import Board


class MinimaxEngine(BaseEngine):
    def __init__(self, board_size: int = 8, search_depth: int = 3, think_delay: float = 0.2):
        super().__init__(board_size=board_size, think_delay=think_delay)
        self.search_depth = search_depth
        self._search_color = Board.BLACK

    def _pick_move(
        self,
        board_snapshot: Board,
        color: str,
        valid_moves: Iterable[Tuple[int, int]],
    ) -> Optional[Tuple[int, int]]:
        _ = valid_moves  # Minimax recomputes moves from the snapshot
        self._search_color = color
        move, _ = self._minimax(board_snapshot, color, self.search_depth, -inf, inf)
        return move

    def _minimax(self, board: Board, player: str, depth: int, alpha: float, beta: float):
        opponent = Board.WHITE if player == Board.BLACK else Board.BLACK
        valid_moves = board.get_valid_moves(player)

        if depth == 0 or board.is_game_over():
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
            value = -inf
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
            value = inf
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
