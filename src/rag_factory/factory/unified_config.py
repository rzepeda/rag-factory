"""YAML configuration with independent indexing and retrieval bindings."""
from pathlib import Path
import yaml
from rag_factory.factory.config import _resolve
from rag_factory.factory.service_registry import ServiceConfig
from rag_factory.factory.unified import StrategySpec, UnifiedConfiguration

def load_unified_config(path: str | Path) -> UnifiedConfiguration:
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or not isinstance(doc.get("services"), dict) or not isinstance(doc.get("strategies"), dict):
        raise ValueError("Expected services and strategies mappings")
    services = {}
    for name, entry in doc["services"].items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            raise ValueError("Invalid service entry")
        interface, implementation, params = entry.get("interface"), entry.get("implementation"), entry.get("parameters", {})
        if not isinstance(interface, str) or not isinstance(implementation, str) or not isinstance(params, dict):
            raise ValueError("Invalid service configuration")
        services[name] = ServiceConfig(interface, implementation, _resolve(params))
    strategies = {}
    for name, entry in doc["strategies"].items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            raise ValueError("Invalid strategy entry")
        indexing, retrieval, parameters = (entry.get("indexing", {}), entry.get("retrieval", {}), entry.get("parameters", {}))
        if not all(isinstance(v, dict) for v in (indexing, retrieval, parameters)):
            raise ValueError("Strategy stage bindings and parameters must be mappings")
        for mapping in (indexing, retrieval):
            if any(not isinstance(k, str) or not isinstance(v, str) for k, v in mapping.items()):
                raise ValueError("Bindings must be strings")
        strategies[name] = StrategySpec(entry.get("kind"), indexing, retrieval, _resolve(parameters))
    return UnifiedConfiguration(services, strategies)
