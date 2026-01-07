from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class GameState:
    board_size: int = 8
    current_turn: str = "BLACK"
    game_started: bool = False
    score_black: int = 2
    score_white: int = 2
    undo_expect_updates: int = 0
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    current_valid_moves: List[str] = field(default_factory=list)

    # Player configuration
    players: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "BLACK": {"name": "Black", "is_human": True},
        "WHITE": {"name": "White", "is_human": False}
    })

    ai_engine_settings: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "BLACK": {"key": "minimax", "params": {"search_depth": 3, "think_delay": 0.2}},
        "WHITE": {"key": "minimax", "params": {"search_depth": 4, "think_delay": 0.2}}
    })

    analysis_settings: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "BLACK": {"enabled": False, "key": "minimax", "params": {}},
        "WHITE": {"enabled": False, "key": "minimax", "params": {}}
    })

    def reset(self, board_size: int):
        self.board_size = board_size
        self.game_started = True
        self.timeline = []
        self.current_valid_moves = []
        self.score_black = 2
        self.score_white = 2
        self.undo_expect_updates = 0
