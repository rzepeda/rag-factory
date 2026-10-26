"""P2 CLI acceptance: validation, ephemeral indexing, retrieval, and evaluation."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from rag_factory.cli.main import main
from rag_factory.evaluation.experiment import ExperimentRun
from rag_factory.factory.service_registry import ServiceConfig, ServiceRegistry
from rag_factory.core.service_contracts import ProviderDescriptor


ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "examples" / "offline_cli.yaml"
PAYLOADS = ROOT / "examples" / "evaluation" / "offline_payloads.v1.json"
DATASET = ROOT / "examples" / "evaluation" / "animals.v1.json"
EXPERIMENT = ROOT / "examples" / "evaluation" / "cli_experiment.v1.json"


def call_cli(capsys, command, *args):
    result = main([command, "--config", str(CONFIG), *args])
    captured = capsys.readouterr()
    return result, captured


def test_validate_does_not_start_providers(capsys):
    status, io = call_cli(capsys, "validate")
    assert status == 0 and io.err == ""
    assert json.loads(io.out) == {
        "status": "valid",
        "services": ["store", "tokens"],
        "strategies": {"lexical": "keyword"},
    }


def test_index_retrieve_evaluate_with_real_command_entrypoint(tmp_path):
    def run(*args):
        return subprocess.run(
            [sys.executable, "-m", "rag_factory.cli.main", *args],
            cwd=ROOT, text=True, capture_output=True,
        )

    base = ["--config", str(CONFIG)]
    indexed = run("index", *base, "--payloads", str(PAYLOADS),
                  "--bundle", str(tmp_path / "artifacts.bundle.json"))
    assert indexed.returncode == 0, indexed.stderr
    data = json.loads(indexed.stdout)
    assert data["ephemeral"] is True
    assert data["artifacts"] == {"lexical": "lexical-index"}
    assert (tmp_path / "artifacts.bundle.json").is_file()

    retrieved = run("retrieve", *base, "--payloads", str(PAYLOADS),
                    "--strategy", "lexical", "--query", "cats", "--limit", "1")
    assert retrieved.returncode == 0, retrieved.stderr
    assert json.loads(retrieved.stdout)["hits"] == [
        {"document_id": "cat-document", "text": None},
    ]

    report = tmp_path / "report.json"
    evaluated = run("evaluate", *base, "--payloads", str(PAYLOADS),
                    "--dataset", str(DATASET), "--experiment", str(EXPERIMENT),
                    "--output", str(report))
    assert evaluated.returncode == 0, evaluated.stderr
    assert json.loads(evaluated.stdout)["results"][0]["strategy"] == "lexical"
    result = ExperimentRun.load(report)
    assert result.config.code_revision == "offline-baseline-v1"
    initial = report.read_bytes()
    again = run("evaluate", *base, "--payloads", str(PAYLOADS),
                "--dataset", str(DATASET), "--experiment", str(EXPERIMENT),
                "--output", str(report))
    assert again.returncode == 0, again.stderr
    assert report.read_bytes() == initial


def test_validate_reports_invalid_reference_without_instantiating(capsys, tmp_path):
    config = tmp_path / "bad.yaml"
    config.write_text("""
services:
  store: {interface: keyword_store, implementation: memory}
strategies:
  broken: {kind: hybrid, parameters: {sources: [unknown]}}
""")
    status = main(["validate", "--config", str(config)])
    io = capsys.readouterr()
    assert status == 2 and io.out == ""
    assert "invalid source reference" in io.err


def test_validate_never_constructs_configured_provider(capsys, tmp_path, monkeypatch):
    import importlib
    module = importlib.import_module("rag_factory.cli.main")
    class ExplodingStore:
        def __init__(self):
            raise RuntimeError("provider must not be constructed")
    registry = ServiceRegistry()
    registry.register(
        ProviderDescriptor("keyword_store", "exploding", frozenset({"upsert", "search"})),
        ExplodingStore,
    )
    registry.register(
        ProviderDescriptor("tokenizer", "exploding", frozenset({"tokenize"})),
        ExplodingStore,
    )
    monkeypatch.setattr(module, "default_registry", lambda: registry)
    config = tmp_path / "no-start.yaml"
    config.write_text("""
services:
  store: {interface: keyword_store, implementation: exploding}
  tokens: {interface: tokenizer, implementation: exploding}
strategies:
  lexical:
    kind: keyword
    indexing: {keyword_store: store}
    retrieval: {keyword_store: store, tokenizer: tokens}
""")
    assert main(["validate", "--config", str(config)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "valid"


@pytest.mark.parametrize("name,data,error", [
    ("bad-version", {"format_version": 2, "indexes": {"lexical": {"documents": {"a": "cat"}}}}, "format_version"),
    ("unknown-index", {"format_version": 1, "indexes": {"other": {"documents": {"a": "cat"}}}}, "Unknown index"),
    ("bad-docs", {"format_version": 1, "indexes": {"lexical": {"documents": {}}}}, "documents"),
])
def test_bad_payloads_fail_without_success_output(capsys, tmp_path, name, data, error):
    source = tmp_path / (name + ".json")
    source.write_text(json.dumps(data))
    status, io = call_cli(capsys, "index", "--payloads", str(source))
    assert status == 2 and io.out == ""
    assert error in io.err


def test_bad_command_limit_and_unknown_strategy(capsys):
    common = ("--payloads", str(PAYLOADS), "--strategy", "lexical",
              "--query", "cat", "--limit", "0")
    status, io = call_cli(capsys, "retrieve", *common)
    assert status == 2 and "positive integer" in io.err

    status, io = call_cli(
        capsys, "retrieve", "--payloads", str(PAYLOADS),
        "--strategy", "no-such-strategy", "--query", "cat",
    )
    assert status == 2 and "Unknown retrieval strategy" in io.err


@pytest.mark.parametrize("yaml_text, message", [
    ("""
services: {}
strategies: {hybrid: {kind: hybrid, parameters: {sources: [missing]}}}
unexpected: value
""", "Unknown top-level"),
    ("""
services:
  store: {interface: keyword_store, implementation: memory, implmentation: typo}
strategies: {key: {kind: keyword}}
""", "Service store: unknown fields"),
    ("""
services: {}
strategies:
  key: {kind: keyword, retrievel: {keyword_store: store}}
""", "Strategy key: unknown fields"),
    ("""
services:
  store: {interface: keyword_store, implementation: memory}
  tok: {interface: tokenizer, implementation: regex}
strategies:
  key:
    kind: keyword
    indexing: {keyword_store: store, embedding: store}
    retrieval: {keyword_store: store, tokenizer: tok}
""", "key / indexing: unknown interface bindings"),
])
def test_strict_yaml_field_diagnostics_include_path(tmp_path, capsys, yaml_text, message):
    file = tmp_path / "bad.yaml"
    file.write_text(yaml_text)
    status = main(["validate", "--config", str(file)])
    io = capsys.readouterr()
    assert status == 2 and io.out == ""
    assert str(file) in io.err
    assert message in io.err
