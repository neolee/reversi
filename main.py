import sys
import os
import argparse
from typing import Any, cast

# Add src directory to python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import flet as ft
from reversi.ui.app import ReversiApp
from reversi.engine.board import Board
from reversi.engine.registry import (
    build_engine_instance,
    engine_supports_depth,
    get_engine_choices,
)
from reversi.cli.duel import EngineSpec, run_duel_series

ENGINE_NAMES = sorted(get_engine_choices().keys())


DEFAULT_PROTOCOL_ENGINE = "minimax"


def run_ui(args: argparse.Namespace) -> None:
    print(f"Starting UI with board size {args.size}...")
    engine = build_engine_instance(DEFAULT_PROTOCOL_ENGINE, board_size=args.size)
    app = ReversiApp(engine, board_size=args.size)
    ft.app(target=app.main)


def _spec_label(engine_name: str, depth: int | None, delay: float | None) -> str:
    details = []
    if depth:
        details.append(f"d{depth}")
    if delay:
        details.append(f"{delay:.2f}s")
    if details:
        return f"{engine_name} ({', '.join(details)})"
    return engine_name


def build_cli_engine_spec(engine_name: str, depth: int, delay: float) -> EngineSpec:
    supports_depth = engine_supports_depth(engine_name)
    search_depth = max(1, depth) if supports_depth and depth else None
    think_delay = max(0.0, delay)
    return EngineSpec(
        key=engine_name,
        label=_spec_label(engine_name, search_depth, think_delay),
        search_depth=search_depth,
        think_delay=think_delay,
    )


def run_duel(args: argparse.Namespace) -> None:
    black_spec = build_cli_engine_spec(args.black_engine, args.black_depth, args.black_delay)
    white_spec = build_cli_engine_spec(args.white_engine, args.white_depth, args.white_delay)

    stats, results = run_duel_series(
        board_size=args.size,
        black_spec=black_spec,
        white_spec=white_spec,
        games=max(1, args.games),
        swap_colors=not args.no_swap,
    )

    print("\nGame results:")
    for index, result in enumerate(results, start=1):
        black_label = result.color_to_label.get(Board.BLACK, "BLACK")
        white_label = result.color_to_label.get(Board.WHITE, "WHITE")
        black_score = result.scores.get(Board.BLACK, 0)
        white_score = result.scores.get(Board.WHITE, 0)
        if result.winner_color == "DRAW":
            verdict = "Draw"
        else:
            verdict = f"Winner: {result.color_to_label.get(result.winner_color, result.winner_color)}"
        print(
            f"Game {index}: {black_label} (Black) {black_score} - "
            f"{white_label} (White) {white_score} | {verdict}"
        )

    summary: dict[str, Any] = stats.summary()
    engines = cast(dict[str, Any], summary["engines"])
    print(f"\nDuel complete: {summary['total_games']} games, {summary['draws']} draws.")
    print(f"Average moves per game: {summary['average_moves']:.2f}")
    print("\nEngine breakdown:")
    for label, data in engines.items():
        if not isinstance(data, dict):
            continue
        wins = data.get("wins", 0)
        games = data.get("games", 0)
        avg_score = data.get("avg_score", 0.0)
        avg_margin = data.get("avg_margin", 0.0)
        print(
            f"- {label}: {wins} wins / {games} games, "
            f"avg score {avg_score:.2f}, avg margin {avg_margin:+.2f}"
        )

def main() -> None:
    parser = argparse.ArgumentParser(description="Reversi Game CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # UI Command
    ui_parser = subparsers.add_parser("ui", help="Start the GUI")
    ui_parser.add_argument("--size", type=int, default=8, help="Board size (default: 8)")
    ui_parser.set_defaults(func=run_ui)

    duel_parser = subparsers.add_parser("duel", help="Run engine vs engine duels")
    duel_parser.add_argument("--size", type=int, default=8, help="Board size (default: 8)")
    duel_parser.add_argument("--games", type=int, default=2, help="Number of games to run (default: 2)")
    duel_parser.add_argument("--no-swap", action="store_true", help="Disable color swapping between games")
    duel_parser.add_argument(
        "--black-engine",
        choices=ENGINE_NAMES,
        default="minimax",
        help="Engine used as black in the first game",
    )
    duel_parser.add_argument(
        "--white-engine",
        choices=ENGINE_NAMES,
        default="rust-alpha",
        help="Engine used as white in the first game",
    )
    duel_parser.add_argument(
        "--black-depth",
        type=int,
        default=3,
        help="Search depth for the black engine when supported",
    )
    duel_parser.add_argument(
        "--white-depth",
        type=int,
        default=3,
        help="Search depth for the white engine when supported",
    )
    duel_parser.add_argument(
        "--black-delay",
        type=float,
        default=0.0,
        help="Think delay in seconds for the black engine",
    )
    duel_parser.add_argument(
        "--white-delay",
        type=float,
        default=0.0,
        help="Think delay in seconds for the white engine",
    )
    duel_parser.set_defaults(func=run_duel)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
