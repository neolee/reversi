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
    timeline: List[TimelineEntry]


@dataclass(frozen=True)
class LoadedGameState:
    timeline: List[TimelineEntry]
    player_modes: Dict[str, str]
    ai_engine_settings: EngineSettings


def serialize(snapshot: GameStateSnapshot) -> JSONDict:
    return {
        "version": SAVE_FILE_VERSION,
        "board_size": snapshot.board_size,
        "human_color": snapshot.human_color,
        "ai_color": snapshot.ai_color,
        "player_modes": dict(snapshot.player_modes),
        "ai_engine_settings": _clone_engine_settings(snapshot.ai_engine_settings),
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
    ai_engine_settings = _merge_engine_settings(
        data.get("ai_engine_settings"),
        default_engine_provider,
        fallback_engine_keys or {"BLACK": "minimax", "WHITE": "rust-alpha"},
    )

    return LoadedGameState(
        timeline=timeline,
        player_modes=player_modes,
        ai_engine_settings=ai_engine_settings,
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
    modes = {
        "BLACK": "human" if fallback_human == "BLACK" else "engine",
        "WHITE": "human" if fallback_human == "WHITE" else "engine",
    }
    if fallback_ai in modes and fallback_ai != fallback_human:
        modes[fallback_ai] = "engine"
    return modes


def _merge_engine_settings(
    raw_settings: Any,
    default_engine_provider: Callable[[str], JSONDict],
    fallback_engine_keys: Dict[str, str],
) -> EngineSettings:
    merged: EngineSettings = {}
    for color in ("BLACK", "WHITE"):
        cfg = raw_settings.get(color) if isinstance(raw_settings, dict) else None
        if isinstance(cfg, dict) and cfg.get("engine_key"):
            engine_key = resolve_engine_key(cfg["engine_key"])
            params = dict(cfg.get("params", {})) if isinstance(cfg.get("params"), dict) else {}
        else:
            fallback_key = fallback_engine_keys.get(color, "minimax")
            engine_key = resolve_engine_key(fallback_key)
            params = {}
        defaults = default_engine_provider(engine_key)
        default_params = dict(defaults.get("params", {}))
        default_params.update(params)
        merged[color] = {
            "engine_key": engine_key,
            "params": default_params,
        }
    return merged


def _clone_engine_settings(settings: EngineSettings) -> EngineSettings:
    cloned: EngineSettings = {}
    for color, cfg in settings.items():
        cloned[color] = {
            "engine_key": cfg.get("engine_key"),
            "params": copy.deepcopy(cfg.get("params", {})),
        }
    return cloned
