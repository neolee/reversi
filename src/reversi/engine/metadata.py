from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class EngineParamMetadata:
    name: str
    label: str
    type: str  # "int", "float", "choice"
    default: Any
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    choices: List[tuple[str, str]] | None = None
    help_text: str | None = None


@dataclass(frozen=True)
class EngineMetadata:
    key: str
    label: str
    description: str
    parameters: List[EngineParamMetadata]
    alias_for: str | None = None


ENGINE_METADATA: Dict[str, EngineMetadata] = {
    "minimax": EngineMetadata(
        key="minimax",
        label="Python Minimax",
        description="Built-in minimax engine with alpha-beta pruning and light randomization.",
        parameters=[
            EngineParamMetadata(
                name="search_depth",
                label="Search Depth",
                type="int",
                default=3,
                min_value=1,
                max_value=8,
            ),
            EngineParamMetadata(
                name="think_delay",
                label="Think Delay (s)",
                type="float",
                default=0.2,
                min_value=0.0,
                max_value=5.0,
                step=0.1,
            ),
            EngineParamMetadata(
                name="selection_top_k",
                label="Top-K Sampling",
                type="int",
                default=2,
                min_value=1,
                max_value=8,
                help_text="Number of top moves considered before sampling",
            ),
            EngineParamMetadata(
                name="selection_temperature",
                label="Sampling Temperature",
                type="float",
                default=0.15,
                min_value=0.01,
                max_value=1.0,
                step=0.05,
            ),
        ],
    ),
    "rust-alpha": EngineMetadata(
        key="rust-alpha",
        label="Rust AlphaBeta",
        description="Deterministic alpha-beta search implemented in Rust.",
        parameters=[
            EngineParamMetadata(
                name="search_depth",
                label="Search Depth",
                type="int",
                default=5,
                min_value=1,
                max_value=10,
            ),
            EngineParamMetadata(
                name="think_delay",
                label="Think Delay (s)",
                type="float",
                default=0.05,
                min_value=0.0,
                max_value=5.0,
                step=0.05,
            ),
            EngineParamMetadata(
                name="win_score",
                label="Win Score",
                type="int",
                default=100_000,
                min_value=1000,
                max_value=1_000_000,
                help_text="Terminal node score used internally",
            ),
        ],
    ),
    "rust-thunder": EngineMetadata(
        key="rust-thunder",
        label="Rust Thunder",
        description="Epsilon-greedy playout search with randomness.",
        parameters=[
            EngineParamMetadata(
                name="think_delay",
                label="Think Delay (s)",
                type="float",
                default=0.05,
                min_value=0.0,
                max_value=5.0,
                step=0.05,
            ),
            EngineParamMetadata(
                name="playouts",
                label="Playouts",
                type="int",
                default=400,
                min_value=50,
                max_value=5000,
            ),
            EngineParamMetadata(
                name="epsilon",
                label="Epsilon",
                type="float",
                default=0.1,
                min_value=0.0,
                max_value=1.0,
                step=0.05,
                help_text="Probability of selecting a random move",
            ),
        ],
    ),
    "rust-mcts": EngineMetadata(
        key="rust-mcts",
        label="Rust MCTS",
        description="Monte Carlo tree search variant from rust-reversi.",
        parameters=[
            EngineParamMetadata(
                name="think_delay",
                label="Think Delay (s)",
                type="float",
                default=0.05,
                min_value=0.0,
                max_value=5.0,
                step=0.05,
            ),
            EngineParamMetadata(
                name="playouts",
                label="Playouts",
                type="int",
                default=800,
                min_value=100,
                max_value=10_000,
            ),
            EngineParamMetadata(
                name="exploration_constant",
                label="Exploration Constant",
                type="float",
                default=1.4,
                min_value=0.1,
                max_value=5.0,
                step=0.1,
            ),
            EngineParamMetadata(
                name="expand_threshold",
                label="Expand Threshold",
                type="int",
                default=8,
                min_value=1,
                max_value=50,
            ),
        ],
    ),
    "trivial": EngineMetadata(
        key="trivial",
        label="Trivial Random",
        description="Random legal move generator useful for debugging.",
        parameters=[
            EngineParamMetadata(
                name="think_delay",
                label="Think Delay (s)",
                type="float",
                default=0.1,
                min_value=0.0,
                max_value=5.0,
                step=0.05,
            ),
        ],
    ),
}

ENGINE_ALIASES: Dict[str, str] = {"rust": "rust-alpha"}


def resolve_engine_key(key: str) -> str:
    return ENGINE_ALIASES.get(key, key)


def get_engine_metadata(key: str) -> EngineMetadata:
    canonical = resolve_engine_key(key)
    try:
        return ENGINE_METADATA[canonical]
    except KeyError as exc:  # pragma: no cover - configuration error
        raise ValueError(f"Unknown engine metadata for '{key}'") from exc


def list_engine_metadata() -> List[EngineMetadata]:
    return list(ENGINE_METADATA.values())
