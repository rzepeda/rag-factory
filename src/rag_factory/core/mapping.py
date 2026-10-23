"""Logical data contracts and declarative physical storage bindings.

Mapping validation here checks field coverage only; a provider must separately
validate its own schema, data types, operations, and index support.
"""

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class LogicalEntity:
    name: str
    required_fields: frozenset[str]

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.required_fields:
            raise ValueError("Entity name and required fields are mandatory")


@dataclass(frozen=True)
class EntityMapping:
    """Physical resource and logical-field -> physical-field mapping."""

    resource: str
    fields: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.resource.strip():
            raise ValueError("Physical resource name must not be empty")


def validate_entity_mapping(entity: LogicalEntity, mapping: EntityMapping) -> None:
    """Fail if the configured physical mapping omits a required logical field."""
    missing = entity.required_fields.difference(mapping.fields)
    if missing:
        raise ValueError(
            f"{entity.name}: missing mappings for {', '.join(sorted(missing))}"
        )
    invalid = [
        field_name for field_name, column in mapping.fields.items()
        if not field_name.strip() or not column.strip()
    ]
    if invalid:
        raise ValueError(f"{entity.name}: mapped field names must not be empty")
