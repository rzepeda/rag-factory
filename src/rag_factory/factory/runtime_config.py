"""Safely load a whole offline pipeline configuration from YAML."""

from pathlib import Path
from typing import Any

import yaml

from rag_factory.factory.config import _resolve
from rag_factory.factory.runtime import PipelineConfiguration
from rag_factory.factory.service_registry import ServiceConfig


def load_pipeline_config(path: str | Path) -> PipelineConfiguration:
    with Path(path).open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    if not isinstance(document, dict):
        raise ValueError("Configuration root must be a mapping")
    raw_services = document.get("services")
    pipeline = document.get("pipeline")
    if not isinstance(raw_services, dict) or not isinstance(pipeline, dict):
        raise ValueError("Expected services and pipeline mappings")
    services: dict[str, ServiceConfig] = {}
    for name, entry in raw_services.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(entry, dict):
            raise ValueError("Services must be named mappings")
        interface, implementation = entry.get("interface"), entry.get("implementation")
        parameters: Any = entry.get("parameters", {})
        if (not isinstance(interface, str) or not interface.strip()
            or not isinstance(implementation, str) or not implementation.strip()
            or not isinstance(parameters, dict)):
            raise ValueError(f"Invalid service definition: {name}")
        services[name] = ServiceConfig(interface, implementation, _resolve(parameters))
    bindings = pipeline.get("bindings")
    strategies = pipeline.get("strategies")
    if not isinstance(bindings, dict) or any(
        not isinstance(key, str) or not isinstance(value, str)
        or not key.strip() or not value.strip()
        for key, value in bindings.items()
    ):
        raise ValueError("Pipeline bindings must map interfaces to service names")
    if not isinstance(strategies, list) or any(not isinstance(s, str) for s in strategies):
        raise ValueError("Pipeline strategies must be a list of names")
    model = pipeline.get("embedding_model")
    if model is not None and not isinstance(model, str):
        raise ValueError("embedding_model must be a string")
    return PipelineConfiguration(services, bindings, tuple(strategies), model)
