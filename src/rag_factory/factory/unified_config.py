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
    unexpected = set(doc) - {"services", "strategies"}
    if unexpected:
        raise ValueError(f"Unknown top-level configuration fields: {', '.join(sorted(map(str, unexpected)))}")
    services = {}
    for name, entry in doc["services"].items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            raise ValueError("Invalid service entry")
        unexpected = set(entry) - {"interface", "implementation", "parameters"}
        if unexpected:
            raise ValueError(f"Service {name}: unknown fields: {', '.join(sorted(map(str, unexpected)))}")
        interface, implementation, params = entry.get("interface"), entry.get("implementation"), entry.get("parameters", {})
        if not isinstance(interface, str) or not isinstance(implementation, str) or not isinstance(params, dict):
            raise ValueError("Invalid service configuration")
        services[name] = ServiceConfig(interface, implementation, _resolve(params))
    strategies = {}
    for name, entry in doc["strategies"].items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            raise ValueError("Invalid strategy entry")
        unexpected = set(entry) - {"kind", "indexing", "retrieval", "parameters"}
        if unexpected:
            raise ValueError(f"Strategy {name}: unknown fields: {', '.join(sorted(map(str, unexpected)))}")
        indexing, retrieval, parameters = (entry.get("indexing", {}), entry.get("retrieval", {}), entry.get("parameters", {}))
        if not all(isinstance(v, dict) for v in (indexing, retrieval, parameters)):
            raise ValueError("Strategy stage bindings and parameters must be mappings")
        for mapping in (indexing, retrieval):
            if any(not isinstance(k, str) or not isinstance(v, str) for k, v in mapping.items()):
                raise ValueError("Bindings must be strings")
        strategies[name] = StrategySpec(entry.get("kind"), indexing, retrieval, _resolve(parameters))
    return UnifiedConfiguration(services, strategies)


def load_validated_unified_config(path: str | Path, registry=None) -> UnifiedConfiguration:
    """Parse and validate a config without constructing providers.

    Report the source path for CLI diagnostics. Registry descriptors express
    declared capabilities only; no endpoint or credentials are contacted.
    """
    from rag_factory.factory.unified import REQUIRES, validate_unified_configuration
    try:
        config = load_unified_config(path)
        for name, spec in config.strategies.items():
            for stage, bindings in (("indexing", spec.indexing), ("retrieval", spec.retrieval)):
                allowed = {requirement.interface for requirement in REQUIRES[spec.kind][stage]}
                extras = set(bindings) - allowed
                if extras:
                    raise ValueError(
                        f"Strategy {name} / {stage}: unknown interface bindings: "
                        + ", ".join(sorted(extras))
                    )
        return validate_unified_configuration(config, registry)
    except (ValueError, TypeError, yaml.YAMLError) as exc:
        raise ValueError(f"Invalid unified configuration {path}: {exc}") from exc
