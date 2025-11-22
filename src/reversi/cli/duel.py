from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from reversi.engine.board import Board
from reversi.engine.registry import build_engine_instance


@dataclass
class EngineSpec:
    key: str
    label: str
    search_depth: int | None = None
    think_delay: float | None = 0.0


class EnginePlayer:
    def __init__(self, spec: EngineSpec, board_size: int):
        self.spec = spec
        self.engine = build_engine_instance(
            spec.key,
            board_size=board_size,
            search_depth=spec.search_depth,
            think_delay=spec.think_delay,
        )

    def choose_move(self, board: Board, color: str):
        snapshot = board.clone()
        valid_moves = snapshot.get_valid_moves(color)
        if not valid_moves:
            return None
        move = self.engine._pick_move(snapshot, color, valid_moves)  # type: ignore[attr-defined]
        return move if move in valid_moves else valid_moves[0]


@dataclass
class MatchResult:
    winner_color: str
    scores: Dict[str, int]
    moves: List[Tuple[str, str]]
    color_to_label: Dict[str, str]


class EngineMatch:
    def __init__(self, board_size: int, black_spec: EngineSpec, white_spec: EngineSpec):
        self.board_size = board_size
        self.players = {
            Board.BLACK: EnginePlayer(black_spec, board_size),
            Board.WHITE: EnginePlayer(white_spec, board_size),
        }

    def play(self) -> MatchResult:
        board = Board(self.board_size)
        move_log: List[Tuple[str, str]] = []

        while not board.is_game_over():
            color = board.current_player
            valid_moves = board.get_valid_moves(color)
            if not valid_moves:
                if board.pass_turn(color):
                    move_log.append((color, "PASS"))
                    continue
                break

            move = self.players[color].choose_move(board, color)
            if move is None or not board.play_move(move[0], move[1], color):
                fallback = valid_moves[0]
                board.play_move(fallback[0], fallback[1], color)
                move_str = board.coord_to_str(fallback[0], fallback[1])
            else:
                move_str = board.coord_to_str(move[0], move[1])
            move_log.append((color, move_str))

        scores = board.get_score()
        winner_color = self._determine_winner(scores)
        color_to_label = {
            Board.BLACK: self.players[Board.BLACK].spec.label,
            Board.WHITE: self.players[Board.WHITE].spec.label,
        }
        return MatchResult(winner_color=winner_color, scores=scores, moves=move_log, color_to_label=color_to_label)

    @staticmethod
    def _determine_winner(scores: Dict[str, int]) -> str:
        black = scores.get(Board.BLACK, 0)
        white = scores.get(Board.WHITE, 0)
        if black > white:
            return Board.BLACK
        if white > black:
            return Board.WHITE
        return "DRAW"


class DuelStats:
    def __init__(self, engine_labels: List[str]):
        self.engine_labels = engine_labels
        self.wins = {label: 0 for label in engine_labels}
        self.draws = 0
        self.score_totals = {label: 0 for label in engine_labels}
        self.score_diff_totals = {label: 0 for label in engine_labels}
        self.games_played = {label: 0 for label in engine_labels}
        self.total_games = 0
        self.total_moves = 0

    def record(self, result: MatchResult):
        self.total_games += 1
        self.total_moves += len(result.moves)
        colors = [Board.BLACK, Board.WHITE]
        for color in colors:
            label = result.color_to_label[color]
            opponent = Board.WHITE if color == Board.BLACK else Board.BLACK
            self.games_played[label] += 1
            self.score_totals[label] += result.scores[color]
            self.score_diff_totals[label] += result.scores[color] - result.scores[opponent]

        if result.winner_color == "DRAW":
            self.draws += 1
        else:
            winner_label = result.color_to_label[result.winner_color]
            self.wins[winner_label] += 1

    def summary(self) -> Dict[str, object]:
        averages = {}
        for label in self.engine_labels:
            games = max(1, self.games_played[label])
            averages[label] = {
                "avg_score": self.score_totals[label] / games,
                "avg_margin": self.score_diff_totals[label] / games,
                "wins": self.wins[label],
                "games": games,
            }
        return {
            "total_games": self.total_games,
            "draws": self.draws,
            "average_moves": self.total_moves / self.total_games if self.total_games else 0.0,
            "engines": averages,
        }


def run_duel_series(
    board_size: int,
    black_spec: EngineSpec,
    white_spec: EngineSpec,
    games: int = 1,
    swap_colors: bool = True,
) -> Tuple[DuelStats, List[MatchResult]]:
    labels = list(dict.fromkeys([black_spec.label, white_spec.label]))
    stats = DuelStats(labels)
    results: List[MatchResult] = []

    for game_index in range(games):
        if swap_colors and game_index % 2 == 1:
            current_black, current_white = white_spec, black_spec
        else:
            current_black, current_white = black_spec, white_spec

        match = EngineMatch(board_size, current_black, current_white)
        result = match.play()
        stats.record(result)
        results.append(result)

    return stats, results
