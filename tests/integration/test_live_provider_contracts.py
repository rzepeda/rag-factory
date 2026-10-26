"""Explicitly opt-in behavioral checks for separately configured live adapters.

WARNING: conformance checks write/upsert and change test records.
Configure an isolated test namespace/database, NEVER production data.

Run with, for example:
    RAG_FACTORY_LIVE_INTERFACE=keyword_store \
    RAG_FACTORY_LIVE_FACTORY=my_test_adapter:create_store \
    python -m pytest tests/integration/test_live_provider_contracts.py -m external -v

The import path is an explicitly operator-controlled Python module:function,
not a CLI-evaluated expression. Nothing external is provisioned automatically.
"""
import importlib
import os

import pytest

from rag_factory.testing.provider_contracts import check_provider_contract


pytestmark = [pytest.mark.integration, pytest.mark.external]


def test_explicitly_configured_live_provider_contract():
    interface = os.environ.get("RAG_FACTORY_LIVE_INTERFACE")
    target = os.environ.get("RAG_FACTORY_LIVE_FACTORY")
    if not interface and not target:
        pytest.skip("No opt-in live provider configured")
    if not interface or not target:
        pytest.fail("Both RAG_FACTORY_LIVE_INTERFACE and RAG_FACTORY_LIVE_FACTORY are required")
    if ":" not in target:
        pytest.fail("RAG_FACTORY_LIVE_FACTORY must be importable module:callable")
    module_name, constructor_name = target.split(":", 1)
    if not module_name or not constructor_name or "." in constructor_name:
        pytest.fail("Expected a module and a single top-level constructor function")
    factory = getattr(importlib.import_module(module_name), constructor_name)
    check_provider_contract(interface, factory)
