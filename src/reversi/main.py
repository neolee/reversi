from reversi.ui.app import run_app
from reversi.engine.mock_engine import MockEngine


def main():
    engine = MockEngine()
    run_app(engine)


if __name__ == "__main__":
    main()
