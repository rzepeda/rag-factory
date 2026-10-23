"""Safe YAML configuration loading for a single keyword pipeline."""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml

from rag_factory.factory.service_registry import ServiceConfig


_ENV_PATTERN = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")


def _resolve(value):
    if isinstance(value, str):
        match = _ENV_PATTERN.fullmatch(value)
        if match:
            name = match.group(1)
            if name not in os.environ:
                raise ValueError(f"Missing environment variable: {name}")
            return os.environ[name]
    if isinstance(value, dict):
        return {key: _resolve(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve(item) for item in value]
    return value


@dataclass(frozen=True)
class KeywordConfiguration:
    services: Mapping[str, ServiceConfig]
    bindings: Mapping[str, str]


def load_keyword_config(path: str | Path) -> KeywordConfiguration:
    """Read YAML only; never start services or migrate schemas."""
    with Path(path).open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    if not isinstance(document, dict):
        raise ValueError("Configuration root must be a mapping")
    definitions = document.get("services")
    pipeline = document.get("keyword")
    if not isinstance(definitions, dict) or not isinstance(pipeline, dict):
        raise ValueError("Expected services and keyword mappings")
    bindings = pipeline.get("bindings")
    if not isinstance(bindings, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in bindings.items()
    ):
        raise ValueError("Keyword bindings must map interfaces to instance names")
    services = {}
    for name, data in definitions.items():
        if not isinstance(name, str) or not isinstance(data, dict):
            raise ValueError("Service definitions must be named mappings")
        params = data.get("parameters", {})
        if not isinstance(params, dict):
            raise ValueError(f"Parameters for {name} must be a mapping")
        interface, implementation = data.get("interface"), data.get("implementation")
        if not isinstance(interface, str) or not isinstance(implementation, str):
            raise ValueError(f"Service {name} needs interface and implementation")
        services[name] = ServiceConfig(interface, implementation, _resolve(params))
    return KeywordConfiguration(services, bindings)
