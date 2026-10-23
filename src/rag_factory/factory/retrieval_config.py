"""Safe YAML parser for named retrieval-strategy composition."""

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml

from rag_factory.factory.strategy_manager import StrategyConfig


@dataclass(frozen=True)
class RetrievalConfiguration:
    strategies: Mapping[str, StrategyConfig]


def load_retrieval_config(path: str | Path) -> RetrievalConfiguration:
    with Path(path).open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    if not isinstance(document, dict):
        raise ValueError("Configuration root must be a mapping")
    definitions = document.get("retrieval")
    if not isinstance(definitions, dict) or not definitions:
        raise ValueError("retrieval must be a nonempty mapping")
    configs = {}
    for name, entry in definitions.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(entry, dict):
            raise ValueError("Each retrieval strategy must be a named mapping")
        implementation = entry.get("implementation")
        parameters = entry.get("parameters", {})
        if not isinstance(implementation, str) or not implementation.strip():
            raise ValueError(f"Invalid implementation for strategy {name}")
        if not isinstance(parameters, dict):
            raise ValueError(f"Parameters for strategy {name} must be a mapping")
        configs[name] = StrategyConfig(implementation, parameters)
    return RetrievalConfiguration(configs)
