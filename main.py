import sys
import os
import argparse

# Add src directory to python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import flet as ft
from reversi.ui.app import ReversiApp
from reversi.engine.local_engine import LocalEngine

def run_ui(args):
    print(f"Starting UI with board size {args.size}...")
    engine = LocalEngine(board_size=args.size)
    app = ReversiApp(engine, board_size=args.size)
    ft.app(target=app.main)

def main():
    parser = argparse.ArgumentParser(description="Reversi Game CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # UI Command
    ui_parser = subparsers.add_parser("ui", help="Start the GUI")
    ui_parser.add_argument("--size", type=int, default=8, help="Board size (default: 8)")
    ui_parser.set_defaults(func=run_ui)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
