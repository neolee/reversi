from __future__ import annotations
import threading
import time
from typing import Iterable, Optional, Tuple, Dict, Any, List

from reversi.engine.base_engine import BaseEngine
from reversi.engine.board import Board
from reversi.engine.registry import build_engine_instance


class RouterEngine(BaseEngine):
    """
    A protocol engine that routes search and analysis requests 
    to specific engine instances based on per-color configuration.
    """

    def __init__(self, board_size: int = 8):
        super().__init__(board_size=board_size)
        self.player_configs: Dict[str, Dict[str, Any]] = {}
        self.analysis_configs: Dict[str, Dict[str, Any]] = {}
        
        self._player_engines: Dict[str, BaseEngine] = {}
        self._analysis_engines: Dict[str, BaseEngine] = {}
        self._engine_lock = threading.Lock()

    def set_player_config(self, color: str, key: str, params: Dict[str, Any]):
        with self._engine_lock:
            self.player_configs[color] = {"key": key, "params": params}
            # Clear cached engine instance to force rebuild on next use
            if color in self._player_engines:
                del self._player_engines[color]

    def set_analysis_config(self, color: str, key: str, params: Dict[str, Any]):
        with self._engine_lock:
            self.analysis_configs[color] = {"key": key, "params": params}
            if color in self._analysis_engines:
                self._analysis_engines[color].stop_analysis()
                del self._analysis_engines[color]

    def _get_player_engine(self, color: str) -> BaseEngine:
        with self._engine_lock:
            if color not in self._player_engines:
                config = self.player_configs.get(color, {"key": "minimax", "params": {}})
                engine = build_engine_instance(
                    config["key"],
                    board_size=self.board_size,
                    **config["params"]
                )
                self._player_engines[color] = engine
            return self._player_engines[color]

    def _get_analysis_engine(self, color: str) -> BaseEngine:
        with self._engine_lock:
            if color not in self._analysis_engines:
                config = self.analysis_configs.get(color, {"key": "minimax", "params": {}})
                # For analysis, always use think_delay=0 unless specified
                params = dict(config["params"])
                if "think_delay" not in params:
                    params["think_delay"] = 0.0
                
                engine = build_engine_instance(
                    config["key"],
                    board_size=self.board_size,
                    **params
                )
                # Redirect analysis engine's emits back to our protocol
                engine.set_callback(self._emit)
                self._analysis_engines[color] = engine
            return self._analysis_engines[color]

    def _pick_move(
        self,
        board_snapshot: Board,
        color: str,
        valid_moves: Iterable[Tuple[int, int]],
    ) -> Optional[Tuple[int, int]]:
        engine = self._get_player_engine(color)
        # Synchronize board state if needed (most engines use the snapshot passed)
        if hasattr(engine, "board"):
            engine.board = board_snapshot
            
        return engine._pick_move(board_snapshot, color, valid_moves)

    def analyze(self, color: str) -> list[tuple[tuple[int, int], float]]:
        # This is for the single-shot _run_analysis path
        # RouterEngine usually uses iterative deepening path via start_analysis
        engine = self._get_analysis_engine(color)
        if hasattr(engine, "board"):
            engine.board = self.board.clone()
        return engine.analyze(color)

    def start_analysis(self, color: str):
        self.stop_analysis()
        engine = self._get_analysis_engine(color)
        if hasattr(engine, "board"):
            engine.board = self.board.clone()
        engine.start_analysis(color)

    def stop_analysis(self):
        with self._engine_lock:
            for engine in self._analysis_engines.values():
                engine.stop_analysis()

    def stop(self):
        super().stop()
        with self._engine_lock:
            for engine in self._player_engines.values():
                engine.stop()
            for engine in self._analysis_engines.values():
                engine.stop()
