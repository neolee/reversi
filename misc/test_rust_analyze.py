from reversi.engine.rust_engine import RustAlphaBetaEngine, RustThunderEngine
from reversi.engine.board import Board

def test_analyze():
    print("Testing RustAlphaBetaEngine.analyze...")
    engine = RustAlphaBetaEngine(search_depth=2)
    # Initial board
    # Black to move
    results = engine.analyze(Board.BLACK)
    print("Results (Black):", results)

    # Should have 4 moves
    assert len(results) == 4

    print("\nTesting RustThunderEngine.analyze...")
    engine_thunder = RustThunderEngine(playouts=100)
    results_thunder = engine_thunder.analyze(Board.BLACK)
    print("Results (Black, Thunder):", results_thunder)
    assert len(results_thunder) == 4

if __name__ == "__main__":
    try:
        test_analyze()
        print("Test passed!")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
