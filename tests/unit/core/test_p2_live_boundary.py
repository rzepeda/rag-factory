"""Core CI verifies live tests are opt-in without touching real services."""
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
LIVE_SUITE = "tests/integration/test_live_provider_contracts.py"


def run_live_suite(env):
    return subprocess.run(
        [sys.executable, "-m", "pytest", LIVE_SUITE, "-q"],
        cwd=ROOT, text=True, capture_output=True, env=env,
    )


def test_live_provider_suite_skips_without_explicit_configuration():
    env = dict(os.environ)
    env.pop("RAG_FACTORY_LIVE_INTERFACE", None)
    env.pop("RAG_FACTORY_LIVE_FACTORY", None)
    result = run_live_suite(env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 skipped" in result.stdout


def test_opted_in_suite_can_use_offline_mock_factory():
    env = dict(os.environ)
    env["RAG_FACTORY_LIVE_INTERFACE"] = "keyword_store"
    env["RAG_FACTORY_LIVE_FACTORY"] = "tests.mocks.services:MockKeywordStore"
    result = run_live_suite(env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed" in result.stdout
