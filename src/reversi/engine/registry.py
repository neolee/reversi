from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Type

from reversi.engine.base_engine import BaseEngine
from reversi.engine.minimax_engine import MinimaxEngine
from reversi.engine.trivial_engine import TrivialEngine
from reversi.engine.rust_engine import (
    RustAlphaBetaEngine,
    RustMctsEngine,
    RustThunderEngine,
)


@dataclass(frozen=True)
class EngineEntry:
    cls: Type[BaseEngine]
    supports_depth: bool


ENGINE_REGISTRY: Dict[str, EngineEntry] = {
    "minimax": EngineEntry(cls=MinimaxEngine, supports_depth=True),
    "rust": EngineEntry(cls=RustAlphaBetaEngine, supports_depth=True),
    "rust-alpha": EngineEntry(cls=RustAlphaBetaEngine, supports_depth=True),
    "rust-thunder": EngineEntry(cls=RustThunderEngine, supports_depth=False),
    "rust-mcts": EngineEntry(cls=RustMctsEngine, supports_depth=False),
    "trivial": EngineEntry(cls=TrivialEngine, supports_depth=False),
}


def get_engine_choices() -> Dict[str, Type[BaseEngine]]:
    """Return mapping of engine key to class."""
    return {name: entry.cls for name, entry in ENGINE_REGISTRY.items()}


def engine_supports_depth(name: str) -> bool:
    entry = ENGINE_REGISTRY.get(name)
    if not entry:
        raise ValueError(f"Unknown engine '{name}'")
    return entry.supports_depth


def build_engine_instance(
    name: str,
    board_size: int,
    search_depth: int | None = None,
    think_delay: float | None = None,
    **engine_options: Any,
) -> BaseEngine:
    entry = ENGINE_REGISTRY.get(name)
    if not entry:
        raise ValueError(f"Unknown engine '{name}'")

    engine_cls: Type[BaseEngine] = entry.cls
    kwargs: Dict[str, Any] = {"board_size": board_size}
    if think_delay is not None:
        kwargs["think_delay"] = think_delay
    if entry.supports_depth and search_depth is not None:
        kwargs["search_depth"] = search_depth
    if engine_options:
        kwargs.update(engine_options)
    return engine_cls(**kwargs)
