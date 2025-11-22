import flet as ft
from reversi.ui.app import ReversiApp
from reversi.engine.mock_engine import MockEngine


def main():
    engine = MockEngine()
    app = ReversiApp(engine)
    ft.app(target=app.main)


if __name__ == "__main__":
    main()
