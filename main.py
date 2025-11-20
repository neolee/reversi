import sys
import os
import argparse

# Add src directory to python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import flet as ft
from reversi.ui.app import ReversiApp
from reversi.engine.minimax_engine import MinimaxEngine
from reversi.engine.trivial_engine import TrivialEngine
from reversi.engine.rust_engine import RustReversiEngine

ENGINE_CHOICES = {
    "minimax": MinimaxEngine,
    "rust": RustReversiEngine,
    "trivial": TrivialEngine,
}

def run_ui(args):
    print(f"Starting UI with board size {args.size}...")
    engine = build_engine(args)
    app = ReversiApp(engine, board_size=args.size)
    ft.app(target=app.main)

def build_engine(args):
    engine_type = args.engine
    if engine_type not in ENGINE_CHOICES:
        raise ValueError(f"Unsupported engine '{engine_type}'")

    if engine_type == "trivial":
        return TrivialEngine(board_size=args.size)

    search_depth = max(1, args.search_depth)
    if engine_type == "rust":
        return RustReversiEngine(board_size=args.size, search_depth=search_depth)

    return MinimaxEngine(board_size=args.size, search_depth=search_depth)

def main():
    parser = argparse.ArgumentParser(description="Reversi Game CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # UI Command
    ui_parser = subparsers.add_parser("ui", help="Start the GUI")
    ui_parser.add_argument("--size", type=int, default=8, help="Board size (default: 8)")
    ui_parser.add_argument(
        "--engine",
        choices=sorted(ENGINE_CHOICES.keys()),
        default="minimax",
        help="Engine to run (default: minimax)",
    )
    ui_parser.add_argument(
        "--search-depth",
        type=int,
        default=3,
        help="Search depth for minimax/rust engines (default: 3)",
    )
    ui_parser.set_defaults(func=run_ui)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
