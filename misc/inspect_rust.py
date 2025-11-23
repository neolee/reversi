
try:
    import rust_reversi
    print("rust_reversi imported successfully")
    print("AlphaBetaSearch attributes:", dir(rust_reversi.AlphaBetaSearch))
    print("ThunderSearch attributes:", dir(rust_reversi.ThunderSearch))
    print("MctsSearch attributes:", dir(rust_reversi.MctsSearch))

    # Check if we can instantiate and see methods
    pe = rust_reversi.PieceEvaluator()
    abs = rust_reversi.AlphaBetaSearch(pe, 1, 1000)
    print("AlphaBetaSearch instance attributes:", dir(abs))

    print("AlphaBetaSearch.get_search_score doc:", abs.get_search_score.__doc__)

    # Test ThunderSearch
    we = rust_reversi.WinrateEvaluator()
    ts = rust_reversi.ThunderSearch(we, 10, 0.1)

    board_std = rust_reversi.Board()
    board_str = "-" * 27 + "OX" + "-" * 6 + "XO" + "-" * 27
    board_std.set_board_str(board_str, rust_reversi.Turn.BLACK)

    try:
        score = ts.get_search_score(board_std)
        print(f"ThunderSearch Standard start, Black to move, Score: {score}")
    except Exception as e:
        print(f"ThunderSearch failed: {e}")


except ImportError:
    print("rust_reversi not found")
except Exception as e:
    print(f"Error: {e}")
