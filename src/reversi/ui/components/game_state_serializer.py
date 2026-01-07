from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from reversi.engine.metadata import resolve_engine_key

SAVE_FILE_VERSION = 2
_DEFAULT_PLAYER_MODES = {"BLACK": "human", "WHITE": "engine"}

JSONDict = Dict[str, Any]
TimelineEntry = Dict[str, Any]
EngineSettings = Dict[str, JSONDict]


@dataclass(frozen=True)
class GameStateSnapshot:
    board_size: int
    human_color: str
    ai_color: str
    player_modes: Dict[str, str]
    ai_engine_settings: EngineSettings
    analysis_settings: EngineSettings
    timeline: List[TimelineEntry]


@dataclass(frozen=True)
class LoadedGameState:
    timeline: List[TimelineEntry]
    player_modes: Dict[str, str]
    ai_engine_settings: EngineSettings
    analysis_settings: EngineSettings


def serialize(snapshot: GameStateSnapshot) -> JSONDict:
    return {
        "version": SAVE_FILE_VERSION,
        "board_size": snapshot.board_size,
        "human_color": snapshot.human_color,
        "ai_color": snapshot.ai_color,
        "player_modes": dict(snapshot.player_modes),
        "ai_engine_settings": _clone_engine_settings(snapshot.ai_engine_settings),
        "analysis_settings": _clone_engine_settings(snapshot.analysis_settings),
        "timeline": copy.deepcopy(snapshot.timeline),
    }


def deserialize(
    data: JSONDict,
    *,
    board_size: int,
    default_engine_provider: Callable[[str], JSONDict],
    fallback_engine_keys: Dict[str, str] | None = None,
) -> LoadedGameState:
    if data.get("version") != SAVE_FILE_VERSION:
        raise ValueError("Unsupported save file version")
    if data.get("board_size") != board_size:
        raise ValueError("Board size mismatch in save file")

    timeline = _normalize_timeline(data.get("timeline"))
    player_modes = _extract_player_modes(data)
    
    # Merge Engine Settings
    ai_engine_settings = _merge_engine_settings(
        data.get("ai_engine_settings"),
        default_engine_provider,
        fallback_engine_keys or {"BLACK": "minimax", "WHITE": "rust-alpha"},
    )
    
    # Merge Analysis Settings
    analysis_settings = _merge_engine_settings(
        data.get("analysis_settings"),
        default_engine_provider,
        fallback_engine_keys or {"BLACK": "minimax", "WHITE": "minimax"},
    )

    return LoadedGameState(
        timeline=timeline,
        player_modes=player_modes,
        ai_engine_settings=ai_engine_settings,
        analysis_settings=analysis_settings
    )


def _normalize_timeline(raw_timeline: Any) -> List[TimelineEntry]:
    if not isinstance(raw_timeline, list) or not raw_timeline:
        raise ValueError("Save file is missing timeline data")
    normalized: List[dict] = []
    for idx, entry in enumerate(raw_timeline):
        entry_data = entry if isinstance(entry, dict) else {}
        move = entry_data.get("move")
        normalized.append(
            {
                "index": entry_data.get("index", idx),
                "board": entry_data.get("board", ""),
                "current_player": entry_data.get("current_player", "BLACK"),
                "move": dict(move) if isinstance(move, dict) else None,
                "scores": dict(entry_data.get("scores", {})),
            }
        )
    return normalized


def _extract_player_modes(data: JSONDict) -> Dict[str, str]:
    raw_modes = data.get("player_modes")
    if isinstance(raw_modes, dict):
        merged = _DEFAULT_PLAYER_MODES.copy()
        merged.update({k: v for k, v in raw_modes.items() if k in merged and v in ("human", "engine")})
        return merged

    fallback_human = data.get("human_color", "BLACK")
    fallback_ai = data.get("ai_color", "WHITE")
    return {
        fallback_human: "human",
        fallback_ai: "engine"
    }


def _merge_engine_settings(
    saved: Any,
    default_provider: Callable[[str], JSONDict],
    fallback_keys: Dict[str, str]
) -> EngineSettings:
    saved_dict = saved if isinstance(saved, dict) else {}
    result: EngineSettings = {}
    for color in ("BLACK", "WHITE"):
        saved_entry = saved_dict.get(color)
        if isinstance(saved_entry, dict) and "key" in saved_entry:
            # We trust the saved key if it exists
            result[color] = saved_entry
        else:
            # Fallback to defaults
            key = fallback_keys.get(color, "minimax")
            result[color] = default_provider(key)
    return result


def _clone_engine_settings(settings: EngineSettings) -> JSONDict:
    return {k: copy.deepcopy(v) for k, v in settings.items()}
