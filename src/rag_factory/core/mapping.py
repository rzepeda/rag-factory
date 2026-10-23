"""Logical models and external physical bindings; no database side effects."""

from dataclasses import dataclass, field
from typing import Mapping, FrozenSet


@dataclass(frozen=True)
class LogicalEntity:
    """Structure required by a strategy, independent of storage technology."""

    name: str
    required_fields: FrozenSet[str]
    required_relationships: FrozenSet[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.required_fields:
            raise ValueError("Entity name and required fields are mandatory")
        if any(not value.strip() for value in self.required_fields | self.required_relationships):
            raise ValueError("Logical fields and relationships must not be blank")


@dataclass(frozen=True)
class LogicalModel:
    """Logical structures and operations a strategy requires."""

    entities: tuple[LogicalEntity, ...]
    required_operations: FrozenSet[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        names = [entity.name for entity in self.entities]
        if len(names) != len(set(names)):
            raise ValueError("Logical entity names must be unique")
        if any(not operation.strip() for operation in self.required_operations):
            raise ValueError("Required operation names must not be blank")


@dataclass(frozen=True)
class EntityMapping:
    """Configured physical resource and logical-to-physical names."""

    resource: str
    fields: Mapping[str, str] = field(default_factory=dict)
    relationships: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.resource.strip():
            raise ValueError("Physical resource name must not be empty")


@dataclass(frozen=True)
class StorageMapping:
    """Bindings supplied by one configured storage-service instance.

    Operations describe capabilities supported by the mapping/provider pair;
    provider-specific schema and query validation still belongs to the adapter.
    """

    entities: Mapping[str, EntityMapping]
    operations: FrozenSet[str] = field(default_factory=frozenset)


def validate_entity_mapping(entity: LogicalEntity, mapping: EntityMapping) -> None:
    """Validate declarative coverage, not actual database schema existence."""
    missing_fields = entity.required_fields.difference(mapping.fields)
    missing_relations = entity.required_relationships.difference(mapping.relationships)
    if missing_fields:
        raise ValueError(
            f"{entity.name}: missing mappings for {', '.join(sorted(missing_fields))}"
        )
    if missing_relations:
        raise ValueError(
            f"{entity.name}: missing relationships {', '.join(sorted(missing_relations))}"
        )
    values = list(mapping.fields.items()) + list(mapping.relationships.items())
    if any(not isinstance(key, str) or not isinstance(value, str)
           or not key.strip() or not value.strip() for key, value in values):
        raise ValueError(f"{entity.name}: mapped names must be nonempty strings")


def validate_storage_mapping(model: LogicalModel, mapping: StorageMapping) -> None:
    """Validate entity and operation coverage before provider-level checks."""
    for entity in model.entities:
        if entity.name not in mapping.entities:
            raise ValueError(f"Missing physical mapping for entity {entity.name}")
        validate_entity_mapping(entity, mapping.entities[entity.name])
    missing_ops = model.required_operations.difference(mapping.operations)
    if missing_ops:
        raise ValueError(f"Missing storage operations: {', '.join(sorted(missing_ops))}")

def validate_operational_support(
    model: LogicalModel, mapping: StorageMapping, provider_operations: FrozenSet[str]
) -> None:
    """Require declared mapping coverage and actual adapter-advertised operations.

    This is metadata validation only; it does not introspect a physical database.
    """
    validate_storage_mapping(model, mapping)
    unsupported = model.required_operations.difference(provider_operations)
    if unsupported:
        raise ValueError(
            "Provider does not support storage operations: "
            + ", ".join(sorted(unsupported))
        )
